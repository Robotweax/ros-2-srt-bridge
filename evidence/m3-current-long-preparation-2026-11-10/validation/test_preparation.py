"""Offline-only nine-case scope, real parsing and mocked sequential dispatch."""
import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parents[1]
OLD=ROOT/'evidence/m3-current-n0-stable-preparation-2026-11-10'
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
plan=load('long_cases','cases.py')
def driver():
    with patch.dict(sys.modules,cases=plan):return load('long_driver','run.py')
class PreparationTests(unittest.TestCase):
    def grant(self):return dict(scope=plan.SCOPE,freeze_sha256='new',execute=True,case_ids=[s['id'] for s in plan.cases()],disabled_case_ids=plan.disabled_ids(),completed_case_ids_not_reexecuted=plan.completed_ids(),launch_readiness_harness_revision='stabilized-lifecycle-v1',lifecycle_assessment_sha256=plan.LIFECYCLE_ASSESSMENT_SHA256,identity_helper_sha256=plan.IDENTITY_HELPER_SHA256,historical_failures_preserved=True,no_tuning=True,no_automatic_retries=True,stop_first_failed_gate=True)
    def test_nine_original_order_and29_completed_exclusions(self):
        rows=plan.cases();self.assertEqual([s['ordinal'] for s in rows],list(range(30,39)));self.assertEqual(len(plan.completed_ids()),29);self.assertEqual(plan.disabled_ids(),plan.completed_ids());self.assertFalse(set(s['id'] for s in rows)&set(plan.completed_ids()));self.assertEqual(sum(s['source_seconds'] for s in rows),4500)
    def test_exact_invocation_flags_profile_seed_duration(self):
        m=driver()
        for s in plan.cases():
            args=m.invocation(s,Path('/synthetic')/s['id']);self.assertEqual(args[args.index('--profile')+1],s['profile']);self.assertEqual(args[args.index('--seed')+1],str(s['seed']));self.assertEqual(args[args.index('--seconds')+1],str(s['source_seconds']));self.assertEqual(args[-7:],list(m.FLAGS));self.assertNotIn('--probe-diagnostics',args)
    def test_exact_grant_and_scope_drift_refusal(self):
        good=self.grant();plan.authorize(good,'new')
        for delta in (dict(scope='old'),dict(freeze_sha256='old'),dict(execute=False),dict(case_ids=good['case_ids'][::-1]),dict(case_ids=good['case_ids'][:-1]),dict(disabled_case_ids=[]),dict(completed_case_ids_not_reexecuted=[]),dict(identity_helper_sha256='bad'),dict(lifecycle_assessment_sha256='bad'),dict(no_tuning=False),dict(no_automatic_retries=False),dict(stop_first_failed_gate=False),dict(extra=True)):
            with self.subTest(delta=delta),self.assertRaises(ValueError):plan.authorize(dict(good,**delta),'new')
    def test_prior_N0_N3_N4_grants_refused(self):
        for name in ('m3-current-n0-stable-execution-2026-11-10','m3-strict-n3-execution-2026-11-10','m3-current-n4-corrected-execution-2026-11-10'):
            with self.assertRaises(ValueError):plan.authorize(json.loads((ROOT/'evidence'/name/'authorization.json').read_text()),'new')
    def test_every_failure_stops_before_next_produce(self):
        m=driver()
        for i in range(9):
            seen=[]
            report=m.sequence(lambda s:seen.append(s['id']),lambda s,p:dict(status='failed' if s==plan.cases()[i] else 'passed'),lambda r:None)
            self.assertEqual(seen,[s['id'] for s in plan.cases()[:i+1]]);self.assertEqual(report['rows'][i]['status'],'failed');self.assertTrue(all(r['status']=='not_executed' for r in report['rows'][i+1:]))
    def test_no_grant_cannot_touch_runtime(self):
        m=driver()
        with patch.object(m.sys,'argv',['run.py']),patch.object(m.subprocess,'check_output',side_effect=AssertionError('no Docker')),self.assertRaises(SystemExit):m.main()
    def test_no_output_reuse_or_modified_slot(self):
        m=driver()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):m.fresh_output(Path(tmp))
        for delta in (dict(profile='N0'),dict(seed=999),dict(source_seconds=15),dict(runtime_layout='baseline')):
            with self.assertRaises(ValueError):m.invocation(dict(plan.cases()[0],**delta),Path('/unused'))
    def test_case_observer_prefixes_unique_and_disjoint(self):
        m=driver();names=[m.case_prefix(dict(prefix='owned'),s) for s in plan.cases()];self.assertEqual(len(set(names)),9);self.assertTrue(all(x.startswith('owned-') for x in names))
    def workload_scope(self,args,accepted):
        with patch.dict(sys.modules,cases=plan):m=load('long_workload','workload.py')
        marker=RuntimeError('scope accepted; before any output or live operation')
        with patch.object(m,'datetime',types.SimpleNamespace(now=lambda *a:(_ for _ in ()).throw(marker))),patch.object(m.subprocess,'check_output',side_effect=AssertionError('no Docker')):
            if accepted:
                with self.assertRaisesRegex(RuntimeError,'scope accepted'):m.main(args,bundle=Path('/unused'),prefix='owned')
            else:
                with self.assertRaises(SystemExit):m.main(args,bundle=Path('/unused'),prefix='owned')
    def test_all_nine_real_parser_accepts_before_mutation(self):
        m=driver()
        for s in plan.cases():self.workload_scope(m.invocation(s,Path('/unused')),True)
    def test_parser_refuses_other_stages_seeds_durations_and_tuning(self):
        m=driver();base=m.invocation(plan.cases()[0],Path('/unused'))
        for option,value in [('--profile','N0'),('--profile','N4'),('--seed','999'),('--seconds','300'),('--runtime-layout','baseline')]:
            args=list(base);args[args.index(option)+1]=value;self.workload_scope(args,False)
        for extra in (['--smoke'],['--build-image'],['--neighbor-mode','permanent'],['--outage-direction','robot'],['--probe-diagnostics'],['--recorder-diagnostics'],['--capture-drain-check']):self.workload_scope(base+extra,False)
    def test_calibrated_lifecycle_modules_byte_identical(self):
        for name in ('launch_readiness.py','launch_records.py','launch_assessment.py','lifecycle.py','sidecar.py','stage_gate.py','socket_gate.py','shutdown_observer.py','observer_entry.py','observer-seccomp.json','observer-architecture.json','emergency_cleanup.py','binary-verification.json','disposition_runtime.py'):
            self.assertEqual((HERE/name).read_bytes(),(OLD/name).read_bytes(),name)
    def test_workload_only_scope_guard_and_import_changes(self):
        expected=(OLD/'workload.py').read_text().replace('from sidecar import Sidecar','from sidecar import Sidecar\nfrom cases import allowed').replace("args.profile!='N0' or args.seed!=1701 or duration!=300","not allowed(args.profile,args.seed,duration)").replace("parser.error('only frozen N0/1701/300s combined scope allowed')","parser.error('only frozen nine N1/N2/N5 cases allowed')").replace("or args.neighbor_mode!='dynamic':parser.error('only frozen nine","or args.neighbor_mode!='dynamic' or args.outage_direction!='both':parser.error('only frozen nine")
        expected=expected.replace('evidence/m3-current-n0-lifecycle-stabilization-2026-11-10/scenario.py','evidence/m3-current-long-preparation-2026-11-10/scenario.py')
        self.assertEqual((HERE/'workload.py').read_text(),expected)
    def test_fresh_runtime_imports_local_helpers_and_bound_identity(self):
        code="import sys;sys.path[:0]=sys.argv[1:];import run,workload,assess,sidecar,launch_assessment,launch_readiness;from pathlib import Path;print(*(str(Path(m.__file__).resolve()) for m in (workload,assess,sidecar,launch_assessment)),sep='\\n');print(launch_readiness.IDENTITY_HELPER_BINDING['sha256'])"
        lines=subprocess.check_output([sys.executable,'-c',code,str(HERE),str(ROOT/'tools')],text=True).splitlines();self.assertEqual(lines,[str(HERE/n) for n in ('workload.py','assess.py','sidecar.py','launch_assessment.py')]+[plan.IDENTITY_HELPER_SHA256])
    def profile(self,path,slot):
        from m3_network import PROFILES
        p=PROFILES[slot['profile']];net=dict(containers={r:'owned-'+r for r in ('operator','robot')},commands=[])
        for r in net['containers']:
            seed=slot['seed']+(r=='operator')
            for i,argv in enumerate(p.commands(seed)):net['commands'].append(dict(label='profile-'+r+'-'+str(i),exit_code=0,argv=['docker','exec',net['containers'][r],*argv]))
            q=dict(kind='netem',handle='1:',root=True,options=dict(seed=seed,limit=p.queue_packets,delay=dict(delay=p.delay_ms/1000,jitter=p.jitter_ms/1000),**{'loss-random':dict(loss=p.loss_percent/100)}))
            state=[q]
            if p.name=='N5':q.pop('root');q.update(handle='10:',parent='1:1');state.insert(0,dict(kind='tbf',handle='1:',root=True,options=dict(rate=64000,burst=4096)))
            (path/('profile-'+r+'-readback.log')).write_text(json.dumps(state))
        (path/'network.json').write_text(json.dumps(net))
    def test_original_profile_commands_and_readback_all_nine(self):
        m=load('profile_check','profile_gate.py')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for s in plan.cases():self.profile(p,s);self.assertTrue(m.profile_gate(p,s)['original_commands_and_kernel_settings_verified'])
    def test_profile_changes_and_missing_install_refused(self):
        m=load('profile_refusal','profile_gate.py')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for index,key,value in [(0,'seed',99),(0,'limit',999),(0,'delay',{}),(6,'seed',99),(6,'limit',256)]:
                s=plan.cases()[index];self.profile(p,s);f=p/'profile-operator-readback.log';qs=json.loads(f.read_text());next(q for q in qs if q['kind']=='netem')['options'][key]=value;f.write_text(json.dumps(qs))
                with self.assertRaises(ValueError):m.profile_gate(p,s)
            s=plan.cases()[6];self.profile(p,s);f=p/'profile-robot-readback.log';qs=json.loads(f.read_text());qs[0]['options']['rate']=128000;f.write_text(json.dumps(qs))
            with self.assertRaises(ValueError):m.profile_gate(p,s)
            self.profile(p,s);f=p/'network.json';net=json.loads(f.read_text());net['commands'].pop();f.write_text(json.dumps(net))
            with self.assertRaises(ValueError):m.profile_gate(p,s)
    def test_postflight_refuses_credential_and_owned_observer(self):
        m=driver()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'network.json').write_text(json.dumps(dict(network='net',containers=dict(operator='one',robot='two'))));(p/'passphrase').touch()
            with patch.object(m.subprocess,'check_output',return_value=''),patch.object(m,'verify') as verify:
                with self.assertRaises(ValueError):m.postflight(p,{},'owned')
                verify.assert_not_called()
            (p/'passphrase').unlink()
            with patch.object(m.subprocess,'check_output',return_value='owned-observer'),self.assertRaises(ValueError):m.postflight(p,{},'owned')
    def mocked_main(self,fail=None,crash=None):
        m=driver();events=[]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);here=root/'prepared';here.mkdir();(root/'out').mkdir()
            freeze=dict(execution_enabled=False,cases=plan.cases(),disabled_case_ids=plan.disabled_ids(),completed_case_ids_not_reexecuted=plan.completed_ids(),output_relative='out/cohort',bundle_relative='bundle',prefix='owned',runtime_layout={},source_sha256={})
            (here/'freeze.json').write_text(json.dumps(freeze));g=self.grant();g['freeze_sha256']=m.sha(here/'freeze.json');(root/'grant.json').write_text(json.dumps(g))
            def workload(argv,**kwargs):
                out=Path(argv[argv.index('--output')+1]);out.mkdir();events.append(('produce',out.name));(out/'run.json').write_text(json.dumps(dict(runtime_layout={},source_sha256={})))
                if out.name==crash:raise RuntimeError('host failed')
            def assess(out,result,slot):events.append(('assess',out.name));return dict(status='failed' if out.name==fail else 'passed')
            def post(out,f,prefix):events.append(('postflight',out.name))
            def cleanup(out,prefix,command):events.append(('cleanup',out.name))
            with patch.dict(sys.modules,workload=types.SimpleNamespace(main=workload),assess=types.SimpleNamespace(assess=assess),emergency_cleanup=types.SimpleNamespace(cleanup=cleanup)),patch.object(m,'ROOT',root),patch.object(m,'HERE',here),patch.object(m,'verify'),patch.object(m,'postflight',side_effect=post),patch.object(m.sys,'argv',['run.py','--authorization',str(root/'grant.json')]):status=m.main()
            return status,events,json.loads((root/'out/cohort/cohort.json').read_text())
    def test_full_mocked_dispatch_nine_once_postflight_before_next(self):
        status,events,r=self.mocked_main();self.assertEqual(status,0);self.assertEqual(events,[(kind,s['id']) for s in plan.cases() for kind in ('produce','assess','postflight')]);self.assertEqual(len(r['rows']),9)
    def test_strict_failure_preserves_postflight_and_stops_tail(self):
        failed=plan.cases()[4]['id'];status,events,r=self.mocked_main(fail=failed);self.assertEqual(status,1);self.assertEqual(events[-3:],[('produce',failed),('assess',failed),('postflight',failed)]);self.assertTrue(all(x['status']=='not_executed' for x in r['rows'][5:]))
    def test_unexpected_host_exception_owned_cleanup_no_retry(self):
        failed=plan.cases()[0]['id'];status,events,r=self.mocked_main(crash=failed);self.assertEqual(status,1);self.assertEqual(events,[('produce',failed),('cleanup',failed)]);self.assertTrue(all(x['status']=='not_executed' for x in r['rows'][1:]))
    def test_unchanged_combined_gate_still_bound(self):
        new=(HERE/'assess.py').read_text();old=(OLD/'assess.py').read_text();expected=old.replace('remaining_campaign_cases_disabled=28,fresh_N0_case=True','completed_campaign_cases_excluded=29,fresh_LONG_case=True').replace("qualification='strict_N0_combined_case_with_shutdown_controls'","qualification='strict_LONG_combined_case_with_shutdown_controls'").replace("proof['combined']=assess_combined(result,out,slot);cleanup(out)","proof['combined']=assess_combined(result,out,slot);proof['profile']=profile_gate(out,slot);cleanup(out)").replace('from launch_assessment import assess_launches','from launch_assessment import assess_launches\nfrom profile_gate import profile_gate');self.assertEqual(new,expected)
    def test_prerequisites_use_actual_published_gate_reports(self):
        m=load('long_prepare','prepare.py')
        with patch.object(m.subprocess,'check_output',side_effect=AssertionError('no Docker')):
            self.assertEqual(m.prerequisites(),dict(N0='passed',N3_passed=9,N4_passed=19))
if __name__=='__main__':unittest.main()
