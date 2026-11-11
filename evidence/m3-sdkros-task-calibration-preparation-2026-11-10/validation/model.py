"""Offline temporary launch/SDK metadata and Docker models; no native execution."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import types
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
from campaign_binding import load

def read(path):return json.loads(path.read_text())
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value)+'\n')
def lines(path):return [json.loads(x) for x in path.read_text().splitlines()]
def jsonl(path,rows):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(''.join(json.dumps(x)+'\n' for x in rows))
def overlay(out):
    path=ROOT/'evidence/m3-campaign-task-assessment-integration-2026-11-10/validation/model.py';spec=importlib.util.spec_from_file_location('prior_overlay',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);result,_,fixture=m.overlay(out)
    capture=out/'native-observer/blocked-target-shutdown-stacks.jsonl';rows=lines(capture)
    def rename(value):
        if isinstance(value,dict):
            if value.get('tid')==8 and value.get('start_ticks')==785 and 'name' in value:value['name']='rwx-shard-0'
            if value.get('status')=='ok' and value.get('text','').startswith('8 (python3)'):value['text']=value['text'].replace('8 (python3)','8 (rwx-shard-0)',1)
            for item in value.values():rename(item)
        elif isinstance(value,list):
            for item in value:rename(item)
    rename(rows);jsonl(capture,rows)
    from m3_network import PROFILES
    profile=PROFILES['N0'];network=read(out/'network.json');network['commands']=[c for c in network['commands'] if not c['label'].startswith('profile-')]
    for role in ('operator','robot'):
        seed=1701+(role=='operator')
        for i,argv in enumerate(profile.commands(seed)):network['commands'].append(dict(label=f'profile-{role}-{i}',exit_code=0,argv=['docker','exec',network['containers'][role],*argv]))
        write(out/(f'profile-{role}-readback.log'),[dict(kind='netem',handle='1:',root=True,options=dict(seed=seed,limit=profile.queue_packets))])
    write(out/'network.json',network);return result,load('cases').cases()[0],fixture

class DockerModel:
    def __init__(self,out,ready_failure=False,bad_policy=False):self.out=out;self.ready_failure=ready_failure;self.bad_policy=bad_policy;self.objects={};self.volumes=set();self.calls=[]
    def command(self,args,**kwargs):
        self.calls.append(args);text='';code=0
        if args[1]=='volume':
            if args[2]=='create':self.volumes.add(args[3])
            elif args[2]=='rm':self.volumes.discard(args[3])
            else:text='\n'.join(self.volumes)
        elif args[1]=='create':
            name=args[args.index('--name')+1];host=dict(Privileged=False,ReadonlyRootfs=True,NetworkMode='none',UsernsMode='',CapDrop=['ALL'],CapAdd=['SYS_ADMIN'],PidMode='',SecurityOpt=['no-new-privileges=true','seccomp='+json.dumps(read(HERE/'observer-seccomp.json'))])
            if self.bad_policy:host['NetworkMode']='host'
            self.objects[name]=dict(HostConfig=host,Mounts=[dict(Destination='/cal',RW=False),dict(Destination='/out',RW=True)],State=dict(Running=False,ExitCode=1 if self.ready_failure else 0,Error=''))
        elif args[1]=='inspect':
            if args[-1] not in self.objects:code=1
            else:text=json.dumps([self.objects[args[-1]]])
        elif args[1]=='start':code=int(self.ready_failure)
        elif args[1]=='cp':
            destination=Path(args[-1]);destination.mkdir(exist_ok=True)
            source=ROOT/'evidence/m3-task-post-sigint-calibration-execution-2026-11-10/run/readiness/observer-exec.jsonl';shutil.copyfile(source,destination/'observer-exec.jsonl')
        elif args[1]=='rm':self.objects.pop(args[-1],None)
        elif args[1]=='ps':text='\n'.join(self.objects)
        elif args[1]=='network':text=''
        elif args[1] not in ('logs','kill'):raise AssertionError('unmodeled Docker command: '+str(args))
        return types.SimpleNamespace(returncode=code,stdout=text,stderr='modeled failure' if code else '')
