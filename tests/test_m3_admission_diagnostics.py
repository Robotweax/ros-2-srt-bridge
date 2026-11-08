import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_admission_diagnostics import correlate


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
