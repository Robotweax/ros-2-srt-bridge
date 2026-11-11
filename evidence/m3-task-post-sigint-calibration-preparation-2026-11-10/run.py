"""One exact readiness check and one controlled fixture; separate grant mandatory."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from m3_observer_filtering import architecture,profile,require_role
from disposition_runtime import matched
from m3_closure_assessor import evaluate_sequence
from plan import authorize,disabled_ids,remaining_ids,SCOPE,CANDIDATE_SHA,assessment_hashes
from assess import assess,presence,absence,snapshot,live_header
STAGES=[dict(id='observer-readiness'),dict(id='controlled-post-sigint-assessment')]

def fresh_output(path):
    if path.exists():raise ValueError('output exists; no resume or retry')
def verify(freeze):
    if source_inventory()!=freeze['source_sha256'] or matched(ROOT,'socket-disposition')!=freeze['runtime_layout']:raise ValueError('source/build drift')
    if any(sha(ROOT/p)!=h for p,h in freeze['inputs_sha256'].items()):raise ValueError('frozen input drift')
    for index,digest in freeze['retained_indexes'].items():
        if sha(ROOT/index)!=digest or any(sha(ROOT/p)!=v['sha256'] for p,v in json.loads((ROOT/index).read_text()).items()):raise ValueError('retained evidence drift')
    if json.loads(subprocess.check_output(['docker','version','--format','{{json .Server.Components}}'],text=True,timeout=20))!=freeze['runtime_version']:raise ValueError('runtime drift')
    if subprocess.check_output(['docker','info','--format','{{.Architecture}}'],text=True,timeout=20).strip()!=freeze['daemon_architecture']:raise ValueError('daemon architecture differs')
    if subprocess.check_output(['docker','ps','-q'],text=True,timeout=20).strip():raise ValueError('live containers remain')
    for platform,image,arch in [('linux/amd64',IMAGE,'amd64'),('linux/arm64',freeze['observer_image'],'arm64')]:
        if subprocess.check_output(['docker','image','inspect','--platform',platform,image,'--format','{{.Architecture}}'],text=True,timeout=20).strip()!=arch:raise ValueError('image architecture differs')
    for argv in (['docker','ps','-a','--format','{{.Names}}'],['docker','volume','ls','--format','{{.Name}}']):
        if any(n.startswith(freeze['prefix']) for n in subprocess.check_output(argv,text=True).splitlines()):raise ValueError('owned prefix exists')
def sequence(readiness,controlled,record):
    callbacks={'observer-readiness':readiness,'controlled-post-sigint-assessment':controlled}
    return evaluate_sequence(STAGES,lambda s:callbacks[s['id']](),lambda s,r:dict(status='passed',proof=r),record)

def execute(grant_path):
    freeze=json.loads((HERE/'freeze.json').read_text());grant=json.loads(grant_path.read_text());grant_sha=sha(grant_path);authorize(grant,sha(HERE/'freeze.json'))
    if freeze['execution_enabled'] is not False or freeze['authorization_supplied'] is not False or freeze['readiness_checks']!=1 or freeze['controlled_target_limit']!=1 or freeze['assessment_candidate_sha256']!=assessment_hashes() or freeze['post_sigint_calibration'] is not True or freeze['disabled_case_ids']!=disabled_ids() or freeze['remaining_case_ids_disabled']!=remaining_ids():raise ValueError('calibration scope differs')
    run=ROOT/freeze['output_relative'];fresh_output(run);verify(freeze);run.mkdir();write(run/'freeze.json',freeze);write(run/'authorization.json',grant)
    bundle=ROOT/freeze['bundle_relative'];native=freeze['observer_image'];policy_path=HERE/'observer-seccomp.json';log=[];objects=[];volumes=[];created_ids={}
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
        elif observer:argv+=['--task-visibility']
        else:argv+=[freeze['prefix']]
        objects.append(name);command('create-'+name,argv)
        data=json.loads(command('inspect-policy-'+name,['docker','inspect',name]).stdout)[0];created_ids[name]=data['Id'];write(run/(name+'-policy.json'),data);host=data['HostConfig']
        if host['Privileged'] or not host['ReadonlyRootfs'] or host['NetworkMode']!='none' or host['UsernsMode']:raise ValueError('container isolation differs')
        caps={x.removeprefix('CAP_') for x in (host['CapAdd'] or [])}
        if caps!=({'SYS_ADMIN'} if observer else set()) or host['CapDrop']!=['ALL']:raise ValueError('role capability policy differs')
        if not any(x.replace(':','=') in ('no-new-privileges','no-new-privileges=true') for x in host['SecurityOpt']):raise ValueError('NNP not configured')
        if observer:
            selected=[x.split('=',1)[1] for x in host['SecurityOpt'] if x.startswith('seccomp=')]
            if len(selected)!=1 or json.loads(selected[0])!=json.loads(policy_path.read_text()):raise ValueError('daemon observer filter differs')
        if pid_target and host['PidMode'] not in ('container:'+pid_target,'container:'+created_ids[pid_target]):raise ValueError('observer joined foreign PID namespace')
        if not pid_target and host['PidMode']:raise ValueError('unexpected PID namespace override')
        if {(m['Destination'],m['RW']) for m in data['Mounts'] if m['Destination']!='/tmp'}!={('/cal',False),('/out',True)}:raise ValueError('mount exposure differs')
    def volume(name):volumes.append(name);command('volume-'+name,['docker','volume','create',name])
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
    def stage_verify():
        if sha(grant_path)!=grant_sha:raise ValueError('grant changed')
        if source_inventory()!=freeze['source_sha256'] or any(sha(ROOT/p)!=h for p,h in freeze['inputs_sha256'].items()):raise ValueError('frozen input drift during calibration')
    def bounded_snapshot(target):
        path=run/'active-observer.jsonl';r=command('snapshot-task-observer',['docker','cp',target+':/out/blocked-target-shutdown-stacks.jsonl',str(path)],check=False)
        if r.returncode:return []
        if path.stat().st_size>8*1024*1024:raise ValueError('calibration snapshot byte bound exceeded')
        return snapshot(path.read_text())
    def wait_proof(target,context,check,deadline):
        while time.monotonic()<deadline:
            rows=bounded_snapshot(target)
            try:live_header(rows,context);return check(rows)
            except ValueError as error:
                # Only incomplete phase populations can wait; schema/access errors stop immediately.
                if str(error) not in ('observer header unavailable','observer samples unavailable','two live worker observations required','controlled absence evidence unavailable'):raise
            if not state(target)['Running']:raise ValueError('target exited before calibration proof')
            time.sleep(.05)
        raise ValueError('calibration evidence deadline exceeded')
    def readiness():
        stage_verify();v=freeze['prefix']+'-ready-out';n=freeze['prefix']+'-ready';volume(v);create(n,v,observer=True,self_check=True)
        r=command('observer-readiness',['docker','start','--attach',n],check=False);s=state(n);export(n,run/'readiness')
        if r.returncode or s['Running'] or s['ExitCode'] or s['Error']:raise ValueError('native interpreter/collector readiness failed')
        events=[json.loads(x) for x in (run/'readiness/observer-exec.jsonl').read_text().splitlines()]
        if [x['kind'] for x in events]!=['entry','preexec_verified','self_check_passed'] or events[1]['collector_sha256']!=CANDIDATE_SHA or events[1]['task_visibility'] is not True:raise ValueError('readiness activation/binding differs')
        require_role(events[1]['permissions'],1<<21);return dict(status='passed',target_launched=False)
    def controlled():
        stage_verify();target=freeze['prefix']+'-target';observer=freeze['prefix']+'-observer';v=freeze['prefix']+'-out';volume(v);create(target,v);command('start-only-controlled-target',['docker','start',target])
        read_file(target,'target-info.json',run/'target-info.json',time.monotonic()+8);info=json.loads((run/'target-info.json').read_text());require_role(info['permissions'],0);require_role(info['supervisor_permissions'],0)
        read_file(target,'fixture-ready.json',run/'fixture-ready.json',time.monotonic()+2);context=json.loads((run/'fixture-ready.json').read_text())
        if context['calibration_id']!=freeze['prefix'] or context['target_pid']!=info['pid'] or context['target_start_ticks']!=info['start_ticks']:raise ValueError('target registration differs')
        create(observer,v,observer=True,pid_target=target);command('start-task-observer',['docker','start',observer]);read_file(target,'blocked-target-shutdown-stacks.ready.json',run/'observer-ready.json',time.monotonic()+5)
        phase_deadline=time.monotonic()+6
        live=wait_proof(target,context,lambda rows:presence(rows,context),phase_deadline);write(run/'live-task-proof.json',live)
        authority=run/'authorize-signal.json';write(authority,dict(scope='one-post-sigint-task-assessment-calibration',calibration_id=freeze['prefix'],target_pid=info['pid'],target_start_ticks=info['start_ticks']));upload(target,authority)
        post_deadline=time.monotonic()+3
        read_file(target,'signal-wait.json',run/'signal-wait.json',post_deadline);waiting=json.loads((run/'signal-wait.json').read_text())
        read_file(target,'signal-seen.json',run/'signal-seen.json',post_deadline);seen=json.loads((run/'signal-seen.json').read_text())
        if any(any(w[k]!=context[k] for k in context) for w in (waiting,seen)):raise ValueError('signal witness context differs')
        post=wait_proof(target,context,lambda rows:presence(rows,context,after_ns=max(waiting['wait_enter_ns'],seen['monotonic_ns'])),post_deadline);write(run/'post-signal-live-proof.json',post)
        authority=run/'release-worker.json';write(authority,dict(**context,phase='post-sigint',wait_enter_ns=waiting['wait_enter_ns']));upload(target,authority)
        read_file(target,'worker-joined.json',run/'worker-joined.json',post_deadline);joined=json.loads((run/'worker-joined.json').read_text())
        gone=wait_proof(target,context,lambda rows:absence(rows,context,joined,waiting),post_deadline);write(run/'controlled-absence-proof.json',gone)
        authority=run/'allow-exit.json';write(authority,dict(**context,phase='post-sigint-exit',absence_end_ns=gone['observed_end_ns']));upload(target,authority)
        waited=command('wait-observer',['docker','wait',observer],timeout=15)
        if waited.stdout.strip()!='0':raise ValueError('observer failed')
        ack=run/'observer-exited.json';write(ack,dict(exit_code=0));upload(target,ack);waited=command('wait-target',['docker','wait',target],timeout=8);export(target,run/'data')
        if waited.stdout.strip()!='0':raise ValueError('fixture supervisor failed')
        proof=assess(run/'data');write(run/'task-calibration-assessment.json',proof);stage_verify();return proof
    def record(value):write(run/'stages.json',dict(value,scope=SCOPE,disabled_case_ids=disabled_ids(),remaining_case_ids_disabled=remaining_ids(),N1_2903_rerun=False,no_tuning=True,no_retries=True))
    report=dict(status='failed',scope=SCOPE,readiness_limit=1,controlled_target_limit=1,N1_2903_rerun=False,no_tuning=True,no_retries=True)
    try:
        report['stages']=sequence(readiness,controlled,record);report['status']=report['stages']['status']
    except BaseException as error:report.update(status='failed',error=dict(type=type(error).__name__,message=str(error)))
    finally:
        errors=[]
        for name in reversed(objects):
            try:
                s=state(name)
                if s['Running']:command('failure-stop-'+name,['docker','kill',name],check=False)
                export(name,run/(name+'-final-output'));command('logs-'+name,['docker','logs',name],check=False)
            except BaseException as error:errors.append(str(error))
            try:command('remove-'+name,['docker','rm','--force',name])
            except BaseException as error:errors.append(str(error))
        for name in reversed(volumes):
            try:command('remove-volume-'+name,['docker','volume','rm',name])
            except BaseException as error:errors.append(str(error))
        try:verify(freeze);write(run/'postflight.json',dict(frozen_integrity_verified=True,owned_objects_absent=True))
        except BaseException as error:errors.append(str(error))
        if errors:report.update(status='failed',cleanup_errors=errors)
        report.update(disabled_case_ids=disabled_ids(),remaining_case_ids_disabled=remaining_ids(),historical_failure_preserved=True,M3_complete=False);write(run/'calibration.json',report)
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--authorization',type=Path,required=True);args=parser.parse_args();return int(execute(args.authorization)['status']!='passed')
if __name__=='__main__':raise SystemExit(main())
