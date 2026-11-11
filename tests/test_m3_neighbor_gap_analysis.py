from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_neighbor_gap_analysis import window_rows


class NeighborGapTests(unittest.TestCase):
    def test_inside_edges_and_boundary_reads_are_not_interchanged(self):
        rows=[dict(sequence=i,begin_ns=b,end_ns=e,entries=[dict(state=[state])]) for i,(b,e,state) in enumerate([(5,9,'REACHABLE'),(9,12,'STALE'),(13,15,'INCOMPLETE'),(18,22,'REACHABLE'),(22,24,'REACHABLE')])]
        r=window_rows(rows,10,20)
        self.assertEqual(r['before']['sequence'],0);self.assertEqual(r['after']['sequence'],4)
        self.assertEqual([s['sequence'] for s in r['inside']],[2]);self.assertEqual([s['sequence'] for s in r['crossing']],[1,3])
        self.assertEqual(r['inside_states'],{'INCOMPLETE':1})
    def test_missing_neighbor_is_preserved_and_invalid_window_rejected(self):
        r=window_rows([dict(begin_ns=12,end_ns=14,entries=[])],10,20)
        self.assertEqual(r['inside_states'],{'ABSENT':1});self.assertIsNone(r['before']);self.assertIsNone(r['after'])
        with self.assertRaises(ValueError):window_rows([],20,10)
