"""Offline only: synthetic procfs, mocked processes/exec and extracted scenario class."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parents[1]
PRIOR=ROOT/'evidence/m3-current-n0-preparation-2026-11-10'
sys.path[:0]=[str(HERE),str(ROOT/'tools'),str(PRIOR)]
import launch_readiness as ready

class Child:
    def __init__(self,pid=127):self.pid=pid;self.returncode=None
    def poll(self):return self.returncode

class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.run=Path(self.temp.name);self.proc=self.run/'proc';self.child=Child();self.set_proc()
        self.launch=ready.new_launch(self.run,'robot','robot-bridge-1','/workspace/install/bridge-socket-disposition/bridge_node')
        self.registration=ready.register(self.child,self.launch,self.proc)
    def set_proc(self,pid=127,ticks=123,cap='0',state='S'):
        p=self.proc/str(pid);p.mkdir(parents=True,exist_ok=True)
        fields=[state,'75']+['0']*17+[str(ticks)]
        (p/'stat').write_text(str(pid)+' (python3) '+' '.join(fields))
        self.permissions=dict(Name='python3',Pid=str(pid),PPid='75',CapEff=cap,CapPrm=cap,CapBnd=cap,CapInh='0',CapAmb='0',NoNewPrivs='1',Seccomp='2')
        (p/'status').write_text('\n'.join(k+': '+v for k,v in self.permissions.items()))
    def publish(self):ready.publish(self.launch,self.child.pid,self.proc)
    def error_record(self,side='parent'):
        return json.loads(Path(self.launch['record']).with_suffix('.'+side+'-failure.json').read_text())
    def test_atomic_launch_record_pass_and_exact_single_snapshot(self):
        self.publish()
        with patch.object(ready,'status',wraps=ready.status) as status:
            result=ready.check(self.child,self.registration,self.proc)
        self.assertEqual(status.call_count,1);self.assertEqual(result['permissions'],self.permissions)
        self.assertEqual(result['launch_token'],self.launch['token']);self.assertFalse(result['execed_bridge_attested'])
        self.assertEqual(result['readiness_phase'],ready.PHASE)
    def test_stale_negative_marker_cannot_release_positive_child(self):
        negative=ready.new_launch(self.run,'robot','wrong-hash',self.launch['binary'])
        self.set_proc(126);ready.publish(negative,126,self.proc)
        # The new child is still privileged. Old role-level marker and valid
        # negative-launch marker must not cause a capability check of this child.
        (self.run/'robot-bridge-preexec.json').write_text(json.dumps(dict(pid=126)))
        self.set_proc(cap='a80425fb')
        with patch.object(ready,'status',side_effect=AssertionError('must wait for this launch')):
            self.assertIsNone(ready.check(self.child,self.registration,self.proc))
        self.set_proc();self.publish();self.assertIsNotNone(ready.check(self.child,self.registration,self.proc))
        self.assertTrue(Path(negative['record']).exists())
    def test_foreign_token_or_name_refused_with_current_snapshot(self):
        for key in ('token','name'):
            with self.subTest(key=key):
                self.publish();p=Path(self.launch['record']);record=json.loads(p.read_text());record['launch'][key]='foreign';p.write_text(json.dumps(record))
                with self.assertRaises(ValueError):ready.check(self.child,self.registration,self.proc)
                self.assertEqual(self.error_record()['snapshot']['permissions'],self.permissions)
                p.unlink()
    def test_foreign_pid_record_refused(self):
        self.set_proc(128);ready.publish(self.launch,128,self.proc)
        with self.assertRaises(ValueError):ready.check(self.child,self.registration,self.proc)
        self.assertIn('identity',self.error_record()['error'])
    def test_pid_reuse_start_ticks_refused(self):
        self.publish();self.set_proc(ticks=124)
        with self.assertRaises(ValueError):ready.check(self.child,self.registration,self.proc)
        self.assertEqual(self.error_record()['expected_identity']['start_ticks'],123)
        self.assertEqual(self.error_record()['snapshot']['identity_before']['start_ticks'],124)
    def test_identity_change_during_status_read_refused(self):
        self.publish();original=ready.status
        def read(pid,proc):
            value=original(pid,proc);self.set_proc(ticks=125);return value
        with patch.object(ready,'status',side_effect=read),self.assertRaises(ValueError):ready.check(self.child,self.registration,self.proc)
        row=self.error_record()['snapshot'];self.assertEqual(row['identity_before']['start_ticks'],123);self.assertEqual(row['identity_after']['start_ticks'],125)
    def test_nonzero_failed_capability_snapshot_retained_exactly(self):
        self.publish();self.set_proc(cap='200000')
        with self.assertRaises(ValueError):ready.check(self.child,self.registration,self.proc)
        self.assertEqual(self.error_record()['snapshot']['permissions'],self.permissions)
    def test_nnp_failure_retained_without_relaxing_policy(self):
        self.publish();p=self.proc/'127/status';p.write_text(p.read_text().replace('NoNewPrivs: 1','NoNewPrivs: 0'))
        with self.assertRaises(ValueError):ready.check(self.child,self.registration,self.proc)
        self.assertEqual(self.error_record()['snapshot']['permissions']['NoNewPrivs'],'0')
    def test_partial_json_and_wrong_phase_fail_closed(self):
        p=Path(self.launch['record']);p.parent.mkdir(exist_ok=True)
        for text in ('{"schema_version":',json.dumps(dict(schema_version=1,phase='execed',launch=self.launch))):
            p.write_text(text)
            with self.assertRaises(ValueError):ready.check(self.child,self.registration,self.proc)
        self.assertIn('permissions',self.error_record()['snapshot'])
    def test_dead_child_or_missing_proc_refused_and_evidence_retained(self):
        self.publish();self.child.returncode=1
        with self.assertRaises(ValueError):ready.check(self.child,self.registration,self.proc)
        self.child.returncode=None;(self.proc/'127/status').unlink()
        with self.assertRaises(ValueError):ready.check(self.child,self.registration,self.proc)
        # First failure stays immutable, not overwritten by later observations.
        self.assertIn('exited',self.error_record()['error'])
    def test_missing_proc_snapshot_carries_read_error(self):
        (self.proc/'127/status').unlink()
        with self.assertRaises(ValueError):ready.unavailable(self.child,self.registration,'deadline expired',self.proc)
        row=self.error_record()['snapshot'];self.assertEqual(row['permissions_error']['type'],'FileNotFoundError')
    def test_timeout_and_early_exit_capture_status(self):
        with self.assertRaises(ValueError):ready.unavailable(self.child,self.registration,'child exited',self.proc)
        self.assertEqual(self.error_record()['snapshot']['permissions'],self.permissions)
    def test_wrapper_publish_failure_and_no_duplicate_ready_overwrite(self):
        self.set_proc(cap='1')
        with self.assertRaises(ValueError):self.publish()
        self.assertEqual(self.error_record('wrapper')['snapshot']['permissions'],self.permissions)
        self.set_proc();self.publish();before=Path(self.launch['record']).read_bytes()
        with self.assertRaises(ValueError):self.publish()
        self.assertEqual(Path(self.launch['record']).read_bytes(),before)
    def test_ready_atomic_write_never_exposes_partial_final_file(self):
        path=Path(self.launch['record']);original=ready.os.replace
        def replace(tmp,target):
            self.assertFalse(Path(target).exists());json.loads(Path(tmp).read_text());return original(tmp,target)
        with patch.object(ready.os,'replace',side_effect=replace):self.publish()
        self.assertFalse(path.with_name(path.name+'.tmp').exists())
    def test_each_launch_has_distinct_token_and_path(self):
        other=ready.new_launch(self.run,'robot','robot-bridge-1',self.launch['binary'])
        self.assertNotEqual(other['token'],self.launch['token']);self.assertNotEqual(other['record'],self.launch['record'])
        for name in ('../bridge','x/y',''):
            with self.assertRaises(ValueError):ready.new_launch(self.run,'robot',name,'binary')
    def test_registration_error_is_recorded(self):
        self.child.returncode=1
        with self.assertRaises(ValueError):ready.register(self.child,self.launch,self.proc)
        self.assertEqual(self.error_record()['phase'],'registration')
    def test_original_reduction_and_benchmark_workload_unchanged(self):
        for file,node_name in (('bridge_exec.py','reduce'),('scenario.py','Benchmark')):
            def node(folder):return next(n for n in ast.parse((folder/file).read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==node_name)
            self.assertEqual(ast.dump(node(HERE)),ast.dump(node(PRIOR)))
    def test_production_scenario_negative_and_real_use_distinct_launches(self):
        tree=ast.parse((HERE/'scenario.py').read_text());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Diagnostic')
        seen=[]
        class FakeSubprocess:
            STDOUT=-2
            @staticmethod
            def Popen(argv,**kwargs):seen.append(argv);return Child(126+len(seen))
        self.set_proc(128)
        env=dict(Benchmark=object,sys=sys,HERE=HERE,subprocess=FakeSubprocess,new_launch=ready.new_launch,register=lambda child,launch:ready.register(child,launch,self.proc))
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'scenario-extracted','exec'),env)
        obj=env['Diagnostic']();obj.args=type('Args',(),dict(role='robot',ros_install='install/m3-socket-disposition-ros'))();obj.run=self.run;obj.processes=[]
        try:
            negative=obj.start('bridge_node','wrong-hash',dict(expected_imu_hash='bad'))
            positive=obj.start('bridge_node','robot-bridge-1',dict(role='caller'))
            self.assertNotEqual(seen[0][2],seen[1][2]);self.assertNotEqual(seen[0][3],seen[1][3])
            self.assertEqual(seen[0][5],'wrong-hash');self.assertEqual(seen[1][5],'robot-bridge-1')
            self.assertEqual(obj.bridge_launches[negative]['identity']['pid'],127);self.assertEqual(obj.bridge_launches[positive]['identity']['pid'],128)
        finally:
            for _,_,log in obj.processes:log.close()
    def test_scenario_waits_for_current_launch_and_uses_returned_snapshot(self):
        tree=ast.parse((HERE/'scenario.py').read_text());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Diagnostic')
        child=self.child;registration=self.registration;calls=[]
        class Base:
            def start_bridge(obj):obj.bridge=child;obj.bridge_launches={child:registration}
        result=dict(pid=127,start_ticks=123,permissions=self.permissions,readiness_phase=ready.PHASE,execed_bridge_attested=False)
        seen=[]
        def check(p,reg):
            self.assertIs(p,child);self.assertIs(reg,registration);calls.append(p.pid)
            return None if len(calls)==1 else result
        import time
        fake_time=type('Clock',(),dict(monotonic=staticmethod(lambda:0),sleep=staticmethod(lambda seconds:seen.append(seconds))))
        class FakePath:
            def __init__(self,path):self.path=path
            def read_text(self):return 'retained clock proof'
        written=[]
        env=dict(Benchmark=Base,time=fake_time,check=check,unavailable=lambda *a:(_ for _ in ()).throw(AssertionError('unexpected refusal')),Path=FakePath,write=lambda p,v:written.append(v))
        exec(compile(ast.Module(body=[cls],type_ignores=[]),'scenario-extracted','exec'),env)
        obj=env['Diagnostic']();obj.run=self.run;obj.args=type('Args',(),dict(role='robot'))();obj.start_bridge()
        self.assertEqual(calls,[127,127]);self.assertEqual(seen,[.01]);self.assertEqual(written[0]['permissions'],self.permissions)
        self.assertFalse(written[0]['execed_bridge_attested'])
    def test_wrapper_success_publishes_then_execs_without_reducing_twice(self):
        spec=importlib.util.spec_from_file_location('fixed_success_wrapper',HERE/'bridge_exec.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        argv=['bridge_exec.py',self.launch['record'],self.launch['token'],'robot',self.launch['name'],self.launch['binary']]
        observed=[]
        with patch.object(module.sys,'argv',argv),patch.object(module.sys,'platform','linux'),patch.object(module.platform,'machine',return_value='x86_64'),patch.object(module,'reduce',side_effect=lambda *a:observed.append('reduce')),patch.object(module,'publish',side_effect=lambda *a:observed.append('publish')),patch.object(module.os,'execv',side_effect=lambda *a:observed.append('exec')),patch.object(Path,'read_text',return_value='40'):
            module.main()
        self.assertEqual(observed,['reduce','publish','exec'])
    def test_wrapper_reduction_failure_retains_actual_snapshot_without_exec(self):
        spec=importlib.util.spec_from_file_location('fixed_wrapper',HERE/'bridge_exec.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        argv=['bridge_exec.py',self.launch['record'],self.launch['token'],'robot',self.launch['name'],self.launch['binary']]
        with patch.object(module.sys,'argv',argv),patch.object(module.sys,'platform','linux'),patch.object(module.platform,'machine',return_value='x86_64'),patch.object(module,'reduce',side_effect=OSError('synthetic reduction failure')),patch.object(module,'snapshot',return_value=dict(permissions=self.permissions)),patch.object(module.os,'execv',side_effect=AssertionError('no exec')),patch.object(Path,'read_text',return_value='40'):
            self.assertEqual(module.main(),125)
        self.assertEqual(self.error_record('wrapper')['snapshot']['permissions'],self.permissions)

if __name__=='__main__':unittest.main()
