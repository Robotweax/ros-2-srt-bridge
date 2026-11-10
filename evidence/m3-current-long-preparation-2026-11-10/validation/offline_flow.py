"""Whole lifecycle model: production Python methods, fake ROS/procfs/children/observer.

No actual ROS node, bridge, capability syscall, capture, Docker object or N0 run.
"""
import ast
import importlib.util
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import types
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'tools'),str(ROOT/'ros2/robotweax_srt_bridge_demo/scripts')]
import launch_readiness as readiness
import launch_assessment

def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value)+'\n');temporary.replace(path)
def read(path):
    try:return json.loads(Path(path).read_text())
    except FileNotFoundError:return {}

def module(name,file):
    spec=importlib.util.spec_from_file_location(name,file);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

class Clock:
    def __init__(self):self.ns=1_000_000_000;self.lock=threading.Lock()
    def monotonic_ns(self):self.ns+=1000;return self.ns
    def monotonic(self):
        with self.lock:return self.ns/1e9
    def sleep(self,seconds):
        with self.lock:self.ns+=int(seconds*1e9)

class Flow:
    def __init__(self,out,fault=None):
        self.out=Path(out);self.out.mkdir(exist_ok=True);self.proc=self.out/'proc-model';self.clock=Clock();self.fault=fault;self.events=[];self.children=[];self.nextpid=100;self.command_index=0;self.failure=None;self.observer_armed=False;self.finish_request=threading.Event();self.robot_finished=threading.Event();self.finish_thread=None;self.finish_error=None;self.reply_ready=threading.Event();self.close_calls=0;self.lab_removed=False
        self.wrapper=module('offline_flow_wrapper',HERE/'bridge_exec.py')
        self._load_methods();self.robot=self._driver('robot');self.operator=self._driver('operator')
        # Execute the actual unchanged host arm-before-release block as written.
        tree=ast.parse((HERE/'workload.py').read_text());node=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and isinstance(n.test,ast.BoolOp) and 'n0-shutdown-ready' in ast.unparse(n.test))
        self.arm_code=compile(ast.Module(body=[node],type_ignores=[]),'workload-arm-release','exec')
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.If) and ast.unparse(n.test)=='observer is not None')
        self.close_finally_code=compile(ast.Module(body=[node],type_ignores=[]),'workload-observer-finally','exec')
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.Expr) and ast.unparse(n)=='lab.cleanup()')
        self.lab_cleanup_code=compile(ast.Module(body=[node],type_ignores=[]),'workload-lab-cleanup','exec')
        node=next(n for n in ast.walk(tree) if isinstance(n,ast.Expr) and ast.unparse(n)=='credential.unlink(missing_ok=True)')
        self.credential_cleanup_code=compile(ast.Module(body=[node],type_ignores=[]),'workload-credential-cleanup','exec')
        (self.out/'passphrase').write_text('offline model only')
    def _path(self,value):
        if str(value) in ('/proc/sys/kernel/random/boot_id','/proc/self/timens_offsets','/proc/sys/kernel/cap_last_cap'):
            text={'/proc/sys/kernel/random/boot_id':'offline-boot','/proc/self/timens_offsets':'monotonic 0 0\nboottime 0 0\n','/proc/sys/kernel/cap_last_cap':'40'}[str(value)]
            return types.SimpleNamespace(read_text=lambda:text)
        return Path(value)
    def _load_methods(self):
        convert=types.ModuleType('rosidl_runtime_py.convert');convert.message_to_ordereddict=lambda x:vars(x)
        self.convert=convert
        ns=dict(Node=object,time=self.clock,Path=self._path,read=read,write=self.write_tracking,signal=signal,subprocess=subprocess,os=types.SimpleNamespace(kill=lambda *a:None))
        tree=ast.parse((ROOT/'ros2/robotweax_srt_bridge_demo/scripts/m2_scenario.py').read_text());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Driver')
        exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-driver','exec'),ns);self.base_ns=ns
        tree=ast.parse((HERE/'scenario.py').read_text());nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name in ('Benchmark','Diagnostic')]
        import launch_records
        env=dict(Driver=ns['Driver'],time=self.clock,Path=self._path,sys=sys,HERE=HERE,read=read,write=self.write_tracking,new_launch=readiness.new_launch,plan_launch=launch_records.plan_launch,save_launches=launch_records.save_launches,SetPublishing=types.SimpleNamespace(Request=types.SimpleNamespace),GetBridgeMetrics=types.SimpleNamespace(Request=types.SimpleNamespace))
        model=self
        env['subprocess']=types.SimpleNamespace(Popen=lambda argv,**kw:model.spawn(argv,kw),STDOUT=-2,TimeoutExpired=subprocess.TimeoutExpired)
        env['register']=lambda child,launch:readiness.register(child,launch,self.proc)
        env['check']=lambda child,registration:readiness.check(child,registration,self.proc)
        env['failure']=readiness.failure
        env['unavailable']=lambda child,registration,reason:readiness.unavailable(child,registration,reason,self.proc)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-scenario','exec'),env);self.scenario_ns=env;self.Diagnostic=env['Diagnostic']
    def _driver(self,role):
        obj=self.Diagnostic.__new__(self.Diagnostic)
        obj.args=types.SimpleNamespace(role=role,run=str(self.out),ros_install='install/m3-socket-disposition-ros',peer='offline-peer',clock_width_ms=200,provider_diagnostics=True,sensor_provider_diagnostics=True,start_diagnostics=True,sender_diagnostics=True,command_diagnostics=True,shutdown_diagnostics=True)
        obj.run=self.out;obj.processes=[];obj.control_sequence=0;obj.retired=set();obj.bridge=None;obj.sim=None;obj.state=None;obj.device=None;obj.source=0;obj.shutdowns=[];obj.last_diagnostic=(None,0)
        obj.resources=types.SimpleNamespace(close=lambda:None);obj.endpoint_sampler=types.SimpleNamespace(close=lambda:None);obj.publishing_client=object();obj.metric_client=object()
        obj.worker_pid=lambda:None  # Worker supervision is outside this offline process model.
        obj.spin=lambda seconds=.05:self.spin(obj,seconds)
        obj.rpc=lambda client,request:types.SimpleNamespace(enabled=request.enabled,snapshot=types.SimpleNamespace(imu_published=0,joints_published=0),monotonic_ns=self.clock.monotonic_ns())
        return obj
    def stat(self,child,zero=False):
        p=self.proc/str(child.pid);p.mkdir(parents=True,exist_ok=True)
        (p/'stat').write_text(str(child.pid)+' (bridge_node) '+' '.join(['S','75']+['0']*17+[str(child.pid*100)]))
        cap='0' if zero else 'a80425fb';nnp='1' if zero else '0'
        (p/'status').write_text(f'Name: bridge_node\nPid: {child.pid}\nPPid: 75\nCapEff: {cap}\nCapPrm: {cap}\nCapBnd: {cap}\nCapInh: 0\nCapAmb: 0\nNoNewPrivs: {nnp}\nSeccomp: 2\n')
    def spawn(self,argv,kwargs):
        if self.fault=='spawn' and Path(kwargs['stdout'].name).stem=='robot-bridge-2':raise OSError('synthetic spawn refusal')
        self.nextpid+=1
        child=Child(self,self.nextpid,argv,kwargs);self.children.append(child);self.stat(child)
        self.events.append(('spawn',child.name,child.pid));return child
    def spin(self,obj,seconds):
        self.clock.sleep(seconds)
        if obj.args.role=='operator':
            observer=types.SimpleNamespace(arm=self.arm)
            exec(self.arm_code,dict(run=self.out,observer=observer,lab=object()))
            return
        obj.device=types.SimpleNamespace(rate_hz=200,generation=0,effects=0);obj.source=25
        if obj.bridge and obj.bridge.poll() is None and obj.bridge.booted:
            obj.state=types.SimpleNamespace(ready=True,clock_qualified=True,sensor_qos_verified=True)
            obj.last_diagnostic=(obj.state,self.clock.monotonic_ns())
        if not (self.out/'robot-ready.json').exists():return
        if self.finish_thread is None:
            def controls():
                try:
                    for action in ('start','pause','reset_link','resume','pause','finish'):
                        self.operator.robot_command(action)
                except BaseException as error:self.finish_error=error
                finally:self.finish_request.set()
            self.finish_thread=threading.Thread(target=controls);self.finish_thread.start()
        if self.finish_error:raise self.finish_error
        control=read(self.out/'control.json');reply=read(self.out/'robot-reply.json')
        if control.get('sequence',0)>reply.get('sequence',0):
            self.finish_request.clear();return
        if not self.finish_request.wait(2):raise RuntimeError('offline coordinator did not publish next RPC')
        self.finish_request.clear()
        if self.finish_error:raise self.finish_error
    def write_tracking(self,path,value):
        write(path,value)
        if Path(path).name=='control.json':
            if value['action']=='finish':self.events.append(('finish_rpc',))
            else:self.events.append(('command',value['action']))
        if Path(path).name=='robot-reply.json':self.reply_ready.set()
    def arm(self,lab):
        self.events.append(('observer_arm',))
        if self.fault=='observer_arm':raise RuntimeError('synthetic observer arm refusal')
        info=read(self.out/'operator-bridge-identity.json');assert info['launch_name']=='operator-bridge-0'
        self.observer_armed=True;stamp=self.clock.monotonic_ns();self.arm_stamp=stamp
        write(self.out/'operator-observer-ready.json',dict(ready_ns=stamp))
        begin=self.clock.monotonic_ns();end=self.clock.monotonic_ns()
        root={k:info[k] for k in ('pid','start_ticks','ppid','name')}
        self.observer_rows=[dict(kind='begin',mode='procfs',observer_independent=True,pid=9999,root=root,boot_id=dict(text=info['boot_id']+'\n')),dict(kind='sample',begin_ns=begin,end_ns=end,process_limit_hit=False,processes=[dict(identity=root,identity_check=dict(status='matching',observed=root,checked_ns=end),status='sampled',identity_still_matches=True,threads_truncated=False,threads=[dict(kernel_stack=dict(status='ok',truncated=False,text='offline modeled stack, not a kernel read'))])])]
    def close(self):
        self.close_calls+=1;self.events.append(('observer_close',))
        self.observer_armed=False
        if hasattr(self,'observer_rows'):
            path=self.out/'native-observer/blocked-target-shutdown-stacks.jsonl';path.parent.mkdir(exist_ok=True)
            path.write_text(''.join(json.dumps(r)+'\n' for r in self.observer_rows+[dict(kind='status',completed=True,budget_exhausted=False)]))
        if self.fault=='observer_close' and self.close_calls==1:raise RuntimeError('synthetic observer close failure')
    def lab_cleanup(self):
        self.lab_removed=True;self.events.append(('lab_cleanup',))
        write(self.out/'network.json',dict(offline_model=True,commands=[dict(label=x,exit_code=0) for x in ('operator-remove','robot-remove','network-remove')]))
    def operator_wait(self,predicate,label,timeout=20):
        # This substitutes only ROS executor scheduling. The actual inherited
        # file-RPC method writes every request and validates every response.
        if read(self.out/'control.json').get('action')=='finish':assert (self.out/'n0-shutdown-release').exists()
        self.finish_request.set()
        if not self.reply_ready.wait(2) or not predicate():raise RuntimeError('offline robot RPC was not acknowledged')
        self.reply_ready.clear()
    def run(self):
        old_wait=self.operator.wait
        with patch.object(readiness,'time',self.clock),patch.dict(sys.modules,{'rosidl_runtime_py.convert':self.convert}):
            try:
                self.operator.start_bridge();self.operator.state=types.SimpleNamespace(ready=True,clock_qualified=True);self.operator.last_diagnostic=(self.operator.state,self.clock.monotonic_ns());self.events.append(('operator_started',))
                self.operator.wait=self.operator_wait
                self.robot.robot();self.robot_finished.set()
                if self.finish_thread:self.finish_thread.join(2)
                if self.finish_error:raise self.finish_error
                self.operator.stop(self.operator.bridge);self.operator.bridge=None
                assert self.observer_armed
                self.events.append(('normal_shutdown_complete',));self.close()
            except BaseException as error:
                self.failure=error;self.events.append(('failed',str(error)))
            finally:
                self.robot_finished.set();self.reply_ready.set();self.finish_request.set()
                if self.finish_thread:self.finish_thread.join(2)
                self.operator.wait=old_wait
                for obj in (self.robot,self.operator):
                    try:obj.cleanup()
                    except BaseException as error:
                        self.failure=self.failure or error;self.events.append(('cleanup_failed',str(error)))
                report=dict(status='failed' if self.failure else 'passed')
                exec(self.close_finally_code,dict(observer=types.SimpleNamespace(close=self.close),report=report))
                if report['status']=='failed' and not self.failure:self.failure=RuntimeError(report.get('observer_cleanup_error','cleanup failed'))
                exec(self.lab_cleanup_code,dict(lab=types.SimpleNamespace(cleanup=self.lab_cleanup)))
                exec(self.credential_cleanup_code,dict(credential=self.out/'passphrase'))
                self.events.append(('cleanup_complete',))
        return self
    def assess(self):
        reports={role:read(self.out/(role+'-child-shutdown.json')) for role in ('operator','robot')}
        # The test runs in a host checkout. Rebase only helper provenance's
        # checkout root to the target /workspace mount; identities/tokens/status
        # and lifecycle evidence come from the actual executed Python methods.
        for path in (self.out/'launch-readiness').glob('*.json'):
            value=read(path)
            if 'snapshot' in value and 'identity_helper' in value['snapshot']:value['snapshot']['identity_helper']['path']=launch_assessment.BINDING['path']
            if 'identity_helper' in value:value['identity_helper']['path']=launch_assessment.BINDING['path']
            write(path,value)
        for role in ('operator','robot'):
            path=self.out/(role+'-bridge-identity.json');value=read(path)
            if value:value['identity_helper']['path']=launch_assessment.BINDING['path'];write(path,value)
        return launch_assessment.assess_launches(self.out,reports)

