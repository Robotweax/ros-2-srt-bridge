import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_start_fence_diagnosis import join


class StartFenceDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.a=dict(state=6,reason=1,route=100,payload_hash='01'*32,session='02'*16,source_epoch='03'*16,owner_epoch='03'*16,source_ns=100,admitted_ns=110,dispatched_ns=0,finished_ns=170,deadline_ns=1100,result_valid=False)
        self.b=dict(self.a,owner_epoch='04'*16,admitted_ns=120,dispatched_ns=150,finished_ns=160,deadline_ns=1090)
        self.entry=dict(number=34,terminal=6,sender=self.a,receiver=self.b)
        self.command=dict(number=34,terminal=6,reason=1,result_valid=False,result_observed_monotonic_ns=180)
        self.admission=dict(request=(34).to_bytes(16,'little').hex(),session=self.a['session'],route=100,origin_ns=100,detail=6,point=32,value=0,clock_error=0,age_error=0,evaluated_ns=115,monotonic_ns=116,clock_deadline_ns=149,request_sequence=9)
    def result(self,events=None):return join(self.entry,self.command,events or [self.admission])
    def test_observed_lapse_keeps_actual_grant_unknown(self):
        r=self.result();self.assertEqual(r['admission_clock_margin_ns'],34);self.assertEqual(r['dispatch_minus_observed_clock_deadline_ns'],1);self.assertIsNone(r['actual_start_grant_deadline_ns']);self.assertIsNone(r['worker_consume_result']);self.assertIsNone(r['execute_submitted']);self.assertEqual(r['branch'],'not_recorded')
    def test_expired_enum_is_not_context_rejection(self):
        self.entry['terminal']=7;self.a['state']=7;self.b['state']=7;self.command['terminal']=7
        with self.assertRaisesRegex(ValueError,'scope'):self.result()
    def test_success_may_have_fresh_later_grant(self):
        self.entry['terminal']=4
        for r in (self.a,self.b,self.command):r.update(state=4,terminal=4,reason=0,result_valid=True)
        r=self.result();self.assertEqual(r['dispatch_minus_observed_clock_deadline_ns'],1);self.assertEqual(r['branch'],'not_recorded')
    def test_cross_context_admission_is_rejected(self):
        for field,value in (('session','ff'*16),('origin_ns',99),('route',101),('request','00'*16),('detail',8)):
            bad=dict(self.admission);bad[field]=value
            with self.assertRaisesRegex(ValueError,'identity/context'):self.result([bad])
    def test_journal_context_must_match(self):
        for field in ('session','payload_hash','source_epoch','source_ns'):
            b=dict(self.b);b[field]='wrong';entry=dict(self.entry,receiver=b)
            with self.assertRaisesRegex(ValueError,'journal context'):join(entry,self.command,[self.admission])
    def test_missing_and_unqualified_admission_rejected(self):
        with self.assertRaisesRegex(ValueError,'no original'):join(self.entry,self.command,[])
        for field in ('clock_error','age_error','value'):
            bad=dict(self.admission);bad[field]=1
            with self.assertRaisesRegex(ValueError,'unqualified'):self.result([bad])
    def test_invalid_brackets_and_journal_order(self):
        for changes in (dict(evaluated_ns=117),dict(clock_deadline_ns=115),dict(evaluated_ns=0),dict(request_sequence=0)):
            with self.assertRaises(ValueError):self.result([dict(self.admission,**changes)])
        self.b['dispatched_ns']=161
        with self.assertRaisesRegex(ValueError,'timeline'):self.result()
    def test_later_recorded_admission_is_not_ignored(self):
        newer=dict(self.admission,point=36,evaluated_ns=130,monotonic_ns=131,clock_deadline_ns=500)
        r=self.result([self.admission,newer]);self.assertEqual(r['last_admission'],newer);self.assertEqual(r['dispatch_minus_observed_clock_deadline_ns'],-350);self.assertIsNone(r['actual_start_grant_deadline_ns'])
    def test_rejected_result_cannot_be_valid(self):
        self.b['result_valid']=True
        with self.assertRaisesRegex(ValueError,'rejection with valid'):self.result()


if __name__=='__main__':unittest.main()
