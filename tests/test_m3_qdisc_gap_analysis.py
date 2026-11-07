from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_qdisc_gap_analysis import inside_deltas,classify


def row(n):return dict(begin_ns=n*10,end_ns=n*10+2,pass_counter=dict(packets=n,bytes=n*100),root=dict(packets=n,bytes=n*100,drops=n,overlimits=n,backlog=20-n,qlen=n))


class QdiscGapTests(unittest.TestCase):
    def test_only_wholly_inside_paired_reads_contribute_and_gauges_are_not_deltas(self):
        r=inside_deltas([row(n) for n in range(5)],12,42)
        self.assertEqual(len(r['pairs']),1);self.assertEqual(r['totals']['pass_packets'],1)
        self.assertEqual(r['max_root_backlog_bytes'],18);self.assertNotIn('backlog',r['totals'])
    def test_positive_and_flat_counters_distinguished_without_unqualified_mapping(self):
        gap={'classification':'selected_send_counters_increased_without_old_flow_egress_observation'};delta=inside_deltas([row(1),row(2)],0,30)
        self.assertEqual(classify(gap,delta,0,True),'pass_counter_growth_without_source_control_tap')
        self.assertEqual(classify(gap,delta,1,True),'other_source_control_observations_present')
        self.assertEqual(classify(gap,delta,0,False),'selector_socket_association_withheld')
        delta['totals']['pass_packets']=0
        self.assertEqual(classify(gap,delta,0,True),'provider_growth_without_pass_counter_growth')
        delta['pairs']=[];self.assertEqual(classify(gap,delta,0,True),'insufficient_counter_pairs')
    def test_counter_regression_rejects(self):
        rows=[row(1),row(2)];rows[1]['pass_counter']['packets']=0
        with self.assertRaises(ValueError):inside_deltas(rows,0,30)
