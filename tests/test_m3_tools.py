#!/usr/bin/env python3
import copy
import json
import struct
import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from m3_network import PROFILES, SEEDS
from m3_capture import classify, summarize
from m3_accounting import summarize_window
from m3_results import percentiles, summarize_commands, summarize_resources, summarize_gaps


class ProfileTests(unittest.TestCase):
    def test_matrix_cannot_substitute_random_loss_for_fec_fault(self):
        with self.assertRaisesRegex(ValueError, 'deterministic'):
            PROFILES['N3'].commands(SEEDS[0])

    def test_profiles_and_bounded_shared_bottleneck(self):
        n1 = PROFILES['N1'].commands(1701)[0]
        self.assertIn('20ms', n1); self.assertIn('5ms', n1); self.assertIn('1%', n1)
        self.assertEqual(n1[-2:], ['seed', '1701'])
        n2 = PROFILES['N2'].commands(2903)[0]
        self.assertIn('60ms', n2); self.assertIn('15ms', n2); self.assertIn('3%', n2)
        n5 = PROFILES['N5'].commands(4211)
        self.assertIn('512kbit', n5[0]); self.assertIn('32768', n5[0]); self.assertIn('1:1', n5[1])
        self.assertIn('16', n5[1])
        for p in PROFILES.values():
            for seed in (0, -1, 2**32):
                with self.assertRaises(ValueError):p.commands(seed)


class CaptureTests(unittest.TestCase):
    def test_parity_and_source_are_distinct(self):
        self.assertEqual(classify(struct.pack('!IIII',7,0xc0000000,0,1),40000,10081),'sensor_fec_parity')
        self.assertEqual(classify(struct.pack('!IIII',7,0xc0000001,0,1),40000,10081),'sensor_source_data')
        self.assertEqual(classify(struct.pack('!IIII',0x80000000,0,0,1),40000,10081),'sensor_srt_control')
        self.assertEqual(classify(b'RTPS'+b'0'*12,7400,7410),'dds_rtps')

    def test_truncated_and_non_ethernet_capture_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'capture'
            p.write_bytes(b'\xd4\xc3\xb2\xa1')
            with self.assertRaisesRegex(ValueError,'truncated'):summarize([p],'10.0.0.1')
            p.write_bytes(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,113))
            with self.assertRaisesRegex(ValueError,'Ethernet'):summarize([p],'10.0.0.1')


