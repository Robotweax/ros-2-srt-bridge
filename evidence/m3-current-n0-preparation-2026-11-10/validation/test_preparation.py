import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
plan=load('n0_fixed_cases','cases.py')
def driver():
    with patch.dict(sys.modules,cases=plan):return load('n0_driver','run.py')

class PreparationTests(unittest.TestCase):
    def test_exact_historical_one_case_and_other28_disabled(self):
        self.assertEqual([(x['id'],x['source_seconds'],x['seed']) for x in plan.cases()],[('N0-combined-1701',300,1701)])
        self.assertEqual(len(plan.disabled_ids()),28)
        self.assertTrue(all(not x.startswith(('N0-','N3-')) for x in plan.disabled_ids()))
    def test_authorization_exact_scope_and_legacy_refusal(self):
        good=dict(scope=plan.SCOPE,freeze_sha256='abc',execute=True,case_ids=['N0-combined-1701'],disabled_case_ids=plan.disabled_ids(),completed_N3_not_reexecuted=True,historical_failures_preserved=True,no_tuning=True,no_automatic_retries=True)
        plan.authorize(good,'abc')
        for delta in (dict(scope='fresh-strict-nine-case-N3-socket-disposition'),dict(freeze_sha256='bad'),dict(execute=False),dict(case_ids=[]),dict(case_ids=['N0-combined-1701','N4-extra']),dict(disabled_case_ids=[]),dict(no_tuning=False),dict(no_automatic_retries=False),dict(extra=True)):
            with self.assertRaises(ValueError):plan.authorize(dict(good,**delta),'abc')
    def test_missing_authorization_never_contacts_docker(self):
        m=driver()
        with patch.object(m.sys,'argv',['run.py']),patch.object(m.subprocess,'check_output',side_effect=AssertionError('Docker forbidden')),self.assertRaises(SystemExit):m.main()
    def test_wrong_profile_seed_duration_or_build_refused_before_docker(self):
        m=load('n0_workload','workload.py');d=driver();base=d.invocation(Path('/unused'))
        for flag,value in (('--profile','N5'),('--seed','2903'),('--seconds','30'),('--runtime-layout','sender-reconcile')):
            args=base.copy();args[args.index(flag)+1]=value
            with patch.object(m.subprocess,'check_output',side_effect=AssertionError('Docker forbidden')),self.assertRaises(SystemExit):m.main(args,bundle=Path('/unused'),prefix='unused')
        args=base.copy();args.remove('--skip-build')
        with patch.object(m.subprocess,'check_output',side_effect=AssertionError('Docker forbidden')),self.assertRaises(SystemExit):m.main(args,bundle=Path('/unused'),prefix='unused')
    def test_single_once_stop_failure_and_no_resume(self):
        m=driver();seen=[]
        for status in ('passed','failed'):
            seen.clear();r=m.sequence(lambda s:seen.append(s['id']),lambda s,p:dict(status=status),lambda r:None)
            self.assertEqual(seen,['N0-combined-1701']);self.assertEqual(r['status'],status)
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(ValueError):m.fresh_output(Path(name))
    def test_calibrated_components_byte_identical(self):
        old=ROOT/'evidence/m3-strict-n3-preparation-2026-11-10'
        for name in ('binary-verification.json','disposition_runtime.py','bridge_exec.py','sidecar.py','observer_entry.py','observer-seccomp.json','observer-architecture.json','shutdown_observer.py','lifecycle.py','socket_gate.py','stage_gate.py','emergency_cleanup.py'):
            self.assertEqual((HERE/name).read_bytes(),(old/name).read_bytes(),name)
    def diagnostic(self):
        tree=ast.parse((HERE/'scenario.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Diagnostic')
        class Base:
            def stop(self,p):
                p.send_signal(2)
                if p.fail:p.kill();raise RuntimeError('original timeout')
        namespace=dict(Benchmark=Base,time=__import__('time'),read=lambda p:json.loads(p.read_text()),write=lambda p,v:p.write_text(json.dumps(v)))
        exec(compile(ast.Module(body=[node],type_ignores=[]),'scenario-extracted','exec'),namespace)
        return namespace['Diagnostic']
    def test_stop_preserves_success_and_retains_forced_failure(self):
        cls=self.diagnostic()
        for fail in (False,True):
            with tempfile.TemporaryDirectory() as path:
                p=types.SimpleNamespace(pid=123,fail=fail,poll=lambda:None,send_signal=lambda sig:None,kill=lambda:None)
                obj=cls();obj.run=Path(path);obj.args=types.SimpleNamespace(role='operator');obj.processes=[(p,'operator-bridge-0',None)]
                if fail:
                    with self.assertRaises(RuntimeError):obj.stop(p)
                else:obj.stop(p)
                row=json.loads((Path(path)/'operator-child-shutdown.json').read_text())['children'][0]
                self.assertEqual(row['passed'],not fail);self.assertEqual(row['forced_kill'],fail)
                self.assertLessEqual(row['signal_begin_ns'],row['signal_end_ns']);self.assertLessEqual(row['signal_end_ns'],row['end_ns'])
    def test_finish_gate_arms_before_release_and_unchanged_workload(self):
        s=(HERE/'workload.py').read_text();segment=s[s.index("if (run/'n0-shutdown-ready')"):];self.assertLess(segment.index('observer.arm(lab)'),segment.index("(run/'n0-shutdown-release').touch()"))
        original=ast.parse((ROOT/'ros2/robotweax_srt_bridge_demo/scripts/m3_scenario.py').read_text());new=ast.parse((HERE/'scenario.py').read_text())
        oldclass=next(n for n in original.body if isinstance(n,ast.ClassDef) and n.name=='Benchmark');newclass=next(n for n in new.body if isinstance(n,ast.ClassDef) and n.name=='Benchmark')
        self.assertEqual(ast.dump(oldclass),ast.dump(newclass))

if __name__=='__main__':unittest.main()
