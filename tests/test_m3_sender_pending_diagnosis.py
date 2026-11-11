import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_sender_pending_diagnosis import reconcile


class SenderPendingDiagnosisTests(unittest.TestCase):
    def setUp(self):
        self.sender=dict(session='01'*16,owner_epoch='02'*16,route=100,source_ns=10,deadline_ns=100,state=8,reason=2,revision=0,result_valid=False)
        self.row=dict(number=118,last_status_observation=dict(state=1,observed_monotonic_ns=130))
        identity=(118).to_bytes(16,'little').hex()
        def event(point,time,value=0,reason=0,request=identity):
            return dict(point=point,monotonic_ns=time,value=value,reason=reason,request=request,session=self.sender['session'],owner_epoch=self.sender['owner_epoch'],route=100)
        self.events=[event(5,20,1),event(6,21),event(29,22,13,7),event(21,101,reason=5),
                     event(2,160,reason=1,request='00'*16),event(3,161,reason=1,request='00'*16),event(4,162,reason=1,request='00'*16)]

    def test_teardown_unknown_does_not_invent_clock_or_outcome_authority(self):
        result=reconcile(self.events,self.sender,self.row,150)
        self.assertEqual(result['drop_after_deadline_ns'],1)
        self.assertIsNone(result['exact_sender_clock_error'])
        self.assertFalse(result['outcome_authority']);self.assertFalse(result['replay_authority'])

    def test_active_invalidation_cannot_be_labelled_teardown(self):
        self.events[-3]['monotonic_ns']=140
        with self.assertRaisesRegex(ValueError,'inside observation'):reconcile(self.events,self.sender,self.row,150)

    def test_context_failed_invalidation_and_missing_stage_fail_closed(self):
        for mutate in (lambda e:e[2].update(session='03'*16),lambda e:e[-1].update(value=3),lambda e:e.pop(3)):
            events=copy.deepcopy(self.events);mutate(events)
            with self.assertRaises(ValueError):reconcile(events,self.sender,self.row,150)

    def test_handoff_or_terminal_cannot_use_pre_sdk_diagnosis(self):
        with self.assertRaisesRegex(ValueError,'handoff'):
            reconcile(self.events+[dict(self.events[0],point=25)],self.sender,self.row,150)
        with self.assertRaisesRegex(ValueError,'terminal'):
            reconcile(self.events,self.sender,dict(self.row,terminal=7),150)


if __name__=='__main__':unittest.main()
