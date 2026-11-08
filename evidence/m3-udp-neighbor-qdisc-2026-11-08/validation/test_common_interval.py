from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_udp_path_witness import common_witness
from m3_provider_stats import COUNTERS


def provider(t,value,**kw):
    r=dict(begin_ns=t,end_ns=t+1,available=1,owner_epoch='x',generation=1,socket=7)
    r.update({k:0 for k in COUNTERS});r.update(data_sent=value);r.update(kw);return r


def window():return dict(identity_stable=True,all_selected_source_control_observations=0,qdisc=dict(pairs=[{}],first=dict(filter_read_ns=[100,110],pass_counter=dict(packets=2,bytes=20)),last=dict(filter_read_ns=[300,310],pass_counter=dict(packets=2,bytes=20))))


class CommonIntervalTests(unittest.TestCase):
    def test_only_positive_increments_fully_inside_counter_read_brackets_qualify(self):
        result=common_witness(window(),[provider(120,10),provider(200,15)],['x',1,7])
        self.assertTrue(result['qualified']);self.assertEqual(result['provider']['totals']['data_sent'],5)
        self.assertEqual(result['between_filter_read_brackets_ns'],[110,300])
    def test_provider_growth_only_at_boundary_does_not_qualify(self):
        result=common_witness(window(),[provider(90,0),provider(120,10),provider(200,10)],['x',1,7])
        self.assertFalse(result['qualified']);self.assertEqual(result['provider']['totals']['data_sent'],0)
        self.assertFalse(common_witness(window(),[provider(105,0),provider(120,10)],['x',1,7])['qualified'])
    def test_unavailable_read_is_not_interpolated(self):
        rows=[provider(120,10),provider(150,0,available=0),provider(200,20)]
        result=common_witness(window(),rows,['x',1,7]);self.assertFalse(result['qualified']);self.assertEqual(result['fully_contained_provider_pairs'],0)
    def test_changed_identity_other_packets_or_pass_growth_withhold(self):
        for key,value in [('identity_stable',False),('all_selected_source_control_observations',1)]:
            w=window();w[key]=value;self.assertFalse(common_witness(w,[provider(120,1),provider(200,2)],['x',1,7])['qualified'])
        w=window();w['qdisc']['last']['pass_counter']['packets']=3
        self.assertFalse(common_witness(w,[provider(120,1),provider(200,2)],['x',1,7])['qualified'])
    def test_short_coverage_and_counter_regression_are_not_witnesses(self):
        w=window();w['qdisc']['pairs']=[];self.assertFalse(common_witness(w,[],['x',1,7])['qualified'])
        w=window();w['qdisc']['last']['filter_read_ns']=[105,108]
        self.assertFalse(common_witness(w,[],['x',1,7])['qualified'])
        w=window();w['qdisc']['last']['pass_counter']['bytes']=0
        with self.assertRaisesRegex(ValueError,'regression'):common_witness(w,[],['x',1,7])
