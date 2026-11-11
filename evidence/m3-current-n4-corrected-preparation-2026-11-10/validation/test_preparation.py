"""Offline contracts only: exact N4 mapping, mocked runners, synthetic outputs."""
import ast
import copy
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
    s=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
plan=load('current_n4_cases','cases.py')
def driver():
    with patch.dict(sys.modules,cases=plan):return load('current_n4_driver','run.py')

class PreparationTests(unittest.TestCase):
    def grant(self):return dict(scope=plan.SCOPE,freeze_sha256='new',execute=True,case_ids=[s['id'] for s in plan.cases()],disabled_case_ids=plan.disabled_ids(),completed_case_ids_not_reexecuted=plan.completed_ids(),runtime_layout='socket-disposition',native_hold_seconds=2,historical_failures_preserved=True,no_tuning=True,no_automatic_retries=True,stop_first_failed_gate=True)
    def test_exact19_original_order_and_disjoint9_disabled10_complete(self):
        rows=plan.cases();old=plan.original();self.assertEqual([s['id'] for s in rows],[s['id'] for s in old if s['stage']=='N4'])
        self.assertEqual([s['ordinal'] for s in rows],list(range(11,30)));self.assertEqual(len(plan.disabled_ids()),9);self.assertEqual(len(plan.completed_ids()),10)
        self.assertEqual(len(set([s['id'] for s in rows]+plan.disabled_ids()+plan.completed_ids())),38)
    def test_exact13_native_and6_ROS_adapters(self):
        specs=[plan.invocation(s) for s in plan.cases()];self.assertEqual([x['adapter'] for x in specs],['native']*13+['ros']*6)
        self.assertEqual(specs[12]['kwargs'],dict(phase='query',direction='both',hold_seconds=2,runtime_layout='socket-disposition'))
        self.assertEqual([s['kwargs']['mode'] for s in specs[13:]],['both','to-robot','to-operator','before','effect','committed'])
    def test_new_exact_grant_and_old_grants_refused(self):
        good=self.grant();plan.authorize(good,'new')
        for delta in (dict(scope='old'),dict(freeze_sha256='old'),dict(execute=False),dict(case_ids=good['case_ids'][::-1]),dict(case_ids=good['case_ids'][:-1]),dict(disabled_case_ids=[]),dict(completed_case_ids_not_reexecuted=[]),dict(native_hold_seconds=6),dict(runtime_layout='sender-reconcile'),dict(no_tuning=False),dict(no_automatic_retries=False),dict(stop_first_failed_gate=False),dict(extra=True)):
            with self.assertRaises(ValueError):plan.authorize(dict(good,**delta),'new')
        old=json.loads((ROOT/'evidence/m3-current-n0-stable-execution-2026-11-10/authorization.json').read_text())
        with self.assertRaises(ValueError):plan.authorize(old,'new')
    def test_modified_slot_and_undeclared_query_direction_refused(self):
        for delta in (dict(hold_seconds=6),dict(seed=2903),dict(runtime_layout='baseline'),dict(id='N1-extra')):
            with self.assertRaises(ValueError):plan.invocation(dict(plan.cases()[0],**delta))
        with self.assertRaises(ValueError):plan.invocation(dict(plan.cases()[12],direction='to-robot'))
    def test_missing_grant_never_accesses_Docker(self):
        m=driver()
        with patch.object(m.sys,'argv',['run.py']),patch.object(m.subprocess,'check_output',side_effect=AssertionError('no Docker')),self.assertRaises(SystemExit):m.main()
    def test_each_failure_position_stops_before_next_produce(self):
        m=driver()
        for failed in range(19):
            seen=[];assessed=[]
            def produce(s):seen.append(s['id']);return 'inner-pass'
            def assess(s,value):assessed.append(s['id']);return dict(status='failed' if s['id']==plan.cases()[failed]['id'] else 'passed')
            result=m.sequence(produce,assess,lambda r:None)
            self.assertEqual(seen,[s['id'] for s in plan.cases()[:failed+1]]);self.assertEqual(seen,assessed);self.assertTrue(all(r['status']=='not_executed' for r in result['rows'][failed+1:]))
    def test_all19_once_and_assessment_before_next_case(self):
        m=driver();events=[]
        result=m.sequence(lambda s:events.append(('produce',s['id'])),lambda s,p:events.append(('assess',s['id'])) or dict(status='passed'),lambda r:None)
        self.assertEqual(events,[(kind,s['id']) for s in plan.cases() for kind in ('produce','assess')]);self.assertEqual(result['status'],'passed');self.assertFalse(result['complete_M3_acceptance'])
    def test_producer_error_refusal_and_existing_output_no_retry(self):
        m=driver();seen=[]
        def fail(s):seen.append(s['id']);raise RuntimeError('startup failed')
        result=m.sequence(fail,lambda *a:None,lambda r:None);self.assertEqual(len(seen),1);self.assertEqual(result['status'],'failed')
        with tempfile.TemporaryDirectory() as path:
            with self.assertRaises(ValueError):m.fresh_output(Path(path))
    def test_native_guard_refuses6s_unknown_phase_and_old_layout_before_binding(self):
        m=load('current_n4_native','native_adapter.py')
        for args in (dict(phase='admission',direction='both',hold_seconds=6,runtime_layout='socket-disposition'),dict(phase='query',direction='to-robot',runtime_layout='socket-disposition'),dict(phase='bad',direction='both',runtime_layout='socket-disposition'),dict(phase='admission',direction='both',runtime_layout='sender-reconcile')):
            with patch.object(m,'native_layout',side_effect=AssertionError('no fixture access')),self.assertRaises(ValueError):m.run_case(Path('/unused'),**args)
    def test_ROS_guard_refuses_other_modes_and_builds(self):
        m=load('current_n4_ROS','ros_adapter.py')
        for mode,layout in (('bad','socket-disposition'),('before','baseline')):
            with patch.object(m,'matched',side_effect=AssertionError('no build access')),self.assertRaises(ValueError):m.run_case(Path('/unused'),mode,layout)
    def test_dispatch19_exact_single_case_call_boundaries(self):
        m=driver();native=load('native_adapter','native_adapter.py');ros=load('ros_adapter','ros_adapter.py')
        with patch.dict(sys.modules,native_adapter=native,ros_adapter=ros):
            for s in plan.cases():
                selected=native if not s['id'].startswith('N4-ROS-') else ros
                with patch.object(selected,'run_case',return_value=dict(status='passed')) as run:
                    out=Path('/synthetic')/s['id'];self.assertEqual(m.dispatch(s,out)['status'],'passed');run.assert_called_once_with(out,**plan.invocation(s)['kwargs'])
    def test_ROS_CLI_requires_current_prefix_before_rclpy(self):
        for file in ('ros_sensor.py','ros_crash.py'):
            tree=ast.parse((HERE/file).read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
            import argparse
            marker=RuntimeError('parser accepted; no ROS initialization')
            rclpy=types.SimpleNamespace(init=lambda:(_ for _ in ()).throw(marker))
            namespace=dict(argparse=argparse,rclpy=rclpy)
            exec(compile(ast.Module(body=[node],type_ignores=[]),file,'exec'),namespace)
            args=[file,'--role','robot','--run','/unused','--peer','offline']+(['--case','before'] if file=='ros_crash.py' else [])
            for extra in ([],['--ros-install','install/m3-sender-reconcile-ros']):
                with patch.object(sys,'argv',args+extra),self.assertRaises(SystemExit):namespace['main']()
            with patch.object(sys,'argv',args+['--ros-install','install/m3-socket-disposition-ros']),self.assertRaisesRegex(RuntimeError,'parser accepted'):namespace['main']()
    def test_phase_kernel_crash_and_ROS_workloads_remain_unchanged(self):
        for file,source,names in [('native_adapter.py',ROOT/'tools/m3_n4.py',('network','check_outcome')),('ros_adapter.py',ROOT/'tools/m3_n4_ros.py',('check_crash',)),('ros_sensor.py',ROOT/'ros2/robotweax_srt_bridge_demo/scripts/m3_ros_n4_sensor.py',('Freshness',)),('ros_crash.py',ROOT/'ros2/robotweax_srt_bridge_demo/scripts/m3_ros_n4_crash.py',('Crash',))]:
            def nodes(path):return {n.name:ast.dump(n) for n in ast.parse(path.read_text()).body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
            a,b=nodes(HERE/file),nodes(source)
            for name in names:self.assertEqual(a[name],b[name],name)
    def test_cleanup_records_only_owned_names_and_deletes_credential(self):
        m=load('current_n4_emergency','emergency_cleanup.py')
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);name='ros2-srt-m3-offline';(out/'network.json').write_text(json.dumps(dict(network=name,containers={r:name+'-'+r for r in ('operator','robot')})));(out/'passphrase').touch();calls=[]
            def command(argv,**kwargs):calls.append(argv);return types.SimpleNamespace(returncode=0,stdout='',stderr='')
            m.cleanup(out,command);self.assertFalse((out/'passphrase').exists());self.assertEqual(calls,[['docker','rm','-f',name+'-operator'],['docker','rm','-f',name+'-robot'],['docker','network','rm',name]])
            value=json.loads((out/'network.json').read_text());value['containers']['operator']='foreign';(out/'network.json').write_text(json.dumps(value))
            with self.assertRaises(ValueError):m.cleanup(out,command)
    def test_postflight_credential_and_drift_refuse_before_next_case(self):
        m=driver()
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);(out/'network.json').write_text(json.dumps(dict(network='owned',containers=dict(operator='one',robot='two'))));(out/'passphrase').touch()
            with patch.object(m.subprocess,'check_output',return_value=''),patch.object(m,'verify') as verify:
                with self.assertRaises(ValueError):m.postflight(out,{})
                verify.assert_not_called()
            (out/'passphrase').unlink()
            with patch.object(m.subprocess,'check_output',return_value=''),patch.object(m,'verify',side_effect=ValueError('hash drift')),self.assertRaises(ValueError):m.postflight(out,{})
    def test_current_provenance_rejects_old_build_or_changed_source(self):
        with patch.dict(sys.modules,cases=plan):m=load('current_n4_assess','assess.py')
        layout=dict(name='socket-disposition',calibration_sha256='manifest');freeze=dict(schema_version=1,runtime_layout=layout,candidate_manifest_sha256='manifest',source_sha256={'source':'sha'})
        from m3_source_preflight import IMAGE
        record=dict(runtime_layout=layout,image=IMAGE,source_sha256={'source':'sha'});m.provenance(record,freeze)
        for delta in (dict(runtime_layout=dict(layout,name='sender-reconcile')),dict(source_sha256={'source':'changed'}),dict(image='other')):
            with self.assertRaises(ValueError):m.provenance(dict(record,**delta),freeze)
    def test_current_fixture_metadata_is_bound_without_execution(self):
        m=load('current_n4_binding','n4_fixture.py');selected=m.native_layout(ROOT,'socket-disposition');self.assertEqual(selected['binding']['sdk'],'install/bridge-socket-disposition');self.assertEqual(len(selected['binding']['files']),37)
        with patch.object(m,'matched',side_effect=AssertionError('no fallback')),self.assertRaises(ValueError):m.native_layout(ROOT,'sender-reconcile')
    def mocked_main(self,fail=None):
        m=driver();events=[]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);here=root/'prepared';here.mkdir();out=root/'.local/cohort';out.parent.mkdir()
            freeze=dict(execution_enabled=False,cases=plan.cases(),disabled_case_ids=plan.disabled_ids(),completed_case_ids_not_reexecuted=plan.completed_ids(),output_relative='.local/cohort')
            (here/'freeze.json').write_text(json.dumps(freeze));good=self.grant()
            from m3_source_preflight import sha
            good['freeze_sha256']=sha(here/'freeze.json');(root/'grant.json').write_text(json.dumps(good))
            def dispatch(slot,target):
                target.mkdir();events.append(('produce',slot['id']));return dict(status='passed')
            def assess(target,slot,frozen):
                events.append(('assess',slot['id']))
                if fail==slot['id']:raise ValueError('strict outcome rejected')
                return dict(status='passed')
            def post(target,frozen):events.append(('postflight',target.name))
            fake=types.ModuleType('assess');fake.assess_case=assess
            with patch.dict(sys.modules,assess=fake),patch.object(m,'ROOT',root),patch.object(m,'HERE',here),patch.object(m,'verify'),patch.object(m,'dispatch',side_effect=dispatch),patch.object(m,'postflight',side_effect=post),patch.object(m.sys,'argv',['run.py','--authorization',str(root/'grant.json')]):
                status=m.main()
            return status,events,json.loads((out/'cohort.json').read_text())
    def test_full_driver_runs_only_mocked19_with_postflight_before_advancement(self):
        status,events,report=self.mocked_main()
        self.assertEqual(status,0);self.assertEqual(events,[(kind,s['id']) for s in plan.cases() for kind in ('produce','assess','postflight')]);self.assertEqual(len(report['rows']),19);self.assertFalse(report['M3_complete'])
    def test_full_driver_preserves_failed_case_postflight_and_disables_tail(self):
        failed=plan.cases()[12]['id'];status,events,report=self.mocked_main(failed)
        self.assertEqual(status,1);self.assertEqual(events[-3:],[('produce',failed),('assess',failed),('postflight',failed)]);self.assertEqual(report['rows'][12]['status'],'failed');self.assertTrue(all(r['status']=='not_executed' for r in report['rows'][13:]));self.assertEqual(report['other_unexecuted_cases_disabled'],9)
    def test_inner_failure_cannot_reach_outcome_checker(self):
        with patch.dict(sys.modules,cases=plan):m=load('current_n4_fail_assess','assess.py')
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);(out/'result.json').write_text(json.dumps(dict(status='failed')));(out/'provenance.json').write_text('{}')
            with patch.object(m,'provenance'),patch.object(m,'assess_native_n4',side_effect=AssertionError('cannot advance')),self.assertRaises(ValueError):m.assess_case(out,plan.cases()[0],{})

if __name__=='__main__':unittest.main()
