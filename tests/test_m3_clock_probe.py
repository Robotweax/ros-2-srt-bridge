#!/usr/bin/env python3
import copy
from pathlib import Path
import sys
import unittest
import tempfile
import json
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ros2/robotweax_srt_bridge_demo/scripts'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from endpoint_measurement import EndpointSampler
from m3_window_measurement import capture_window,summarize_endpoints
from m3_clock_probe import CHANNELS,analyze


def samples():
    return [{name:dict(begin_ns=i*100000000,value_ns=i*100000000+(1000000000 if 'realtime' in name else 5000),end_ns=i*100000000+1000) for name in CHANNELS} for i in range(12)]


class ClockProbeTests(unittest.TestCase):
    def test_stable_channels_and_insufficient_observations(self):
        self.assertTrue(analyze(samples())['realtime_model_passed'])
        for rows in ([],samples()[:3]):self.assertFalse(analyze(rows)['realtime_model_passed'])

    def test_correlated_realtime_jump_keeps_raw_and_boottime_separate(self):
        rows=samples()
        for row in rows[5:]:
            for name in CHANNELS[:3]:row[name]['value_ns']+=500000
        result=analyze(rows)
        self.assertFalse(result['realtime_model_passed'])
        for name in CHANNELS[:3]:
            violation=result['channels'][name]['violations'][0]
            self.assertEqual(violation['index'],5)
            self.assertEqual(violation['minimum_change_ns'],499000)
        for name in CHANNELS[3:]:self.assertTrue(result['channels'][name]['observed_model_passed'])

    def test_python_only_failure_does_not_invent_kernel_failure(self):
        rows=samples();rows[5]['python_realtime']['value_ns']-=500000
        result=analyze(rows)
        self.assertFalse(result['channels']['python_realtime']['observed_model_passed'])
        self.assertTrue(result['channels']['syscall_realtime']['observed_model_passed'])

    def test_wide_reversed_reads_and_sample_gaps_reject(self):
        for field,value in [('end_ns',501000001),('end_ns',499999999),('begin_ns',0)]:
            rows=copy.deepcopy(samples());rows[5]['syscall_realtime'][field]=value
            self.assertFalse(analyze(rows)['realtime_model_passed'])
        self.assertFalse(analyze(samples()[:1]+samples()[11:])['realtime_model_passed'])


class DedicatedClockTests(unittest.TestCase):
    def test_clock_sampling_runs_between_process_samples_and_keeps_files_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'samples.jsonl'
            sampler=EndpointSampler(path)
            for now in (1000000000,1050000000,1100000000):
                with patch('endpoint_measurement.time.monotonic_ns',return_value=now),patch('endpoint_measurement.time.time_ns',return_value=now+9000):sampler.tick([])
            sampler.close()
            self.assertEqual(len(path.read_text().splitlines()),1)
            self.assertEqual(len((Path(str(path)+'.clock.jsonl')).read_text().splitlines()),3)

    def test_faster_calibration_catches_step_hidden_between_process_samples(self):
        def series(stride):
            rows=[]
            for begin in range(0,1000000001,stride):
                wall=begin+10000000000+(150000 if begin>=500000000 else 0)
                rows.append(dict(begin_ns=begin,end_ns=begin+1000,wall_ns=wall,offset_min_ns=wall-begin-1000,offset_max_ns=wall-begin,hz=100,errors=[],processes=[]))
            return rows
        coarse=series(250000000);fast=series(50000000)
        self.assertTrue(capture_window(coarse,250000000,750000000)['qualified'])
        self.assertFalse(capture_window(fast,250000000,750000000,max_gap_ns=100000000)['qualified'])
        with tempfile.TemporaryDirectory() as tmp:
            for role in ('robot','operator'):
                for suffix,rows in [('endpoint-samples',coarse),('clock-samples',fast)]:
                    (Path(tmp)/(role+'-'+suffix+'.jsonl')).write_text(''.join(json.dumps(row)+'\n' for row in rows))
            wire=summarize_endpoints(tmp,dict(source_enabled=[250000000,750000000]))['windows']['source_enabled']['wire_clock']
            self.assertFalse(wire['qualified'])
            for role in ('robot','operator'):(Path(tmp)/(role+'-clock-samples.jsonl')).unlink()
            missing=summarize_endpoints(tmp,dict(source_enabled=[250000000,750000000]),require_dedicated=True)
            self.assertEqual(missing['windows']['source_enabled']['wire_clock']['calibrations']['robot']['reason'],'dedicated clock samples missing')
            self.assertEqual(wire['calibrations']['robot']['sample_source'],'dedicated-clock')

    def test_dedicated_clock_gap_limit_is_enforced(self):
        rows=[]
        for begin in range(0,1000000001,250000000):
            rows.append(dict(begin_ns=begin,end_ns=begin+1000,wall_ns=begin+10000,offset_min_ns=9000,offset_max_ns=10000))
        r=capture_window(rows,250000000,750000000,max_gap_ns=100000000)
        self.assertFalse(r['qualified']);self.assertIn('gap',r['reason'])


if __name__=='__main__':unittest.main()
