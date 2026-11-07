from pathlib import Path
import json,sys,tempfile,unittest,subprocess
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_qdisc_diagnostics import selector,counters,root,summarize,sample,LIMIT


def rules():return [dict(kind='u32',protocol='ip',options=dict(not_in_hw=True,actions=[dict(kind='gact',control_action=dict(type='pass'),stats=dict(packets=2,bytes=200,drops=0))]))]
def row(n):return dict(sequence=n,begin_ns=n*100,end_ns=n*100+40,error=None,filter_read_ns=[n*100+1,n*100+10],root_read_ns=[n*100+20,n*100+30],pass_counter=dict(packets=n,bytes=n*100,drops=0),root=dict(kind='tbf',handle='1:',packets=n,bytes=n*100,drops=n,overlimits=n,backlog=20,qlen=1))


class QdiscTests(unittest.TestCase):
    def test_selector_is_exact_owned_peer_control_and_pass(self):
        a=selector('operator','10.0.0.2');self.assertIn('sport',a);self.assertIn('10.0.0.2/32',a);self.assertEqual(a[-2:],['action','pass']);self.assertNotIn('10081',a)
        self.assertIn('dport',selector('robot','10.0.0.1'))
    def test_scoped_json_accepts_omitted_pref_but_not_wrong_action_or_offload(self):
        self.assertEqual(counters(rules())['packets'],2)
        for variant in ('pref','drop','hardware','multiple','loss'):
            r=rules()
            if variant=='pref':r[0]['pref']=1
            if variant=='drop':r[0]['options']['actions'][0]['control_action']['type']='drop'
            if variant=='hardware':r[0]['options']['not_in_hw']=False
            if variant=='multiple':r+=rules()
            if variant=='loss':r[0]['options']['actions'][0]['stats']['drops']=1
            with self.assertRaises(ValueError):counters(r)
    def test_root_counters_are_separate_from_child(self):
        r=row(1)['root']|dict(root=True);self.assertEqual(root([r,dict(r,root=False)])['drops'],1)
        with self.assertRaises(ValueError):root([r,r])
    def write(self,path,rows):
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows));path.with_suffix('.status.json').write_text(json.dumps(dict(complete=True,records=len(rows),limit=LIMIT)))
    def test_read_brackets_accounting_regression_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'s.jsonl';self.write(p,[row(1),row(2)]);r=summarize(p);self.assertTrue(r['complete']);self.assertEqual(r['max_read_span_ns'],40)
            for variant in ('sequence','counter','root','span','error','drop'):
                rows=[row(1),row(2)]
                if variant=='sequence':rows[1]['sequence']=3
                if variant=='counter':rows[1]['pass_counter']['packets']=0
                if variant=='root':rows[1]['root']['handle']='2:'
                if variant=='span':rows[1]['root_read_ns'][0]=100
                if variant=='error':rows[1]['error']='TimeoutExpired'
                if variant=='drop':rows[1]['pass_counter']['drops']=1
                self.write(p,rows)
                with self.assertRaises(ValueError):summarize(p)
    def test_existing_outputs_not_mutated_and_budget_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'s.jsonl';p.write_text('retained')
            with self.assertRaises(FileExistsError):sample(p,Path(tmp)/'ready',Path(tmp)/'stop')
            self.assertEqual(p.read_text(),'retained');self.assertFalse(p.with_suffix('.status.json').exists())
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'s.jsonl'
            with patch('m3_qdisc_diagnostics.LIMIT',1),patch('m3_qdisc_diagnostics.observe',return_value=row(1)),patch('m3_qdisc_diagnostics.time.sleep'):
                with self.assertRaisesRegex(RuntimeError,'budget'):sample(p,Path(tmp)/'ready',Path(tmp)/'stop')
            self.assertFalse(json.loads(p.with_suffix('.status.json').read_text())['complete'])
    def test_runner_rejects_classifier_fault_combination(self):
        p=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'tools/run_m3.py'),'--control-qdisc-diagnostics','--control-egress-fault','operator','--seconds','45','--monotonic-capture','--command-diagnostics','--provider-diagnostics'],capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertIn('qdisc diagnostics require',p.stderr)

    def test_probe_root_kind_changes_explicitly_remove_only_owned_root(self):
        from m3_qdisc_counter_probe import apply_profile
        class Lab:
            def __init__(self,kind):self.kind=kind;self.calls=[]
            def inside(self,role,label,argv):
                self.calls.append((role,argv))
                return json.dumps([dict(kind=self.kind,root=True)]) if 'show' in argv else ''
            def apply(self,*args,**kw):self.applied=(args,kw)
        for current,target,remove in [('netem','N5',True),('tbf','N0',True),('netem','N4',False)]:
            lab=Lab(current);apply_profile(lab,target,'phase')
            self.assertEqual(any('del' in args for _,args in lab.calls),remove)
            self.assertTrue(all(role=='operator' for role,_ in lab.calls))
            self.assertEqual(lab.applied[1]['roles'],('operator',))
