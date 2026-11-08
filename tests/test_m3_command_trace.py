import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_command_trace import summarize, summarize_run


class CommandTraceTests(unittest.TestCase):
    def parse(self,events,status):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bridge.log'
            p.write_text('unrelated SDK log\n'+''.join('COMMAND_TRACE '+json.dumps(e)+'\n' for e in events)+
                ('' if status is None else 'COMMAND_TRACE_STATUS '+json.dumps(status)+'\n'))
            return summarize(p)

    def event(self,seq,point):
        return dict(sequence=seq,monotonic_ns=seq,point=point,reason=0,request='00'*16,session='01'*16,owner_epoch='02'*16,entry_owner_epoch='00'*16)

    def test_complete_lifecycle_and_concurrent_arrival_order(self):
        events=[self.event(1,1),self.event(3,25),self.event(2,6),self.event(4,8),self.event(5,28),self.event(6,9)]
        result=self.parse(events,dict(attempted=6,dropped=0))
        self.assertTrue(result['complete']);self.assertEqual(result['counts']['provider_sent'],1)

    def test_connection_cause_fields_and_legacy_records_are_readable(self):
        events=[self.event(1,1),self.event(2,31),self.event(3,30),self.event(4,8),self.event(5,28),self.event(6,9)]
        events[1].update(reason=11,value=6,detail=0)
        events[2].update(reason=16,value=14,detail=7)
        result=self.parse(events,dict(attempted=6,dropped=0))
        self.assertTrue(result['complete']);self.assertEqual(result['counts']['link_lost'],1)
        self.assertEqual(result['events'][2]['value'],14)
        events[1]['detail']=2
        with self.assertRaisesRegex(ValueError,'channel'):self.parse(events,dict(attempted=6,dropped=0))
        events[1]['detail']=0;events[2]['detail']=8
        with self.assertRaisesRegex(ValueError,'flags'):self.parse(events,dict(attempted=6,dropped=0))

    def test_admission_errors_keep_request_kind_and_clock_boundary(self):
        events=[self.event(1,32),self.event(2,33),self.event(3,34)]
        for event in events:event.update(detail=6,value=0,request_sequence=14,origin_ns=1,evaluated_ns=1,clock_deadline_ns=9,clock_error=0,age_error=0)
        events[0].update(value=13,clock_error=2,clock_deadline_ns=1)
        events[1].update(value=5)
        events[2].update(detail=8,value=2)
        parsed=self.parse(events,dict(attempted=3,dropped=0))
        self.assertEqual(parsed['counts']['control_admission'],1)
        self.assertEqual(parsed['events'][1]['detail'],6)
        self.assertEqual(parsed['events'][2]['detail'],8)
        for key,value in [('detail',7),('request_sequence',0),('value',27),('clock_error',10),('evaluated_ns',2)]:
            invalid=[dict(e) for e in events];invalid[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.parse(invalid,dict(attempted=3,dropped=0))

    def test_receiver_retention_schema_and_fresh_revalidation(self):
        events=[self.event(1,35),self.event(2,36),self.event(3,37),self.event(4,38)]
        for e in events:e.update(detail=6,value=0,request_sequence=7,origin_ns=1,evaluated_ns=1,clock_deadline_ns=10,clock_error=0,age_error=0)
        events[0]['value']=13;events[2]['value']=13;events[3]['value']=1
        self.assertEqual(self.parse(events,dict(attempted=4,dropped=0))['counts']['receiver_resumed'],1)
        events[1]['detail']=8
        with self.assertRaisesRegex(ValueError,'COMMAND'):self.parse(events,dict(attempted=4,dropped=0))

    def test_loss_is_explicit_and_never_complete(self):
        events=[self.event(1,1),self.event(3,9)]
        self.assertFalse(self.parse(events,dict(attempted=4,dropped=2))['complete'])
        with self.assertRaisesRegex(ValueError,'unaccounted'):self.parse(events,dict(attempted=4,dropped=0))

    def test_truncation_duplicate_sequences_and_missing_shutdown_rejected(self):
        events=[self.event(1,1)]
        with self.assertRaisesRegex(ValueError,'final'):self.parse(events,None)
        self.assertFalse(self.parse(events,dict(attempted=1,dropped=0))['complete'])
        with self.assertRaisesRegex(ValueError,'sequences'):self.parse(events*2,dict(attempted=2,dropped=0))


class TraceRunTests(unittest.TestCase):
    def test_all_robot_incarnations_are_kept_and_validated(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)
            for name in ('operator-bridge-0.log','robot-bridge-1.log','robot-bridge-2.log'):(run/name).touch()
            with patch('m3_command_trace.summarize',return_value={'complete':True}):self.assertEqual(len(summarize_run(run)),3)
            with patch('m3_command_trace.summarize',side_effect=[{'complete':True},{'complete':False},{'complete':True}]):
                with self.assertRaisesRegex(ValueError,'incomplete'):summarize_run(run)
            (run/'operator-bridge-0.log').unlink()
            with patch('m3_command_trace.summarize',return_value={'complete':True}):
                with self.assertRaisesRegex(ValueError,'missing endpoint'):summarize_run(run)
