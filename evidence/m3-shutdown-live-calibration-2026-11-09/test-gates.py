"""Offline calibration gate controls; no live fixture/capture launch."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('calibration',Path(__file__).with_name('calibrate.py'));c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class Gates(unittest.TestCase):
    def test_plan_has_no_loss_or_retry_slot(self):
        self.assertEqual([s['id'] for s in c.PLAN],['default-off-N0','enabled-procfs-N0','independent-blocked-procfs'])
        self.assertNotIn('4211',str(c.PLAN))
    def test_fixture_marker_pairs_and_drop_failures(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'trace';rows=[dict(sequence=i+1,pid=1,tid=2,monotonic_ns=i+1,dropped_before=0,point=point) for i,point in enumerate(('fixture_ready','fixture_sigint_observed','fixture_blocked_begin','fixture_blocked_end','fixture_exit'))]
            p.write_text('\n'.join(json.dumps(r) for r in rows));c.trace_check(p,1,True)
            for kind in ('gap','drop','thread','point'):
                data=[dict(r) for r in rows]
                if kind=='gap':data[2]['sequence']=99
                elif kind=='drop':data[-1]['dropped_before']=1
                elif kind=='thread':data[3]['tid']=3
                else:data[-1]['point']='missing'
                p.write_text('\n'.join(json.dumps(r) for r in data))
                with self.subTest(kind=kind),self.assertRaises(ValueError):c.trace_check(p,1,True)
if __name__=='__main__':unittest.main()
