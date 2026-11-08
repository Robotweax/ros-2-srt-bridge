import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_dds_discovery_loss import selector,counters,assess,trace


def fixture():
    def state(role):return dict(peer_discovered=True,writer_matches=1,reader_matches=1,received=25,invalid=0,pid=1,started_ns=1,participant=role+'part',writer=role+'write',reader=role+'read',writer_metadata_bytes=4096 if role=='robot' else 0,reader_metadata_bytes=4096 if role=='robot' else 0,sent=60,monotonic_ns=10_000_000_000)
    states={r:state(r) for r in ('operator','robot')};blocked=copy.deepcopy(states);blocked['operator'].update(writer_matches=0,reader_matches=0,received=0)
    result=dict(case='fragment-cut',initial=copy.deepcopy(states),final=copy.deepcopy(states),blocked=blocked,hold=dict(begin_ns=1,end_ns=8_000_000_001),drops=[dict(drops=3)],remove=dict(begin_ns=9_000_000_000,end_ns=9_000_000_001),qualified=copy.deepcopy(states),steady=dict(end_ns=10_000_000_000))
    traces={role:dict(rows=[dict(event='hello_received',valid=True,sent_ns=9_000_000_010,monotonic_ns=10_000_000_000) for _ in range(20)]) for role in states}
    return result,traces


class DiscoveryLossTests(unittest.TestCase):
    def test_fragment_selector_matches_exact_offset_without_assuming_continuation_udp_ports(self):
        cmd=selector('10.0.0.2','10.0.0.3')
        self.assertIn('0x00b9',cmd);self.assertIn('0x1fff',cmd);self.assertNotIn('dport',cmd);self.assertNotIn('sport',cmd)
        for src,dst in [('127.0.0.1','10.0.0.2'),('10.0.0.2','10.0.0.2'),('::1','::2')]:
            with self.assertRaises(ValueError):selector(src,dst)

    def test_drop_counters_require_exact_owned_preference_and_real_drop(self):
        r=[dict(kind='u32',protocol='ip',pref=49146,options=dict(actions=[dict(kind='gact',control_action=dict(type='drop'),stats=dict(packets=3,drops=3,bytes=100))]))]
        self.assertEqual(counters(r)[0]['drops'],3)
        for kind in ('preference','pass','mismatch'):
            bad=copy.deepcopy(r)
            if kind=='preference':bad[0]['pref']=49149
            elif kind=='pass':bad[0]['options']['actions'][0]['control_action']['type']='pass'
            else:bad[0]['options']['actions'][0]['stats']['drops']=2
            with self.assertRaises(ValueError):counters(bad)

    def test_recovery_needs_original_endpoints_fresh_callbacks_and_preserved_participant_discovery(self):
        result,traces=fixture();self.assertEqual(assess(result,traces)['fresh_callbacks'],dict(operator=20,robot=20))
        for defect in ('restart','stale','participant','early_match','metadata','deadline','late_callback'):
            r=copy.deepcopy(result);t=copy.deepcopy(traces)
            if defect=='restart':r['final']['robot']['writer']='replacement'
            elif defect=='stale':t['robot']['rows'][0]['sent_ns']=1
            elif defect=='participant':r['blocked']['operator']['peer_discovered']=False
            elif defect=='early_match':t['operator']['rows'].append(dict(event='writer_match',current=1,monotonic_ns=1))
            elif defect=='metadata':r['initial']['robot']['writer_metadata_bytes']=1
            elif defect=='deadline':r['qualified']['robot']['monotonic_ns']=60_000_000_000
            else:t['robot']['rows'][0]['monotonic_ns']=10_000_000_001
            with self.subTest(defect=defect),self.assertRaises(ValueError):assess(r,t)

    def test_trace_refuses_missing_footer_exhaustion_and_unclean_teardown(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'log';p.write_text('DDS_PROBE '+json.dumps(dict(record=1))+'\n')
            with self.assertRaises(ValueError):trace(p)
            base=p.read_text();footer=dict(attempted=1,recorded=1,limit=2048,exhausted=False,dds_closed=True,shutdown_ns=10)
            for defect in (None,'exhausted','closed','dropped'):
                f=copy.deepcopy(footer)
                if defect=='exhausted':f['exhausted']=True
                elif defect=='closed':f['dds_closed']=False
                elif defect=='dropped':f['attempted']=2
                p.write_text(base+'DDS_PROBE_STATUS '+json.dumps(f)+'\n')
                if defect is None:self.assertEqual(trace(p)['status']['recorded'],1)
                else:
                    with self.assertRaises(ValueError):trace(p)
