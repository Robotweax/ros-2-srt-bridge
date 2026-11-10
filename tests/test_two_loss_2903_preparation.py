import copy
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
HERE=ROOT/'evidence/m3-two-loss-2903-preparation-2026-11-10'
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(HERE))
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class TwoLossPreparationTests(unittest.TestCase):
    def test_exact_single_scope_authorization_rejects_4211_and_broader_grants(self):
        m=load('two_loss_prepared_run','run.py')
        good=dict(scope=m.SCOPE,freeze_sha256='abc',execute=True,remaining_campaign_cases_disabled=29,retry_two_loss_4211=False,no_tuning=True)
        self.assertIn('2903-30s',m.SCOPE);m.authorize(good,'abc')
        for value in (dict(good,scope=m.SCOPE.replace('2903','4211')),dict(good,no_tuning=False),dict(good,retry_two_loss_4211=True),dict(good,remaining_campaign_cases_disabled=0),dict(good,another_case=True),dict(good,freeze_sha256='other')):
            with self.assertRaises(ValueError):m.authorize(value,'abc')
    def test_other_seed_loss_duration_capture_or_trace_refused_before_docker(self):
        m=load('two_loss_prepared_workload','workload.py')
        args=dict(capture=True,losses=2,seed=2903,seconds=30,runtime_layout='socket-disposition',shutdown_diagnostics=True,shutdown_stacks=False,shutdown_stack_mode='procfs',bundle=Path('/unused'),prefix='unused')
        for delta in (dict(seed=4211),dict(seed=1701),dict(losses=1),dict(losses=0),dict(seconds=10),dict(capture=False),dict(shutdown_diagnostics=False),dict(shutdown_stacks=True),dict(shutdown_stack_mode='gdb')):
            with patch.object(m,'matched',side_effect=AssertionError('scope must fail before runtime/Docker')),self.assertRaises(ValueError):m.run(Path('/unused'),**dict(args,**delta))
    def test_selection_binds_exact_source_messages_and_fresh_session_tuple(self):
        m=load('two_loss_prepared_selection','workload.py')
        identity=dict(initial_sequence=100,binding=dict(socket_id=99,source_port=41000,destination_port=10081));before=copy.deepcopy(identity)
        selected=m.selection_for(identity)
        self.assertEqual(selected.targets(),[dict(position=2,sequence=106,message_number=7),dict(position=3,sequence=107,message_number=8)])
        self.assertEqual((selected.socket_id,selected.source_port,selected.destination_port),(99,41000,10081));self.assertEqual(identity,before)
        identity['initial_sequence']=200;identity['binding']['socket_id']=101
        second=m.selection_for(identity);self.assertEqual(second.targets()[0]['sequence'],206);self.assertEqual(second.socket_id,101)
    def test_invalid_or_control_channel_tuple_cannot_be_selected(self):
        m=load('two_loss_prepared_bad_selection','workload.py')
        for port,socket in ((10080,99),(10081,0),(0,99)):
            with self.assertRaises(ValueError):m.selection_for(dict(initial_sequence=100,binding=dict(socket_id=socket,source_port=41000,destination_port=port)))
        with self.assertRaises(KeyError):m.selection_for(dict(initial_sequence=100))
    def test_no_authorization_refuses_before_docker(self):
        m=load('two_loss_missing_authorization','run.py')
        with patch.object(m.sys,'argv',['run.py']),patch.object(m.subprocess,'check_output',side_effect=AssertionError('Docker must not run')),self.assertRaises(SystemExit):m.main()
    def test_calibrated_tracing_observer_and_native_manifest_are_exact_copies(self):
        previous=ROOT/'evidence/m3-socket-disposition-2026-11-10'
        for name in ('binary-verification.json','observer-seccomp.json','observer-architecture.json','observer_entry.py','shutdown_observer.py','lifecycle.py','socket_gate.py','stage_gate.py','sidecar.py','bridge_exec.py','scenario.py'):
            self.assertEqual(hashlib.sha256((HERE/name).read_bytes()).digest(),hashlib.sha256((previous/name).read_bytes()).digest(),name)

if __name__=='__main__':unittest.main()
