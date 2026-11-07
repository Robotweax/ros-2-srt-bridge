import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_sample_trace import summarize,correlate


def event(point=1, result=0):
    return dict(sequence=point,point=point,begin_ns=20 if point==1 else 21,end_ns=30,origin_ns=10,owner_epoch='01'*16,session='02'*16,control_generation=1,sensor_generation=1,envelope_sequence=1,callback_sequence=1,route=1,bytes=100 if point==1 else 196,kind=5,result=result,stamp_sec=1,stamp_nanosec=2,socket=-1 if point==1 else 99,message_number=0 if point==1 else 2,initial_sequence=-1 if point==1 else 123,initial_sequence_available=point!=1)


class SampleTraceTests(unittest.TestCase):
    def write(self,path,rows,status=None):
        if status is None:status=dict(attempted=len(rows),dropped=0,exhausted=0,limit=75000)
        path.write_text(''.join('SAMPLE_TRACE '+json.dumps(e)+'\n' for e in rows)+'SAMPLE_TRACE_STATUS '+json.dumps(status)+'\n')

    def test_cross_lane_result_end_does_not_precede_handoff(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'trace';self.write(p,[event(),event(2)])
            r=correlate(summarize(p));self.assertEqual(len(r['joined']),1);self.assertEqual(r['joined'][0]['wire_sequence_candidate'],124)

    def test_busy_preserved_and_never_joins_sdk_success(self):
        busy=event(result=1)
        self.assertEqual(len(correlate(dict(events=[busy]))['rejected']),1)
        with self.assertRaises(ValueError):correlate(dict(events=[busy,event(2)]))

    def test_missing_status_overflow_exhaustion_and_duplicates_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'trace'
            for status in (dict(attempted=2,dropped=1,exhausted=0,limit=75000),dict(attempted=1,dropped=0,exhausted=1,limit=1)):
                self.write(p,[event()],status)
                with self.assertRaises(ValueError):summarize(p)
            self.write(p,[event(),event()])
            with self.assertRaises(ValueError):summarize(p)
            p.write_text('')
            with self.assertRaises(ValueError):summarize(p)

    def test_incomplete_identity_size_and_duplicate_handoff_not_rescued(self):
        for change in ('origin','size','initial','duplicate'):
            sdk=event(2)
            if change=='origin':sdk['origin_ns']=11
            elif change=='size':sdk['bytes']=197
            elif change=='initial':sdk['initial_sequence_available']=False
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/'trace';rows=[event(),sdk]
                if change=='duplicate':rows.append(dict(sdk,sequence=3))
                self.write(p,rows)
                with self.assertRaises(ValueError):correlate(summarize(p))

    def test_missing_queued_handoff_is_explicit_unknown(self):
        r=correlate(dict(events=[event()]));self.assertEqual(len(r['queued_without_observed_handoff']),1);self.assertFalse(r['joined'])
