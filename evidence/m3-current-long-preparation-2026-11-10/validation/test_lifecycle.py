"""Offline catalogs/procfs/child mocks; retained stage fixtures are not new runs."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
from launch_readiness import new_launch
from launch_records import plan_launch,save_launches
import launch_assessment as gate

def write(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True);Path(path).write_text(json.dumps(value)+'\n')
def read(path):return json.loads(Path(path).read_text())

class Fixture:
    def __init__(self,out):
        self.out=out;self.reports={r:dict(passed=True,children=[]) for r in ('operator','robot')};self.entries={};self.counter=0
        self.source=ROOT/'evidence/m3-strict-n3-execution-2026-11-10/cases/N3-baseline-1701'
        self.recent=ROOT/'evidence/m3-current-n0-bound-execution-2026-11-10/case'
        for role in ('operator','robot'):
            rows=[]
            names=['operator-bridge-0'] if role=='operator' else ['wrong-hash','robot-bridge-1','robot-bridge-2']
            for ordinal,name in enumerate(names):
                self.counter+=1;token=f'{self.counter:032x}';context=dict(schema_version=1,token=token,role=role,name=name,binary='/workspace/bridge_node',record='/workspace/.local/synthetic/launch-readiness/'+role+'-'+name+'-'+token+'.json')
                entry=plan_launch(context,1 if role=='operator' else max(ordinal,1));negative=entry['purpose']=='negative_type_hash';warm=entry['purpose']=='warmup'
                if negative:
                    stages=[];child=None;pid=100;ticks=500;lower=1
                else:
                    stage_path=self.recent/'robot-shutdown-stages.jsonl' if warm else self.source/(role+'-shutdown-stages.jsonl')
                    stages=[json.loads(x) for x in stage_path.read_text().splitlines()]
                    old=self.recent/'robot-child-shutdown.json' if warm else self.source/(role+'-child-shutdown.json')
                    child=next(c for c in read(old)['children'] if '-bridge-' in c['name'])
                    if role=='robot' and not warm:
                        for row in stages:row['monotonic_ns']+=100_000_000_000
                        for key in ('begin_ns','signal_begin_ns','signal_end_ns','end_ns'):
                            if key in child:child[key]+=100_000_000_000
                    pid=child['pid'];ticks=1180 if warm else 1119 if role=='operator' else 6000
                    lower=min(s['monotonic_ns'] for s in stages)-1000
                identity=dict(pid=pid,start_ticks=ticks,ppid=75,state='R',name='python3')
                permissions=dict(Pid=str(pid),PPid='75',CapEff='0',CapPrm='0',CapBnd='0',CapInh='0',CapAmb='0',NoNewPrivs='1',Seccomp='2')
                snapshot=dict(identity_before=identity,identity_after=identity,permissions=permissions,identity_helper=gate.BINDING,begin_ns=lower-1,end_ns=lower)
                write(out/entry['readiness_path'],dict(schema_version=1,phase=gate.PHASE,launch=context,snapshot=snapshot))
                entry.update(pid=pid,registration=identity,attested=not negative,returncode=1 if negative else 0)
                if not negative:
                    info=dict(**identity,permissions=permissions,identity_helper=gate.BINDING,launch_token=token,launch_name=name,boot_id='3fafbaab-7085-4fad-8600-cacd1874a053',time_namespace_offsets='monotonic           0         0\nboottime            0         0\n',monotonic_ns=lower,readiness_phase=gate.PHASE,execed_bridge_attested=False)
                    write(out/entry['identity_path'],info);(out/entry['trace_path']).write_text(''.join(json.dumps(s)+'\n' for s in stages))
                    child.update(name=name,launch_token=token,start_ticks=ticks,purpose=entry['purpose'],trace_path=entry['trace_path'],identity_path=entry['identity_path']);self.reports[role]['children'].append(child)
                    if entry['purpose']=='measurement':write(out/(role+'-bridge-identity.json'),info)
                rows.append(entry);self.entries[(role,entry['purpose'])]=entry
            write(out/(role+'-bridge-launches.json'),dict(schema_version=1,role=role,launches=rows))
        (out/'wrong-hash.log').write_text('bridge startup failed: ROS type hash mismatch\n');write(out/'robot-ready.json',dict(wrong_hash_rejected=True))
    def assess(self):return gate.assess_launches(self.out,self.reports)
    def mutate_entry(self,role,purpose,change):
        path=self.out/(role+'-bridge-launches.json');value=read(path);entry=next(e for e in value['launches'] if e['purpose']==purpose);change(entry);write(path,value)

class LifecycleTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name);self.f=Fixture(self.out)
    def test_all_three_positive_launches_pass_existing_socket_stage_gates(self):
        result=self.f.assess();self.assertEqual(set(result['robot']),{'warmup','measurement'});self.assertEqual(set(result['operator']),{'measurement'})
        self.assertEqual(result['robot']['warmup']['stages']['records'],51)
    def test_missing_warmup_refused(self):
        p=self.out/'robot-bridge-launches.json';v=read(p);v['launches'].pop(1);write(p,v)
        with self.assertRaises(ValueError):self.f.assess()
    def test_duplicate_or_swapped_launch_order_refused(self):
        p=self.out/'robot-bridge-launches.json';v=read(p);v['launches'][1:]=v['launches'][1:][::-1];write(p,v)
        with self.assertRaises(ValueError):self.f.assess()
    def test_trace_path_reuse_refused(self):
        self.f.mutate_entry('robot','measurement',lambda e:e.update(trace_path=self.f.entries['robot','warmup']['trace_path']))
        with self.assertRaises(ValueError):self.f.assess()
    def test_foreign_pid_trace_refused(self):
        p=self.out/self.f.entries['robot','measurement']['trace_path'];rows=[json.loads(x) for x in p.read_text().splitlines()];rows[0]['pid']+=1;p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        with self.assertRaises(ValueError):self.f.assess()
    def test_reused_pid_does_not_accept_warmup_trace_as_final(self):
        warm=self.f.entries['robot','warmup'];final=self.f.entries['robot','measurement'];(self.out/final['trace_path']).write_bytes((self.out/warm['trace_path']).read_bytes())
        with self.assertRaisesRegex(ValueError,'outside launch lifetime'):self.f.assess()
    def test_missing_final_child_refused(self):
        self.f.reports['robot']['children'].pop()
        with self.assertRaises(ValueError):self.f.assess()
    def test_wrong_child_start_ticks_refused(self):
        self.f.reports['robot']['children'][-1]['start_ticks']+=1
        with self.assertRaises(ValueError):self.f.assess()
    def test_duplicate_child_outcome_refused(self):
        self.f.reports['robot']['children'].append(copy.deepcopy(self.f.reports['robot']['children'][-1]))
        with self.assertRaises(ValueError):self.f.assess()
    def test_forced_or_nonzero_warmup_shutdown_refused(self):
        self.f.reports['robot']['children'][0]['forced_kill']=True
        with self.assertRaises(ValueError):self.f.assess()
    def test_foreign_final_compatibility_identity_refused(self):
        (self.out/'robot-bridge-identity.json').write_bytes((self.out/self.f.entries['robot','warmup']['identity_path']).read_bytes())
        with self.assertRaises(ValueError):self.f.assess()
    def test_negative_test_not_treated_as_successful_shutdown(self):
        self.f.mutate_entry('robot','negative_type_hash',lambda e:e.update(returncode=0))
        with self.assertRaises(ValueError):self.f.assess()
    def test_unlisted_and_legacy_traces_refused(self):
        (self.out/'robot-shutdown-stages.jsonl').write_text('old')
        with self.assertRaises(ValueError):self.f.assess()
        (self.out/'robot-shutdown-stages.jsonl').unlink();(self.out/'launch-readiness/unknown.shutdown.jsonl').write_text('unknown')
        with self.assertRaises(ValueError):self.f.assess()
    def test_socket_close_failure_still_refused(self):
        p=self.out/self.f.entries['operator','measurement']['trace_path'];rows=[json.loads(x) for x in p.read_text().splitlines()];next(r for r in rows if r['point']=='socket_close_result')['detail']=-1;p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        with self.assertRaisesRegex(ValueError,'srt_close returned error'):self.f.assess()
    def test_readiness_token_and_helper_binding_still_refused(self):
        p=self.out/self.f.entries['robot','measurement']['readiness_path'];v=read(p);v['launch']['token']='f'*32;write(p,v)
        with self.assertRaises(ValueError):self.f.assess()
    def test_child_report_order_does_not_select_warmup_as_final(self):
        self.f.reports['robot']['children'].reverse()
        result=self.f.assess();self.assertEqual(result['robot']['measurement']['child']['name'],'robot-bridge-2')
    def test_warmup_missing_required_stage_refused(self):
        p=self.out/self.f.entries['robot','warmup']['trace_path'];rows=[json.loads(x) for x in p.read_text().splitlines()];rows=[r for r in rows if r['point']!='worker_join_end']
        for i,row in enumerate(rows):row['sequence']=i+1
        p.write_text(''.join(json.dumps(r)+'\n' for r in rows))
        with self.assertRaisesRegex(ValueError,'missing shutdown stage'):self.f.assess()
    def test_missing_trace_is_not_inferred_from_another_launch(self):
        (self.out/self.f.entries['robot','measurement']['trace_path']).unlink()
        with self.assertRaises(FileNotFoundError):self.f.assess()
    def test_child_trace_path_mismatch_refused(self):
        self.f.reports['robot']['children'][-1]['trace_path']=self.f.entries['robot','warmup']['trace_path']
        with self.assertRaises(ValueError):self.f.assess()
    def test_full_assessor_selects_final_operator_and_retains_warmup(self):
        for role in self.f.reports:write(self.out/(role+'-child-shutdown.json'),self.f.reports[role])
        for filename in ('operator-observer-ready.json','operator-shutdown-stacks.jsonl'):
            target=self.out/('native-observer/blocked-target-shutdown-stacks.jsonl' if filename.endswith('stacks.jsonl') else filename);target.parent.mkdir(exist_ok=True);target.write_bytes((self.f.source/filename).read_bytes())
        spec=importlib.util.spec_from_file_location('trace_lifecycle_assessor',HERE/'assess.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with patch.object(module,'assess_combined',return_value=dict(status='passed')),patch.object(module,'cleanup'),patch.object(module,'profile_gate'):
            proof=module.assess(self.out,dict(status='passed'),dict())
        self.assertEqual(proof['status'],'passed',proof.get('error'));self.assertIn('warmup',proof['launches']['robot'])
        self.assertGreater(proof['operator_observer']['nonempty_kernel_stacks'],0)

class Child:
    def __init__(self,pid):self.pid=pid;self.returncode=None;self.fail=False
    def poll(self):return self.returncode
    def send_signal(self,sig):pass
    def kill(self):self.returncode=-9

class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.out=Path(self.temp.name);self.calls=[]
        calls=self.calls
        class FakeSubprocess:
            STDOUT=-2
            @staticmethod
            def Popen(argv,**kwargs):
                calls.append(argv)
                for value in argv:
                    if value.startswith('shutdown_trace_path:='):
                        p=Path(value.split(':=',1)[1]);p.parent.mkdir(exist_ok=True)
                        with p.open('x') as file:file.write('original launch trace\n')
                return Child(100+len(calls))
        class Base:
            def stop(obj,p):
                if p.poll() is None:
                    p.send_signal(2)
                    if p.fail:p.kill();raise RuntimeError('original5s timeout')
                    p.returncode=0
        def register(child,launch):return dict(launch=launch,identity=dict(pid=child.pid,start_ticks=child.pid*100,ppid=75,state='R',name='python3'))
        tree=ast.parse((HERE/'scenario.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Diagnostic')
        env=dict(Benchmark=Base,sys=sys,HERE=HERE,subprocess=FakeSubprocess,new_launch=new_launch,register=register,plan_launch=plan_launch,save_launches=save_launches,time=__import__('time'),read=read,write=write)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'scenario-extracted','exec'),env)
        self.env=env;self.cls=env['Diagnostic'];self.obj=self.cls();self.obj.args=types.SimpleNamespace(role='robot',ros_install='install/m3-socket-disposition-ros');self.obj.run=self.out;self.obj.processes=[]
        self.addCleanup(lambda:[log.close() for _,_,log in self.obj.processes])
    def test_negative_warmup_reset_paths_are_unique_and_old_trace_preserved(self):
        negative=self.obj.start('bridge_node','wrong-hash',dict(expected_imu_hash='bad'));negative.returncode=1
        original=dict(shutdown_diagnostics='true',shutdown_trace_path='role-level.jsonl')
        warm=self.obj.start('bridge_node','robot-bridge-1',original);first=self.obj.launch_entries[warm]['trace_path'];self.obj.stop(warm)
        final=self.obj.start('bridge_node','robot-bridge-2',original);second=self.obj.launch_entries[final]['trace_path']
        self.assertNotEqual(first,second);self.assertEqual((self.out/first).read_text(),'original launch trace\n');self.assertEqual(original['shutdown_trace_path'],'role-level.jsonl')
        self.assertNotIn('shutdown_trace_path:=',str(self.calls[0]));self.assertTrue(self.obj.launch_entries[negative]['trace_path'] is None)
        self.obj.stop(final);catalog=read(self.out/'robot-bridge-launches.json');self.assertEqual([e['returncode'] for e in catalog['launches']],[1,0,0])
        children=read(self.out/'robot-child-shutdown.json')['children'];self.assertEqual(len(children),2);self.assertEqual(children[0]['trace_path'],first);self.assertEqual(children[1]['trace_path'],second)
    def test_early_child_exit_recorded_and_not_clean(self):
        child=self.obj.start('bridge_node','robot-bridge-1',{});child.returncode=1;self.obj.stop(child);self.obj.stop(child)
        report=read(self.out/'robot-child-shutdown.json');self.assertFalse(report['passed']);self.assertEqual(len(report['children']),1);self.assertEqual(report['children'][0]['error'],'bridge exited before requested stop')
    def test_forced_stop_retains_failure_and_launch_identity(self):
        child=self.obj.start('bridge_node','robot-bridge-1',{});child.fail=True
        with self.assertRaises(RuntimeError):self.obj.stop(child)
        row=read(self.out/'robot-child-shutdown.json')['children'][0];self.assertTrue(row['forced_kill']);self.assertFalse(row['passed']);self.assertEqual(row['start_ticks'],child.pid*100)
    def test_unplanned_third_positive_launch_refused(self):
        self.obj.start('bridge_node','robot-bridge-1',{});self.obj.start('bridge_node','robot-bridge-2',{})
        with self.assertRaises(ValueError):self.obj.start('bridge_node','robot-bridge-3',{})
    def test_parent_attestation_exports_unique_and_current_identity(self):
        def start(obj):obj.bridge=obj.start('bridge_node','robot-bridge-1',{})
        self.env['Benchmark'].start_bridge=start
        def check(child,registration):
            identity=registration['identity']
            return dict(**identity,launch_token=registration['launch']['token'],launch_name='robot-bridge-1',permissions=dict(),identity_helper=gate.BINDING,monotonic_ns=1,execed_bridge_attested=False)
        self.env['check']=check;self.env['Path']=lambda value:types.SimpleNamespace(read_text=lambda:'test clock')
        self.obj.start_bridge();entry=self.obj.launch_entries[self.obj.bridge]
        unique=read(self.out/entry['identity_path']);compat=read(self.out/'robot-bridge-identity.json')
        self.assertEqual(unique,compat);self.assertTrue(entry['attested']);self.assertEqual(unique['launch_token'],entry['context']['token'])
    def test_native_reduce_benchmark_and_calibrated_gates_unchanged(self):
        prior=ROOT/'evidence/m3-current-n0-identity-binding-fix-2026-11-10'
        for file,name in (('bridge_exec.py','reduce'),('scenario.py','Benchmark')):
            def node(folder):return next(n for n in ast.parse((folder/file).read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
            self.assertEqual(ast.dump(node(HERE)),ast.dump(node(prior)))
        for name in ('launch_readiness.py','bridge_exec.py'):self.assertEqual((HERE/name).read_bytes(),(prior/name).read_bytes())
        for name in ('stage_gate.py','socket_gate.py','lifecycle.py'):self.assertEqual((HERE/name).read_bytes(),(ROOT/'evidence/m3-current-n0-preparation-2026-11-10'/name).read_bytes())

if __name__=='__main__':unittest.main()
