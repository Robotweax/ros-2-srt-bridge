import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import m3_campaign_dispatcher as campaign
from m3_source_preflight import sha,write,source_inventory


class CampaignDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.out=self.root/'.local/new-campaign'
        self.cases=campaign.slots();self.freeze=dict(case_ids=[s['id'] for s in self.cases],execution_authorized=False)
        self.path=self.root/'freeze.json';write(self.path,self.freeze)
        self.grant=dict(schema_version=1,execution_authorized=True,freeze_sha256=sha(self.path),case_ids=self.freeze['case_ids'],output_relative='.local/new-campaign')
    def test_all_38_cases_map_to_single_case_adapters_without_tuning(self):
        specs=[campaign.invocation(s) for s in self.cases]
        self.assertEqual({name:sum(s['adapter']==name for s in specs) for name in ('n3','combined','native_n4','ros_n4')},dict(n3=9,combined=10,native_n4=13,ros_n4=6))
        query=specs[22];self.assertEqual(query['kwargs']['phase'],'query');self.assertEqual(query['kwargs']['hold_seconds'],2)
        for s in specs:
            if s['adapter']=='combined':
                self.assertIn('--skip-build',s['argv']);self.assertIn(campaign.IMAGE,s['argv'])
                for flag in ('--build-image','--root-loss-burst','--control-egress-fault','--probe-diagnostics','--neighbor-mode','--arp-packet-trace'):self.assertNotIn(flag,s['argv'])
        self.assertEqual(specs[26]['kwargs']['mode'],'before')
    def test_authorization_must_bind_exact_freeze_order_and_fresh_output(self):
        campaign.authorize(self.grant,self.path,self.freeze,self.out,self.root)
        for key,value in [('execution_authorized',False),('freeze_sha256','other'),('case_ids',list(reversed(self.freeze['case_ids']))),('output_relative','.local/other')]:
            with self.subTest(key=key),self.assertRaises(ValueError):campaign.authorize(dict(self.grant,**{key:value}),self.path,self.freeze,self.out,self.root)
        self.out.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError,'already exists'):campaign.authorize(self.grant,self.path,self.freeze,self.out,self.root)
    def test_preparation_never_dispatches_and_freeze_is_disabled(self):
        selected=dict(layout=dict(calibration_sha256='candidate'),binding={'sdk':'selected'})
        with patch.object(campaign,'native_layout',return_value=selected),patch.object(campaign,'slots',return_value=self.cases),patch.object(campaign,'source_inventory',return_value={'source':'hash'}),patch.object(campaign,'sha',return_value='hash'),patch.object(campaign,'dispatch_slot') as launch:
            frozen=campaign.prepare(self.root)
        launch.assert_not_called();self.assertFalse(frozen['execution_authorized']);self.assertFalse(frozen['automatic_start']);self.assertEqual(len(frozen['invocations']),38)
    def test_unauthorized_execute_never_preflights_or_creates_output(self):
        with patch.object(campaign,'verify_freeze') as preflight,patch.object(campaign,'dispatch_slot') as launch,self.assertRaisesRegex(ValueError,'not authorized'):
            campaign.execute(self.path,{},self.out,self.root)
        preflight.assert_not_called();launch.assert_not_called();self.assertFalse(self.out.exists())
    def run_mocked(self,assess,verify=None):
        def dispatch(slot,out,root):
            out.mkdir();return dict(run=str(out.relative_to(root)),inner_status='passed')
        with patch.object(campaign,'slots',return_value=self.cases),patch.object(campaign,'verify_freeze',side_effect=verify),patch.object(campaign,'dispatch_slot',side_effect=dispatch) as launch,patch.object(campaign,'assess_case',side_effect=assess):
            result=campaign.execute(self.path,self.grant,self.out,self.root)
        return result,launch
    def test_full_mocked_cohort_assesses_before_next_dispatch_and_never_accepts_m3(self):
        checked=[]
        def assess(run,slot,freeze):
            self.assertEqual(len(list(self.out.glob('N*-assessment.json'))),len(checked))
            checked.append(slot['id']);return dict(status='passed')
        result,launch=self.run_mocked(assess)
        self.assertEqual(launch.call_count,38);self.assertEqual(checked,self.freeze['case_ids']);self.assertEqual(result['status'],'passed');self.assertFalse(result['complete_M3_acceptance'])
        self.assertEqual(json.loads((self.out/'campaign.json').read_text()),result)
    def test_independent_cleanup_rejection_stops_even_if_inner_harness_passed(self):
        result,launch=self.run_mocked(ValueError('owned cleanup incomplete'))
        self.assertEqual(launch.call_count,1);self.assertEqual(result['rows'][0]['produced']['inner_status'],'passed');self.assertEqual(result['rows'][0]['status'],'failed')
        self.assertTrue(all(s['status']=='not_executed' for s in result['rows'][1:]))
    def test_postrun_drift_prevents_assessment_or_next_case(self):
        checks=[]
        def verify(*args):
            checks.append(1)
            if len(checks)==3:raise ValueError('source drift after case')
        with patch.object(campaign,'assess_case') as assessor:
            result,launch=self.run_mocked(assessor,verify)
        assessor.assert_not_called();self.assertEqual(launch.call_count,1);self.assertEqual(result['rows'][1]['status'],'not_executed')
    def test_initial_drift_refuses_before_output(self):
        with patch.object(campaign,'prepare',return_value=dict(self.freeze,source_sha256={'changed':'x'})),patch.object(campaign,'dispatch_slot') as launch,self.assertRaisesRegex(ValueError,'freeze drift'):
            campaign.execute(self.path,self.grant,self.out,self.root)
        launch.assert_not_called();self.assertFalse(self.out.exists())
    def test_source_inventory_binds_root_cmake_and_detects_added_source(self):
        (self.root/'CMakeLists.txt').write_text('fixed')
        before=source_inventory(self.root);self.assertIn('CMakeLists.txt',before)
        (self.root/'tools').mkdir();(self.root/'tools/new.py').write_text('new')
        self.assertNotEqual(source_inventory(self.root),before)
    def test_live_adapter_boundaries_are_mocked_and_use_exact_output(self):
        examples=[(self.cases[0],'m3_ros_multiroute.run'),(self.cases[9],'run_m3.main'),(self.cases[22],'m3_n4.run_case'),(self.cases[26],'m3_n4_ros.run_case')]
        for slot,target in examples:
            out=self.root/slot['id']
            def closed(*args,**kwargs):
                out.mkdir();write(out/('run.json' if slot['stage']=='N0' else 'result.json'),dict(status='passed'))
            with self.subTest(slot=slot['id']),patch(target,side_effect=closed) as runner:
                result=campaign.dispatch_slot(slot,out,self.root)
                self.assertEqual(result['inner_status'],'passed');self.assertEqual(runner.call_count,1)
                if slot['stage']=='N0':self.assertEqual(runner.call_args.args[0][-2:],['--output',str(out)])
                else:self.assertEqual(runner.call_args.args[0],out)
    def test_combined_runner_refuses_existing_output_before_lab(self):
        import run_m3
        self.out.mkdir(parents=True)
        with patch.object(run_m3,'ROOT',self.root),patch.object(run_m3,'NetworkLab') as lab,self.assertRaises(FileExistsError):
            run_m3.main(['--skip-build','--runtime-layout','sender-reconcile','--output',str(self.out)])
        lab.assert_not_called()
    def test_combined_runner_refuses_output_outside_repository_before_lab(self):
        import run_m3
        with patch.object(run_m3,'ROOT',self.root/'repository'),patch.object(run_m3,'NetworkLab') as lab,self.assertRaises(ValueError):
            run_m3.main(['--skip-build','--runtime-layout','sender-reconcile','--output',str(self.out)])
        lab.assert_not_called();self.assertFalse(self.out.exists())
    def test_cli_requires_explicit_execute_grant(self):
        with patch.object(campaign,'dispatch_slot') as launch,self.assertRaises(SystemExit):campaign.main(['--freeze',str(self.path),'--execute'])
        launch.assert_not_called()


if __name__=='__main__':unittest.main()
