import ast
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ros2/robotweax_srt_bridge_demo/scripts'))
import shutdown_observer as observer
from scenario_processes import stop_children


def fake_process(root,pid,start,children=''):
    proc=root/str(pid);task=proc/'task'/str(pid);task.mkdir(parents=True)
    fields=['0']*30;fields[0]='S';fields[19]=str(start)
    raw=str(pid)+' (owned child) '+' '.join(fields)
    (proc/'stat').write_text(raw)
    for name,value in [('stat',raw),('wchan','futex_wait_queue'),('stack','[<0>] futex_wait\n'),('syscall','202 0 0'),('children',children)]: (task/name).write_text(value)


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.proc=self.root/'proc';self.proc.mkdir();fake_process(self.proc,101,700,'102');fake_process(self.proc,102,701)
    def test_only_registered_tree_is_read_with_start_identity(self):
        fake_process(self.proc,999,900)
        known={(101,700):dict(pid=101,start_ticks=700)};result=observer.collect(self.proc,known)
        self.assertEqual({p['identity']['pid'] for p in result['processes']},{101,102});self.assertEqual(len(known),2)
        self.assertIn('futex_wait',result['processes'][0]['threads'][0]['kernel_stack']['text'])
    def test_pid_reuse_is_not_a_valid_stack_target(self):
        result=observer.collect(self.proc,{(101,999):dict(pid=101,start_ticks=999)})
        self.assertEqual(result['processes'][0]['status'],'gone_or_reused')
        with patch.object(observer.subprocess,'Popen') as launch:r=observer.gdb_stack(self.proc,dict(pid=101,start_ticks=999))
        launch.assert_not_called();self.assertEqual(r['status'],'gone_or_reused')
    def test_denied_or_missing_stacks_remain_unavailable_not_empty_success(self):
        (self.proc/'101/task/101/stack').unlink();r=observer.collect(self.proc,{(101,700):dict(pid=101,start_ticks=700)})
        self.assertEqual(r['processes'][0]['threads'][0]['kernel_stack']['status'],'unavailable')
        (self.root/'large').write_bytes(b'a'*100)
        self.assertTrue(observer.read_limited(self.root/'large',5)['truncated'])
    def test_observer_loop_runs_without_parent_spin_and_has_footer(self):
        output=self.root/'observed.jsonl';ready=self.root/'ready';stop=self.root/'stop'
        with patch.object(observer.time,'sleep',side_effect=lambda _:stop.touch()):observer.observe(101,700,output,ready,stop,'procfs',self.proc)
        rows=[json.loads(x) for x in output.read_text().splitlines()]
        self.assertTrue(ready.exists());self.assertEqual(rows[1]['kind'],'sample');self.assertTrue(rows[-1]['completed']);self.assertFalse(rows[-1]['userspace_stacks_requested']);self.assertGreater(rows[-1]['kernel_stack_reads_ok'],0)
    def test_sample_budget_exhaustion_is_explicit(self):
        with patch.object(observer,'MAX_SAMPLES',1),patch.object(observer.time,'sleep'):observer.observe(101,700,self.root/'o',self.root/'r',self.root/'s','procfs',self.proc)
        footer=json.loads((self.root/'o').read_text().splitlines()[-1]);self.assertTrue(footer['budget_exhausted'])
    def test_missing_gdb_is_explicit_no_install_or_fallback(self):
        with patch.object(observer.subprocess,'Popen',side_effect=FileNotFoundError(2,'missing')):r=observer.gdb_stack(self.proc,dict(pid=101,start_ticks=700))
        self.assertEqual(r['status'],'unavailable');self.assertTrue(r['intrusive'])
    def test_gdb_timeout_targets_debugger_and_never_claims_resume(self):
        class Debugger:
            returncode=-9
            def __init__(self):self.calls=0;self.signals=[];self.killed=False
            def wait(self,timeout):
                self.calls+=1
                if self.calls<=2:raise subprocess.TimeoutExpired('gdb',timeout)
            def send_signal(self,value):self.signals.append(value)
            def kill(self):self.killed=True
        child=Debugger()
        with patch.object(observer.subprocess,'Popen',return_value=child):r=observer.gdb_stack(self.proc,dict(pid=101,start_ticks=700))
        self.assertEqual(child.signals,[signal.SIGINT]);self.assertTrue(child.killed);self.assertTrue(r['timed_out']);self.assertFalse(r['resume_verified']);self.assertNotEqual(r['status'],'captured')
    def test_default_shutdown_never_starts_observer_and_wait_is_unchanged(self):
        class Child:
            pid=101
            def __init__(self):self.code=None;self.timeouts=[]
            def poll(self):return self.code
            def send_signal(self,value):self.signal=value
            def wait(self,timeout):self.timeouts.append(timeout);self.code=0
        child=Child()
        with patch.object(observer,'Observer') as start:r=stop_children([(child,'bridge',io.StringIO())])
        start.assert_not_called();self.assertEqual(child.timeouts,[5]);self.assertTrue(r['passed'])
    def test_observer_is_armed_before_sigint_and_closed_after_child_wait(self):
        events=[]
        class Watch:
            armed=True
            def __init__(self,*args):events.append('observer_armed')
            def close(self):events.append('observer_closed');return dict(complete=True)
        class Child:
            pid=101;code=None
            def poll(self):return self.code
            def send_signal(self,_):events.append('SIGINT')
            def wait(self,timeout):events.append('child_wait');self.code=0
        with patch.object(observer,'Observer',Watch):r=stop_children([(Child(),'bridge',io.StringIO())],observer_directory=self.root)
        self.assertEqual(events,['observer_armed','SIGINT','child_wait','observer_closed']);self.assertTrue(r['passed']);self.assertTrue(r['children'][0]['stack_observer']['complete'])
    def test_process_budget_does_not_scan_unowned_pids(self):
        (self.proc/'102/task/102/children').write_text('103');fake_process(self.proc,103,702,'104');fake_process(self.proc,104,703)
        with patch.object(observer,'MAX_PROCESSES',3):
            known={(101,700):dict(pid=101,start_ticks=700)};result=observer.collect(self.proc,known)
        self.assertEqual(len(known),3);self.assertTrue(result['process_limit_hit']);self.assertNotIn(104,[p['identity']['pid'] for p in result['processes']])
    def test_observer_refuses_stale_root_before_output(self):
        with self.assertRaises(ValueError):observer.observe(101,999,self.root/'o',self.root/'r',self.root/'s','procfs',self.proc)
        self.assertFalse((self.root/'o').exists())
    def test_thread_budget_is_explicit_and_gdb_refuses_over_budget(self):
        extra=self.proc/'101/task/103';extra.mkdir()
        for p in (self.proc/'101/task/101').iterdir():(extra/p.name).write_bytes(p.read_bytes())
        with patch.object(observer,'MAX_THREADS',1),patch.object(observer.subprocess,'Popen') as launch:
            result=observer.collect(self.proc,{(101,700):dict(pid=101,start_ticks=700)})
            self.assertTrue(result['processes'][0]['threads_truncated']);r=observer.gdb_stack(self.proc,dict(pid=101,start_ticks=700))
        launch.assert_not_called();self.assertEqual(r['status'],'thread_budget_exceeded')
    def test_failed_observer_start_does_not_prevent_child_cleanup(self):
        class Child:
            pid=101;code=None
            def poll(self):return self.code
            def send_signal(self,value):self.sent=value
            def wait(self,timeout):self.code=0
        child=Child()
        with patch.object(observer,'Observer',side_effect=RuntimeError('observer unavailable')):
            r=stop_children([(child,'bridge',io.StringIO())],observer_directory=self.root)
        self.assertEqual(child.sent,signal.SIGINT);self.assertEqual(child.code,0);self.assertIn('unavailable',r['children'][0]['stack_observer_error'])
    def test_observer_owns_separate_session_and_missing_footer_is_not_complete(self):
        prefix=self.root/'bridge-stacks'
        class Child:
            pid=777;returncode=0
            def wait(self,timeout):return 0
        def start(*args,**kwargs):
            self.assertTrue(kwargs['start_new_session']);prefix.with_suffix('.ready.json').write_text('{}');return Child()
        with patch.object(observer,'identity',return_value=dict(pid=101,start_ticks=700)),patch.object(observer.subprocess,'Popen',side_effect=start),patch.object(observer.os,'killpg',side_effect=ProcessLookupError) as killgroup:
            watch=observer.Observer(101,prefix);r=watch.close()
        self.assertEqual(killgroup.call_args.args,(777,signal.SIGKILL));self.assertFalse(r['complete'])
    def test_forced_observer_cleanup_targets_own_group_and_fails_diagnostics(self):
        watch=observer.Observer.__new__(observer.Observer);watch.prefix=self.root/'x';watch.stop=self.root/'stop';watch.output=self.root/'x.jsonl';watch.log=io.StringIO();watch.armed=True
        watch.output.write_text(json.dumps(dict(kind='status',completed=True,budget_exhausted=False))+'\n')
        class Child:
            pid=777;returncode=-9
            def __init__(self):self.n=0
            def wait(self,timeout):
                self.n+=1
                if self.n==1:raise subprocess.TimeoutExpired('observer',timeout)
        watch.process=Child()
        with patch.object(observer.os,'killpg',side_effect=[None,ProcessLookupError]) as killgroup:r=watch.close()
        self.assertEqual(killgroup.call_args_list[0].args,(777,signal.SIGKILL));self.assertFalse(r['complete']);self.assertTrue(r['forced_kill']);self.assertTrue(watch.log.closed)
    def test_gdb_is_not_in_default_multiroute_invocation(self):
        sys.path.insert(0,str(ROOT/'tools'))
        from m3_campaign_dispatcher import invocation,slots
        for s in slots()[:9]:
            self.assertFalse(invocation(s)['kwargs'].get('shutdown_stacks',False));self.assertFalse(invocation(s)['kwargs'].get('shutdown_diagnostics',False))
        source=(ROOT/'ros2/robotweax_srt_bridge/src/bridge_node.cpp').read_text();self.assertIn('declare_parameter<bool>("shutdown_diagnostics",false)',source)
        ast.parse((ROOT/'tools/m3_ros_multiroute.py').read_text())

if __name__=='__main__':unittest.main()
