"""One permission-scoped blocked-target rerun. No bridge/sensor/campaign adapter."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from m3_runtime_layout import matched
from m3_observer_permissions import SYS_ADMIN,require_caps,filter_program
OUT=Path(__file__).resolve().parent


def assess(run):
    result=json.loads((run/'result.json').read_text())
    if result['status']!='passed':raise ValueError('inner preparation/target failure: '+str(result.get('error')))
    child=result['shutdown']['children'][0];elapsed=child['end_ns']-child['signal_end_ns']
    if not child['passed'] or child['forced_kill'] or not 2_500_000_000<=elapsed<=5_000_000_000:raise ValueError('unchanged target/5s lifecycle gate failed')
    permissions=json.loads((run/'permission-proof.json').read_text());require_caps(permissions['supervisor_before_signal'],0);require_caps(permissions['target_before_signal'],0);require_caps(permissions['observer_before_signal'],SYS_ADMIN)
    require_caps(json.loads((run/'supervisor-final-permissions.json').read_text()),0)
    stages=[json.loads(line) for line in (run/'stages.jsonl').read_text().splitlines()]
    points=['fixture_ready','fixture_sigint_observed','fixture_blocked_begin','fixture_blocked_end','fixture_exit']
    if [r['point'] for r in stages]!=points or [r['sequence'] for r in stages]!=list(range(1,6)) or any(r['pid']!=child['pid'] or r['dropped_before'] for r in stages):raise ValueError('fixture stage proof incomplete')
    control=child.get('stack_observer',{})
    if not control.get('complete') or not child['stack_observer_armed']:raise ValueError('restricted observer lifecycle incomplete')
    rows=[json.loads(line) for line in (run/'blocked-target-shutdown-stacks.jsonl').read_text().splitlines()]
    begin=rows[0];ready=json.loads((run/'blocked-target-shutdown-stacks.ready.json').read_text())
    if not begin['observer_independent'] or begin['root']['pid']!=child['pid'] or begin['pid']==child['pid'] or ready['ready_ns']>child['signal_begin_ns']:raise ValueError('observer readiness/identity gate failed')
    if begin['mode']!='procfs' or any(r['kind']=='userspace_stack' for r in rows):raise ValueError('unplanned debugger mode')
    if begin['boot_id']['status']!='ok' or begin['time_namespace_offsets']['status']!='ok':raise ValueError('observer clock proof missing')
    offsets=begin['time_namespace_offsets']['text'].splitlines()
    if not offsets or any(len(r.split())!=3 or any(int(v) for v in r.split()[1:]) for r in offsets):raise ValueError('nonzero observer time namespace')
    post=[r for r in rows if r['kind']=='sample' and max(child['signal_end_ns'],stages[2]['monotonic_ns'])<=r['begin_ns']<=r['end_ns']<=min(child['end_ns'],stages[3]['monotonic_ns'])]
    if len(post)<2:raise ValueError('independent observer did not cover controlled blocked interval')
    tids=set();success={};denied=[];wchan=set();reads=0
    for sample in post:
        if sample['process_limit_hit']:raise ValueError('observer process budget hit')
        for process in sample['processes']:
            if process['status']!='sampled' or not process['identity_still_matches'] or process['threads_truncated']:raise ValueError('target identity/thread budget gate failed')
            if process['identity']['pid']!=child['pid']:raise ValueError('unexpected process in finite target tree')
            for thread in process['threads']:
                tids.add(thread['tid']);reads+=1;k=thread['kernel_stack']
                if k['status']!='ok':denied.append(k)
                elif k['truncated']:raise ValueError('kernel stack truncated')
                elif k['text'].strip():success[thread['tid']]=success.get(thread['tid'],0)+1
                wchan.add(thread['wchan'].get('text','').strip())
    proof=dict(status='passed' if len(tids)==2 and set(success)==tids and not denied else 'failed',post_signal_blocked_samples=len(post),thread_reads=reads,target_tids=sorted(tids),nonempty_stack_reads_by_tid=success,unavailable_reads=len(denied),errors=denied[:4],observed_wchan=sorted(wchan),signal_to_reap_ns=elapsed,permission_proof=permissions,scope='kernel stacks on exact finite target only; not original bridge hang/user stacks/N3 acceptance')
    write(run/'stack-assessment.json',proof)
    if proof['status']!='passed':raise ValueError('nonempty kernel stacks unavailable for both registered blocked threads')
    return proof


def execute():
    freeze=json.loads((OUT/'freeze.json').read_text());run=ROOT/freeze['output_relative'];bundle=ROOT/freeze['bundle_relative'];name=freeze['container'];volume=freeze['volume'];commands=[]
    def verify():
        if matched(ROOT,'shutdown-tracing')!=freeze['runtime_layout'] or source_inventory()!=freeze['source_sha256']:raise ValueError('matched build/source drift')
        if any(sha(ROOT/p)!=h for p,h in freeze['inputs_sha256'].items()):raise ValueError('driver/permission/bundle drift')
    verify()
    if run.exists():raise ValueError('one-shot output exists; no retry')
    run.mkdir();write(run/'freeze.json',freeze)
    def command(label,argv,check=True,timeout=20):
        result=subprocess.run(argv,capture_output=True,text=True,timeout=timeout);commands.append(dict(label=label,argv=argv,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr));write(run/'commands.json',commands)
        if check and result.returncode:raise ValueError(label+' failed; no fallback')
        return result
    result=dict(status='running',blocked_thread_slots=1,remaining_campaign_cases_disabled=29,no_tuning=True,retry_two_loss_4211=False)
    created_volume=False;created_container=False;exported=False
    try:
        command('volume-create',['docker','volume','create',volume]);created_volume=True
        argv=['docker','create','--name',name,'--pull=never','--platform','linux/amd64','--network','none','--read-only','--cap-drop','ALL','--cap-add','SYS_ADMIN','--security-opt','no-new-privileges=true','--mount','type=bind,source='+str(bundle)+',target=/cal,readonly','--mount','type=volume,source='+volume+',target=/out','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=16m','-e','PYTHONDONTWRITEBYTECODE=1','-w','/cal',IMAGE,'python3','/cal/inside.py']
        command('container-create',argv);created_container=True
        inspect=json.loads(command('policy-inspect',['docker','inspect',name]).stdout)[0];write(run/'container-policy.json',inspect)
        host=inspect['HostConfig'];mounts=inspect['Mounts']
        if host['Privileged'] or not host['ReadonlyRootfs'] or host['NetworkMode']!='none' or host['PidMode'] or host['UsernsMode']:raise ValueError('container isolation differs')
        if {x.removeprefix('CAP_') for x in host['CapAdd']}!={'SYS_ADMIN'} or host['CapDrop']!=['ALL'] or not any(x.replace(':','=') in ('no-new-privileges','no-new-privileges=true') for x in host['SecurityOpt']):raise ValueError('capability/NNP scope differs')
        if any('unconfined' in value for value in host['SecurityOpt']):raise ValueError('default seccomp must remain enforced')
        if {(m['Destination'],m['RW']) for m in mounts if m['Destination']!='/tmp'}!={('/cal',False),('/out',True)} or any(m['Destination']=='/tmp' and m['Type']!='tmpfs' for m in mounts):raise ValueError('unexpected mount exposure')
        with (run/'container.log').open('w') as log:
            started=subprocess.run(['docker','start','--attach',name],stdout=log,stderr=subprocess.STDOUT,timeout=25)
        commands.append(dict(label='one-blocked-slot',argv=['docker','start','--attach',name],exit_code=started.returncode));write(run/'commands.json',commands)
        command('export-evidence',['docker','cp',name+':/out/.',str(run)]);exported=True
        command('final-container-state',['docker','inspect',name])
        if started.returncode:raise ValueError('single blocked calibration failed inside container')
        result['assessment']=assess(run);verify();result['status']='passed'
    except Exception as error:result.update(status='failed',error=type(error).__name__+': '+str(error))
    finally:
        if created_container:
            if not exported:
                command('failure-stop',['docker','kill',name],check=False)
                command('failure-export',['docker','cp',name+':/out/.',str(run)],check=False)
            stopped=command('container-remove',['docker','rm','--force',name],check=False)
            if stopped.returncode:result.update(status='failed',cleanup_error='owned container removal failed')
        if created_volume:
            removed=command('volume-remove',['docker','volume','rm',volume],check=False)
            if removed.returncode:result.update(status='failed',cleanup_error='owned volume removal failed')
        write(run/'calibration.json',result);print(json.dumps(dict(status=result['status'],error=result.get('error'),run=str(run.relative_to(ROOT)),remaining_campaign_cases_disabled=29)),flush=True)
    return result


if __name__=='__main__':raise SystemExit(execute()['status']!='passed')
