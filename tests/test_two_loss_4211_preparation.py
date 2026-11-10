import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'evidence/m3-two-loss-4211-preparation-2026-11-10'
sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(HERE))
def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class Seed4211PreparationTests(unittest.TestCase):
    def grant(self,m):return dict(scope=m.SCOPE,freeze_sha256='abc',execute=True,seed4211_execution_authorized=True,remaining_campaign_cases_disabled=29,seed4211_diagnostic=True,historical_4211_failure_preserved=True,no_tuning=True)
    def test_exact_seed4211_authorization_needs_explicit_execution_and_preservation(self):
        m=load('seed4211_prepared_grant','run.py');good=self.grant(m)
        self.assertIn('4211-30s',m.SCOPE);m.authorize(good,'abc')
        for delta in (dict(scope=m.SCOPE.replace('4211','2903')),dict(seed4211_execution_authorized=False),dict(execute=False),dict(historical_4211_failure_preserved=False),dict(no_tuning=False),dict(remaining_campaign_cases_disabled=0),dict(extra_case=True)):
            with self.assertRaises(ValueError):m.authorize(dict(good,**delta),'abc')
    def test_missing_seed_permission_or_wrong_freeze_cannot_authorize(self):
        m=load('seed4211_prepared_permission','run.py');g=self.grant(m);g.pop('seed4211_execution_authorized')
        with self.assertRaises(ValueError):m.authorize(g,'abc')
        with self.assertRaises(ValueError):m.authorize(self.grant(m),'other')
    def test_other_case_tuples_refused_before_runtime_or_docker(self):
        m=load('seed4211_prepared_workload','workload.py');args=dict(capture=True,losses=2,seed=4211,seconds=30,runtime_layout='socket-disposition',shutdown_diagnostics=True,shutdown_stacks=False,shutdown_stack_mode='procfs',bundle=Path('/unused'),prefix='unused')
        for delta in (dict(seed=2903),dict(seed=1701),dict(losses=0),dict(losses=1),dict(seconds=10),dict(capture=False),dict(shutdown_diagnostics=False),dict(shutdown_stacks=True),dict(shutdown_stack_mode='gdb')):
            with patch.object(m,'matched',side_effect=AssertionError('must reject before runtime/Docker')),self.assertRaises(ValueError):m.run(Path('/unused'),**dict(args,**delta))
    def test_no_authorization_refuses_without_docker_access(self):
        m=load('seed4211_no_grant','run.py')
        with patch.object(m.sys,'argv',['run.py']),patch.object(m.subprocess,'check_output',side_effect=AssertionError('Docker must not run')),self.assertRaises(SystemExit):m.main()
    def test_same_fresh_exact_sensor_selection_excludes_control(self):
        m=load('seed4211_selection','workload.py');identity=dict(initial_sequence=100,binding=dict(socket_id=99,source_port=41000,destination_port=10081))
        self.assertEqual(m.selection_for(identity).targets(),[dict(position=2,sequence=106,message_number=7),dict(position=3,sequence=107,message_number=8)])
        identity['binding']['destination_port']=10080
        with self.assertRaises(ValueError):m.selection_for(identity)
    def test_components_equal_validated_2903_package_and_native_manifest(self):
        prior=ROOT/'evidence/m3-two-loss-2903-preparation-2026-11-10'
        for n in ('binary-verification.json','observer-seccomp.json','observer-architecture.json','observer_entry.py','shutdown_observer.py','lifecycle.py','socket_gate.py','stage_gate.py','sidecar.py','bridge_exec.py','scenario.py'):
            self.assertEqual(hashlib.sha256((HERE/n).read_bytes()).digest(),hashlib.sha256((prior/n).read_bytes()).digest(),n)

if __name__=='__main__':unittest.main()