class Child:
    def __init__(self,flow,pid,argv,kwargs):
        self.flow=flow;self.pid=pid;self.argv=argv;self.log=kwargs['stdout'];self.name=Path(self.log.name).stem;self.returncode=None;self.booted=False;self.polls=0;self.signaled=False;self.killed=False
        self.bridge=len(argv)>1 and argv[1].endswith('bridge_exec.py');self.negative=self.name=='wrong-hash';self.trace=None
    def boot(self):
        if self.booted:return
        self.booted=True
        if not self.bridge:return
        f=self.flow;m=f.wrapper
        def execute(binary,args):
            f.events.append(('exec',self.name,self.pid))
            if self.negative:
                self.log.write('bridge startup failed: ROS type hash mismatch\n');self.log.flush();self.returncode=0 if f.fault=='negative_success' else 1;return
            trace=next(v.split(':=',1)[1] for v in args if v.startswith('shutdown_trace_path:='));self.trace=Path(trace)
            if f.fault=='trace_collision' and self.name=='robot-bridge-2':self.trace.parent.mkdir(exist_ok=True);self.trace.write_text('occupied\n')
            try:
                self.trace.parent.mkdir(exist_ok=True)
                with self.trace.open('x') as log:log.write(json.dumps(self.rows()[0])+'\n')
            except FileExistsError:
                self.log.write('bridge startup failed: cannot create shutdown trace\n');self.log.flush();self.returncode=1
        overrides=dict(sys=types.SimpleNamespace(argv=self.argv[1:],platform='linux'),platform=types.SimpleNamespace(machine=lambda:'x86_64'),os=types.SimpleNamespace(getpid=lambda:self.pid,execv=execute),Path=f._path,reduce=lambda *a:f.stat(self,zero=not(f.fault=='capability' and self.name=='robot-bridge-1')),publish=lambda launch,pid:readiness.publish(launch,self.pid,f.proc),snapshot=lambda pid:readiness.snapshot(self.pid,f.proc),ctypes=types.SimpleNamespace(CDLL=lambda *a,**k:None))
        with patch.multiple(m,**overrides):code=m.main()
        if code is not None:self.returncode=code
    def rows(self):
        role='operator' if self.name.startswith('operator') else 'robot'
        source=ROOT/'evidence/m3-strict-n3-execution-2026-11-10/cases/N3-baseline-1701'/(role+'-shutdown-stages.jsonl')
        rows=[json.loads(x) for x in source.read_text().splitlines()]
        for row in rows:row['pid']=self.pid;row['monotonic_ns']=self.flow.clock.monotonic_ns()
        return rows
    def poll(self):
        self.polls+=1
        if self.polls>1:self.boot()
        return self.returncode
    def send_signal(self,sig):
        self.signaled=True;self.flow.events.append(('sigint',self.name,self.pid))
        if self.bridge and self.trace and self.trace.exists():
            with self.trace.open('a') as log:
                for row in self.rows()[1:]:log.write(json.dumps(row)+'\n')
    def wait(self,timeout=None):
        self.boot()
        if self.signaled:
            if ((self.flow.fault=='shutdown_timeout' and self.name=='robot-bridge-2') or (self.flow.fault=='warmup_timeout' and self.name=='robot-bridge-1')) and not self.killed:
                self.flow.events.append(('wait_timeout',self.name,timeout));self.flow.clock.sleep(timeout);raise subprocess.TimeoutExpired(self.argv,timeout)
            self.flow.clock.sleep(.001);self.returncode=-9 if self.killed else 0
        if self.returncode is None:raise RuntimeError('offline model would block without signal')
        if self.negative:self.log.close()
        return self.returncode
    def kill(self):self.killed=True;self.returncode=-9;self.flow.events.append(('kill',self.name,self.pid))
