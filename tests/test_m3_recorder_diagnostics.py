import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_recorder_diagnostics import observe, read_process, summarize


class RecorderDiagnosticsTests(unittest.TestCase):
    def fixture(self, root):
        path=root/'17';path.mkdir();(path/'comm').write_text('tcpdump\n')
        fields=['0']*40;fields[0]='T';fields[11]='7';fields[12]='3';fields[19]='123'
        (path/'stat').write_text('17 (test (recorder)) '+' '.join(fields))
        (path/'schedstat').write_text('100 200 3\n');(path/'wchan').write_text('do_signal_stop')
        (path/'io').write_text('rchar: 4\nwchar: 5\nsyscr: 6\nsyscw: 7\nread_bytes: 8\nwrite_bytes: 9\ncancelled_write_bytes: 0\n')
        (path/'status').write_text('voluntary_ctxt_switches: 10\nnonvoluntary_ctxt_switches: 11\n')
        return path

    def test_stopped_process_and_counters_survive_parenthesized_comm(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=self.fixture(Path(tmp));row=observe(Path(tmp))
            self.assertEqual(row['errors'],[])
            process=row['processes'][0]
            self.assertEqual((process['pid'],process['start_ticks'],process['cpu_ticks'],process['state']),(17,123,10,'T'))
            self.assertEqual(process['scheduler']['runqueue_wait_ns'],200)
            self.assertEqual(process['io']['write_bytes'],9)
            self.assertEqual(process['context_switches']['nonvoluntary_ctxt_switches'],11)

    def test_unavailable_counters_are_explicit_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=self.fixture(Path(tmp));(path/'io').unlink()
            row=read_process(path)
            self.assertNotIn('io',row)
            self.assertEqual(row['unavailable'],[dict(field='io',error='FileNotFoundError')])

    def test_pid_reuse_and_missing_process_samples_not_joined(self):
        a=dict(begin_ns=1,end_ns=2,errors=[],processes=[dict(pid=3,start_ticks=10,state='T')])
        b=copy.deepcopy(a);b.update(begin_ns=5,end_ns=6);b['processes'][0].update(start_ticks=11,state='R')
        c=dict(begin_ns=9,end_ns=10,errors=[],processes=[])
        result=summarize([a,b,c])
        self.assertEqual(len(result['processes']),2)
        self.assertEqual(result['processes'][0]['states'],{'T':1})
        self.assertEqual(result['missing_process_samples'],1)
        self.assertEqual(result['maximum_sample_gap_ns'],3)

    def test_bad_clock_brackets_rejected(self):
        with self.assertRaises(ValueError):summarize([])
        with self.assertRaises(ValueError):summarize([dict(begin_ns=2,end_ns=1)])
        row=dict(begin_ns=1,end_ns=3,processes=[],errors=[])
        with self.assertRaises(ValueError):summarize([row,row])
