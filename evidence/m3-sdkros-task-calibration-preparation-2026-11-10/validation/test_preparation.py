"""Scoped grant, integrated SDK gates, actual arm flow and modeled orchestration."""
import ast
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from model import ROOT,HERE,load,read,write,lines,jsonl,overlay,DockerModel
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
import run,workload_entry
plan=load('plan')

class PreparationTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name)
    def grant(self,digest='new'):
        return dict(scope=plan.SCOPE,freeze_sha256=digest,execute=True,readiness_checks=1,SDKROS_fixture_limit=1,profile='N0',seed=1701,source_seconds=10,task_visibility=True,module_manifest_sha256=hashlib.sha256((HERE/'bindings.json').read_bytes()).hexdigest(),disabled_case_ids=plan.disabled_ids(),remaining_case_ids_disabled=plan.remaining_ids(),N1_2903_rerun=False,historical_failure_preserved=True,no_tuning=True,no_retries=True,stop_first_failed_gate=True)
    def test_exact_grant_and_all_campaign_exclusions(self):
        grant=self.grant();plan.authorize(grant,'new');self.assertEqual(len(grant['disabled_case_ids']),38);self.assertEqual(len(grant['remaining_case_ids_disabled']),7)
        for delta in (dict(scope='campaign'),dict(freeze_sha256='old'),dict(readiness_checks=2),dict(SDKROS_fixture_limit=2),dict(seed=2903),dict(source_seconds=300),dict(profile='N1'),dict(task_visibility=False),dict(module_manifest_sha256='old'),dict(disabled_case_ids=[]),dict(N1_2903_rerun=True),dict(no_tuning=False),dict(no_retries=False),dict(extra=True)):
            with self.subTest(delta=delta),self.assertRaises(ValueError):plan.authorize(dict(grant,**delta),'new')
    def test_old_grants_rejected(self):
        for name in ('m3-current-long-execution-2026-11-10','m3-task-post-sigint-calibration-execution-2026-11-10'):
            with self.assertRaises(ValueError):plan.authorize(read(ROOT/'evidence'/name/'authorization.json'),'new')
    def test_missing_grant_never_calls_runtime(self):
        with patch.object(sys,'argv',['run.py']),patch.object(subprocess,'run',side_effect=AssertionError('no runtime')),self.assertRaises(SystemExit):run.main()
    def test_fresh_output_no_resume(self):
        with self.assertRaises(ValueError):run.fresh_output(self.out)
    def test_first_gate_failure_stops_fixture(self):
        seen=[]
        def fail():seen.append('ready');raise ValueError('failed')
        report=run.sequence(fail,lambda:seen.append('fixture'),lambda r:None);self.assertEqual(seen,['ready']);self.assertEqual([r['status'] for r in report['rows']],['failed','not_executed'])
    def test_second_gate_failure_never_retried(self):
        seen=[]
        def fail():seen.append('fixture');raise ValueError('failed')
        report=run.sequence(lambda:seen.append('ready'),fail,lambda r:None);self.assertEqual(seen,['ready','fixture']);self.assertEqual(report['status'],'failed')
    def test_unactivated_workload_and_sidecar_refused_before_IO(self):
        scope=load('calibration_scope');self.assertIsNone(scope._active)
        with patch.object(subprocess,'run',side_effect=AssertionError('no runtime')):
            with self.assertRaisesRegex(ValueError,'inactive'):load('workload').main(workload_entry.invocation(dict(output_relative='missing',prefix='owned',bundle_relative='bundle')),bundle=self.out,prefix='owned')
            with self.assertRaisesRegex(ValueError,'inactive'):load('sidecar').Sidecar(self.out,self.out,'owned').arm(None)
    def test_scope_output_bundle_prefix_exact(self):
        scope=load('calibration_scope');freeze=dict(output_relative='.local/new',bundle_relative='.local/bundle',prefix='owned')
        with patch.object(scope,'_active',freeze):
            scope.guard(ROOT/'.local/new/fixture',ROOT/'.local/bundle','owned-sdkros')
            for out,bundle,prefix in [(ROOT/'.local/foreign',ROOT/'.local/bundle','owned-sdkros'),(ROOT/'.local/new/fixture',ROOT/'.local/foreign','owned-sdkros'),(ROOT/'.local/new/fixture',ROOT/'.local/bundle','N1-combined-2903')]:
                with self.assertRaises(ValueError):scope.guard(out,bundle,prefix)
    def test_exact_invocation_and_single_calibration_grammar(self):
        args=workload_entry.invocation(dict(output_relative='.local/cal'));self.assertEqual(args[args.index('--profile')+1],'N0');self.assertEqual(args[args.index('--seconds')+1],'10');self.assertIn('--skip-build',args);self.assertNotIn('--build-image',args)
        cases=load('cases');self.assertEqual(len(cases.cases()),1);self.assertEqual(cases.enabled_ids(),[]);self.assertEqual(len(cases.disabled_ids()),38)
        for profile,seed,seconds in [('N0',1701,300),('N1',2903,600),('N0',2903,10)]:self.assertFalse(cases.allowed(profile,seed,seconds))
    def test_provider_presence_uses_recomputed_metadata(self):
        out=self.out/'overlay';result,slot,fixture=overlay(out);target=read(out/'operator-bridge-identity.json');rows=lines(out/'native-observer/blocked-target-shutdown-stacks.jsonl')[:-1];proof=load('sdk_visibility').presence(rows,target);self.assertEqual(proof['samples'],4);self.assertEqual(proof['provider_names'],['rwx-shard-0'])
    def test_insufficient_or_error_provider_samples_refused(self):
        out=self.out/'overlay';_,_,_=overlay(out);target=read(out/'operator-bridge-identity.json');rows=lines(out/'native-observer/blocked-target-shutdown-stacks.jsonl')[:-1]
        with self.assertRaisesRegex(ValueError,'two SDK provider'):load('sdk_visibility').presence(rows[:2],target)
        changed=deepcopy(rows);changed[1]['processes'][0]['threads'][0]['task_evidence']['confirmed_exit']=True
        with self.assertRaises(ValueError):load('sdk_visibility').presence(changed,target)
    def test_integrated_calibration_assessment_links_unchanged_common_gates(self):
        out=self.out/'overlay';result,slot,_=overlay(out);assessor=load('assess')
        # Common workload gate already passed retained integration tests; the
        # 600s retained workload is not relabeled as real 10s SDK evidence.
        with patch.object(assessor,'assess_combined',return_value=dict(gate='modeled_common_callback')) as common:proof=assessor.assess(out,result,slot)
        self.assertEqual(proof['status'],'passed',proof.get('error'));self.assertEqual(proof['qualification'],'bounded_SDKROS_calibration_only');self.assertFalse(proof['campaign_qualification']);self.assertGreaterEqual(proof['sdk_provider_visibility']['samples'],2);common.assert_called_once_with(result,out,slot)
    def test_bad_bootstrap_stops_before_common_gate(self):
        out=self.out/'overlay';result,slot,_=overlay(out);events=lines(out/'operator-observer-exec.jsonl');events[1]['task_visibility']=False;jsonl(out/'operator-observer-exec.jsonl',events);jsonl(out/'native-observer/observer-exec.jsonl',events);assessor=load('assess')
        with patch.object(assessor,'assess_combined',side_effect=AssertionError('must stop')) as common:proof=assessor.assess(out,result,slot)
        self.assertEqual(proof['status'],'failed');common.assert_not_called()
    def full_driver(self,ready_failure=False,bad_policy=False,fixture_failure=False):
        here=self.out/'prepared';here.mkdir();root=self.out/'root';root.mkdir();(root/'.local').mkdir();f=dict(output_relative='.local/cal',bundle_relative='bundle',prefix='owned',observer_image='native',slot=load('cases').cases()[0],source_sha256={},runtime_layout={})
        shutil.copyfile(HERE/'observer-seccomp.json',here/'observer-seccomp.json');write(here/'freeze.json',f);grant=self.out/'grant.json';write(grant,self.grant(run.sha(here/'freeze.json')));backend=DockerModel(self.out,ready_failure,bad_policy);fixtures=[];assessor=load('assess')
        def fixture(argv,log):
            fixtures.append(argv);target=root/f['output_relative']/'fixture';target.mkdir();write(target/'run.json',dict(source_sha256={},runtime_layout={}));write(target/'network.json',dict(network='ros2-srt-m3-model',containers=dict(operator='ros2-srt-m3-model-operator',robot='ros2-srt-m3-model-robot'),commands=[]))
            if fixture_failure:(target/'passphrase').touch();raise ValueError('fixture failed')
        with patch.object(run,'HERE',here),patch.object(run,'ROOT',root),patch.object(run,'verify'),patch.object(run.integrity,'verify_files'),patch.object(subprocess,'run',side_effect=backend.command),patch.object(run,'fixture_process',side_effect=fixture),patch.object(assessor,'assess',return_value=dict(status='passed',calibration_only=True)):report=run.execute(grant)
        self.assertFalse(backend.objects);self.assertFalse(backend.volumes);return report,backend.calls,fixtures
    def test_full_modeled_driver_readiness_then_one_fixture(self):
        report,calls,fixtures=self.full_driver();self.assertEqual(report['status'],'passed');self.assertEqual(len(fixtures),1);self.assertEqual(len([c for c in calls if c[1]=='create']),1);create=next(c for c in calls if c[1]=='create');self.assertNotIn('--pid',create);self.assertEqual(create[-1],'--self-check')
    def test_readiness_failure_never_starts_SDKROS(self):
        report,calls,fixtures=self.full_driver(ready_failure=True);self.assertEqual(report['status'],'failed');self.assertFalse(fixtures);self.assertEqual(report['stages']['rows'][1]['status'],'not_executed')
    def test_wrong_policy_never_starts_native_readiness_or_fixture(self):
        report,calls,fixtures=self.full_driver(bad_policy=True);self.assertFalse(fixtures);self.assertFalse(any(c[1]=='start' for c in calls));self.assertEqual(report['status'],'failed')
    def test_fixture_failure_cleanup_no_restart(self):
        report,calls,fixtures=self.full_driver(fixture_failure=True);self.assertEqual(report['status'],'failed');self.assertEqual(len(fixtures),1);self.assertTrue(any(c[1]=='network' and c[2]=='rm' for c in calls));self.assertFalse((self.out/'root/.local/cal/fixture/passphrase').exists())
    def test_watchdog_owns_only_one_host_group_and_no_retry(self):
        process=types.SimpleNamespace(pid=777,wait=unittest.mock.Mock(side_effect=[subprocess.TimeoutExpired('fixture',240),0]));created=unittest.mock.Mock(return_value=process)
        with patch.object(run.os,'killpg') as kill,self.assertRaisesRegex(ValueError,'240s host watchdog'):run.fixture_process(['python','fixture'],None,popen=created)
        created.assert_called_once();kill.assert_called_once_with(777,run.signal.SIGTERM);self.assertEqual(process.wait.call_args_list[0].kwargs['timeout'],240)
    def test_successful_host_fixture_has_no_group_signals(self):
        process=types.SimpleNamespace(wait=lambda timeout:0)
        with patch.object(run.os,'killpg',side_effect=AssertionError('no signals')):run.fixture_process([],None,popen=lambda *a,**k:process)
    def test_budget_policy_and_candidate_unchanged(self):
        original=ROOT/'evidence/m3-campaign-task-assessment-integration-2026-11-10'
        for name in ('task_assessment.py','lifecycle.py','shutdown_observer.py','observer_entry.py','observer-seccomp.json','observer-architecture.json','scenario.py','bridge_exec.py','launch_readiness.py','launch_records.py','launch_assessment.py','stage_gate.py','socket_gate.py'):self.assertEqual((HERE/name).read_bytes(),(original/name).read_bytes(),name)
    def test_runtime_busy_refuses_before_any_creation(self):
        f=dict(scope=plan.SCOPE,execution_enabled=False,authorization_supplied=False,disabled_case_ids=plan.disabled_ids(),remaining_case_ids_disabled=plan.remaining_ids(),readiness_checks=1,SDKROS_fixture_limit=1,slot=load('cases').cases()[0],runtime_version=[],daemon_architecture='aarch64')
        with patch.object(run.integrity,'verify_files'),patch.object(subprocess,'check_output',side_effect=['[]','aarch64','unrelated']),self.assertRaisesRegex(ValueError,'live containers remain'):run.verify(f)
    def test_sdk_visibility_deadline_never_releases_shutdown(self):
        module=load('sdk_visibility');s=types.SimpleNamespace(out=self.out,name='owned')
        with patch.object(module.time,'monotonic',side_effect=[0,7]),self.assertRaisesRegex(ValueError,'no release'):module.wait_provider_visibility(s,{})
    def test_private_host_import_graph_and_exact_bound_modules(self):
        code="import sys;sys.path[:0]=sys.argv[1:];import run,workload_entry;from campaign_binding import load;print(load('assess').coverage.__module__);print(load('workload').Sidecar.__module__);print(load('cases').cases()[0]['source_seconds'])"
        output=subprocess.check_output([sys.executable,'-c',code,str(HERE),str(ROOT/'tools')],text=True).splitlines();self.assertEqual(output,['_robotweax_campaign_task_lifecycle','_robotweax_campaign_task_sidecar','10'])

    def test_activation_requires_exact_frozen_context_and_grant(self):
        scope=load('calibration_scope');freeze=dict(execution_enabled=False,authorization_supplied=False,output_relative='.local/cal',bundle_relative='.local/bundle',prefix='owned');write(self.out/'freeze.json',freeze);grant=self.out/'grant.json';write(grant,self.grant(run.sha(self.out/'freeze.json')))
        with patch.object(scope,'HERE',self.out),patch.object(scope,'_active',None),patch.object(load('integrity'),'verify_files') as verified:
            scope.activate(grant,freeze);verified.assert_called_once_with(freeze)
            with self.assertRaisesRegex(ValueError,'context differs'):scope.activate(grant,dict(freeze,prefix='foreign'))
            changed=read(grant);changed['SDKROS_fixture_limit']=2;write(grant,changed)
            with self.assertRaises(ValueError):scope.activate(grant,freeze)
    def test_ordinary_python_thread_does_not_count_as_SDK_provider(self):
        out=self.out/'overlay';_,_,_=overlay(out);rows=lines(out/'native-observer/blocked-target-shutdown-stacks.jsonl')[:-1];target=read(out/'operator-bridge-identity.json')
        # Exact calibrated pure Python fixture has no named SDK provider task.
        original=ROOT/'evidence/m3-task-post-sigint-calibration-execution-2026-11-10/run/data';rows=lines(original/'blocked-target-shutdown-stacks.jsonl')[:-1]
        with self.assertRaisesRegex(ValueError,'two SDK provider'):load('sdk_visibility').presence(rows,dict(pid=7,start_ticks=769))
    def test_watchdog_escalation_stays_with_owned_group(self):
        process=types.SimpleNamespace(pid=888,wait=unittest.mock.Mock(side_effect=[subprocess.TimeoutExpired('fixture',240),subprocess.TimeoutExpired('fixture',2),0]))
        with patch.object(run.os,'killpg') as kill,self.assertRaises(ValueError):run.fixture_process([],None,popen=lambda *a,**k:process)
        self.assertEqual(kill.call_args_list,[unittest.mock.call(888,run.signal.SIGTERM),unittest.mock.call(888,run.signal.SIGKILL)])
    def test_sdk_visibility_access_error_fails_before_release(self):
        out=self.out/'overlay';_,_,_=overlay(out);rows=lines(out/'native-observer/blocked-target-shutdown-stacks.jsonl')[:-1];rows[1]['processes'][0]['threads'][1]['task_evidence']['reads']['stack']['result']=dict(status='unavailable',error='PermissionError',errno=13);path=out/'active-sdk-observer.jsonl';jsonl(path,rows);s=types.SimpleNamespace(out=out,name='owned',command=lambda *a,**k:types.SimpleNamespace(returncode=0))
        with self.assertRaises(ValueError):load('sdk_visibility').wait_provider_visibility(s,read(out/'operator-bridge-identity.json'))
        self.assertFalse((out/'sdk-provider-live-proof.json').exists())
    def test_private_matched_runtime_has_exact_local_manifest(self):
        retained=ROOT/'evidence/m3-current-long-preparation-2026-11-10'
        self.assertEqual((HERE/'binary-verification.json').read_bytes(),(retained/'binary-verification.json').read_bytes())
        expected=read(ROOT/'evidence/m3-task-post-sigint-calibration-preparation-2026-11-10/freeze.json')['runtime_layout']
        actual=load('disposition_runtime').matched(ROOT,'socket-disposition');self.assertEqual(actual,dict(expected,calibration=actual['calibration']));self.assertEqual(actual['calibration'],str((HERE/'binary-verification.json').relative_to(ROOT)))
if __name__=='__main__':unittest.main()
