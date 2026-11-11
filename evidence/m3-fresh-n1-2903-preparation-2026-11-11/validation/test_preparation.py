"""Offline scope, ordered dispatcher, calibration bindings and strict gate tests."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from model import ROOT,HERE,load,read,write,lines,jsonl,overlay
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
import run,workload_entry
plan=load('plan');cases=load('cases')
class PreparationTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name)
    def grant(self,digest='new'):
        return dict(scope=cases.SCOPE,freeze_sha256=digest,execute=True,case_ids=[s['id'] for s in cases.cases()],disabled_case_ids=cases.disabled_ids(),completed_case_ids_not_reexecuted=cases.completed_ids(),historical_LONG_case_ids_excluded=cases.historical_case_ids_excluded(),module_manifest_sha256=hashlib.sha256((HERE/'bindings.json').read_bytes()).hexdigest(),task_visibility=True,SDK_provider_visibility=True,fresh_N1_2903_qualification=True,resume_original_run=False,original_failure_reference=cases.original_failure_reference(),historical_failures_preserved=True,no_tuning=True,no_retries=True,stop_first_failed_gate=True)
    def test_single_fresh_scope_and_all_other37_excluded(self):
        self.assertEqual([s['id'] for s in cases.cases()],['N1-combined-2903']);self.assertEqual(cases.cases()[0]['ordinal'],31);self.assertEqual(cases.cases()[0]['source_seconds'],600);self.assertEqual(len(cases.disabled_ids()),37);self.assertEqual(len(cases.completed_ids()),37);self.assertNotIn('N1-combined-2903',cases.disabled_ids());self.assertEqual(cases.enabled_ids(),[])
    def test_grant_exact_and_mutations_refused(self):
        grant=self.grant();plan.authorize(grant,'new')
        for delta in (dict(freeze_sha256='old'),dict(case_ids=grant['case_ids']*2),dict(case_ids=grant['case_ids'][1:]),dict(case_ids=['N1-combined-1701',*grant['case_ids']]),dict(disabled_case_ids=[]),dict(historical_LONG_case_ids_excluded=[]),dict(module_manifest_sha256='old'),dict(task_visibility=False),dict(SDK_provider_visibility=False),dict(fresh_N1_2903_qualification=False),dict(resume_original_run=True),dict(original_failure_reference={}),dict(no_tuning=False),dict(no_retries=False),dict(stop_first_failed_gate=False),dict(extra=True)):
            with self.subTest(delta=delta),self.assertRaises(ValueError):plan.authorize(dict(grant,**delta),'new')
    def test_old_campaign_and_calibration_grants_refused(self):
        for name in ('m3-current-long-execution-2026-11-10','m3-sdkros-task-calibration-execution-2026-11-10'):
            with self.assertRaises(ValueError):plan.authorize(read(ROOT/'evidence'/name/'authorization.json'),'new')
    def test_missing_grant_never_calls_runtime(self):
        with patch.object(sys,'argv',['run.py']),patch.object(subprocess,'run',side_effect=AssertionError('no runtime')),self.assertRaises(SystemExit):run.main()
    def test_existing_output_refused_no_resume(self):
        with self.assertRaises(ValueError):run.fresh_output(self.out)
    def test_invocation_all_seven_original_flags(self):
        f=dict(output_relative='.local/new')
        for slot in cases.cases():
            args=workload_entry.invocation(f,slot);self.assertEqual(args[args.index('--profile')+1],slot['profile']);self.assertEqual(args[args.index('--seed')+1],str(slot['seed']));self.assertEqual(args[args.index('--seconds')+1],str(slot['source_seconds']));self.assertIn('--skip-build',args);self.assertNotIn('--build-image',args);self.assertIn('--sensor-provider-diagnostics',args);self.assertIn('--sender-diagnostics',args)
        for p,s,t in [('N0',1701,10),('N1',1701,600),('N1',4211,600),('N2',1701,10)]:self.assertFalse(cases.allowed(p,s,t))
    def test_inactive_workload_sidecar_before_IO(self):
        slot=cases.cases()[0];args=workload_entry.invocation(dict(output_relative='.local/new'),slot)
        with patch.object(subprocess,'run',side_effect=AssertionError('no runtime')):
            with self.assertRaisesRegex(ValueError,'inactive'):load('workload').main(args,bundle=self.out,prefix='owned')
            with self.assertRaisesRegex(ValueError,'inactive'):load('sidecar').Sidecar(self.out,self.out,'owned').arm(None)
    def test_active_scope_binds_slot_profile_seed_duration_output(self):
        scope=load('campaign_scope');slot=cases.cases()[0];f=dict(output_relative='.local/new',bundle_relative='bundle',prefix='owned');prefix='owned-'+slot['id'].lower();out=ROOT/f['output_relative']/slot['id']
        with patch.object(scope,'_active',(f,slot)):
            scope.guard(out,ROOT/'bundle',prefix,parameters=('N1',2903,600))
            for parameters in [('N1',4211,600),('N2',2903,600),('N1',2903,300)]:
                with self.assertRaisesRegex(ValueError,'parameters'):scope.guard(out,ROOT/'bundle',prefix,parameters=parameters)
            with self.assertRaises(ValueError):scope.guard(ROOT/'.local/foreign',ROOT/'bundle',prefix)
        with self.assertRaises(ValueError):scope.select('N1-combined-1701')
    def test_activation_exact_context_and_grant(self):
        scope=load('campaign_scope');f=dict(execution_enabled=False,authorization_supplied=False,cases=cases.cases());write(self.out/'freeze.json',f);grant=self.out/'grant.json';write(grant,self.grant(run.sha(self.out/'freeze.json')))
        with patch.object(scope,'HERE',self.out),patch.object(scope,'_active',None),patch.object(load('integrity'),'verify_files') as verified:
            scope.activate(grant,f,cases.EXPECTED_IDS[0]);verified.assert_called_once_with(f)
            with self.assertRaises(ValueError):scope.activate(grant,dict(f,cases=[]),cases.EXPECTED_IDS[0])
            self.assertIsNone(scope._active)
    def mocked_driver(self,failed=None,crash=None,postfail=None,provenance_bad=None):
        here=self.out/'prepared';here.mkdir();root=self.out/'root';root.mkdir();f=dict(execution_enabled=False,authorization_supplied=False,output_relative='out',bundle_relative='bundle',prefix='owned',cases=cases.cases(),runtime_layout={},source_sha256={});write(here/'freeze.json',f);grant=self.out/'grant.json';write(grant,self.grant(run.sha(here/'freeze.json')));events=[]
        def process(args,log,slot):
            events.append(('produce',slot['id']));target=root/'out'/slot['id'];target.mkdir();write(target/'run.json',dict(runtime_layout={},source_sha256={'foreign':'x'} if slot['id']==provenance_bad else {}))
            if slot['id']==crash:raise ValueError('modeled workload failure')
        def assess(target,result,slot):events.append(('assess',slot['id']));return dict(status='failed' if slot['id']==failed else 'passed')
        def post(target,f,prefix):
            events.append(('postflight',target.name))
            if target.name==postfail:raise ValueError('modeled cleanup failure')
        def cleanup(target,prefix,command):events.append(('emergency',target.name))
        with patch.object(run,'HERE',here),patch.object(run,'ROOT',root),patch.object(run,'verify'),patch.object(run,'case_process',side_effect=process),patch.object(load('assess'),'assess',side_effect=assess),patch.object(run,'postflight_case',side_effect=post),patch.object(load('emergency_cleanup'),'cleanup',side_effect=cleanup):report=run.execute(grant)
        return report,events
    def test_full_mocked_driver_seven_once_in_declared_order(self):
        report,events=self.mocked_driver();self.assertEqual(report['status'],'passed');self.assertEqual(events,[(kind,slot['id']) for slot in cases.cases() for kind in ('produce','assess','postflight')]);self.assertEqual(len(report['rows']),1)
    def test_strict_failure_stops_tail_without_retry(self):
        id=cases.EXPECTED_IDS[0];report,events=self.mocked_driver(failed=id);self.assertEqual([r['status'] for r in report['rows']],['failed']);self.assertEqual(sum(kind=='produce' for kind,_ in events),1);self.assertEqual(events[-1],('postflight',id))
    def test_workload_crash_cleanup_and_tail_stop(self):
        id=cases.EXPECTED_IDS[0];report,events=self.mocked_driver(crash=id);self.assertEqual(events,[('produce',id),('emergency',id)]);self.assertEqual(report['rows'][0]['status'],'failed');self.assertTrue(all(r['status']=='not_executed' for r in report['rows'][1:]))
    def test_postflight_failure_stops_next_case(self):
        report,events=self.mocked_driver(postfail=cases.EXPECTED_IDS[0]);self.assertEqual(report['status'],'failed');self.assertEqual(sum(k=='produce' for k,_ in events),1)
    def test_provenance_failure_before_assessment_and_next_case(self):
        report,events=self.mocked_driver(provenance_bad=cases.EXPECTED_IDS[0]);self.assertEqual(report['status'],'failed');self.assertFalse(any(k=='assess' for k,_ in events));self.assertIn('provenance',report['rows'][0]['produced'] and read(self.out/'root/out'/cases.EXPECTED_IDS[0]/'strict-assessment.json')['error'])
    def test_watchdog_uses_source_plus240_and_owned_group(self):
        for slot in (cases.cases()[0],cases.cases()[-1]):
            process=types.SimpleNamespace(pid=999,wait=unittest.mock.Mock(side_effect=[subprocess.TimeoutExpired('case',slot['source_seconds']+240),0]))
            with patch.object(run.os,'killpg') as kill,self.assertRaises(ValueError):run.case_process([],None,slot,popen=lambda *a,**k:process)
            kill.assert_called_once_with(999,run.signal.SIGTERM);self.assertEqual(process.wait.call_args_list[0].kwargs['timeout'],slot['source_seconds']+240)
    def test_all_seven_original_profile_readbacks_pass(self):
        for i,slot in enumerate(cases.cases()):
            out=self.out/str(i);overlay(out,slot);self.assertTrue(load('profile_gate').profile_gate(out,slot)['original_commands_and_kernel_settings_verified'])
    def test_profile_change_still_refused(self):
        slot=cases.cases()[-1];out=self.out/'overlay';overlay(out,slot);path=out/'profile-operator-readback.log';q=read(path);q[0]['options']['limit']=1;write(path,q)
        with self.assertRaises(ValueError):load('profile_gate').profile_gate(out,slot)
    def test_integrated_assessment_scoped_labels_and_calibrated_gates(self):
        slot=cases.cases()[0];out=self.out/'overlay';result,_=overlay(out,slot);assessor=load('assess')
        with patch.object(assessor,'assess_combined',return_value=dict(gate='modeled_common_callback')) as common:proof=assessor.assess(out,result,slot)
        self.assertEqual(proof['status'],'passed',proof.get('error'));self.assertFalse(proof['calibration_only']);self.assertEqual(proof['qualification'],'strict_LONG_combined_case_with_calibrated_task_visibility');self.assertGreaterEqual(proof['sdk_provider_visibility']['samples'],2);common.assert_called_once_with(result,out,slot)
    def test_actual_SDK_calibration_and_old_N1_slots_cannot_advance_seven(self):
        assessor=load('assess')
        for slot in [dict(id='N1-combined-1701',profile='N1',seed=1701,source_seconds=600),dict(id='SDKROS-calibration-N0-1701-10s',profile='N0',seed=1701,source_seconds=10)]:
            proof=assessor.assess(self.out,{},slot);self.assertEqual(proof['status'],'failed');self.assertIn('only exact fresh N1/2903',proof['error'])
    def test_bad_task_metadata_stops_common_gate(self):
        slot=cases.cases()[0];out=self.out/'overlay';result,_=overlay(out,slot);path=out/'native-observer/blocked-target-shutdown-stacks.jsonl';rows=lines(path);rows[1]['processes'][0]['threads'][0]['task_evidence']['confirmed_exit']=True;jsonl(path,rows);assessor=load('assess')
        with patch.object(assessor,'assess_combined',side_effect=AssertionError('must stop')) as common:proof=assessor.assess(out,result,slot)
        self.assertEqual(proof['status'],'failed');common.assert_not_called()
    def test_calibrated_helpers_and_private_build_manifest_exact(self):
        prior=ROOT/'evidence/m3-sdkros-task-calibration-preparation-2026-11-10'
        for name in ('task_assessment.py','lifecycle.py','shutdown_observer.py','observer_entry.py','sdk_visibility.py','observer_gate.py','scenario.py','bridge_exec.py','launch_assessment.py','launch_readiness.py','launch_records.py','stage_gate.py','socket_gate.py','profile_gate.py','binary-verification.json','observer-seccomp.json','observer-architecture.json'):self.assertEqual((HERE/name).read_bytes(),(prior/name).read_bytes(),name)
        expected=read(prior/'freeze.json')['runtime_layout'];actual=load('disposition_runtime').matched(ROOT,'socket-disposition');self.assertEqual(actual,dict(expected,calibration=actual['calibration']))
    def test_busy_runtime_refused_before_creation(self):
        f=dict(scope=cases.SCOPE,execution_enabled=False,authorization_supplied=False,cases=cases.cases(),disabled_case_ids=cases.disabled_ids(),completed_case_ids_not_reexecuted=cases.completed_ids(),historical_LONG_case_ids_excluded=cases.historical_case_ids_excluded(),runtime_version=[],daemon_architecture='aarch64',original_failure_reference=cases.original_failure_reference(),fresh_N1_2903_qualification=True,resume_original_run=False)
        with patch.object(run.integrity,'verify_files'),patch.object(subprocess,'check_output',side_effect=['[]','aarch64','unrelated']),self.assertRaisesRegex(ValueError,'live containers remain'):run.verify(f)
    def test_native_bundle_has_exact_six_calibrated_files(self):
        self.assertEqual(set(load('observer_bundle').sources()),{'observer_entry.py','shutdown_observer.py','observer-architecture.json','observer-seccomp.json','collector-binding.json','m3_observer_filtering.py'})
    def test_fresh_private_host_import_order(self):
        code="import sys;sys.path[:0]=sys.argv[1:];import run,workload_entry;from campaign_binding import load;print(load('assess').coverage.__module__);print(load('workload').Sidecar.__module__);print(len(load('cases').cases()))"
        output=subprocess.check_output([sys.executable,'-c',code,str(HERE),str(ROOT/'tools')],text=True).splitlines();self.assertEqual(output,['_robotweax_campaign_task_lifecycle','_robotweax_campaign_task_sidecar','1'])

    def test_original_failure_reference_is_fixed_and_readonly(self):
        ref=cases.original_failure_reference();self.assertEqual(hashlib.sha256((ROOT/ref['path']).read_bytes()).hexdigest(),ref['sha256']);self.assertEqual(read(ROOT/ref['path'])['status'],'failed')
    def test_old_seven_case_grant_cannot_authorize_fresh_attempt(self):
        grant=read(ROOT/'evidence/m3-current-remaining-execution-2026-11-11/authorization.json')
        with self.assertRaises(ValueError):plan.authorize(grant,'new')
    def test_consolidated_acceptance_has37_pass_one_preserved_failure(self):
        import importlib.util
        path=ROOT/'evidence/m3-acceptance-consolidation-2026-11-11/verify_record.py';spec=importlib.util.spec_from_file_location('acceptance_verify',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);self.assertEqual(m.verify()['passing_slots'],37)
        record=read(path.parent/'acceptance.json');record['matrix']['entries'][30]['status']='passed'
        with self.assertRaises(ValueError):m.verify(record)
        record=read(path.parent/'acceptance.json');record['pending_fresh_attempt']['execution_authorized']=True
        with self.assertRaises(ValueError):m.verify(record)
if __name__=='__main__':unittest.main()
