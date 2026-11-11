"""Temporary procfs and Docker-command models, no real subprocess/container calls."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
import types
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
import shutdown_observer as collector
from plan import CANDIDATE_SHA
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value)+'\n')
def perms(cap=0):return dict(CapEff=hex(cap)[2:],CapPrm=hex(cap)[2:],CapBnd=hex(cap)[2:],CapInh='0',CapAmb='0',NoNewPrivs='1',Seccomp='2')
def stat(tid,start):return str(tid)+' (fixture task) '+' '.join(['S','1']+['0']*17+[str(start)]+['0']*10)
def fixture(folder):
    data=folder/'data';data.mkdir();proc=folder/'proc';task=proc/'101/task';task.mkdir(parents=True);(proc/'101/stat').write_text(stat(101,700))
    for tid,start in ((101,700),(102,701)):
        d=task/str(tid);d.mkdir()
        for name,text in dict(stat=stat(tid,start),wchan='futex_wait',syscall='98 0',stack='[<0>] futex_wait\n',children='').items():(d/name).write_text(text)
    context=dict(calibration_id='owned',target_pid=101,target_start_ticks=700,worker_tid=102,worker_start_ticks=701)
    known={(101,700):dict(pid=101,start_ticks=700)};history={};samples=[]
    def sample():
        begin=time.monotonic_ns();value=collector.collect_with_task_visibility(proc,known,history);return dict(kind='sample',begin_ns=begin,end_ns=time.monotonic_ns(),**value)
    samples.extend([sample(),sample()]);release=time.monotonic_ns();shutil.rmtree(task/'102');joined_time=time.monotonic_ns();samples.append(sample())
    header=dict(kind='begin',clock='monotonic',mode='procfs',observer_independent=True,pid=500,root=dict(pid=101,start_ticks=700),boot_id=dict(text='model-boot'),time_namespace_offsets=dict(text='monotonic 0 0\nboottime 0 0\n'),task_visibility_schema_version=1,task_history_capacity=512)
    footer=dict(kind='status',completed=True,budget_exhausted=False,userspace_stacks_requested=False,samples=3,sample_limit=48,kernel_stack_reads_ok=5,kernel_stack_reads_unavailable=0)
    signal=samples[-1]['end_ns']+10000;child=dict(pid=101,passed=True,forced_kill=False,returncode=0,signal_begin_ns=signal,signal_end_ns=signal+100,end_ns=signal+10000)
    write(data/'result.json',dict(status='passed',calibration_id='owned',shutdown=dict(passed=True,children=[child])))
    write(data/'fixture-ready.json',context);write(data/'worker-joined.json',dict(**context,joined=True,release_ns=release,monotonic_ns=joined_time))
    write(data/'target-info.json',dict(pid=101,start_ticks=700,calibration_id='owned',permissions=perms(),supervisor_permissions=perms(),boot_id='model-boot',time_namespace_offsets=header['time_namespace_offsets']['text']))
    write(data/'target-before-signal.json',dict(target=perms(),supervisor=perms()));write(data/'target-supervisor-final.json',perms());write(data/'blocked-target-shutdown-stacks.ready.json',dict(pid=500,ready_ns=samples[0]['begin_ns']-1))
    import hashlib
    execution=[dict(kind='entry',pid=500),dict(kind='preexec_verified',permissions=perms(1<<21),collector_sha256=CANDIDATE_SHA,task_visibility=True,profile_sha256=hashlib.sha256((HERE/'observer-seccomp.json').read_bytes()).hexdigest(),boot_id='model-boot',time_namespace_offsets=header['time_namespace_offsets']['text']),dict(kind='exec_begin',collector_sha256=CANDIDATE_SHA,task_visibility=True,target=dict(pid=101,start_ticks=700))]
    (data/'observer-exec.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in execution));rows=[header,*samples,footer];(data/'blocked-target-shutdown-stacks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
    stages=[];points=['worker_started','fixture_ready','worker_release','worker_return','worker_joined','fixture_sigint','fixture_exit'];times=[samples[0]['begin_ns']-100,samples[0]['begin_ns']-50,release,release+1,joined_time-1,signal+1000,signal+2000]
    for i,(point,t) in enumerate(zip(points,times)):
        row=dict(sequence=i+1,point=point,monotonic_ns=t,pid=101,tid=102 if i in (0,3) else 101,calibration_id='owned')
        if i==0:row['task_identity']=dict(tid=102,start_ticks=701)
        if i==2:row['release_ns']=release
        stages.append(row)
    (data/'task-stages.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in stages))
    return data,rows,context

class DockerModel:
    def __init__(self,folder,data,rows,ready_failure=False,bad_header=False,foreign_pid=False):self.folder=folder;self.data=data;self.rows=rows;self.ready_failure=ready_failure;self.bad_header=bad_header;self.foreign_pid=foreign_pid;self.objects={};self.volumes={};self.calls=[]
    def command(self,argv,**kwargs):
        self.calls.append(argv);out='';code=0
        if argv[:2]==['docker','volume']:
            name=argv[3]
            if argv[2]=='create':p=self.folder/name;p.mkdir();self.volumes[name]=p
            elif argv[2]=='rm':self.volumes.pop(name,None)
        elif argv[1]=='create':
            name=argv[argv.index('--name')+1];observer='/cal/observer_entry.py' in argv
            mounts=[argv[i+1] for i,a in enumerate(argv) if a=='--mount'];volume=next(m.split('source=')[1].split(',')[0] for m in mounts if 'target=/out' in m)
            pid=argv[argv.index('--pid')+1] if '--pid'in argv else ''
            sec=['no-new-privileges=true']+(['seccomp='+json.dumps(json.loads((HERE/'observer-seccomp.json').read_text()))] if observer else [])
            host=dict(Privileged=False,ReadonlyRootfs=True,NetworkMode='none',UsernsMode='',CapAdd=['SYS_ADMIN'] if observer else [],CapDrop=['ALL'],SecurityOpt=sec,PidMode=pid)
            if observer and pid and self.foreign_pid:host['PidMode']='container:foreign'
            self.objects[name]=dict(Id=name+'-id',HostConfig=host,Mounts=[dict(Destination='/cal',RW=False),dict(Destination='/out',RW=True)],State=dict(Running=False,ExitCode=0,Error=''),volume=volume,argv=argv)
        elif argv[1]=='inspect':
            if argv[-1] not in self.objects:code=1
            else:out=json.dumps([self.objects[argv[-1]]])
        elif argv[1]=='start':
            name=argv[-1];obj=self.objects[name];v=self.volumes[obj['volume']]
            if name.endswith('-ready'):
                e=[json.loads(x) for x in (self.data/'observer-exec.jsonl').read_text().splitlines()][:2]+[dict(kind='self_check_passed')];(v/'observer-exec.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in e));obj['State']['ExitCode']=int(self.ready_failure);code=int(self.ready_failure)
            elif name.endswith('-target'):
                obj['State']['Running']=True
                for n in ('target-info.json','fixture-ready.json'):shutil.copyfile(self.data/n,v/n)
            else:
                obj['State']['Running']=True
                for n in ('observer-exec.jsonl','blocked-target-shutdown-stacks.ready.json'):shutil.copyfile(self.data/n,v/n)
                rows=json.loads(json.dumps(self.rows[:-2]))
                if self.bad_header:rows[0]['task_visibility_schema_version']=0
                (v/'blocked-target-shutdown-stacks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
        elif argv[1]=='cp':
            src,dst=argv[2:4]
            if ':/out/' in src:
                name,part=src.split(':/out/');v=self.volumes[self.objects[name]['volume']]
                if part=='.':shutil.copytree(v,Path(dst),dirs_exist_ok=True)
                elif (v/part).exists():shutil.copyfile(v/part,dst)
                else:code=1
            else:
                name,part=dst.split(':/out/');v=self.volumes[self.objects[name]['volume']];shutil.copyfile(src,v/part)
                if part=='release-worker.json':
                    shutil.copyfile(self.data/'worker-joined.json',v/'worker-joined.json');(v/'blocked-target-shutdown-stacks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in self.rows[:-1]))
        elif argv[1]=='wait':
            name=argv[-1];obj=self.objects[name];obj['State']['Running']=False;out='0\n';v=self.volumes[obj['volume']]
            if name.endswith('-observer'):
                for f in self.data.iterdir():
                    if f.is_file():shutil.copyfile(f,v/f.name)
        elif argv[1]=='kill':self.objects[argv[-1]]['State']['Running']=False
        elif argv[1]=='rm':self.objects.pop(argv[-1],None)
        elif argv[1]!='logs':raise AssertionError('unmodeled command: '+str(argv))
        return types.SimpleNamespace(returncode=code,stdout=out,stderr='modeled failure' if code else '')
