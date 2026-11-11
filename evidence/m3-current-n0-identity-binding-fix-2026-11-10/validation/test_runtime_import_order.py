"""Actual runtime search order and ROS helper cache in fresh offline interpreters."""
import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parents[1]
ROS=ROOT/'ros2/robotweax_srt_bridge_demo/scripts';PRIOR=ROOT/'evidence/m3-current-n0-preparation-2026-11-10'

def load(file):
    spec=importlib.util.spec_from_file_location('bound_readiness_under_test',file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class RuntimeImportOrderTests(unittest.TestCase):
    def fresh(self,entry,poison_cache=False):
        # ROOT=/workspace inside the target. Map only that root in the parent
        # scenario AST to this checkout; execute all other module imports as-is.
        code=r'''
import ast,importlib.util,json,sys,tempfile,types
from pathlib import Path
root=Path(sys.argv[1]);here=Path(sys.argv[2]);entry=sys.argv[3];poison=sys.argv[4]=='True'
ros=root/'ros2/robotweax_srt_bridge_demo/scripts';prior=root/'evidence/m3-current-n0-preparation-2026-11-10'
sys.path[:0]=[str(root/'tools'),str(ros),str(here),str(prior)]
import shutdown_observer as shadow
assert Path(shadow.__file__)==ros/'shutdown_observer.py'
if poison:
    shadow.identity=lambda *a:(_ for _ in ()).throw(AssertionError('cached colliding identity must never run'))
if entry=='scenario':
    # No ROS installation, nodes or child launches; stub only ROS-facing imports.
    for name in ('rclpy','robotweax_srt_bridge_msgs','robotweax_srt_bridge_msgs.msg','robotweax_srt_bridge_msgs.srv','m2_scenario','command_workload'):
        sys.modules[name]=types.ModuleType(name)
    sys.modules['robotweax_srt_bridge_msgs.msg'].CommandStatus=object
    for name in ('ExecuteCommand','GetCommandStatus','GetBridgeMetrics','SetPublishing'):setattr(sys.modules['robotweax_srt_bridge_msgs.srv'],name,object)
    base=sys.modules['m2_scenario'];base.Driver=object;base.read=lambda p:{};base.write=lambda *a:None
    sys.modules['command_workload'].record_status_observation=lambda *a:None
    tree=ast.parse((here/'scenario.py').read_text())
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ROOT' for t in node.targets):node.value=ast.Call(func=ast.Name(id='Path',ctx=ast.Load()),args=[ast.Constant(str(root))],keywords=[])
    ast.fix_missing_locations(tree);namespace=dict(__name__='offline_scenario_import',__file__=str(here/'scenario.py'))
    exec(compile(tree,str(here/'scenario.py'),'exec'),namespace)
else:
    spec=importlib.util.spec_from_file_location('offline_wrapper_import',here/'bridge_exec.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
ready=sys.modules['launch_readiness']
with tempfile.TemporaryDirectory() as temp:
    proc=Path(temp)/'proc';p=proc/'127';p.mkdir(parents=True)
    (p/'stat').write_text('127 (python3) '+' '.join(['R','75']+['0']*17+['123']))
    (p/'status').write_text('Name: python3\nPid: 127\nPPid: 75\nCapEff: 0\nCapPrm: 0\nCapBnd: 0\nCapInh: 0\nCapAmb: 0\nNoNewPrivs: 1\nSeccomp: 2\n')
    class Child:
        pid=127
        def poll(self):return None
    child=Child();launch=ready.new_launch(Path(temp),'robot','robot-bridge-1','/workspace/bridge_node')
    registration=ready.register(child,launch,proc);ready.publish(launch,127,proc);observed=ready.check(child,registration,proc)
    assert observed['ppid']==75 and observed['name']=='python3' and observed['start_ticks']==123
    # Failure retention must also use the bound schema under runtime imports.
    (p/'status').write_text((p/'status').read_text().replace('CapEff: 0','CapEff: 200000'))
    try:ready.check(child,registration,proc)
    except ValueError:pass
    else:raise AssertionError('nonzero capability was accepted')
    failed=json.loads(Path(launch['record']).with_suffix('.parent-failure.json').read_text())
    assert failed['snapshot']['permissions']['CapEff']=='200000'
    assert failed['snapshot']['identity_before']['ppid']==75
    assert failed['snapshot']['identity_helper']==ready.IDENTITY_HELPER_BINDING
    print(json.dumps(dict(entry=entry,poison_cache=poison,shadow_path=shadow.__file__,identity_helper=observed['identity_helper'],parent_pid=observed['ppid'],failure_snapshot_retained=True)))
'''
        done=subprocess.run([sys.executable,'-c',code,str(ROOT),str(HERE),entry,str(poison_cache)],text=True,capture_output=True,timeout=15)
        self.assertEqual(done.returncode,0,done.stderr);return json.loads(done.stdout)
    def test_parent_runtime_order_with_actual_ros_helper_cached(self):
        result=self.fresh('scenario');self.assertEqual(result['identity_helper']['path'],str(PRIOR/'shutdown_observer.py'))
    def test_wrapper_runtime_order_with_actual_ros_helper_cached(self):self.fresh('wrapper')
    def test_parent_ignores_poisoned_collision_cache(self):self.fresh('scenario',True)
    def test_wrapper_ignores_poisoned_collision_cache(self):self.fresh('wrapper',True)
    def test_bound_helper_hash_change_fails_without_fallback(self):
        with patch.dict(sys.modules,shutdown_observer=type('Shadow',(),{'identity':lambda *a:None})()),patch.object(Path,'read_bytes',return_value=b'wrong helper'),self.assertRaisesRegex(RuntimeError,'source hash differs'):load(HERE/'launch_readiness.py')
    def test_bound_helper_missing_fails_without_fallback(self):
        with patch.object(Path,'read_bytes',side_effect=FileNotFoundError('missing bound helper')),self.assertRaises(FileNotFoundError):load(HERE/'launch_readiness.py')
    def test_capability_reduction_and_workload_bodies_unchanged(self):
        old=ROOT/'evidence/m3-current-n0-readiness-fix-2026-11-10'
        for file,name in (('bridge_exec.py','reduce'),('scenario.py','Benchmark'),('scenario.py','Diagnostic')):
            def node(folder):return next(n for n in ast.parse((folder/file).read_text()).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name==name)
            self.assertEqual(ast.dump(node(old)),ast.dump(node(HERE)))
    def test_host_adapter_selects_bound_candidate(self):
        new=(HERE/'workload.py').read_text();old=(ROOT/'evidence/m3-current-n0-readiness-fix-2026-11-10/workload.py').read_text()
        self.assertEqual(new,old.replace('evidence/m3-current-n0-readiness-fix-2026-11-10/scenario.py','evidence/m3-current-n0-identity-binding-fix-2026-11-10/scenario.py'))

if __name__=='__main__':unittest.main()
