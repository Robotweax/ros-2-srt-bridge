from pathlib import Path
import json,sys,tempfile,unittest,subprocess
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_neighbor_diagnostics import normalize,valid_mac,summarize,configure,LIMIT,observe,sample

PEER='10.0.0.2';MAC='02:00:00:00:00:02'
def entry(state='REACHABLE',address=PEER,mac=MAC):return dict(dst=address,dev='eth0',state=[state],lladdr=mac)


class Lab:
    containers={'operator':'owned-op','robot':'owned-robot'}
    addresses={'operator':'10.0.0.1','robot':PEER}
    def __init__(self):self.calls=[];self.entries={};self.macs={'operator':'02:00:00:00:00:01','robot':MAC}
    def inside(self,role,label,argv):
        self.calls.append((role,argv))
        if label.startswith('neighbor-link'):return json.dumps([dict(ifname='eth0',address=self.macs[role])])
        if label.startswith('neighbor-install'):
            self.entries[role]=entry('PERMANENT',argv[3],argv[5]);return ''
        return json.dumps([self.entries[role]] if role in self.entries else [])


class NeighborTests(unittest.TestCase):
    def test_empty_failed_and_valid_states_are_preserved(self):
        self.assertEqual(normalize([],PEER),[])
        r=entry('FAILED');r.pop('lladdr');self.assertEqual(normalize([r],PEER),[r])
        self.assertEqual(normalize([entry()],PEER)[0]['state'],['REACHABLE'])
    def test_wrong_identity_duplicate_and_mac_rejected(self):
        for raw in ([entry(),entry()],[entry(address='10.0.0.3')],[entry(mac='ff:ff:ff:ff:ff:ff')],[dict(entry(),dev='eth1')],[dict(entry(),state=[])],{}):
            with self.assertRaises(ValueError):normalize(raw,PEER)
        self.assertFalse(valid_mac('00:00:00:00:00:00'));self.assertTrue(valid_mac(MAC))
    def test_dynamic_configuration_does_not_mutate_neighbors(self):
        lab=Lab();r=configure(lab,'dynamic');self.assertEqual(r['before'],{'operator':[],'robot':[]})
        self.assertFalse(any('replace' in argv for _,argv in lab.calls))
    def test_permanent_configuration_uses_actual_owned_peer_macs(self):
        lab=Lab();r=configure(lab,'permanent');self.assertEqual(r['before']['operator'][0]['lladdr'],MAC)
        self.assertEqual(r['before']['robot'][0]['lladdr'],lab.macs['operator'])
        self.assertTrue(all(role in lab.containers for role,_ in lab.calls))
        lab=Lab();lab.macs['robot']='ff:ff:ff:ff:ff:ff'
        with self.assertRaises(ValueError):configure(lab,'permanent')
    def test_read_only_query_has_brackets_and_scoped_show(self):
        with patch('m3_neighbor_diagnostics.subprocess.run') as run:
            run.return_value.returncode=0;run.return_value.stdout=json.dumps([entry()]);r=observe(PEER)
            self.assertIsNone(r['error']);self.assertGreaterEqual(r['end_ns'],r['begin_ns'])
            self.assertEqual(run.call_args.args[0],['ip','-j','-s','neigh','show','to',PEER])
    def test_query_error_explicit(self):
        with patch('m3_neighbor_diagnostics.subprocess.run',side_effect=OSError):self.assertEqual(observe(PEER)['error'],'OSError')
    def write(self,p,rows,status=None):
        p.write_text(''.join(json.dumps(r)+'\n' for r in rows));p.with_suffix('.status.json').write_text(json.dumps(status or dict(complete=True,records=len(rows),limit=LIMIT)))
    def rows(self):return [dict(sequence=i,begin_ns=i*100,end_ns=i*100+10,entries=[entry()] if i==1 else [],error=None) for i in (1,2)]
    def test_summary_retains_absence_cadence_and_span(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'r.jsonl';self.write(p,self.rows());r=summarize(p,PEER)
            self.assertEqual(r['states'],{'REACHABLE':1,'ABSENT':1});self.assertEqual(r['max_read_span_ns'],10);self.assertEqual(r['max_sample_start_gap_ns'],100)
    def test_incomplete_loss_error_overlap_and_budget_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'r.jsonl'
            for mutate in ('error','sequence','overlap','status','count','limit'):
                rows=self.rows();status=dict(complete=True,records=2,limit=LIMIT)
                if mutate=='error':rows[1]['error']='TimeoutExpired'
                if mutate=='sequence':rows[1]['sequence']=3
                if mutate=='overlap':rows[1]['begin_ns']=105
                if mutate=='status':status['complete']=False
                if mutate=='count':status['records']=3
                if mutate=='limit':status['limit']=3
                self.write(p,rows,status)
                with self.assertRaises(ValueError):summarize(p,PEER)
    def test_sampler_finishes_with_status_and_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);stop=root/'stop';stop.touch();out=root/'r.jsonl'
            with patch('m3_neighbor_diagnostics.observe',return_value=self.rows()[0]):sample(out,root/'ready',stop,PEER)
            self.assertTrue((root/'ready').exists());self.assertTrue(summarize(out,PEER)['complete'])
    def test_runner_permanent_mode_requires_explicit_diagnostics(self):
        root=Path(__file__).resolve().parents[1]
        p=subprocess.run([sys.executable,str(root/'tools/run_m3.py'),'--neighbor-mode','permanent'],capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertIn('requires neighbor diagnostics',p.stderr)
