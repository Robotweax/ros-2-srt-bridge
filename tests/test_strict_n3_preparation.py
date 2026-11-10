import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];HERE=ROOT/'evidence/m3-strict-n3-preparation-2026-11-10'
sys.path.insert(0,str(ROOT/'tools'))
# Isolated module names avoid importing a historic evidence-local case module.
def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
plan=load('strict_n3_fixed_plan','cases.py')
def driver():
    with patch.dict(sys.modules,cases=plan):return load('strict_n3_driver','run.py')

class StrictN3PreparationTests(unittest.TestCase):
    def test_exact_seed_major_historical_order_nine_unique_cases(self):
        old=json.loads((ROOT/'evidence/m3-n3-frozen-cohort-2026-11-09/authorization.json').read_text())
        self.assertEqual([s['id'] for s in plan.cases()],old['case_ids']);self.assertEqual(plan.disabled_ids(),old['disabled_case_ids'])
        self.assertEqual(len({(s['seed'],s['losses']) for s in plan.cases()}),9)
        self.assertTrue(all(s['source_seconds']==30 and s['runtime_layout']=='socket-disposition' for s in plan.cases()))
    def test_scope_grant_rejects_reordering_subset_extra_and_later_stage(self):
        good=dict(scope=plan.SCOPE,freeze_sha256='abc',execute=True,case_ids=[s['id'] for s in plan.cases()],disabled_case_ids=plan.disabled_ids(),seed4211_execution_authorized=True,historical_failures_preserved=True,no_tuning=True,no_automatic_retries=True)
        plan.authorize(good,'abc')
        historical=json.loads((ROOT/'evidence/m3-n3-frozen-cohort-2026-11-09/authorization.json').read_text())
        with self.assertRaises(ValueError):plan.authorize(historical,'abc')
        for delta in (dict(case_ids=good['case_ids'][::-1]),dict(case_ids=good['case_ids'][:-1]),dict(case_ids=good['case_ids']+['N4-extra']),dict(disabled_case_ids=[]),dict(seed4211_execution_authorized=False),dict(no_automatic_retries=False),dict(extra=True)):
            with self.assertRaises(ValueError):plan.authorize(dict(good,**delta),'abc')
    def test_missing_authorization_does_not_access_docker(self):
        m=driver()
        with patch.object(m.sys,'argv',['run.py']),patch.object(m.subprocess,'check_output',side_effect=AssertionError('no Docker')),self.assertRaises(SystemExit):m.main()
    def test_unlisted_case_duration_and_disabled_tracing_refused_before_build(self):
        m=load('strict_n3_workload_scope','workload.py');args=dict(capture=True,losses=0,seed=1701,seconds=30,runtime_layout='socket-disposition',shutdown_diagnostics=True,shutdown_stacks=False,shutdown_stack_mode='procfs',bundle=Path('/unused'),prefix='unused')
        for delta in (dict(seed=999),dict(losses=3),dict(seconds=10),dict(capture=False),dict(shutdown_diagnostics=False),dict(shutdown_stacks=True),dict(shutdown_stack_mode='gdb')):
            with patch.object(m,'matched',side_effect=AssertionError('must fail before build/Docker')),self.assertRaises(ValueError):m.run(Path('/unused'),**dict(args,**delta))
    def test_baseline_one_and_two_loss_selection_exact(self):
        m=load('strict_n3_selection','workload.py');identity=dict(initial_sequence=100,binding=dict(socket_id=99,source_port=41000,destination_port=10081))
        self.assertIsNone(m.selection_for(identity,0));self.assertEqual(m.selection_for(identity,1).message_numbers,(8,));self.assertEqual(m.selection_for(identity,1).positions,(3,))
        self.assertEqual(m.selection_for(identity,2).message_numbers,(7,8));self.assertEqual(m.selection_for(identity,2).positions,(2,3))
        with self.assertRaises(ValueError):m.selection_for(identity,3)
    def test_first_failed_assessment_prevents_every_later_case_and_retry(self):
        m=driver();produced=[];assessed=[]
        def produce(slot):produced.append(slot['id']);return {}
        def assess(slot,_):assessed.append(slot['id']);return dict(status='failed' if slot['ordinal']==3 else 'passed')
        report=m.sequence(produce,assess,lambda r:None)
        self.assertEqual(produced,[s['id'] for s in plan.cases()[:3]]);self.assertEqual(assessed,produced)
        self.assertEqual([r['status'] for r in report['rows']],['passed','passed','failed']+['not_executed']*6)
        produced.clear()
        def fail(slot):produced.append(slot['id']);raise ValueError('readiness failure')
        report=m.sequence(fail,assess,lambda r:None);self.assertEqual(len(produced),1);self.assertEqual(report['status'],'failed')
    def test_all_pass_visits_nine_once_and_existing_output_refuses_resume(self):
        m=driver();seen=[]
        result=m.sequence(lambda s:seen.append(s['id']),lambda s,p:dict(status='passed'),lambda r:None)
        self.assertEqual(result['status'],'passed');self.assertEqual(seen,[s['id'] for s in plan.cases()])
        with tempfile.TemporaryDirectory() as path:
            with self.assertRaises(ValueError):m.fresh_output(Path(path))
    def test_calibrated_components_are_identical_and_emergency_cleanup_is_owned(self):
        prior=ROOT/'evidence/m3-two-loss-4211-preparation-2026-11-10'
        for name in ('binary-verification.json','observer_entry.py','observer-seccomp.json','shutdown_observer.py','lifecycle.py','socket_gate.py','stage_gate.py','sidecar.py','bridge_exec.py','scenario.py'):
            self.assertEqual(hashlib.sha256((HERE/name).read_bytes()).digest(),hashlib.sha256((prior/name).read_bytes()).digest(),name)
        m=load('strict_n3_emergency_cleanup','emergency_cleanup.py')
        import types
        with tempfile.TemporaryDirectory() as name:
            target=Path(name);network='ros2-srt-m3-owned';(target/'network.json').write_text(json.dumps(dict(network=network,containers=dict(operator=network+'-operator',robot=network+'-robot'))));(target/'passphrase').touch();commands=[]
            def command(args,**kw):commands.append(args);return types.SimpleNamespace(returncode=1 if args[:2]==['docker','inspect'] else 0,stdout='',stderr='')
            m.cleanup(target,'unique-case',command)
            self.assertFalse((target/'passphrase').exists());self.assertIn(['docker','rm','-f',network+'-operator'],commands);self.assertIn(['docker','network','rm',network],commands)

if __name__=='__main__':unittest.main()
