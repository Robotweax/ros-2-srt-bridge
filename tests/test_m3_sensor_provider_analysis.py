from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_sensor_provider_analysis import connection_windows
import test_m3_provider_stats as provider_tests


class SensorWindowTests(unittest.TestCase):
    def rows(self):return provider_tests.SensorProviderStatsTest().rows()
    def test_window_boundary_and_gauges_are_not_total_deltas(self):
        rows=self.rows();rows[1].update(receiver_drop=8,receive_buffer_packets=0)
        self.assertEqual(connection_windows(rows,101,220)[0]['contained_pairs'],0)
        g=connection_windows(rows,100,220)[0]
        self.assertEqual(g['contained_pair_totals']['receiver_drop'],6)
        self.assertEqual(g['gauges']['receive_buffer_packets'],[0,2])
        self.assertEqual(g['last_cumulative']['receiver_drop'],8)
        self.assertEqual(g['contained_first_read_ns'],[100,110])
    def test_unavailable_read_and_connection_reset_never_bridge(self):
        rows=self.rows();gap=dict(rows[0],available=0,begin_ns=130,end_ns=140)
        self.assertEqual(connection_windows([rows[0],gap,rows[1]],90,220)[0]['contained_pairs'],0)
        rows[1]['generation']=2;groups=connection_windows(rows,90,220)
        self.assertEqual(len(groups),2);self.assertFalse(any(g['contained_pairs'] for g in groups))
    def test_invalid_interval_and_negative_counter_delta_fail(self):
        for start,end in [(0,2),(2,2),(4,3)]:
            with self.assertRaises(ValueError):connection_windows(self.rows(),start,end)
        rows=self.rows();rows[1]['receiver_drop']=0
        with self.assertRaisesRegex(ValueError,'regression'):connection_windows(rows,90,220)
