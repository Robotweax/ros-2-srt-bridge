import io
from pathlib import Path
import signal
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ros2/robotweax_srt_bridge_demo/scripts'))
from scenario_processes import stop_children


class Process:
    def __init__(self,initial=None,exitcode=0,timeout=False):self.pid=123;self.code=initial;self.exitcode=exitcode;self.timeout=timeout;self.signals=[];self.killed=False
    def poll(self):return self.code
    def send_signal(self,value):self.signals.append(value)
    def wait(self,timeout):
        if self.timeout and not self.killed:raise subprocess.TimeoutExpired('owned-child',timeout)
        self.code=-9 if self.killed else self.exitcode;return self.code
    def kill(self):self.killed=True


class ScenarioProcessTests(unittest.TestCase):
    def test_controlled_clean_exit_is_recorded_with_signal_bracket(self):
        p=Process();log=io.StringIO();r=stop_children([(p,'bridge',log)])
        self.assertTrue(r['passed']);self.assertTrue(log.closed);self.assertEqual(p.signals,[signal.SIGINT])
        row=r['children'][0];self.assertIsNone(row['initial_returncode']);self.assertEqual(row['returncode'],0)
        self.assertLessEqual(row['begin_ns'],row['signal_begin_ns']);self.assertLessEqual(row['signal_end_ns'],row['end_ns'])

    def test_preexisting_exit_even_zero_and_abnormal_signal_exit_are_not_hidden(self):
        for p in (Process(initial=0),Process(initial=-11),Process(exitcode=-11)):
            log=io.StringIO();r=stop_children([(p,'bridge',log)])
            self.assertFalse(r['passed']);self.assertTrue(log.closed)
            if r['children'][0]['initial_returncode'] is not None:self.assertFalse(p.signals)
            else:self.assertEqual(r['children'][0]['returncode'],-11)

    def test_forced_kill_stays_failed_and_other_owned_children_are_cleaned(self):
        p=Process(timeout=True);other=Process();logs=[io.StringIO(),io.StringIO()]
        r=stop_children([(other,'source',logs[0]),(p,'bridge',logs[1])])
        self.assertFalse(r['passed']);self.assertTrue(p.killed);self.assertTrue(all(log.closed for log in logs))
        self.assertEqual(r['children'][0]['returncode'],-9);self.assertTrue(r['children'][0]['forced_kill'])
        self.assertTrue(r['children'][1]['passed'])
