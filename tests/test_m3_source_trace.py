import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_source_trace import summarize,qualify


def fixtures():
    start=1_000_000_000;events=[]
    for route,count,period in ((1,2000,5_000_000),(2,500,20_000_000)):
        for n in range(count):
            due=start+n*period
            events.append(dict(window=1,sequence=0,route=route,counter=n+1,stamp_sec=due//1_000_000_000,stamp_nanosec=due%1_000_000_000,begin_ns=due+1,end_ns=due+2,due_ns=due,period_ns=period,skipped_slots=0,payload_bytes=320 if route==1 else 251,payload_sha256='ab'*32))
    events.sort(key=lambda e:(e['begin_ns'],e['route']))
    for n,e in enumerate(events,1):e['sequence']=n
    status=dict(schema_version=1,window=1,attempted=2500,recorded=2500,printed=2500,dropped=0,encoding_failed=0,hash_failed=0,limit=10000,complete=True)
    resume=dict(enabled=True,monotonic_ns=start,imu_published=0,joints_published=0,rate_hz=200,generation=0,effects=0)
    pause=dict(resume,enabled=False,monotonic_ns=start+10_000_000_000,imu_published=2000,joints_published=500)
    observed=[{k:e[k] for k in ('route','counter','stamp_sec','stamp_nanosec','payload_sha256')} for e in events]
    return dict(events=events,status=status),dict(resume=resume,pause=pause,observed=observed)


class SourceTraceTests(unittest.TestCase):
    def parse(self,trace):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'trace';p.write_text(''.join('SOURCE_TRACE '+json.dumps(e)+'\n' for e in trace['events'])+'SOURCE_TRACE_STATUS '+json.dumps(trace['status'])+'\n')
            return summarize(p)

    def test_full_two_route_window_and_typed_hashes(self):
        trace,result=fixtures();summary=qualify(self.parse(trace),result)
        self.assertTrue(summary['passed']);self.assertEqual(summary['routes']['1']['actual_hz'],200)
        self.assertEqual(summary['routes']['2']['actual_hz'],50);self.assertFalse(summary['unobserved'])

    def test_cadence_uses_measured_fences(self):
        trace,result=fixtures();result['pause']['monotonic_ns']+=1_000_000_000
        self.assertFalse(qualify(trace,result)['passed'])

    def test_observer_loss_is_explicit_without_delivery_claim(self):
        trace,result=fixtures();del result['observed'][0]
        summary=qualify(trace,result);self.assertTrue(summary['passed']);self.assertEqual(summary['unobserved'],[[1,1]])
        self.assertEqual(summary['routes']['1']['unobserved'],1)

    def test_payload_order_duplicate_and_stamp_errors_fail(self):
        for fault in ('hash','order','duplicate','stamp'):
            trace,result=fixtures()
            if fault=='hash':result['observed'][0]['payload_sha256']='cd'*32
            if fault=='order':result['observed'][0],result['observed'][3]=result['observed'][3],result['observed'][0]
            if fault=='duplicate':result['observed'].append(result['observed'][0])
            if fault=='stamp':result['observed'][0]['stamp_sec']+=1
            with self.assertRaises(ValueError):qualify(trace,result)

    def test_phase_count_and_fence_errors_fail(self):
        for fault in ('phase','count','fence','rate','generation'):
            trace,result=fixtures()
            if fault=='phase':trace['events'][2]['due_ns']+=1
            if fault=='count':result['pause']['imu_published']+=1
            if fault=='fence':result['pause']['enabled']=True
            if fault=='rate':result['pause']['rate_hz']=100
            if fault=='generation':result['pause']['generation']=1
            with self.assertRaises(ValueError):qualify(trace,result)

    def test_trace_loss_hash_and_sequence_errors_fail_closed(self):
        for fault in ('incomplete','drop','missing','duplicate','stamp','hash','counter','type'):
            trace,_=fixtures()
            if fault=='incomplete':trace['status']['complete']=False
            if fault=='drop':trace['status']['dropped']=1
            if fault=='missing':trace['events'].pop()
            if fault=='duplicate':trace['events'][2]['stamp_nanosec']=trace['events'][0]['stamp_nanosec']
            if fault=='stamp':trace['events'][0]['stamp_nanosec']=1_000_000_000
            if fault=='hash':trace['events'][0]['payload_sha256']='not a digest'
            if fault=='counter':trace['events'][0]['counter']=2
            if fault=='type':trace['events'][0]['skipped_slots']=False
            with self.assertRaises(ValueError):self.parse(trace)

    def test_skipped_slots_preserve_phase_and_count(self):
        trace,result=fixtures();events=trace['events'];lost=next(e for e in events if e['route']==1 and e['counter']==2);events.remove(lost)
        for e in events:
            if e['route']==1 and e['counter']>=3:
                e['counter']-=1
                if e['counter']==2:e['due_ns']-=e['period_ns'];e['skipped_slots']=1
        for n,e in enumerate(events,1):e['sequence']=n
        for k in ('attempted','recorded','printed'):trace['status'][k]-=1
        result['pause']['imu_published']-=1;result['observed']=[]
        summary=qualify(self.parse(trace),result)
        self.assertTrue(summary['passed']);self.assertEqual(summary['routes']['1']['skipped_slots'],1)
