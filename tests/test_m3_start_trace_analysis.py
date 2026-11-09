import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_start_trace_analysis import analyze,validate


class StartTraceTests(unittest.TestCase):
    def setUp(self):
        base=dict(start_trace_version=1,check_token=11,worker_token=0,grant_slot=2**32-1,grant_generation=0,grant_deadline_ns=0,command_deadline_ns=1000,start_granted=False,worker_observation_available=False,consume_ns=0,consume_deadline_ns=0,consume_result=0,second_gate_ns=0,second_gate_deadline_ns=0,second_gate_checked=False,handler_invoked=False,terminal_state=0,terminal_reason=0,detail=6,request_sequence=3,origin_ns=50,owner_epoch='01'*16,session='02'*16,request='03'*16,route=100,value=0,evaluated_ns=0,clock_deadline_ns=0,clock_error=0)
        a=dict(base,point=40,monotonic_ns=110)
        b=dict(base,point=41,monotonic_ns=120,evaluated_ns=100,clock_deadline_ns=600,start_granted=True,grant_slot=0,grant_generation=7,grant_deadline_ns=500)
        c=dict(b,point=42,monotonic_ns=130,worker_token=9)
        d=dict(c,point=43,monotonic_ns=180,worker_observation_available=True,consume_ns=135,consume_deadline_ns=500,consume_result=1,second_gate_ns=140,second_gate_deadline_ns=500,second_gate_checked=True,handler_invoked=True,terminal_state=4)
        self.rows=[a,b,c,d]
    def test_success_and_cross_lane_order(self):
        self.assertEqual(analyze(self.rows)[0]['branch'],'worker_handler_invoked');self.assertEqual(analyze([self.rows[1],self.rows[0],*self.rows[2:]])[0]['branch'],'worker_handler_invoked')
    def test_actual_consume_expiry(self):
        self.rows[-1].update(monotonic_ns=600,consume_result=2,consume_ns=500,second_gate_ns=0,second_gate_deadline_ns=0,second_gate_checked=False,handler_invoked=False,terminal_state=6,terminal_reason=1)
        self.assertEqual(analyze(self.rows)[0]['branch'],'worker_consume_expired')
    def test_revoked_is_not_inferred_as_session_loss(self):
        self.rows[-1].update(consume_result=3,second_gate_ns=0,second_gate_deadline_ns=0,second_gate_checked=False,handler_invoked=False,terminal_state=6,terminal_reason=1)
        self.assertEqual(analyze(self.rows)[0]['branch'],'worker_consume_revoked')
    def test_second_gate_is_distinct(self):
        self.rows[-1].update(monotonic_ns=600,second_gate_ns=550,handler_invoked=False,terminal_state=6,terminal_reason=1)
        self.assertEqual(analyze(self.rows)[0]['branch'],'worker_second_gate_elapsed')
    def test_coordinator_decline_has_no_execution(self):
        denial=dict(self.rows[1],start_granted=False,grant_deadline_ns=0,value=12,clock_deadline_ns=0,evaluated_ns=0)
        declined=dict(denial,point=44,monotonic_ns=125)
        self.assertEqual(analyze([self.rows[0],denial,declined])[0]['branch'],'coordinator_start_declined')
        with self.assertRaises(ValueError):analyze([self.rows[0],denial,declined,*self.rows[2:]])
    def test_missing_wrong_generation_token_and_context(self):
        with self.assertRaises(ValueError):analyze(self.rows[:2])
        for key,value in (('grant_generation',8),('worker_token',10),('session','ff'*16),('command_deadline_ns',1001)):
            rows=copy.deepcopy(self.rows);rows[-1][key]=value
            with self.assertRaises(ValueError):analyze(rows)
    def test_missing_worker_observation_stays_unavailable(self):
        self.rows[-1].update(worker_observation_available=False,consume_ns=0,consume_deadline_ns=0,consume_result=0,second_gate_ns=0,second_gate_deadline_ns=0,second_gate_checked=False,handler_invoked=False)
        with self.assertRaisesRegex(ValueError,'unavailable'):analyze(self.rows)
    def test_bad_schema_deadline_and_booleans(self):
        for change in (dict(start_trace_version=0),dict(consume_ns=500),dict(handler_invoked=1),dict(grant_slot=64),dict(consume_result=5),dict(second_gate_deadline_ns=501)):
            row=dict(self.rows[-1],**change)
            with self.assertRaises(ValueError):validate(row)
    def test_empty_and_duplicate_events(self):
        self.assertEqual(analyze([]),[])
        with self.assertRaisesRegex(ValueError,'duplicate'):analyze(self.rows+[self.rows[-1]])
