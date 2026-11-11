import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_loaded_arp_diagnostics import selected_slots


class StartSeedCoverageTests(unittest.TestCase):
    def test_focused_unchanged_and_predeclared_extension_has_no_2903_retry(self):
        self.assertEqual([(r['profile'],r['seed'],r['seconds']) for r in selected_slots('focused',False)],[('N0',2903,15),('N5',2903,300)])
        self.assertEqual([(r['profile'],r['seed'],r['seconds']) for r in selected_slots('additional-seeds',True)],[('N0',1701,15),('N5',1701,300),('N5',4211,300)])
    def test_extension_cannot_silently_use_old_runtime(self):
        for name,enabled in [('additional-seeds',False),('unknown',True)]:
            with self.assertRaises(ValueError):selected_slots(name,enabled)
    def test_sender_cohort_is_separate_and_bounded_without_4211(self):
        self.assertEqual([(r['profile'],r['seed'],r['seconds']) for r in selected_slots('sender-visibility',True,True)],[('N0',1701,15),('N5',1701,300)])
    def test_sender_cohort_cannot_borrow_old_selection_or_omit_diagnostics(self):
        for coverage,start,sender in [('focused',True,True),('additional-seeds',True,True),('sender-visibility',False,True),('sender-visibility',True,False)]:
            with self.subTest(coverage=coverage,start=start,sender=sender),self.assertRaises(ValueError):selected_slots(coverage,start,sender)
    def test_probe_cohort_is_explicit_and_bounded(self):
        self.assertEqual([(r['profile'],r['seed'],r['seconds']) for r in selected_slots('probe-tracing',True,True,True)],[('N0',1701,15),('N5',1701,300)])
    def test_probe_cohort_cannot_borrow_or_drop_diagnostics(self):
        for args in [('focused',True,True,True),('sender-visibility',True,True,True),('probe-tracing',False,True,True),('probe-tracing',True,False,True),('probe-tracing',True,True,False)]:
            with self.subTest(args=args),self.assertRaises(ValueError):selected_slots(*args)


if __name__=='__main__':unittest.main()
