from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_root_loss_analysis import settled_window


class LossWindowTests(unittest.TestCase):
    def test_predeclared_settling_margins_preserve_command_brackets(self):
        fault=dict(restored=True,install=dict(end_ns=1000000000),remove=dict(begin_ns=3200000000))
        self.assertEqual(settled_window(fault),(1500000000,3100000000))
    def test_short_or_unrestored_not_silently_extended(self):
        for f in (dict(restored=False),dict(restored=True,install=dict(end_ns=1000000000),remove=dict(begin_ns=2000000000))):
            with self.assertRaises(ValueError):settled_window(f)
