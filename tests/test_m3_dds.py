#!/usr/bin/env python3
"""Fenced DDS populations must not conceal pre-callback or age-gate losses."""
import copy
from pathlib import Path
import sys
import struct
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_dds import summarize_sensor_window
from m3_capture import summarize
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ros2/robotweax_srt_bridge_demo/scripts'))
from dds_clock import interval_distance, ClockMonitor


class FragmentTests(unittest.TestCase):
    def capture(self,path,port=22410):
        frames=[]
        for fragment,payload in [(0x2000,struct.pack('!HHHH',port,22412,2000,0)+b'RTPS'+b'x'*4),(2,b'y'*16)]:
            ip=bytearray(20);ip[0]=0x45;ip[9]=17
            struct.pack_into('!H',ip,2,len(ip)+len(payload));struct.pack_into('!H',ip,6,fragment)
            ip[12:16]=bytes([10,0,0,1]);ip[16:20]=bytes([10,0,0,2])
            frames.append(b'\0'*12+b'\x08\x00'+ip+payload)
        data=struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1)
        for frame in frames:data+=struct.pack('<IIII',0,0,len(frame),len(frame))+frame
        path.write_bytes(data)
        return sum(map(len,frames))

    def test_fragment_opt_in_counts_frames_without_claiming_rtps_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'capture';size=self.capture(path)
            self.assertEqual(summarize([path],'10.0.0.1')['unaccounted'],{'fragmented':2})
            result=summarize([path],'10.0.0.1',allow_udp_fragments=True)
            self.assertFalse(result['unaccounted'])
            row=result['classes']['out/ipv4_udp_fragment']
            self.assertEqual(row['packets'],2);self.assertEqual(row['ethernet_bytes'],size)
            self.assertIsNone(row['udp_payload_bytes'])
            self.capture(path,10081)
            self.assertEqual(summarize([path],'10.0.0.1',allow_udp_fragments=True)['unaccounted'],{'fragmented_srt':1})


class ClockTests(unittest.TestCase):
    def test_scheduling_uncertainty_is_not_clock_drift(self):
        self.assertEqual(interval_distance((100,200),(0,2000000)),0)
        self.assertEqual(interval_distance((100,200),(300,400)),100)
        with self.assertRaises(ValueError):interval_distance((200,100),(300,400))


    def test_clock_step_disqualifies_age_but_preserves_bounded_evidence(self):
        monitor=ClockMonitor((100,200),1000)
        self.assertTrue(monitor.observe(0,(150,250)))
        self.assertFalse(monitor.observe(1,(10000,10100)))
        self.assertFalse(monitor.qualified)
        self.assertEqual(monitor.steps[0]['minimum_step_ns'],9750)
        self.assertFalse(monitor.observe(2,(10010,10110)))
        for i in range(100):monitor.observe(i,(i*10000,i*10000+100))
        self.assertLessEqual(len(monitor.steps),16)
        with self.assertRaises(ValueError):ClockMonitor((0,1001),1000)

    def test_wide_clock_read_does_not_become_permanent_clock_failure(self):
        monitor=ClockMonitor((100,200),1000)
        self.assertFalse(monitor.observe(0,(-10000,10000)))
        self.assertTrue(monitor.qualified)
        self.assertTrue(monitor.observe(1,(110,210)))


class DdsWindowTests(unittest.TestCase):
    def fixture(self):
        row=dict(received=0,accepted=0,stale=0,invalid=0,clock_rejected=0,age_estimate_histogram_ms=[0]*251)
        begin=dict(device=dict(imu_published=120,joints_published=30),observer=dict(imu=copy.deepcopy(row),joints=copy.deepcopy(row)))
        end=copy.deepcopy(begin);end['device'].update(imu_published=320,joints_published=80)
        end['observer']['imu'].update(received=190,accepted=187,stale=2,invalid=1)
        end['observer']['imu']['age_estimate_histogram_ms'][20]=187
        end['observer']['joints'].update(received=50,accepted=49,clock_rejected=1)
        end['observer']['joints']['age_estimate_histogram_ms'][30]=49
        return begin,end,dict(resume_monotonic_ns=1000000000,pause_monotonic_ns=2000000000)

    def test_partitions_callback_and_pre_callback_losses(self):
        a,b,t=self.fixture();r=summarize_sensor_window(a,b,t)
        self.assertEqual(r['routes']['imu']['missing_before_callback'],10)
        self.assertEqual(r['routes']['imu']['total_not_accepted'],13)
        self.assertEqual(r['routes']['imu']['actual_source_hz'],200)
        self.assertEqual(r['routes']['joints']['total_not_accepted'],1)
        self.assertIn('not physical WAN',r['scope'])

    def test_rejects_source_reset_or_extra_population(self):
        a,b,t=self.fixture();b['device']['imu_published']=119
        with self.assertRaisesRegex(ValueError,'reset'):summarize_sensor_window(a,b,t)
        a,b,t=self.fixture();b['device']['imu_published']=309
        with self.assertRaisesRegex(ValueError,'fenced'):summarize_sensor_window(a,b,t)

    def test_rejects_missing_classification_or_histogram(self):
        a,b,t=self.fixture();b['observer']['imu']['stale']=1
        with self.assertRaisesRegex(ValueError,'accounting'):summarize_sensor_window(a,b,t)
        a,b,t=self.fixture();b['observer']['imu']['age_estimate_histogram_ms'][20]=186
        with self.assertRaisesRegex(ValueError,'histogram'):summarize_sensor_window(a,b,t)

    def test_rejects_clock_or_counter_regression(self):
        a,b,t=self.fixture();t['pause_monotonic_ns']=t['resume_monotonic_ns']
        with self.assertRaisesRegex(ValueError,'interval'):summarize_sensor_window(a,b,t)
        a,b,t=self.fixture();b['observer']['imu']['invalid']=-1
        with self.assertRaisesRegex(ValueError,'reset'):summarize_sensor_window(a,b,t)


if __name__=='__main__':unittest.main()
