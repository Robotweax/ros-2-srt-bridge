from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_control_fault_analysis import baseline,inside_deltas,connection
from m3_provider_stats import COUNTERS


def row(n,**kw):
    result=dict(owner_epoch='01'*16,generation=1,socket=42,available=1,begin_ns=n*10,end_ns=n*10+2)
    result.update({key:n for key in COUNTERS});result.update(kw);return result


class AnalysisTests(unittest.TestCase):
    def test_delta_uses_whole_read_brackets_inside_window(self):
        rows=[row(n) for n in range(5)]
        result=inside_deltas(rows,connection(rows[0]),12,42)
        self.assertEqual(len(result['adjacent_pairs']),2)
        self.assertEqual(result['totals']['data_sent'],2)
        self.assertEqual(result['adjacent_pairs'][0]['previous_read_ns'],[20,22])

    def test_unavailable_and_reconnect_break_adjacency(self):
        rows=[row(1),row(2,available=0),row(3),row(4,generation=2),row(5)]
        self.assertFalse(inside_deltas(rows,connection(rows[0]),0,100)['adjacent_pairs'])
        rows=[row(1),row(2,socket=43)]
        self.assertFalse(inside_deltas(rows,connection(rows[0]),0,100)['adjacent_pairs'])

    def test_baseline_recent_and_ends_before_boundary(self):
        stats={'old':dict(records=[row(1)]),'new':dict(records=[row(2),row(3)])}
        self.assertEqual(baseline(stats,25)[0],'new')
        self.assertEqual(baseline(stats,25)[1]['begin_ns'],20)
        with self.assertRaises(ValueError):baseline(stats,3000000000)
        with self.assertRaises(ValueError):baseline(stats,1)
