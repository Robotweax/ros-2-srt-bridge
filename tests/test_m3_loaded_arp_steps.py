from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_loaded_arp_steps import positive_steps,root_context
import test_m3_loaded_arp as fixtures


class ArpStepTests(unittest.TestCase):
    def test_all_positive_actions_retained_without_double_count_assumption(self):
        a=fixtures.row(1);b=fixtures.row(2,1);b['counters']['verdict']['packets']=0;c=fixtures.row(3,1)
        steps=positive_steps([a,b,c],90,330);self.assertEqual(len(steps),2)
        self.assertEqual(steps[0]['delta']['eligible']['packets'],1);self.assertEqual(steps[1]['delta']['eligible']['packets'],0)
    def test_boundary_crossing_and_regression(self):
        self.assertEqual(positive_steps([fixtures.row(1),fixtures.row(2,1)],110,230),[])
        with self.assertRaises(ValueError):positive_steps([fixtures.row(1,2),fixtures.row(2,1)],90,230)
    def test_root_context_is_wider_and_censoring_not_zero(self):
        rows=fixtures.ReplyRootScopeTests().roots(7);r=root_context(rows,150,250)
        self.assertTrue(r['available']);self.assertEqual(r['window_ns'],[100,310])
        self.assertFalse(root_context(rows,50,250)['available'])
