from pathlib import Path
import copy,json,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_arp_reply_diagnostics import summarize,LIMIT
from m3_loaded_arp_analysis import interval,reply_witness


def row(n,p=0):
    return dict(sequence=n,begin_ns=n*100,end_ns=n*100+20,read_ns=[n*100+2,n*100+18],error=None,counters=dict(verdict_type='pass',eligible=dict(index=1,packets=p,bytes=p*42,drops=0),verdict=dict(index=2,packets=p,bytes=p*42,drops=0)))


class LoadedArpTests(unittest.TestCase):
    def parse(self,rows,**kw):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'s.jsonl';p.write_text(''.join(json.dumps(r)+'\n' for r in rows));p.with_suffix('.status.json').write_text(json.dumps(dict(complete=True,records=len(rows),limit=LIMIT)|kw));return summarize(p)
    def test_live_nonatomic_pipe_and_pass_need_not_equal(self):
        rows=[row(1),row(2,1)];rows[1]['counters']['verdict']['packets']=0;rows[1]['counters']['verdict']['bytes']=0
        self.assertTrue(self.parse(rows)['complete'])
    def test_drop_regression_action_change_and_bad_bracket_fail(self):
        for change in ('drop','regression','index','bracket','alias'):
            rows=[row(1,2),row(2,3)]
            if change=='drop':rows[1]['counters']['eligible']['drops']=1
            if change=='regression':rows[1]['counters']['eligible']['packets']=0
            if change=='index':rows[1]['counters']['eligible']['index']=3
            if change=='bracket':rows[1]['read_ns']=[0,100]
            if change=='alias':rows[1]['counters']['verdict']['index']=1
            with self.assertRaises(ValueError):self.parse(rows)
    def test_budget_and_population_fail_closed(self):
        for kw in (dict(complete=False),dict(records=3),dict(limit=1)):
            with self.assertRaises(ValueError):self.parse([row(1)],**kw)
        with self.assertRaises(ValueError):self.parse([])
    def test_outer_envelope_includes_edges_not_just_inner_gap(self):
        v=interval([row(1),row(2,1)],90,230)
        self.assertEqual(v['outer_read_envelope_ns'],[102,218]);self.assertEqual(v['inner_read_gap_ns'],[118,202])
        self.assertIn('with_source',reply_witness(v,[dict(monotonic_ns=110)],[])['classification'])
        self.assertIn('without_source',reply_witness(v,[],[])['classification'])
    def test_crossing_reads_and_zero_growth_never_infer_absent_generation(self):
        v=interval([row(1),row(2),row(3)],110,320)
        self.assertEqual(len(v['crossing']),1);self.assertIn('not_generation_absence',reply_witness(v,[],[])['classification'])
        self.assertIn('insufficient',reply_witness(interval([row(1)],90,130),[],[])['classification'])
