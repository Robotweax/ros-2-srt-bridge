import ctypes
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'evidence/m3-bridge-shutdown-preparation-2026-11-10'
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(HERE))


def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class PreparationTests(unittest.TestCase):
    def test_scope_bound_authorization_and_no_broader_grant(self):
        m=load('bridge_diagnostic_run','run.py')
        good=dict(scope=m.SCOPE,freeze_sha256='abc',execute=True,remaining_campaign_cases_disabled=29,retry_two_loss_4211=False,no_tuning=True)
        m.authorize(good,'abc')
        for altered in (dict(good,execute=False),dict(good,retry_two_loss_4211=True),dict(good,remaining_campaign_cases_disabled=0),dict(good,extra_case=True),dict(good,freeze_sha256='other')):
            with self.assertRaises(ValueError):m.authorize(altered,'abc')
    def test_workload_rejects_other_seed_duration_loss_and_missing_capture(self):
        m=load('bridge_diagnostic_workload','workload.py')
        fixed=dict(capture=True,losses=0,seed=1701,seconds=10,runtime_layout='shutdown-tracing',shutdown_diagnostics=True,shutdown_stacks=False,shutdown_stack_mode='procfs',bundle=Path('/unused'),prefix='unused')
        for delta in (dict(seed=4211),dict(seed=2903),dict(losses=1),dict(losses=2),dict(seconds=30),dict(capture=False),dict(shutdown_stacks=True),dict(shutdown_diagnostics=False)):
            with patch.object(m,'matched',side_effect=AssertionError('must refuse before build/Docker access')),self.assertRaises(ValueError):m.run(Path('/unused'),**dict(fixed,**delta))
    def test_missing_authorization_refuses_before_docker(self):
        m=load('bridge_diagnostic_missing_authorization','run.py')
        with patch.object(m.sys,'argv',['run.py']),patch.object(m.subprocess,'check_output',side_effect=AssertionError('Docker must not run')),self.assertRaises(SystemExit):m.main()
    def test_capability_reduction_order_and_errno_fail_closed(self):
        m=load('bridge_diagnostic_exec','bridge_exec.py');events=[]
        class Lib:
            class Capset:
                def __call__(self,*args):events.append(('capset',));return 0
            capset=Capset()
            def prctl(self,op,*args):events.append(('prctl',op));return 0
        m.reduce(Lib(),3)
        self.assertEqual(events,[('prctl',24)]*4+[('capset',),('prctl',38),('prctl',4)])
        class Bad(Lib):
            def prctl(self,*args):ctypes.set_errno(1);return -1
        with self.assertRaises(OSError) as e:m.reduce(Bad(),3)
        self.assertEqual(e.exception.errno,1)
    def test_observer_wait_failure_still_exports_and_removes_owned_resources(self):
        import tempfile
        import types
        m=load('bridge_diagnostic_sidecar_cleanup','sidecar.py')
        with tempfile.TemporaryDirectory() as folder:
            sidecar=m.Sidecar(Path(folder),Path('/unused'),'owned');sidecar.created=sidecar.volume_created=sidecar.started=True
            calls=[]
            def command(argv,**kwargs):
                calls.append(argv)
                if argv[:2]==['docker','wait']:raise TimeoutError('wait failed')
                if argv[:2]==['docker','inspect']:return types.SimpleNamespace(returncode=0,stdout=json.dumps([dict(State=dict(Running=True))]))
                return types.SimpleNamespace(returncode=0,stdout='')
            sidecar.command=command
            with self.assertRaises(ValueError):sidecar.close()
            self.assertTrue(any(x[:2]==['docker','kill'] for x in calls))
            self.assertTrue(any(x[:2]==['docker','cp'] and x[2].endswith('/out/.') for x in calls))
            self.assertIn(['docker','rm','-f','owned-observer'],calls)
            self.assertIn(['docker','volume','rm','owned-observer-output'],calls)
            self.assertFalse(sidecar.created or sidecar.volume_created)
    def fixture(self,forced=False):
        child=dict(pid=7,signal_end_ns=100,end_ns=200,forced_kill=forced)
        row=dict(kind='sample',begin_ns=80,end_ns=90,process_limit_hit=False,processes=[dict(status='sampled',identity_still_matches=True,threads_truncated=False,threads=[dict(kernel_stack=dict(status='ok',truncated=False,text='futex_do_wait'))])])
        return child,[dict(kind='begin',mode='procfs',observer_independent=True,root=dict(pid=7),pid=9),row,dict(kind='status',completed=True,budget_exhausted=False)]
    def test_fast_clean_exit_does_not_require_post_signal_sample(self):
        m=load('bridge_diagnostic_assess','assess.py');child,rows=self.fixture()
        self.assertEqual(m.coverage(rows,child)['post_signal_samples'],0)
        rows[1]['processes'][0]['threads'][0]['kernel_stack']=dict(status='unavailable',errno=13)
        with self.assertRaises(ValueError):m.coverage(rows,child)
    def test_hang_requires_real_post_signal_stack_coverage(self):
        m=load('bridge_diagnostic_hang','assess.py');child,rows=self.fixture(True)
        with self.assertRaises(ValueError):m.coverage(rows,child)
        import copy
        for begin,end in ((110,120),(140,150)):
            sample=copy.deepcopy(rows[1]);sample.update(begin_ns=begin,end_ns=end);rows.insert(-1,sample)
        self.assertEqual(m.coverage(rows,child)['post_signal_samples'],2)

if __name__=='__main__':unittest.main()
