import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_sender_trace_analysis import validate,summarize


class SenderTraceTests(unittest.TestCase):
    def event(self,point=45):
        return dict(point=point,monotonic_ns=100,reason=7,request='01'*16,entry_owner_epoch='02'*16,sender_trace_version=1,
            origin_ns=1,evaluated_ns=99,clock_deadline_ns=0,clock_error=2,command_deadline_ns=1000,clock_previous_deadline_ns=90,
            probe_anchor_ns=10,offset_lower_ns=-20,offset_upper_ns=30,clock_observed=True,worker_token=0,
            journal_entry_available=False,journal_revision=0,terminal_state=0,terminal_reason=0,detail=1,value=13)

    def test_real_clock_state_required_and_signed_interval_retained(self):
        e=self.event();validate(e)
        for key,value in [('clock_error',0),('clock_error',9),('evaluated_ns',101),('offset_lower_ns',31),('clock_observed',1),('probe_anchor_ns',100),('sender_trace_version',2)]:
            with self.subTest(key=key),self.assertRaises(ValueError):validate(dict(e,**{key:value}))

    def test_no_probe_and_recovery_are_distinct(self):
        e=self.event();e.update(clock_observed=False,probe_anchor_ns=0,offset_lower_ns=0,offset_upper_ns=0,clock_error=1);validate(e)
        e['clock_error']=2
        with self.assertRaisesRegex(ValueError,'probe invented'):validate(e)
        e=self.event();e.update(detail=2,value=0,clock_error=0,clock_deadline_ns=110);validate(e)
        e['clock_deadline_ns']=98
        with self.assertRaisesRegex(ValueError,'recovery'):validate(e)

    def test_release_branch_does_not_become_a_terminal_result(self):
        for value,reason in ((1,5),(1,3),(1,4),(2,7),(3,8),(4,0),(5,10),(5,3)):
            e=self.event(46);e.update(value=value,reason=reason);validate(e)
        e.update(value=4,reason=5)
        with self.assertRaisesRegex(ValueError,'release'):validate(e)

    def journal(self,point=47):
        e=self.event(point);e.update(value=0,detail=2 if point==47 else 0,worker_token=9 if point==47 else 0,
            journal_entry_available=True,terminal_state=1,terminal_reason=0,journal_revision=0,reason=0);return e

    def test_journal_entry_and_absence_are_explicit(self):
        e=self.journal();validate(e)
        e['journal_entry_available']=False
        with self.assertRaisesRegex(ValueError,'entry invented'):validate(e)
        e.update(origin_ns=0,command_deadline_ns=0,terminal_state=0,entry_owner_epoch='00'*16);validate(e)
        e.update(detail=5);validate(e) # Session invalidation completion without entry.
        e['worker_token']=0
        with self.assertRaisesRegex(ValueError,'metadata'):validate(e)

    def test_receipt_worker_operation_is_bounded(self):
        e=self.journal();e['detail']=11;validate(e)
        e['detail']=12
        with self.assertRaises(ValueError):validate(e)

    def test_required_new_observations_and_capture_loss_cannot_be_ignored(self):
        release=self.event(46);release.update(value=4,reason=0)
        trace={'operator.log':dict(complete=True,events=[release,self.journal(),self.journal(48)])}
        result=summarize(trace);self.assertEqual(result['counts']['45'],0)
        for point in (46,47,48):
            t=copy.deepcopy(trace);t['operator.log']['events']=[e for e in t['operator.log']['events'] if e['point']!=point]
            with self.assertRaisesRegex(ValueError,'missing'):summarize(t)
        trace['operator.log']['complete']=False
        with self.assertRaisesRegex(ValueError,'incomplete'):summarize(trace)


if __name__=='__main__':unittest.main()
