import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_admission_diagnostics import correlate,successful_receiver_pairs,MATRIX_SLOTS,SLOTS


class CorrelationTests(unittest.TestCase):
    def test_only_same_original_command_context_correlates(self):
        receiver=dict(point=32,detail=6,value=13,session='a',route=100,request='b',request_sequence=7)
        sender=dict(receiver,point=33,value=5)
        def check(r,s):return correlate({'robot-bridge-2.log':{'events':[r]},'operator-bridge-0.log':{'events':[s]}})
        self.assertEqual(len(check(receiver,sender)),1)
        for field,value in [('session','old'),('route',101),('request','other'),('request_sequence',8),('detail',8),('value',3)]:
            with self.subTest(field=field):self.assertEqual(check(receiver,dict(sender,**{field:value})),[])
        self.assertEqual(check(dict(receiver,value=0),sender),[])
        self.assertEqual(correlate({'operator-bridge-0.log':{'events':[receiver,sender]}}),[])


class MatrixEvidenceTests(unittest.TestCase):
    def test_matrix_has_one_control_then_three_fixed_seeds(self):
        self.assertEqual([(s['profile'],s['seconds'],s['seed']) for s in MATRIX_SLOTS],
                         [('N0',15,4211),('N5',300,4211),('N5',300,1701),('N5',300,2903)])
        self.assertEqual(len(SLOTS),2)
        self.assertEqual(len({s['label'] for s in MATRIX_SLOTS}),4)

    def test_success_requires_original_context_origin_and_sequence(self):
        entry=dict(sender=dict(session='original',route=100,source_ns=42))
        a=dict(point=32,detail=6,value=0,session='original',route=100,origin_ns=42,request_sequence=7)
        w=dict(a,point=34)
        self.assertEqual(len(successful_receiver_pairs(entry,[a,w])),1)
        for field,value in [('session','other'),('route',101),('origin_ns',43),('request_sequence',8),('detail',8),('value',2)]:
            with self.subTest(field=field):self.assertEqual(successful_receiver_pairs(entry,[a,dict(w,**{field:value})]),[])
        self.assertEqual(len(successful_receiver_pairs(entry,[a,a,w])),2)

    def test_resumed_original_frame_uses_fresh_gate_without_double_counting(self):
        entry=dict(sender=dict(session='original',route=100,source_ns=42))
        first=dict(point=32,detail=6,value=0,session='original',route=100,origin_ns=42,request_sequence=7)
        resumed=dict(first,point=36);worker=dict(first,point=34)
        pairs=successful_receiver_pairs(entry,[first,resumed,worker])
        self.assertEqual(len(pairs),1);self.assertEqual(pairs[0]['admission']['point'],36)
        self.assertEqual(len(successful_receiver_pairs(entry,[dict(first,value=13),resumed,worker])),1)
