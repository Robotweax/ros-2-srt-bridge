"""Offline calibration contracts and full mocked Docker orchestration."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from model import ROOT,HERE,fixture,DockerModel,perms,write
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
import run,assess,plan
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.data,self.rows,self.context=fixture(self.root)
    def grant(self,digest='new'):
        return dict(scope=plan.SCOPE,freeze_sha256=digest,execute=True,candidate_collector_sha256=plan.CANDIDATE_SHA,readiness_checks=1,controlled_target_limit=1,task_visibility=True,disabled_case_ids=plan.disabled_ids(),remaining_case_ids_disabled=plan.remaining_ids(),N1_2903_rerun=False,historical_failure_preserved=True,no_tuning=True,no_retries=True,stop_first_failed_gate=True)
    def test_exact_grant_excludes_all_campaigns_and_failed_case(self):
        g=self.grant();plan.authorize(g,'new');self.assertEqual(len(g['disabled_case_ids']),38);self.assertEqual(len(g['remaining_case_ids_disabled']),7)
        for delta in (dict(scope='N1'),dict(freeze_sha256='old'),dict(execute=False),dict(candidate_collector_sha256='old'),dict(readiness_checks=2),dict(controlled_target_limit=2),dict(task_visibility=False),dict(disabled_case_ids=[]),dict(remaining_case_ids_disabled=[]),dict(N1_2903_rerun=True),dict(no_tuning=False),dict(no_retries=False),dict(stop_first_failed_gate=False),dict(extra=True)):
            with self.subTest(delta=delta),self.assertRaises(ValueError):plan.authorize(dict(g,**delta),'new')
    def test_old_campaign_grants_not_accepted(self):
        for name in ('m3-current-long-execution-2026-11-10','m3-current-n4-corrected-execution-2026-11-10'):
            g=json.loads((ROOT/'evidence'/name/'authorization.json').read_text())
            with self.assertRaises(ValueError):plan.authorize(g,'new')
    def test_missing_grant_never_calls_Docker(self):
        with patch.object(run.sys,'argv',['run.py']),patch.object(run.subprocess,'run',side_effect=AssertionError('no Docker')),self.assertRaises(SystemExit):run.main()
    def test_one_shot_output_refuses_resume(self):
        with self.assertRaises(ValueError):run.fresh_output(self.root)
    def test_first_stage_failure_never_calls_target(self):
        seen=[]
        def failed():seen.append('ready');raise ValueError('readiness failed')
        r=run.sequence(failed,lambda:seen.append('target'),lambda r:None);self.assertEqual(seen,['ready']);self.assertEqual([x['status'] for x in r['rows']],['failed','not_executed'])
    def test_second_stage_failure_has_no_retry(self):
        seen=[]
        def failed():seen.append('target');raise ValueError('target failed')
        r=run.sequence(lambda:seen.append('ready'),failed,lambda r:None);self.assertEqual(seen,['ready','target']);self.assertEqual([x['status'] for x in r['rows']],['passed','failed'])
    def test_assessor_uses_real_candidate_records_from_temp_procfs(self):
        result=assess.assess(self.data);self.assertEqual(result['status'],'passed');self.assertEqual(result['live_task']['samples'],2);self.assertEqual(result['controlled_absence']['kind'],'not_in_complete_enumeration');self.assertFalse(result['candidate_confirmed_exit'])
    def test_mutated_task_schema_access_identity_times_refused(self):
        for mutation in ('schema','tid','timestamp','confirmed_exit','denied','truncated','footer','root','boot','clock','activation','stages','forced'):
            with self.subTest(mutation=mutation):
                rows=copy.deepcopy(self.rows);other=None
                if mutation=='schema':rows[1]['processes'][0]['threads'][0]['task_evidence']['schema_version']=0
                if mutation=='tid':rows[0]['root']['start_ticks']=999
                if mutation=='timestamp':rows[1]['processes'][0]['threads'][0]['task_evidence']['reads']['stack']['begin_ns']=1
                if mutation=='confirmed_exit':rows[3]['processes'][0]['prior_tasks_not_listed'][0]['confirmed_exit']=True
                if mutation=='denied':rows[1]['processes'][0]['threads'][0]['task_evidence']['reads']['stack']['result']=dict(status='unavailable',errno=13)
                if mutation=='truncated':rows[1]['processes'][0]['threads_truncated']=True
                if mutation=='footer':rows[-1]['kernel_stack_reads_ok']+=1
                if mutation=='root':rows[0]['root']['pid']=999
                if mutation=='boot':rows[0]['boot_id']['text']='foreign'
                if mutation=='clock':rows[0]['clock']='wall'
                if mutation=='activation':rows[0]['task_visibility_schema_version']=0
                if mutation=='stages':
                    f=self.data/'task-stages.jsonl';other=(f,f.read_text());f.write_text('\n'.join(reversed(f.read_text().splitlines()))+'\n')
                if mutation=='forced':
                    f=self.data/'result.json';other=(f,f.read_text());r=json.loads(f.read_text());r['shutdown']['children'][0]['forced_kill']=True;write(f,r)
                (self.data/'blocked-target-shutdown-stacks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
                with self.assertRaises((ValueError,KeyError)):assess.assess(self.data)
                if other:other[0].write_text(other[1])
        (self.data/'blocked-target-shutdown-stacks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in self.rows))
    def test_insufficient_present_or_absence_population_refused(self):
        with self.assertRaisesRegex(ValueError,'two live'):assess.presence(self.rows[:2],self.context)
        joined=json.loads((self.data/'worker-joined.json').read_text())
        with self.assertRaisesRegex(ValueError,'absence evidence'):assess.absence(self.rows[:3],self.context,joined)
        with self.assertRaisesRegex(ValueError,'join context'):assess.absence(self.rows,self.context,dict(joined,worker_tid=999))
    def test_snapshot_ignores_only_incomplete_last_line(self):
        text='{"kind":"begin"}\n{"partial"';self.assertEqual(assess.snapshot(text),[dict(kind='begin')])
        with self.assertRaises(ValueError):assess.snapshot('not-json\n')
    def full_driver(self,ready_failure=False,bad_header=False,foreign_pid=False):
        prepared=self.root/'prepared';prepared.mkdir();(self.root/'.local').mkdir();docker=self.root/'docker';docker.mkdir()
        f=dict(execution_enabled=False,authorization_supplied=False,readiness_checks=1,controlled_target_limit=1,disabled_case_ids=plan.disabled_ids(),remaining_case_ids_disabled=plan.remaining_ids(),output_relative='.local/cal',bundle_relative='bundle',observer_image='native-image',prefix='owned',source_sha256={},inputs_sha256={})
        write(prepared/'freeze.json',f);write(self.root/'grant.json',self.grant(run.sha(prepared/'freeze.json')));shutil.copyfile(HERE/'observer-seccomp.json',prepared/'observer-seccomp.json')
        model=DockerModel(docker,self.data,self.rows,ready_failure,bad_header,foreign_pid)
        with patch.object(run,'ROOT',self.root),patch.object(run,'HERE',prepared),patch.object(run,'verify'),patch.object(run,'source_inventory',return_value={}),patch.object(run.subprocess,'run',side_effect=model.command):result=run.execute(self.root/'grant.json')
        self.assertFalse(model.objects);self.assertFalse(model.volumes);return result,model.calls
    def test_full_mocked_driver_readiness_then_single_fixture_with_cleanup(self):
        result,calls=self.full_driver();self.assertEqual(result['status'],'passed');creates=[c for c in calls if c[1]=='create'];self.assertEqual(len(creates),3)
        target=next(c for c in creates if '/cal/target_entry.py'in c);observer=next(c for c in creates if '--task-visibility'in c)
        self.assertNotIn('--pid',target);self.assertIn('--pid',observer);self.assertIn('--cap-drop',target);self.assertNotIn('SYS_ADMIN',target);self.assertIn('SYS_ADMIN',observer);self.assertTrue(all(c[c.index('--network')+1]=='none' for c in creates));self.assertEqual(len([c for c in calls if c[1]=='start' and c[-1]=='owned-target']),1)
    def test_full_readiness_failure_stops_before_target(self):
        result,calls=self.full_driver(ready_failure=True);self.assertEqual(result['status'],'failed');self.assertFalse(any('/cal/target_entry.py'in c for c in calls));self.assertEqual(result['stages']['rows'][1]['status'],'not_executed')
    def test_full_schema_failure_stops_before_worker_release(self):
        result,calls=self.full_driver(bad_header=True);self.assertEqual(result['status'],'failed');self.assertFalse(any(c[1]=='cp' and c[-1].endswith('/release-worker.json') for c in calls));self.assertEqual(result['stages']['rows'][1]['status'],'failed')
    def test_foreign_PID_namespace_refused_before_observer_start(self):
        result,calls=self.full_driver(foreign_pid=True);self.assertEqual(result['status'],'failed');self.assertFalse(any(c[1]=='start' and c[-1]=='owned-observer' for c in calls))
    def test_fixture_controls_refuse_foreign_identity_and_scope(self):
        target=load('controlled_target','task_target.py');target.bound(self.context,self.context)
        for delta in (dict(target_pid=999),dict(worker_start_ticks=999),dict(calibration_id='N1-combined-2903')):
            with self.assertRaises(ValueError):target.bound(dict(self.context,**delta),self.context)
    def test_actual_fixture_methods_complete_with_temp_procfs_and_mock_signal(self):
        target=load('controlled_fixture_model','task_target.py');out=self.root/'fixture-out';out.mkdir();proc=self.root/'proc';captured={};actual_write=target.write
        # A normal Python unit-test thread executes the real worker function. No
        # live procfs, OS signal, child process, capability or container is used.
        main_ident=threading.get_ident()
        def native_id():return 101 if threading.get_ident()==main_ident else 102
        def signal_handler(sig,handler):captured['handler']=handler;return None
        def save(path,value):
            actual_write(path,value)
            if path.name=='worker-joined.json':captured['handler'](None,None)
        def sleep(seconds):
            ready=out/'fixture-ready.json'
            if ready.exists() and not (out/'release-worker.json').exists():actual_write(out/'release-worker.json',json.loads(ready.read_text()))
        # fixture() removed its modeled worker directory to create absence data.
        worker=proc/'101/task/102';worker.mkdir()
        from model import stat
        (worker/'stat').write_text(stat(102,701))
        with patch.object(target.os,'getpid',return_value=101),patch.object(target.threading,'get_native_id',side_effect=native_id),patch.object(target.signal,'signal',side_effect=signal_handler),patch.object(target.time,'sleep',side_effect=sleep),patch.object(target,'write',side_effect=save):code=target.main(out,'owned',proc)
        self.assertEqual(code,0);rows=[json.loads(x) for x in (out/'task-stages.jsonl').read_text().splitlines()];self.assertEqual([r['point'] for r in rows],['worker_started','fixture_ready','worker_release','worker_return','worker_joined','fixture_sigint','fixture_exit']);self.assertTrue(json.loads((out/'worker-joined.json').read_text())['joined'])
    def test_collector_and_filter_bytes_exact_bound_candidates(self):
        self.assertEqual(run.sha(HERE/'shutdown_observer.py'),plan.CANDIDATE_SHA);old=ROOT/'evidence/m3-current-long-preparation-2026-11-10';self.assertEqual((HERE/'observer-seccomp.json').read_bytes(),(old/'observer-seccomp.json').read_bytes());self.assertEqual((HERE/'observer-architecture.json').read_bytes(),(old/'observer-architecture.json').read_bytes())
    def test_fresh_interpreter_bundle_imports_exact_collector_and_wrappers(self):
        bundle=self.root/'import-bundle';bundle.mkdir()
        for name in ('shutdown_observer.py','observer_entry.py','target_entry.py','task_target.py'):shutil.copyfile(HERE/name,bundle/name)
        shutil.copyfile(ROOT/'tools/m3_observer_filtering.py',bundle/'m3_observer_filtering.py');shutil.copyfile(ROOT/'ros2/robotweax_srt_bridge_demo/scripts/scenario_processes.py',bundle/'scenario_processes.py')
        code="import sys;sys.path.insert(0,sys.argv[1]);import shutdown_observer,observer_entry,target_entry,task_target;from pathlib import Path;import hashlib;print(*(str(Path(m.__file__).resolve()) for m in (shutdown_observer,observer_entry,target_entry,task_target)),sep='\\n');print(hashlib.sha256(Path(shutdown_observer.__file__).read_bytes()).hexdigest())"
        lines=subprocess.check_output([sys.executable,'-c',code,str(bundle)],text=True).splitlines();self.assertEqual(lines,[str((bundle/name).resolve()) for name in ('shutdown_observer.py','observer_entry.py','target_entry.py','task_target.py')]+[plan.CANDIDATE_SHA])
    def test_actual_host_import_order_ignores_cached_ROS_collector(self):
        code="import sys,importlib.util;from pathlib import Path;spec=importlib.util.spec_from_file_location('shutdown_observer',sys.argv[2]);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);sys.modules['shutdown_observer']=old;sys.path.insert(0,sys.argv[1]);import run;import assess;print(Path(assess._collector.__file__).resolve());print(assess.task_identity.__module__);print(sys.modules['shutdown_observer'] is old)"
        lines=subprocess.check_output([sys.executable,'-c',code,str(HERE),str(ROOT/'ros2/robotweax_srt_bridge_demo/scripts/shutdown_observer.py')],text=True).splitlines();self.assertEqual(lines,[str(HERE/'shutdown_observer.py'),'_robotweax_task_visibility_calibration_v1','True'])
        wrong=self.root/'wrong-collector.py';wrong.write_text("raise AssertionError('must never execute')\n")
        with self.assertRaisesRegex(ValueError,'bound calibration collector differs'):assess.bound_collector(wrong)
    def entry(self,args,stale=False):
        m=load('calibration_entry_model','observer_entry.py');cal=self.root/'cal';cal.mkdir();out=self.root/'entry-out';out.mkdir()
        for name in ('observer-seccomp.json','observer-architecture.json','shutdown_observer.py'):shutil.copyfile(HERE/name,cal/name)
        if stale:(cal/'shutdown_observer.py').write_text('wrong collector')
        write(cal/'collector-binding.json',dict(sha256=plan.CANDIDATE_SHA,task_visibility=True));write(out/'target-info.json',dict(pid=101,start_ticks=700))
        def path(value):
            if str(value)=='/cal':return cal
            if str(value)=='/proc/sys/kernel/random/boot_id':return type('Text',(),dict(read_text=lambda s:'model-boot'))()
            if str(value)=='/proc/self/timens_offsets':return type('Text',(),dict(read_text=lambda s:'monotonic 0 0\nboottime 0 0\n'))()
            return Path(value)
        import shutdown_observer
        with patch.object(m,'OUT',out),patch.object(m,'Path',side_effect=path),patch.object(m.os,'umask'),patch.object(m.platform,'machine',return_value='aarch64'),patch.object(m,'status',return_value=perms(1<<21)),patch.object(shutdown_observer,'same_identity',return_value=True),patch.object(m.os,'execv',side_effect=RuntimeError('modeled exec boundary')) as execute,patch.object(m.sys,'argv',['entry.py',*args]):code=m.main()
        return code,execute.call_args
    def test_native_entry_forwards_explicit_flag_and_bound_collector(self):
        code,call=self.entry(['--task-visibility']);self.assertEqual(code,125);self.assertIsNotNone(call);self.assertEqual(call.args[1][-3:],['--mode','procfs','--task-visibility'])
    def test_native_entry_readiness_imports_without_collector_exec(self):
        code,call=self.entry(['--self-check']);self.assertEqual(code,0);self.assertIsNone(call)
    def test_native_entry_rejects_missing_activation(self):
        code,call=self.entry([]);self.assertEqual(code,125);self.assertIsNone(call)
    def test_native_entry_rejects_stale_collector_before_exec(self):
        code,call=self.entry(['--task-visibility'],stale=True);self.assertEqual(code,125);self.assertIsNone(call)
if __name__=='__main__':unittest.main()
