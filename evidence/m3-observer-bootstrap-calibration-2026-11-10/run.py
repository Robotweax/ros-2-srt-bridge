"""One native-observer readiness check, then one original blocked-target calibration."""
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from m3_runtime_layout import matched
from m3_observer_filtering import architecture,profile,require_role
OUT=Path(__file__).resolve().parent


def assess(data):
    result=json.loads((data/'result.json').read_text())
    if result['status']!='passed':raise ValueError('target controller failed: '+str(result.get('error')))
    child=result['shutdown']['children'][0];elapsed=child['end_ns']-child['signal_end_ns']
    if not child['passed'] or child['forced_kill'] or not 2_500_000_000<=elapsed<=5_000_000_000:raise ValueError('original3s target/5s wait gate failed')
    info=json.loads((data/'target-info.json').read_text());before=json.loads((data/'target-before-signal.json').read_text());require_role(info['permissions'],0);require_role(before['target'],0);require_role(before['supervisor'],0);require_role(json.loads((data/'target-supervisor-final.json').read_text()),0)
    execution=[json.loads(x) for x in (data/'observer-exec.jsonl').read_text().splitlines()]
    if [x['kind'] for x in execution]!=['entry','preexec_verified','exec_begin']:raise ValueError('observer pre-exec/exec records incomplete')
    require_role(execution[1]['permissions'],1<<21)
    stages=[json.loads(x) for x in (data/'stages.jsonl').read_text().splitlines()]
    if [x['point'] for x in stages]!=['fixture_ready','fixture_sigint_observed','fixture_blocked_begin','fixture_blocked_end','fixture_exit'] or [x['sequence'] for x in stages]!=list(range(1,6)) or any(x['pid']!=child['pid'] or x['dropped_before'] for x in stages):raise ValueError('original fixture stage gate failed')
    rows=[json.loads(x) for x in (data/'blocked-target-shutdown-stacks.jsonl').read_text().splitlines()];ready=json.loads((data/'blocked-target-shutdown-stacks.ready.json').read_text());begin=rows[0];footer=rows[-1]
    if not begin['observer_independent'] or begin['root']['pid']!=child['pid'] or begin['pid']==child['pid'] or begin['pid']!=execution[0]['pid'] or ready['ready_ns']>child['signal_begin_ns']:raise ValueError('independent observer identity/readiness failed')
    if begin['mode']!='procfs' or any(x['kind']=='userspace_stack' for x in rows):raise ValueError('unplanned GDB mode')
    if footer.get('kind')!='status' or not footer['completed'] or footer['budget_exhausted']:raise ValueError('observer did not finish within declared budget')
    if begin['boot_id']['text'].strip()!=info['boot_id'] or execution[1]['boot_id']!=info['boot_id']:raise ValueError('different kernel clock origins')
    for text in (begin['time_namespace_offsets']['text'],info['time_namespace_offsets'],execution[1]['time_namespace_offsets']):
        if not text.splitlines() or any(len(x.split())!=3 or any(int(v) for v in x.split()[1:]) for x in text.splitlines()):raise ValueError('nonzero time namespace offsets')
    post=[x for x in rows if x['kind']=='sample' and max(child['signal_end_ns'],stages[2]['monotonic_ns'])<=x['begin_ns']<=x['end_ns']<=min(child['end_ns'],stages[3]['monotonic_ns'])]
    if len(post)<2:raise ValueError('observer did not cover parent blocked wait')
    tids=set();success={};errors=[];wchan=set();read_count=0
    for sample in post:
        if sample['process_limit_hit']:raise ValueError('process observation budget hit')
        for process in sample['processes']:
            if process['status']!='sampled' or not process['identity_still_matches'] or process['threads_truncated'] or process['identity']['pid']!=child['pid']:raise ValueError('owned target identity/thread observation failed')
            for thread in process['threads']:
                tids.add(thread['tid']);read_count+=1;stack=thread['kernel_stack'];wchan.add(thread['wchan'].get('text','').strip())
                if stack['status']!='ok':errors.append(stack)
                elif stack['truncated']:raise ValueError('kernel stack truncated')
                elif stack['text'].strip():success[thread['tid']]=success.get(thread['tid'],0)+1
    proof=dict(status='passed' if len(tids)==2 and set(success)==tids and not errors else 'failed',post_signal_samples=len(post),thread_reads=read_count,target_tids=sorted(tids),nonempty_stacks_by_tid=success,unavailable_stack_reads=len(errors),errors=errors[:4],wchan=sorted(wchan),signal_to_reap_ns=elapsed,scope='native observer/kernel stacks on unchanged synthetic target only')
    write(data/'stack-assessment.json',proof)
    if proof['status']!='passed':raise ValueError('nonempty kernel stacks not available for both original blocked threads')
    return proof


