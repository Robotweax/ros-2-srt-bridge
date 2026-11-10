"""Offline complete assessment pipeline, import graph and disabled entrypoints."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from model import ROOT,HERE,overlay,read,write,lines,jsonl,load
import campaign_binding

class CampaignIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name);self.result,self.slot,self.fixture=overlay(self.out);self.assessor=load('assess')
    def assess(self):return self.assessor.assess(self.out,self.result,self.slot)
    def test_complete_modeled_pipeline_preserves_real_combined_profile_gates(self):
        proof=self.assess();self.assertEqual(proof['status'],'passed',proof.get('error'));self.assertTrue(proof['prospective_task_assessment_only']);self.assertFalse(proof['execution_enabled']);self.assertEqual(proof['combined']['gate'],'combined_strict_success');self.assertTrue(proof['profile']['original_commands_and_kernel_settings_verified']);self.assertEqual(proof['operator_observer']['confirmed_task_exits'],0);self.assertEqual(len(proof['operator_observer']['observed_task_disappearances']),1)
    def test_legacy_capture_refused_no_common_gate_or_historical_reclassification(self):
        old=ROOT/'evidence/m3-current-long-execution-2026-11-10/cases/N1-combined-2903/native-observer/blocked-target-shutdown-stacks.jsonl';jsonl(self.out/'native-observer/blocked-target-shutdown-stacks.jsonl',lines(old))
        proof=self.assess();self.assertEqual(proof['status'],'failed');self.assertNotIn('combined',proof)
    def test_failed_metadata_stops_before_common_gates(self):
        path=self.out/'native-observer/blocked-target-shutdown-stacks.jsonl';rows=lines(path);rows[1]['processes'][0]['threads'][0]['task_evidence']['confirmed_exit']=True;jsonl(path,rows)
        with patch.object(self.assessor,'assess_combined',side_effect=AssertionError('must stop')) as common:
            proof=self.assess();self.assertEqual(proof['status'],'failed');common.assert_not_called()
    def test_wrong_activation_hash_or_flags_refused(self):
        for delta in (dict(collector_sha256='wrong'),dict(task_visibility=False)):
            with self.subTest(delta=delta):
                p=self.out/'operator-observer-exec.jsonl';original=p.read_text();events=lines(p);events[1].update(delta);jsonl(p,events);jsonl(self.out/'native-observer/observer-exec.jsonl',events)
                proof=self.assess();self.assertEqual(proof['status'],'failed');self.assertIn('activation binding',proof['error']);p.write_text(original);(self.out/'native-observer/observer-exec.jsonl').write_text(original)
    def test_changed_boot_target_profile_or_event_population_refused(self):
        path=self.out/'operator-observer-exec.jsonl';original=path.read_text()
        for change in ('boot','target','profile','extra'):
            with self.subTest(change=change):
                events=json.loads(json.dumps([json.loads(x) for x in original.splitlines()]))
                if change=='boot':events[1]['boot_id']='foreign'
                if change=='target':events[2]['target']['start_ticks']+=1
                if change=='profile':events[1]['profile_sha256']='wrong'
                if change=='extra':events.append(dict(kind='exec_failed'))
                jsonl(path,events);jsonl(self.out/'native-observer/observer-exec.jsonl',events);self.assertEqual(self.assess()['status'],'failed')
        path.write_text(original);(self.out/'native-observer/observer-exec.jsonl').write_text(original)
    def test_missing_or_divergent_exported_exec_proof_refused(self):
        path=self.out/'native-observer/observer-exec.jsonl';events=lines(path);events[0]['pid']+=1;jsonl(path,events);self.assertEqual(self.assess()['status'],'failed');path.unlink();self.assertEqual(self.assess()['status'],'failed')
    def test_clock_origin_or_permissions_still_fail(self):
        path=self.out/'operator-observer-exec.jsonl';original=path.read_text()
        for change in ('clock','caps'):
            events=[json.loads(x) for x in original.splitlines()]
            if change=='clock':events[1]['time_namespace_offsets']='monotonic 1 0\nboottime 0 0\n'
            else:events[1]['permissions']['CapEff']='0'
            jsonl(path,events);jsonl(self.out/'native-observer/observer-exec.jsonl',events);self.assertEqual(self.assess()['status'],'failed')
        path.write_text(original);(self.out/'native-observer/observer-exec.jsonl').write_text(original)
    def test_original_sensor_command_capture_and_workload_gates_remain_fail_closed(self):
        for mutation in ('inner','sensor','command','capture'):
            result=deepcopy(self.result)
            if mutation=='inner':result['status']='failed'
            if mutation=='sensor':result['results']['typed_errors']=['modeled type error']
            if mutation=='command':result['results']['commands'][0]['new_generation']+=1
            if mutation=='capture':result['captures']['operator']['tcpdump_kernel_drops']=1
            with self.subTest(mutation=mutation):self.assertEqual(self.assessor.assess(self.out,result,self.slot)['status'],'failed')
    def test_profile_tuning_still_refused(self):
        path=self.out/'profile-operator-readback.log';rows=read(path);next(q for q in rows if q['kind']=='netem')['options']['limit']=999;write(path,rows);proof=self.assess();self.assertEqual(proof['status'],'failed');self.assertIn('kernel settings',proof['error'])
    def test_socket_stage_and_launch_gates_still_refuse_missing_proof(self):
        entry=self.fixture.entries['operator','measurement'];path=self.out/entry['trace_path'];stages=lines(path);jsonl(path,[r for r in stages if r['point']!='provider_cleanup_end']);proof=self.assess();self.assertEqual(proof['status'],'failed');self.assertNotIn('combined',proof)
    def test_missing_warmup_launch_remains_failure(self):
        path=self.out/'robot-bridge-launches.json';value=read(path);value['launches'].pop(1);write(path,value);self.assertEqual(self.assess()['status'],'failed')
    def test_cleanup_credential_gate_still_required(self):
        (self.out/'passphrase').touch();proof=self.assess();self.assertEqual(proof['status'],'failed');self.assertIn('credential retained',proof['error'])
    def test_driver_workload_sidecar_and_dispatch_disabled_before_IO(self):
        sidecar=load('sidecar').Sidecar(self.out,self.out/'bundle','owned')
        with patch.object(subprocess,'run',side_effect=AssertionError('no processes')),patch.object(subprocess,'check_output',side_effect=AssertionError('no Docker')):
            for call in (lambda:load('driver').main(),lambda:load('workload').main([]),lambda:sidecar.arm(None),lambda:load('driver').sequence(lambda s:None,lambda s:None,lambda s:None)):
                with self.assertRaisesRegex(ValueError,'disabled|offline integration'):call()
    def test_all38_case_ids_disabled_and_all_old_grants_rejected(self):
        cases=load('cases');self.assertEqual(len(cases.disabled_ids()),38);self.assertFalse(cases.enabled_ids());self.assertFalse(cases.allowed('N1',2903,600))
        for name in ('m3-current-long-execution-2026-11-10','m3-task-post-sigint-calibration-execution-2026-11-10'):
            with self.assertRaises(ValueError):cases.authorize(read(ROOT/'evidence'/name/'authorization.json'),'anything')
    def test_sidecar_command_forwards_explicit_calibrated_flag_and_isolation(self):
        s=load('sidecar').Sidecar(self.out,self.out/'bundle','owned');argv=s.create_argv('owned-operator');self.assertEqual(argv[-2:],['/cal/observer_entry.py','--task-visibility']);self.assertEqual(argv[argv.index('--pid')+1],'container:owned-operator');self.assertEqual(argv[argv.index('--network')+1],'none');self.assertEqual(argv[argv.index('--cap-add')+1],'SYS_ADMIN');self.assertIn('--read-only',argv)
    def test_bound_collector_and_candidate_bytes_match_calibrated_originals(self):
        old=ROOT/'evidence/m3-task-post-sigint-calibration-preparation-2026-11-10'
        for name in ('task_assessment.py','lifecycle.py','shutdown_observer.py','observer_entry.py','observer-seccomp.json','observer-architecture.json'):self.assertEqual((HERE/name).read_bytes(),(old/name).read_bytes(),name)
    def test_private_graph_ignores_poisoned_generic_helpers(self):
        names=('lifecycle','task_assessment','cases','assess','sidecar','launch_readiness','launch_records','launch_assessment','profile_gate','socket_gate','stage_gate','shutdown_observer');poison=types.ModuleType('unrelated')
        source=(HERE/'campaign_binding.py').read_bytes();m=types.ModuleType('independent_campaign_graph');m.__file__=str(HERE/'campaign_binding.py')
        with patch.dict(sys.modules,{n:poison for n in names}):
            exec(compile(source,m.__file__,'exec'),m.__dict__);assessor=m.load('assess');self.assertEqual(assessor.coverage.__module__,'_robotweax_campaign_task_lifecycle');self.assertIs(assessor.coverage.__globals__['assess_metadata'],m.load('task_assessment').assess_metadata);self.assertTrue(all(sys.modules[n] is poison for n in names))
    def test_loader_rejects_changed_source_even_after_cache_hit(self):
        load('lifecycle')
        with patch.object(campaign_binding.Path,'read_bytes',return_value=b'changed'),self.assertRaisesRegex(ValueError,'bound campaign source differs'):load('lifecycle')
    def test_unregistered_path_rejected(self):
        with self.assertRaises(ValueError):load('../lifecycle')
    def test_real_retained_calibration_passes_exact_bound_lifecycle(self):
        data=ROOT/'evidence/m3-task-post-sigint-calibration-execution-2026-11-10/run/data';rows=lines(data/'blocked-target-shutdown-stacks.jsonl');stages=lines(data/'task-stages.jsonl');child=read(data/'result.json')['shutdown']['children'][0];child=dict(child,start_ticks=769)
        proof=load('lifecycle').coverage(rows,child,stages);self.assertEqual(len(proof['observed_task_disappearances']),1);self.assertEqual(proof['post_signal_samples'],3);self.assertEqual(proof['confirmed_task_exits'],0)

    def test_old_freeze_refused_before_any_runtime_query(self):
        frozen=read(ROOT/'evidence/m3-current-long-preparation-2026-11-10/freeze.json')
        with patch.object(subprocess,'check_output',side_effect=AssertionError('no Docker')),self.assertRaisesRegex(ValueError,'old freezes refused'):load('driver').verify(frozen)
    def test_native_bundle_has_exact_activation_binding_and_unchanged_policy(self):
        bundle=load('observer_bundle');files=bundle.sources();self.assertEqual(set(files),{'observer_entry.py','observer-seccomp.json','observer-architecture.json','shutdown_observer.py','collector-binding.json','m3_observer_filtering.py'});binding=bundle.binding();self.assertTrue(binding['task_visibility']);self.assertEqual(binding['candidate_sha256']['lifecycle.py'],campaign_binding.PINNED['lifecycle']);self.assertTrue(read(files['collector-binding.json'])['task_visibility'])
    def test_actual_sidecar_arm_body_under_modeled_Docker_only(self):
        import ast
        sidecar=load('sidecar');s=sidecar.Sidecar(self.out,self.out/'readonly-model-bundle','owned');calls=[]
        host=dict(Privileged=False,ReadonlyRootfs=True,NetworkMode='none',UsernsMode='',CapDrop=['ALL'],CapAdd=['SYS_ADMIN'],PidMode='container:owned-operator',SecurityOpt=['no-new-privileges=true','seccomp='+json.dumps(read(HERE/'observer-seccomp.json'))])
        def command(argv,**kwargs):
            calls.append(argv);text=''
            if argv[1]=='inspect':text=json.dumps([dict(HostConfig=host,Mounts=[dict(Destination='/cal',RW=False),dict(Destination='/out',RW=True)])])
            return types.SimpleNamespace(returncode=0,stdout=text,stderr='')
        s.command=command;tree=ast.parse((HERE/'sidecar.py').read_text());method=next(n for c in tree.body if isinstance(c,ast.ClassDef) and c.name=='Sidecar' for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='arm');self.assertIsInstance(method.body[0],ast.Raise);method.body=method.body[1:];scope=dict(sidecar.__dict__);exec(compile(ast.Module(body=[method],type_ignores=[]),'offline-sidecar-body','exec'),scope);scope['arm'](s,types.SimpleNamespace(containers={'operator':'owned-operator'}))
        self.assertTrue(s.started);creates=[a for a in calls if a[1]=='create'];self.assertEqual(len(creates),1);self.assertEqual(creates[0][-1],'--task-visibility')
    def test_historical_N1_failure_reproduces_with_original_gate(self):
        import importlib.util
        path=ROOT/'evidence/m3-current-long-execution-2026-11-10/cases/N1-combined-2903';launch=read(path/'strict-assessment.json')['launches']['operator']['measurement'];rows=lines(path/'native-observer/blocked-target-shutdown-stacks.jsonl');spec=importlib.util.spec_from_file_location('frozen_original_lifecycle',ROOT/'evidence/m3-current-long-preparation-2026-11-10/lifecycle.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
        with self.assertRaisesRegex(ValueError,'live target kernel stack unavailable'):old.coverage(rows,launch['child'],launch['stages']['rows'])
        with self.assertRaisesRegex(ValueError,'schema1 required'):load('lifecycle').coverage(rows,launch['child'],launch['stages']['rows'])
    def test_fresh_host_import_order_resolves_private_campaign_graph(self):
        code="import sys;sys.path[:0]=sys.argv[1:];import run;from campaign_binding import load;print(load('assess').coverage.__module__);print(load('workload').Sidecar.__module__);print(len(load('cases').disabled_ids()))"
        output=subprocess.check_output([sys.executable,'-c',code,str(HERE),str(ROOT/'tools')],text=True).splitlines();self.assertEqual(output,['_robotweax_campaign_task_lifecycle','_robotweax_campaign_task_sidecar','38'])
if __name__=='__main__':unittest.main()