class ResultTests(unittest.TestCase):
    def test_censored_commands_are_counted(self):
        commands=[dict(terminal=4,reason=0,submitted_monotonic_ns=0,result_observed_monotonic_ns=1000000),
                  dict(submission=0),dict(terminal='not_admitted')]
        result=summarize_commands(commands)
        self.assertEqual(result['unresolved'],1);self.assertEqual(result['not_admitted'],1)
        self.assertEqual(result['terminal_observation_latency_ms']['maximum'],1)
        self.assertIsNone(percentiles([])['p99'])

    def test_missing_source_instrumentation_is_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            result=dict(final_bridge_state={},source_marker_spans={'imu':100},missing_within_observed_source_span={'imu':40})
            before=summarize_gaps(directory,result)
            self.assertIsNone(before['source_snapshot'])
            source=dict(observed_monotonic_ns=50,bridge=dict(imu_ingress=100,transport_sensor_replaced=39))
            (Path(directory)/'robot-final-bridge-state.json').write_text(json.dumps(source))
            after=summarize_gaps(directory,result)
            self.assertEqual(after['source_snapshot']['transport_sensor_replaced'],39)
            self.assertIsNone(after['source_snapshot']['samples_submit_busy'])
            self.assertIn('not an exact',after['scope'])

    def test_process_identity_and_cpu_accounting(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'resources'
            records=[dict(monotonic_ns=0,clock_ticks_per_second=100,processes=[dict(pid=1,start_ticks=10,cpu_ticks=50,rss_bytes=100)]),
                     dict(monotonic_ns=1000000000,clock_ticks_per_second=100,processes=[dict(pid=1,start_ticks=10,cpu_ticks=75,rss_bytes=150)]),
                     dict(monotonic_ns=2000000000,clock_ticks_per_second=100,processes=[dict(pid=1,start_ticks=20,cpu_ticks=2,rss_bytes=120)])]
            p.write_text('\n'.join(json.dumps(r) for r in records))
            result=summarize_resources(p)
            self.assertEqual(result['cpu_seconds'],.25)
            self.assertEqual(result['average_cpu_core_percent'],12.5)
            self.assertEqual(result['maximum_sum_rss_bytes'],150)


class WindowTests(unittest.TestCase):
    def fixture(self):
        keys=('sensor_ingress_pending sensor_outbound_pending sensor_receive_pending samples_ingress sensor_submitted invalid_samples oversize_samples context_drops sensor_ingress_replaced sensor_ingress_flushed sensor_inputs sensor_input_rejected sensor_outbound_replaced sensor_outbound_expired sensor_outbound_flushed sensor_sent transport_samples_received transport_samples_rejected sensor_receive_replaced sensor_receive_flushed sensor_polled sensor_poll_expired samples_published stale_samples').split()
        node=dict.fromkeys(keys,0);node['owner_epoch']=[1]*16;node['imu_age_upper_histogram_ms']=[0]*251;node['joint_age_upper_histogram_ms']=[0]*251
        begin=dict(sender=copy.deepcopy(node),receiver=copy.deepcopy(node),device=dict(imu_published=0,joints_published=0),observer=dict(imu=0,joints=0))
        end=copy.deepcopy(begin);end['device']['imu_published']=10;end['observer']['imu']=7
        end['sender'].update(samples_ingress=10,sensor_submitted=10,sensor_inputs=10,sensor_outbound_replaced=3,sensor_sent=7)
        end['receiver'].update(transport_samples_received=7,sensor_polled=7,samples_published=7)
        end['receiver']['imu_age_upper_histogram_ms'][10]=7
        return begin,end,dict(resume_monotonic_ns=0,pause_monotonic_ns=1000000000)

    def test_accounts_exact_outbound_loss_without_diagnostic_tail(self):
        a,b,t=self.fixture();r=summarize_window(a,b,t)
        self.assertEqual(r['missing'],3);self.assertEqual(r['losses']['outbound_replaced'],3)
        self.assertFalse(any(r['balances'].values()));self.assertEqual(r['age_upper_histograms']['imu']['maximum_ms'],10)

    def test_owner_restart_is_not_a_counter_window(self):
        a,b,t=self.fixture();b['sender']['owner_epoch']=[2]*16
        with self.assertRaisesRegex(ValueError,'owner restarted'):summarize_window(a,b,t)

    def test_rejects_pending_or_unbalanced_checkpoints(self):
        a,b,t=self.fixture();a['sender']['sensor_ingress_pending']=1
        with self.assertRaisesRegex(ValueError,'pending'):summarize_window(a,b,t)
        a,b,t=self.fixture();b['sender']['sensor_outbound_replaced']=2
        with self.assertRaisesRegex(ValueError,'balance'):summarize_window(a,b,t)

    def test_rejects_reset_missing_counter_and_histogram_population(self):
        a,b,t=self.fixture();a['sender']['sensor_submitted']=20
        with self.assertRaisesRegex(ValueError,'reset'):summarize_window(a,b,t)
        a,b,t=self.fixture();del b['receiver']['sensor_polled']
        with self.assertRaises(KeyError):summarize_window(a,b,t)
        a,b,t=self.fixture();b['receiver']['imu_age_upper_histogram_ms'][10]=6
        with self.assertRaisesRegex(ValueError,'histogram population'):summarize_window(a,b,t)


if __name__ == '__main__':
    unittest.main()