def execute():
    freeze=json.loads((OUT/'freeze.json').read_text());run=ROOT/freeze['output_relative'];bundle=ROOT/freeze['bundle_relative'];native=freeze['observer_image'];policy_path=OUT/'observer-seccomp.json';log=[];objects=[];volumes=[]
    def verify():
        if matched(ROOT,'shutdown-tracing')!=freeze['runtime_layout'] or source_inventory()!=freeze['source_sha256']:raise ValueError('matched build/source drift')
        if any(sha(ROOT/p)!=h for p,h in freeze['inputs_sha256'].items()):raise ValueError('frozen inputs drift')
    verify()
    if run.exists():raise ValueError('one-shot output already exists')
    run.mkdir();write(run/'freeze.json',freeze)
    def command(label,argv,check=True,timeout=20):
        r=subprocess.run(argv,capture_output=True,text=True,timeout=timeout);log.append(dict(label=label,argv=argv,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));write(run/'commands.json',log)
        if check and r.returncode:raise ValueError(label+' failed; inspect Docker/OCI diagnostics')
        return r
    def create(name,volume,observer=False,pid_target=None,self_check=False):
        argv=['docker','create','--name',name,'--pull=never','--platform','linux/arm64' if observer else 'linux/amd64','--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges=true','--mount','type=bind,source='+str(bundle)+',target=/cal,readonly','--mount','type=volume,source='+volume+',target=/out','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=16m','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','/usr/bin/python3','-w','/cal']
        if observer:argv+=['--cap-add','SYS_ADMIN','--security-opt','seccomp='+str(policy_path)]
        if pid_target:argv+=['--pid','container:'+pid_target]
        argv+=[native if observer else IMAGE,'/cal/observer_entry.py' if observer else '/cal/target_entry.py']
        if self_check:argv+=['--self-check']
        command('create-'+name,argv);objects.append(name)
        data=json.loads(command('inspect-policy-'+name,['docker','inspect',name]).stdout)[0];write(run/(name+'-policy.json'),data);host=data['HostConfig']
        if host['Privileged'] or not host['ReadonlyRootfs'] or host['NetworkMode']!='none' or host['UsernsMode']:raise ValueError('container isolation differs')
        caps={x.removeprefix('CAP_') for x in (host['CapAdd'] or [])}
        if caps!=({'SYS_ADMIN'} if observer else set()) or host['CapDrop']!=['ALL']:raise ValueError('role capability policy differs')
        if not any(x.replace(':','=') in ('no-new-privileges','no-new-privileges=true') for x in host['SecurityOpt']):raise ValueError('NNP not configured')
        if observer:
            selected=[x.split('=',1)[1] for x in host['SecurityOpt'] if x.startswith('seccomp=')]
            if len(selected)!=1 or json.loads(selected[0])!=json.loads(policy_path.read_text()):raise ValueError('daemon observer filter differs')
        if pid_target and not host['PidMode'].startswith('container:'):raise ValueError('observer must join only owned target PID namespace')
        if not pid_target and host['PidMode']:raise ValueError('unexpected PID namespace override')
        if {(m['Destination'],m['RW']) for m in data['Mounts'] if m['Destination']!='/tmp'}!={('/cal',False),('/out',True)}:raise ValueError('mount exposure differs')
    def volume(name):command('volume-'+name,['docker','volume','create',name]);volumes.append(name)
    def export(name,destination):destination.mkdir(exist_ok=True);command('export-'+name,['docker','cp',name+':/out/.',str(destination)])
    def upload(name,path):command('upload-'+path.name,['docker','cp',str(path),name+':/out/'+path.name])
    def state(name):return json.loads(command('state-'+name,['docker','inspect',name]).stdout)[0]['State']
    def read_file(name,path,destination,deadline):
        while time.monotonic()<deadline:
            r=command('poll-'+path,['docker','cp',name+':/out/'+path,str(destination)],check=False)
            if r.returncode==0:return
            s=state(name)
            if not s['Running']:raise ValueError(name+' exited before '+path+'; retained State.Error='+s['Error'])
            time.sleep(.05)
        raise ValueError('readiness timed out for '+path)
    report=dict(status='running',blocked_calibration_runs=0,remaining_campaign_cases_disabled=29,retry_two_loss_4211=False,no_tuning=True)
    try:
        components=json.loads(command('runtime-version',['docker','version','--format','{{json .Server.Components}}']).stdout)
        if components!=freeze['runtime_version']:raise ValueError('frozen runtime version drift')
        daemon=command('daemon-native-architecture',['docker','info','--format','{{.Architecture}}']).stdout.strip()
        image=command('observer-image-architecture',['docker','image','inspect','--platform','linux/arm64',native,'--format','{{.Architecture}}']).stdout.strip()
        if architecture(daemon)!='arm64' or architecture(image)!=architecture(daemon) or profile(daemon,image)!=json.loads(policy_path.read_text()):raise ValueError('native daemon/image/profile mismatch before readiness')
        # Exact-policy interpreter/exec readiness, no target and no stack read.
        v=freeze['prefix']+'-ready-out';n=freeze['prefix']+'-ready';volume(v);create(n,v,observer=True,self_check=True)
        r=command('observer-readiness',['docker','start','--attach',n],check=False);s=state(n);export(n,run/'readiness')
        if r.returncode or s['ExitCode'] or s['Error']:raise ValueError('native observer readiness failed; no target launched')
        ready=[json.loads(x) for x in (run/'readiness/observer-exec.jsonl').read_text().splitlines()]
        if [x['kind'] for x in ready]!=['entry','preexec_verified','self_check_passed']:raise ValueError('native readiness stages incomplete')
        report['observer_readiness']='passed';verify()
        target=freeze['prefix']+'-target';observer=freeze['prefix']+'-observer';v=freeze['prefix']+'-out';volume(v);create(target,v)
        command('start-only-blocked-target',['docker','start',target]);report['blocked_calibration_runs']=1
        target_info=run/'target-info.json';read_file(target,'target-info.json',target_info,time.monotonic()+8);info=json.loads(target_info.read_text());require_role(info['permissions'],0);require_role(info['supervisor_permissions'],0)
        create(observer,v,observer=True,pid_target=target);command('start-native-observer',['docker','start',observer])
        read_file(target,'blocked-target-shutdown-stacks.ready.json',run/'observer-ready.json',time.monotonic()+5)
        export(target,run/'before-signal');execution=[json.loads(x) for x in (run/'before-signal/observer-exec.jsonl').read_text().splitlines()]
        if [x['kind'] for x in execution]!=['entry','preexec_verified','exec_begin']:raise ValueError('observer explicit exec gates incomplete')
        require_role(execution[1]['permissions'],1<<21)
        if execution[1]['boot_id']!=info['boot_id'] or not 0<=execution[1]['monotonic_ns']-info['monotonic_ns']<=10_000_000_000:raise ValueError('native/target clock origin mismatch')
        authority=run/'authorize-signal.json';write(authority,dict(scope='one-blocked-calibration',target_pid=info['pid']));upload(target,authority)
        waited=command('wait-observer',['docker','wait',observer],timeout=15)
        if waited.stdout.strip()!='0':raise ValueError('observer failed; inspect explicit exec/status logs')
        ack=run/'observer-exited.json';write(ack,dict(exit_code=0));upload(target,ack)
        waited=command('wait-target',['docker','wait',target],timeout=8)
        export(target,run/'data')
        if waited.stdout.strip()!='0':raise ValueError('target controller failed')
        report['assessment']=assess(run/'data');verify();report['status']='passed'
    except BaseException as error:report.update(status='failed',error=dict(type=type(error).__name__,errno=getattr(error,'errno',None),message=str(error)))
    finally:
        # Stop only owned processes, then export closed files even on bootstrap failure.
        for name in reversed(objects):
            s=state(name)
            if s['Running']:command('failure-stop-'+name,['docker','kill',name],check=False)
            export(name,run/(name+'-final-output'))
            command('logs-'+name,['docker','logs',name],check=False)
            r=command('remove-'+name,['docker','rm','--force',name],check=False)
            if r.returncode:report.update(status='failed',cleanup_error='container removal failed')
        for name in reversed(volumes):
            r=command('remove-volume-'+name,['docker','volume','rm',name],check=False)
            if r.returncode:report.update(status='failed',cleanup_error='volume removal failed')
        write(run/'calibration.json',report);print(json.dumps(report),flush=True)
    return report


if __name__=='__main__':raise SystemExit(execute()['status']!='passed')
