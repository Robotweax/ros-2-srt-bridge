"""Preparation-only checks; callbacks and Docker access are mocked."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parents[1]
FIX=ROOT/'evidence/m3-current-n0-identity-binding-fix-2026-11-10'
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
def load(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
plan=load('corrected_n0_cases','cases.py')
def driver():
    with patch.dict(sys.modules,cases=plan):return load('corrected_n0_driver','run.py')

class PreparationTests(unittest.TestCase):
    def grant(self):return dict(scope=plan.SCOPE,freeze_sha256='new',execute=True,case_ids=['N0-combined-1701'],disabled_case_ids=plan.disabled_ids(),launch_readiness_harness_revision='explicit-identity-v1',identity_helper_sha256=plan.IDENTITY_HELPER_SHA256,completed_N3_not_reexecuted=True,historical_failures_preserved=True,no_tuning=True,no_automatic_retries=True)
    def test_exact_historical_scope(self):
        self.assertEqual([(s['id'],s['seed'],s['source_seconds']) for s in plan.cases()],[('N0-combined-1701',1701,300)])
        self.assertEqual(len(plan.disabled_ids()),28)
    def test_new_grant_required_and_old_grants_refused(self):
        grant=self.grant();plan.authorize(grant,'new')
        for name in ('m3-current-n0-execution-2026-11-10','m3-current-n0-corrected-execution-2026-11-10','m3-strict-n3-execution-2026-11-10'):
            old=json.loads((ROOT/'evidence'/name/'authorization.json').read_text())
            with self.assertRaises(ValueError):plan.authorize(old,'new')
        for delta in (dict(freeze_sha256='old'),dict(scope='current-build-N0-combined-socket-disposition'),dict(launch_readiness_harness_revision='old'),dict(execute=False),dict(case_ids=[]),dict(disabled_case_ids=[]),dict(no_tuning=False),dict(no_automatic_retries=False),dict(extra=True)):
            with self.assertRaises(ValueError):plan.authorize(dict(grant,**delta),'new')
    def test_explicit_helper_hash_and_grant_binding(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT/plan.IDENTITY_HELPER_PATH).read_bytes()).hexdigest(),plan.IDENTITY_HELPER_SHA256)
        good=self.grant();good['identity_helper_sha256']='foreign'
        with self.assertRaises(ValueError):plan.authorize(good,'new')
        prepare=(HERE/'prepare.py').read_text();self.assertIn("identity_helper_binding=dict(path=IDENTITY_HELPER_PATH,sha256=IDENTITY_HELPER_SHA256",prepare)
    def test_no_authorization_never_contacts_docker(self):
        m=driver()
        with patch.object(m.sys,'argv',['run.py']),patch.object(m.subprocess,'check_output',side_effect=AssertionError('no Docker')),self.assertRaises(SystemExit):m.main()
    def test_only_single_case_and_no_resume(self):
        m=driver();seen=[]
        for status in ('passed','failed'):
            seen.clear();r=m.sequence(lambda s:seen.append(s['id']),lambda s,p:dict(status=status),lambda r:None)
            self.assertEqual(seen,['N0-combined-1701']);self.assertEqual(r['status'],status)
        with tempfile.TemporaryDirectory() as path:
            with self.assertRaises(ValueError):m.fresh_output(Path(path))
    def test_exception_stops_without_retry(self):
        m=driver();seen=[]
        def produce(s):seen.append(s['id']);raise ValueError('startup failed')
        r=m.sequence(produce,lambda *a:(_ for _ in ()).throw(AssertionError('no assessment')),lambda r:None)
        self.assertEqual(seen,['N0-combined-1701']);self.assertEqual(r['status'],'failed')
    def test_corrected_adapter_is_byte_identical_and_selects_corrected_scenario(self):
        self.assertEqual((HERE/'workload.py').read_bytes(),(FIX/'workload.py').read_bytes())
        s=(HERE/'workload.py').read_text();self.assertIn('evidence/m3-current-n0-identity-binding-fix-2026-11-10/scenario.py',s)
        self.assertNotIn("'evidence/m3-current-n0-preparation-2026-11-10/scenario.py'",s)
    def test_observer_gates_unchanged(self):
        prior=ROOT/'evidence/m3-current-n0-preparation-2026-11-10'
        for name in ('binary-verification.json','sidecar.py','observer_entry.py','observer-seccomp.json','observer-architecture.json','shutdown_observer.py','lifecycle.py','socket_gate.py','stage_gate.py','emergency_cleanup.py','assess.py'):
            self.assertEqual((HERE/name).read_bytes(),(prior/name).read_bytes(),name)
    def test_wrong_duration_seed_or_profile_refused_without_docker(self):
        m=load('corrected_n0_workload','workload.py');base=driver().invocation(Path('/unused'))
        for flag,value in (('--seconds','30'),('--seed','2903'),('--profile','N5')):
            argv=base.copy();argv[argv.index(flag)+1]=value
            with patch.object(m.subprocess,'check_output',side_effect=AssertionError('no Docker')),self.assertRaises(SystemExit):m.main(argv,bundle=Path('/unused'),prefix='unused')
    def test_old_driver_remains_immutable_and_cannot_select_new_adapter(self):
        old=(ROOT/'evidence/m3-current-n0-preparation-2026-11-10/workload.py').read_text()
        self.assertIn("'evidence/m3-current-n0-preparation-2026-11-10/scenario.py'",old)
        self.assertNotIn('launch-readiness-v2',old)

if __name__=='__main__':unittest.main()
