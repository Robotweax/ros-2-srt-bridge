from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_control_provider_liveness import correlate
from m3_provider_stats import COUNTERS


def provider(t,socket,**kw):
    r=dict(available=1,begin_ns=t,end_ns=t+1,socket=socket,generation=1,owner_epoch=str(socket),session='ab'*16)
    r.update({k:0 for k in COUNTERS});r.update(kw);return r


class CorrelationTests(unittest.TestCase):
    def setup_data(self):
        flow=dict(direction='out',source='10.0.0.1',destination='10.0.0.2',source_port=10080,destination_port=40000,destination_socket_id=20)
        stats={'operator-bridge-0.log':dict(records=[provider(90,10),provider(120,10),provider(180,10,data_sent=5)]),'robot-bridge-0.log':dict(records=[provider(90,20)])}
        reverse=dict(flow,direction='in',source=flow['destination'],destination=flow['source'],source_port=40000,destination_port=10080,destination_socket_id=10,monotonic_ns=95)
        return flow,stats,{'operator':[reverse],'robot':[]}
    def run_case(self,change=None):
        f,s,c=self.setup_data()
        if change:change(f,s,c)
        return correlate(f,100,200,'operator','robot',s,c)
    def test_growth_with_no_egress_is_preserved(self):
        r=self.run_case();self.assertIn('increased_without',r['classification']);self.assertEqual(r['provider']['totals']['data_sent'],5)
    def test_zero_selected_counters_never_claim_no_udp(self):
        def change(f,s,c):s['operator-bridge-0.log']['records'][-1]['data_sent']=0
        self.assertIn('not_udp_absence_proof',self.run_case(change)['classification'])
    def test_mapping_mismatch_withheld(self):
        for change in (lambda f,s,c:f.update(destination_socket_id=99),lambda f,s,c:c.update(operator=[]),lambda f,s,c:s['robot-bridge-0.log']['records'][0].update(session='cd'*16)):
            self.assertEqual(self.run_case(change)['classification'],'mapping_withheld')
    def test_unavailable_or_new_generation_has_no_delta(self):
        for kw in (dict(available=0),dict(generation=2)):
            def change(f,s,c):s['operator-bridge-0.log']['records'][-1].update(kw)
            self.assertEqual(self.run_case(change)['classification'],'insufficient_available_provider_pairs')
    def test_source_observation_is_not_hidden_by_counter_growth(self):
        def change(f,s,c):c['operator'].append(dict(f,monotonic_ns=150))
        self.assertEqual(self.run_case(change)['classification'],'old_flow_egress_present_in_interval')
