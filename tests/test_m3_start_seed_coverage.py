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


if __name__=='__main__':unittest.main()
