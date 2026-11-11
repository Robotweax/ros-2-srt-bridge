import importlib.util
import json
from pathlib import Path
import tempfile
import sys
import threading
import unittest
from unittest.mock import patch
from offline_flow import Flow,ROOT,HERE,read

class WholeFlowTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name)
    def test_complete_startup_negative_warmup_restart_observer_and_shutdown(self):
        flow=Flow(self.out).run()
        self.assertIsNone(flow.failure,str(flow.failure));proof=flow.assess()
        self.assertEqual(set(proof['robot']),{'warmup','measurement'})
        self.assertEqual([e[1] for e in flow.events if e[0]=='spawn'],['operator-bridge-0','simulator','wrong-hash','robot-bridge-1','robot-bridge-2'])
        names=[e[0] for e in flow.events];self.assertLess(names.index('observer_arm'),names.index('finish_rpc'))
        child_names=[e[1] for e in flow.events if e[0]=='sigint'];self.assertEqual(child_names,['robot-bridge-1','robot-bridge-2','simulator','operator-bridge-0'])
        self.assertTrue(all(p.returncode is not None for p in flow.children));self.assertFalse(any(e[0]=='kill' for e in flow.events));self.assert_cleanup(flow)
        self.assertEqual([e['purpose'] for e in read(self.out/'robot-bridge-launches.json')['launches']],['negative_type_hash','warmup','measurement'])
        self.assertEqual([e[1] for e in flow.events if e[0]=='command'],['start','pause','reset_link','resume','pause'])
        self.assertTrue((self.out/'operator-final-bridge-state.json').exists());self.assertTrue((self.out/'robot-final.json').exists())
        self.assertEqual(flow.close_calls,2)
    def assert_cleanup(self,flow):
        self.assertTrue(all(p.returncode is not None for p in flow.children));self.assertTrue(flow.lab_removed);self.assertFalse(flow.observer_armed);self.assertFalse((self.out/'passphrase').exists())
        if flow.finish_thread:self.assertFalse(flow.finish_thread.is_alive())
    def test_actual_production_lifecycle_methods_and_host_blocks_are_executed(self):
        seen=set();files=set()
        def profile(frame,event,arg):
            if event=='call':
                files.add(frame.f_code.co_filename)
                if frame.f_code.co_filename in ('actual-driver','actual-scenario'):seen.add(frame.f_code.co_qualname)
        before=sys.getprofile();thread_before=threading.getprofile()
        try:
            sys.setprofile(profile);threading.setprofile(profile)
            flow=Flow(self.out).run()
        finally:sys.setprofile(before);threading.setprofile(thread_before)
        self.assertIsNone(flow.failure)
        required={'Driver.robot','Driver.robot_command','Driver.wait','Driver.stop','Driver.cleanup','Benchmark.start_bridge','Benchmark.robot_action','Benchmark.stop','Benchmark.cleanup','Diagnostic.start','Diagnostic.start_bridge','Diagnostic.robot_command','Diagnostic.stop','Diagnostic.cleanup'}
        self.assertTrue(required<=seen,required-seen)
        self.assertTrue({'workload-arm-release','workload-observer-finally','workload-lab-cleanup','workload-credential-cleanup'}<=files)
        self.assertIn(str(HERE/'bridge_exec.py'),files)
        self.assert_cleanup(flow)
    def test_complete_flow_full_lifecycle_assessor_with_modeled_observer(self):
        flow=Flow(self.out).run();self.assertIsNone(flow.failure);flow.assess()
        spec=importlib.util.spec_from_file_location('stabilized_assessor',HERE/'assess.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with patch.object(module,'assess_combined',return_value=dict(scope='outside lifecycle model')):
            proof=module.assess(self.out,dict(status='passed'),dict())
        self.assertEqual(proof['status'],'passed',proof.get('error'));self.assertEqual(proof['operator_observer']['nonempty_kernel_stacks'],1);self.assert_cleanup(flow)
    def test_spawn_failure_retains_record_and_closes_logs(self):
        flow=Flow(self.out,'spawn').run();self.assertIsNotNone(flow.failure);self.assert_cleanup(flow)
        records=[read(p) for p in (self.out/'launch-readiness').glob('*.parent-failure.json')]
        self.assertTrue(any(r['phase']=='spawn' and r['snapshot']['pid'] is None for r in records));self.assertFalse(any(e[0]=='observer_arm' for e in flow.events))
    def test_capability_failure_stops_before_restart_and_retains_status(self):
        flow=Flow(self.out,'capability').run();self.assertIsNotNone(flow.failure);self.assert_cleanup(flow)
        self.assertFalse(any(e[:2]==('spawn','robot-bridge-2') for e in flow.events))
        records=[read(p) for p in (self.out/'launch-readiness').glob('*.wrapper-failure.json')]
        self.assertTrue(records);self.assertNotEqual(records[0]['snapshot']['permissions']['CapEff'],'0')
    def test_unexpected_negative_success_stops_before_real_robot_start(self):
        flow=Flow(self.out,'negative_success').run();self.assertIsNotNone(flow.failure);self.assert_cleanup(flow)
        self.assertFalse(any(e[:2]==('spawn','robot-bridge-1') for e in flow.events));self.assertFalse((self.out/'robot-ready.json').exists())
    def test_warmup_shutdown_failure_never_launches_replacement(self):
        flow=Flow(self.out,'warmup_timeout').run();self.assertIsNotNone(flow.failure);self.assert_cleanup(flow)
        self.assertFalse(any(e[:2]==('spawn','robot-bridge-2') for e in flow.events));self.assertIn(('wait_timeout','robot-bridge-1',5),flow.events)
    def test_observer_close_failure_not_masked_by_successful_cleanup(self):
        flow=Flow(self.out,'observer_close').run();self.assertIsNotNone(flow.failure);self.assert_cleanup(flow)
        self.assertEqual(str(flow.failure),'synthetic observer close failure');self.assertEqual(flow.close_calls,2)
    def test_host_observer_failure_cannot_be_hidden_by_clean_child_lifecycle(self):
        flow=Flow(self.out,'observer_close').run();self.assertIsNotNone(flow.failure);flow.assess()
        spec=importlib.util.spec_from_file_location('failed_host_assessor',HERE/'assess.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with patch.object(module,'assess_combined',side_effect=AssertionError('must not advance')):
            proof=module.assess(self.out,dict(status='failed',error=str(flow.failure)),dict())
        self.assertEqual(proof['status'],'failed');self.assertIn('workload failed',proof['error'])
    def test_failed_flows_never_pass_lifecycle_assessment(self):
        for fault in ('observer_arm','trace_collision','shutdown_timeout','capability','negative_success','warmup_timeout','spawn'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temp:
                flow=Flow(Path(temp),fault).run();self.assertIsNotNone(flow.failure)
                with self.assertRaises((ValueError,KeyError,OSError)):flow.assess()
    def test_observer_arm_failure_never_releases_or_finishes_rpc(self):
        flow=Flow(self.out,'observer_arm').run()
        self.assertIsNotNone(flow.failure);self.assertFalse((self.out/'n0-shutdown-release').exists());self.assertFalse(any(e[0]=='finish_rpc' for e in flow.events));self.assertTrue(all(p.returncode is not None for p in flow.children));self.assert_cleanup(flow)
    def test_warmup_trace_collision_fails_once_without_restart_retry(self):
        flow=Flow(self.out,'trace_collision').run()
        self.assertIsNotNone(flow.failure);self.assertEqual(sum(e[:2]==('spawn','robot-bridge-2') for e in flow.events),1);self.assertFalse(any(e[0]=='observer_arm' for e in flow.events))
        self.assertTrue(all(p.returncode is not None for p in flow.children));self.assert_cleanup(flow)
    def test_final_shutdown_timeout_preserves_forced_failure(self):
        flow=Flow(self.out,'shutdown_timeout').run()
        self.assertIsNotNone(flow.failure);self.assertEqual(sum(e[:2]==('spawn','robot-bridge-2') for e in flow.events),1)
        rows=read(self.out/'robot-child-shutdown.json')['children'];final=next(r for r in rows if r.get('purpose')=='measurement')
        self.assertFalse(final['passed']);self.assertTrue(final['forced_kill']);self.assertEqual(final['returncode'],-9)
        self.assertTrue(all(p.returncode is not None for p in flow.children));self.assert_cleanup(flow)

if __name__=='__main__':unittest.main()
