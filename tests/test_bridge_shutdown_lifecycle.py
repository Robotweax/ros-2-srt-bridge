import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'evidence/m3-bridge-shutdown-lifecycle-2026-11-10'
def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
collector=load('shutdown_lifecycle_collector','shutdown_observer.py')
gates=load('shutdown_lifecycle_gates','lifecycle.py')

class LifecycleTests(unittest.TestCase):
    def test_proc_absence_is_distinct_from_pid_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            proc=Path(folder);expected=dict(pid=9,start_ticks=100)
            self.assertEqual(collector.identity_state(proc,expected)['status'],'process_missing')
            (proc/'9').mkdir();fields=['S','7']+['0']*17+['100']
            (proc/'9/stat').write_text('9 (robotweax-journ) '+' '.join(fields))
            matching=collector.identity_state(proc,expected)
            self.assertEqual(matching['status'],'matching');self.assertEqual(matching['observed']['ppid'],7)
            fields[-1]='101';(proc/'9/stat').write_text('9 (robotweax-journ) '+' '.join(fields))
            self.assertEqual(collector.identity_state(proc,expected)['status'],'pid_reused')
    def test_identity_read_errors_are_never_reported_as_exit(self):
        for error in (PermissionError(13,'denied'),ValueError('malformed stat')):
            with patch.object(collector,'identity',side_effect=error):
                self.assertEqual(collector.identity_state(Path('/unused'),dict(pid=9,start_ticks=100))['status'],'identity_unavailable')
    def fixture(self):
        root=dict(pid=7,start_ticks=70);worker=dict(pid=9,start_ticks=90,ppid=7,name='robotweax-journ')
        def live(identity,at):return dict(identity=identity,status='sampled',identity_still_matches=True,threads_truncated=False,identity_check=dict(status='matching',observed=identity,checked_ns=at),threads=[dict(kernel_stack=dict(status='ok',truncated=False,text='futex'))])
        first=dict(kind='sample',begin_ns=10,end_ns=20,process_limit_hit=False,processes=[live(root,15),live(worker,16)])
        missing=dict(identity=worker,status='process_missing',identity_check=dict(status='process_missing',errno=2,checked_ns=155))
        second=dict(kind='sample',begin_ns=150,end_ns=160,process_limit_hit=False,processes=[live(root,154),missing])
        rows=[dict(kind='begin',mode='procfs',observer_independent=True,root=root,pid=11),first,second,dict(kind='status',completed=True,budget_exhausted=False)]
        child=dict(pid=7,signal_begin_ns=100,signal_end_ns=101,end_ns=300,forced_kill=False)
        stages=[dict(pid=7,tid=8,sequence=i,point=p,monotonic_ns=t,dropped_before=0) for i,p,t in ((1,'worker_join_begin',110),(2,'worker_join_end',120))]
        return rows,child,stages
    def test_registered_worker_exit_after_join_is_confirmed(self):
        rows,child,stages=self.fixture();proof=gates.coverage(rows,child,stages)
        self.assertEqual(proof['confirmed_worker_exits'],[dict(pid=9,start_ticks=90)])
        self.assertEqual(proof['post_signal_samples'],1)
    def test_reuse_and_read_failures_reject_even_after_root_reap(self):
        for state in ('pid_reused','identity_unavailable'):
            rows,child,stages=self.fixture();rows[2].update(begin_ns=350,end_ns=360)
            rows[2]['processes'][1].update(status=state,identity_check=dict(status=state,checked_ns=355))
            rows[2]['processes'][0]['identity_check']['checked_ns']=354
            with self.assertRaises(ValueError):gates.coverage(rows,child,stages)
    def test_missing_join_wrong_worker_and_premature_absence_reject(self):
        for variant in ('no_join','early','wrong_name','wrong_parent','root_missing','stage_drop'):
            rows,child,stages=self.fixture()
            if variant=='no_join':stages=stages[:1]
            if variant=='early':stages[-1]['monotonic_ns']=170
            if variant=='wrong_name':rows[1]['processes'][1]['identity']['name']='unrelated'
            if variant=='wrong_parent':rows[1]['processes'][1]['identity']['ppid']=99
            if variant=='root_missing':rows[2]['processes'][1]['identity']=rows[0]['root']
            if variant=='stage_drop':stages[-1]['dropped_before']=1
            with self.subTest(variant=variant),self.assertRaises(ValueError):gates.coverage(rows,child,stages)
    def test_ambiguous_legacy_status_and_mid_sample_identity_change_reject(self):
        for state in ('gone_or_reused','process_missing'):
            rows,child,stages=self.fixture();p=rows[2]['processes'][1]
            p.update(status='sampled',identity_still_matches=False,threads_truncated=False,threads=[],identity_check=dict(status=state,checked_ns=155))
            with self.subTest(state=state),self.assertRaises(ValueError):gates.coverage(rows,child,stages)

if __name__=='__main__':unittest.main()
