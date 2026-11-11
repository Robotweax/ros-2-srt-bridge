"""Host-only native observer lifecycle, launched only by authorized diagnostic driver."""
import json
from pathlib import Path
import subprocess
import time
from m3_source_preflight import write
from m3_observer_filtering import require_role
HERE=Path(__file__).resolve().parent
COLLECTOR_SHA='6deab3c5e83e48b7c33dbbb4613c361469d9b62aa1bea86db0c1a8012cfae72e'
NATIVE='ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617'


def validate_isolation(host):
    capabilities={name.removeprefix('CAP_') for name in (host['CapAdd'] or [])}
    if host['Privileged'] or not host['ReadonlyRootfs'] or host['NetworkMode']!='none' or host['UsernsMode'] or host['CapDrop']!=['ALL'] or capabilities!={'SYS_ADMIN'}:
        raise ValueError('observer isolation mismatch')


class Sidecar:
    def __init__(self,out,bundle,prefix):
        self.out=out;self.bundle=bundle;self.name=prefix+'-observer';self.volume=prefix+'-observer-output';self.created=False;self.volume_created=False;self.commands=[];self.started=False
    def command(self,args,check=True,timeout=15):
        r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        self.commands.append(dict(argv=args,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));write(self.out/'native-observer-commands.json',self.commands)
        if check and r.returncode:raise ValueError('observer command failed; retained Docker diagnostics')
        return r
    def create_argv(self,operator):
        return ['docker','create','--name',self.name,'--pull=never','--platform','linux/arm64','--network','none','--pid','container:'+operator,'--read-only','--cap-drop','ALL','--cap-add','SYS_ADMIN','--security-opt','no-new-privileges=true','--security-opt','seccomp='+str(HERE/'observer-seccomp.json'),'--mount','type=bind,source='+str(self.bundle)+',target=/cal,readonly','--mount','type=volume,source='+self.volume+',target=/out','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=16m','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','/usr/bin/python3',NATIVE,'/cal/observer_entry.py','--task-visibility']
    def arm(self,lab):
        from calibration_scope import guard
        guard(self.out,self.bundle,self.name.removesuffix('-observer'))
        target=json.loads((self.out/'operator-bridge-identity.json').read_text());require_role(target['permissions'],0)
        self.command(['docker','volume','create',self.volume]);self.volume_created=True
        self.created=True
        self.command(self.create_argv(lab.containers['operator']));self.created=True
        inspected=json.loads(self.command(['docker','inspect',self.name]).stdout)[0];write(self.out/'native-observer-policy.json',inspected);h=inspected['HostConfig']
        validate_isolation(h)
        if h['PidMode']!='container:'+lab.containers['operator'] and h['PidMode']!='container:'+lab.execute('operator-id',['docker','inspect','--format','{{.Id}}',lab.containers['operator']]).strip():raise ValueError('observer joined wrong PID namespace')
        if {(m['Destination'],m['RW']) for m in inspected['Mounts'] if m['Destination']!='/tmp'}!={('/cal',False),('/out',True)}:raise ValueError('unexpected observer mounts')
        selected=[x.split('=',1)[1] for x in h['SecurityOpt'] if x.startswith('seccomp=')]
        if len(selected)!=1 or json.loads(selected[0])!=json.loads((HERE/'observer-seccomp.json').read_text()):raise ValueError('observer filter mismatch')
        write(self.out/'target-info.json',target);self.command(['docker','cp',str(self.out/'target-info.json'),self.name+':/out/target-info.json'])
        self.command(['docker','start',self.name]);self.started=True
        until=time.monotonic()+5
        while time.monotonic()<until:
            r=self.command(['docker','cp',self.name+':/out/blocked-target-shutdown-stacks.ready.json',str(self.out/'operator-observer-ready.json')],check=False)
            if r.returncode==0:break
            state=json.loads(self.command(['docker','inspect',self.name]).stdout)[0]['State']
            if not state['Running']:raise ValueError('observer exited before readiness: '+str(state))
            time.sleep(.05)
        else:raise ValueError('observer not ready within5s; no release authorization')
        self.command(['docker','cp',self.name+':/out/observer-exec.jsonl',str(self.out/'operator-observer-exec.jsonl')])
        execution=[json.loads(x) for x in (self.out/'operator-observer-exec.jsonl').read_text().splitlines()]
        if [x['kind'] for x in execution]!=['entry','preexec_verified','exec_begin']:raise ValueError('observer exec proof incomplete')
        require_role(execution[1]['permissions'],1<<21)
        if any(e.get('collector_sha256')!=COLLECTOR_SHA or e.get('task_visibility') is not True for e in execution[1:]):raise ValueError('observer collector activation binding differs')
        if execution[1]['boot_id']!=target['boot_id'] or execution[1]['time_namespace_offsets']!=target['time_namespace_offsets']:raise ValueError('observer target clock origin differs')
        from sdk_visibility import wait_provider_visibility
        wait_provider_visibility(self,target)
    def close(self):
        errors=[]
        def attempt(call):
            try:return call()
            except BaseException as error:errors.append(str(error));return None
        if self.created:
            if self.started:
                (self.out/'observer.stop').touch()
                attempt(lambda:self.command(['docker','cp',str(self.out/'observer.stop'),self.name+':/out/observer.stop']))
                code=attempt(lambda:self.command(['docker','wait',self.name],timeout=5))
                if code is None or code.stdout.strip()!='0':errors.append('observer failed during collection')
            state=attempt(lambda:self.command(['docker','inspect',self.name],check=False))
            if state is not None and state.returncode==0:
                value=json.loads(state.stdout)[0]['State'];write(self.out/'native-observer-final-state.json',value)
                if value['Running']:
                    attempt(lambda:self.command(['docker','kill',self.name],check=False));errors.append('observer forced cleanup; incomplete lifecycle')
                destination=self.out/'native-observer';destination.mkdir(exist_ok=True)
                attempt(lambda:self.command(['docker','cp',self.name+':/out/.',str(destination)]))
                attempt(lambda:self.command(['docker','logs',self.name],check=False))
                removed=attempt(lambda:self.command(['docker','rm','-f',self.name]))
                if removed is not None:self.created=False
            elif state is not None:self.created=False
        if self.volume_created:
            removed=attempt(lambda:self.command(['docker','volume','rm',self.volume]))
            if removed is not None:self.volume_created=False
        if errors:raise ValueError('; '.join(errors))
