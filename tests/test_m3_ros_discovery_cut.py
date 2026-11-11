import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_ros_discovery_cut import blocked,recovered,FIELDS
from m3_capture import wait_ready


def state(ready=False):
    s=dict(ready=ready,failed=False,journal_ready=True,handler_ready=True,qos_verified=True,commands_sent=0,start_claims=0,effects=0,hellos_sent=60,hellos_received=10 if ready else 0,process_epoch=[1]*16)
    s.update({k:1 if ready else 0 for k in FIELDS});return s


class RosDiscoveryTests(unittest.TestCase):
    def test_no_work_is_allowed_inside_discovery_barrier_even_if_ready(self):
        states={r:state() for r in ('operator','robot')};blocked(states)
        for field in ('commands_sent','start_claims','effects'):
            bad=copy.deepcopy(states);bad['robot'][field]=1
            with self.assertRaises(ValueError):blocked(bad)
        bad=copy.deepcopy(states);bad['operator']=state(True)
        with self.assertRaises(ValueError):blocked(bad)

    def test_recovery_requires_full_matches_live_hello_callbacks_and_original_owner(self):
        initial={r:state() for r in ('operator','robot')};after={r:state(True) for r in initial};recovered(initial,after)
        for defect in ('owner','match','hello','work'):
            bad=copy.deepcopy(after)
            if defect=='owner':bad['robot']['process_epoch']=[2]*16
            elif defect=='match':bad['operator']['control_subscribers']=0
            elif defect=='hello':bad['operator']['hellos_received']=0
            else:bad['operator']['commands_sent']=1
            with self.subTest(defect=defect),self.assertRaises(ValueError):recovered(initial,bad)

    def test_capture_readiness_never_accepts_dead_recorder_or_missing_listener(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for r in ('operator','robot'):(p/(r+'-capture.log')).write_text('listening on eth0\n')
            alive=Mock();alive.poll.return_value=None;wait_ready(p,[(alive,None)])
            dead=Mock();dead.poll.return_value=0
            with self.assertRaises(ValueError):wait_ready(p,[(dead,None)])
            (p/'robot-capture.log').write_text('not initialized')
            with self.assertRaises(ValueError):wait_ready(p,[(alive,None)],seconds=0)
