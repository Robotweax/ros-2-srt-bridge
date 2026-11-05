#!/usr/bin/env python3
import json
import struct
import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from m3_network import PROFILES, SEEDS
from m3_capture import classify, summarize
from m3_results import percentiles, summarize_commands, summarize_resources


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


if __name__ == '__main__':
    unittest.main()
