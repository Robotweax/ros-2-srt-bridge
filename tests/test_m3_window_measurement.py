#!/usr/bin/env python3
import copy
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ros2/robotweax_srt_bridge_demo/scripts'))
from m3_window_measurement import summarize_cpu,capture_window,summarize_endpoints
from m3_capture import summarize
from endpoint_measurement import parse_stat,EndpointSampler

SECOND=10**9

def samples():
    return [dict(begin_ns=i*SECOND//4,end_ns=i*SECOND//4+1000,wall_ns=i*SECOND//4+10000,
        offset_min_ns=9000,offset_max_ns=10000,hz=100,errors=[],
        processes=[dict(label='observer',pid=3,start_ticks=10,cpu_ticks=i*2,waited_child_cpu_ticks=0,rss_bytes=4096)]) for i in range(17)]

class CpuTests(unittest.TestCase):
    def test_inner_outer_deltas_no_interpolation_and_rss_scope(self):
        r=summarize_cpu(samples(),SECOND,3*SECOND)
        self.assertTrue(r['qualified']);self.assertEqual(r['inner_cpu_seconds'],.14);self.assertEqual(r['outer_cpu_seconds'],.18)
        self.assertLess(r['inner_cpu_core_percent'],r['outer_cpu_core_percent'])
        self.assertEqual(r['maximum_observed_sum_rss_bytes'],4096)
        self.assertEqual(r['tick_resolution_seconds'],.01)

    def test_missing_brackets_churn_regressions_gaps_and_errors_are_unqualified(self):
        self.assertFalse(summarize_cpu(samples(),0,3*SECOND)['qualified'])
        for mutation in ['pid','ticks','gap','errors','hz','child']:
            rows=samples()
            if mutation=='pid':rows[7]['processes'][0]['start_ticks']=20
            if mutation=='ticks':rows[7]['processes'][0]['cpu_ticks']=0
            if mutation=='gap':rows=rows[:5]+rows[11:]
            if mutation=='errors':rows[7]['errors']=[dict(error='missing')]
            if mutation=='hz':rows[7]['hz']=0
            if mutation=='child':rows[7]['processes'][0]['waited_child_cpu_ticks']=1
            self.assertFalse(summarize_cpu(rows,SECOND,3*SECOND)['qualified'],mutation)

    def test_stat_parser_handles_parentheses_and_does_not_add_child_cpu(self):
        fields=['S']+['0']*21;fields[11]='7';fields[12]='8';fields[13]='999';fields[14]='999';fields[19]='123';fields[21]='5'
        self.assertEqual(parse_stat('12 (odd (process) name) '+' '.join(fields),4096),dict(start_ticks=123,cpu_ticks=15,waited_child_cpu_ticks=1998,rss_bytes=20480))

class ClockTests(unittest.TestCase):
    def test_clock_envelope_includes_bracket_and_declared_drift_padding(self):
        r=capture_window(samples(),SECOND,3*SECOND);self.assertTrue(r['qualified'])
        self.assertEqual(r['drift_padding_ns'],250001)
        self.assertEqual(r['timestamp_bounds_ns'],[SECOND-241001,SECOND+260001,3*SECOND-241001,3*SECOND+260001])
        self.assertIn('undetected',r['assumptions'])

    def test_steps_wide_reads_and_gaps_do_not_create_wire_measurements(self):
        for mutation in ['step','width','gap']:
            rows=samples()
            if mutation=='step':rows[7]['offset_min_ns']=3000000;rows[7]['offset_max_ns']=3001000
            if mutation=='width':rows[7]['offset_max_ns']=2000000
            if mutation=='gap':rows=rows[:5]+rows[11:]
            r=capture_window(rows,SECOND,3*SECOND);self.assertFalse(r['qualified'],mutation);self.assertNotIn('timestamp_bounds_ns',r)

    def test_observed_drift_must_fit_the_declared_model(self):
        rows=samples()
        for i,row in enumerate(rows):
            change=i*500000
            row['wall_ns']+=change;row['offset_min_ns']+=change;row['offset_max_ns']+=change
        r=capture_window(rows,SECOND,3*SECOND)
        self.assertFalse(r['qualified']);self.assertIn('drift',r['reason'])

    def test_common_envelope_and_cpu_are_separate_qualification(self):
        with tempfile.TemporaryDirectory() as d:
            for role in ['robot','operator']:
                rows=samples()
                if role=='robot':rows[7]['processes'][0]['start_ticks']=20
                Path(d,role+'-endpoint-samples.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
            r=summarize_endpoints(d,dict(load=[SECOND,3*SECOND]))['windows']['load']
            self.assertTrue(r['wire_clock']['qualified']);self.assertFalse(r['cpu']['robot']['qualified']);self.assertTrue(r['cpu']['operator']['qualified'])

class CaptureTests(unittest.TestCase):
    def write(self,path):
        ip=bytearray(20);ip[0]=0x45;ip[9]=17;ip[12:16]=bytes([10,0,0,1]);ip[16:20]=bytes([10,0,0,2])
        payload=b'RTPS';struct.pack_into('!H',ip,2,20+8+len(payload))
        frame=b'\0'*12+b'\x08\x00'+ip+struct.pack('!HHHH',7400,7401,12,0)+payload
        raw=struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1)
        for us in [0,9,10,11,15,19,20,21,30]:raw+=struct.pack('<IIII',0,us,len(frame),len(frame))+frame
        path.write_bytes(raw)

    def test_partition_and_quantization_preserve_old_whole_capture(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.pcap';self.write(p)
            whole=summarize([p],'10.0.0.1');window=summarize([p],'10.0.0.1',timestamp_window=[9000,10000,20000,21000])
            for k,v in whole.items():self.assertEqual(window[k],v)
            buckets=window['time_window']['buckets'];self.assertEqual(sum(v['records'] for v in buckets.values()),9)
            self.assertEqual({k:v['records'] for k,v in buckets.items()},dict(inside=2,boundary=5,outside=2))
            self.assertEqual(sum(v['classes']['out/dds_rtps']['ethernet_bytes'] for v in buckets.values()),whole['classes']['out/dds_rtps']['ethernet_bytes'])
            with self.assertRaises(ValueError):summarize([p],'10.0.0.1',timestamp_window=[20,21,10,11])

    def test_nanosecond_capture_has_nanosecond_boundary_uncertainty(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'nano.pcap';self.write(p);raw=p.read_bytes()
            p.write_bytes(struct.pack('<I',0xa1b23c4d)+raw[4:])
            r=summarize([p],'10.0.0.1',timestamp_window=[9,10,20,21])
            self.assertEqual({k:v['records'] for k,v in r['time_window']['buckets'].items()},dict(inside=2,boundary=5,outside=2))

if __name__=='__main__':unittest.main()
