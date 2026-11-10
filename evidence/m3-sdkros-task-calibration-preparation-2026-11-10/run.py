"""Exactly one readiness check and one bounded SDKROS diagnostic; no campaigns."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import IMAGE,write,sha
from m3_closure_assessor import evaluate_sequence
from m3_observer_filtering import require_role
from campaign_binding import load
plan=load('plan');integrity=load('integrity')
STAGES=[dict(id='observer-readiness'),dict(id='SDKROS-fixture')]

def fresh_output(path):
    if path.exists():raise ValueError('output exists; no resume or retry')
def verify(freeze):
    if freeze['scope']!=plan.SCOPE or freeze['execution_enabled'] is not False or freeze['authorization_supplied'] is not False or freeze['disabled_case_ids']!=plan.disabled_ids() or freeze['remaining_case_ids_disabled']!=plan.remaining_ids() or freeze['readiness_checks']!=1 or freeze['SDKROS_fixture_limit']!=1 or freeze['slot']!=load('cases').cases()[0]:raise ValueError('SDKROS calibration scope differs')
    integrity.verify_files(freeze)
    def query(args):return subprocess.check_output(args,text=True,timeout=20).strip()
    if json.loads(query(['docker','version','--format','{{json .Server.Components}}']))!=freeze['runtime_version'] or query(['docker','info','--format','{{.Architecture}}'])!=freeze['daemon_architecture']:raise ValueError('runtime drift')
    if query(['docker','ps','-q']):raise ValueError('live containers remain')
    for platform,image,arch in [('linux/amd64',IMAGE,'amd64'),('linux/arm64',freeze['observer_image'],'arm64')]:
        if query(['docker','image','inspect','--platform',platform,image,'--format','{{.Architecture}}'])!=arch:raise ValueError('image architecture differs')
    for argv in (['docker','ps','-a','--format','{{.Names}}'],['docker','volume','ls','--format','{{.Name}}']):
        if any(n.startswith(freeze['prefix']) for n in query(argv).splitlines()):raise ValueError('owned prefix exists')
def sequence(readiness,fixture,record):
    callbacks={'observer-readiness':readiness,'SDKROS-fixture':fixture}
    return evaluate_sequence(STAGES,lambda s:callbacks[s['id']](),lambda s,r:dict(status='passed',proof=r),record)
def fixture_process(argv,log,popen=subprocess.Popen):
    process=popen(argv,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,start_new_session=True)
    try:
        code=process.wait(timeout=240)
        if code:raise ValueError('SDKROS workload failed; retained fixture log')
    except subprocess.TimeoutExpired:
        # Only this owned host process group; fixture is already failed.
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=2)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
        raise ValueError('SDKROS fixture exceeded 240s host watchdog; no retry')
def postflight_fixture(target,freeze,command):
    net=json.loads((target/'network.json').read_text());prefix=freeze['prefix']+'-sdkros'
    def names(args):return set(command('postflight-inventory',args).stdout.splitlines())
    containers=names(['docker','ps','-a','--format','{{.Names}}']);networks=names(['docker','network','ls','--format','{{.Name}}']);volumes=names(['docker','volume','ls','--format','{{.Name}}'])
    if (set(net['containers'].values())|{prefix+'-observer'})&containers or net['network'] in networks or prefix+'-observer-output' in volumes or (target/'passphrase').exists():raise ValueError('SDKROS owned cleanup incomplete')
    write(target/'calibration-postflight.json',dict(owned_objects_absent=True,credential_deleted=True))
def execute(grant_path):
    freeze=json.loads((HERE/'freeze.json').read_text());grant=json.loads(grant_path.read_text());grant_sha=sha(grant_path);plan.authorize(grant,sha(HERE/'freeze.json'))
    out=ROOT/freeze['output_relative'];fresh_output(out);verify(freeze);out.mkdir();write(out/'freeze.json',freeze);write(out/'authorization.json',grant);commands=[]
    def command(label,args,check=True,timeout=20):
        r=subprocess.run(args,capture_output=True,text=True,timeout=timeout);commands.append(dict(label=label,argv=args,exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr));write(out/'commands.json',commands)
        if check and r.returncode:raise ValueError(label+' failed; inspect retained OCI/runtime diagnostics')
        return r
    def stage_verify():
        if sha(grant_path)!=grant_sha:raise ValueError('grant changed')
        integrity.verify_files(freeze)
    def readiness():
        stage_verify();name=freeze['prefix']+'-ready';volume=name+'-out';created=volume_created=False;errors=[]
        try:
            volume_created=True;command('create-readiness-volume',['docker','volume','create',volume]);created=True
            # Reuse the integrated sidecar's exact isolation/entry/activation argv,
            # replacing only its target-PID option with a target-free self-check.
            sidecar=load('sidecar').Sidecar(out,ROOT/freeze['bundle_relative'],freeze['prefix']);args=sidecar.create_argv('unused')
            del args[args.index('--pid'):args.index('--pid')+2];args[args.index('--name')+1]=name
            mount=args.index('type=volume,source='+sidecar.volume+',target=/out');args[mount]='type=volume,source='+volume+',target=/out';args[-1]='--self-check'
            command('create-native-readiness',args)
            inspected=json.loads(command('inspect-readiness-policy',['docker','inspect',name]).stdout)[0];write(out/'readiness-policy.json',inspected);h=inspected['HostConfig'];load('sidecar').validate_isolation(h)
            if h['PidMode'] or not any(s.replace(':','=') in ('no-new-privileges','no-new-privileges=true') for s in h['SecurityOpt']):raise ValueError('readiness PID/NNP policy differs')
            profiles=[s.split('=',1)[1] for s in h['SecurityOpt'] if s.startswith('seccomp=')]
            if len(profiles)!=1 or json.loads(profiles[0])!=json.loads((HERE/'observer-seccomp.json').read_text()) or {(m['Destination'],m['RW']) for m in inspected['Mounts'] if m['Destination']!='/tmp'}!={('/cal',False),('/out',True)}:raise ValueError('readiness filter/mount exposure differs')
            result=command('one-native-readiness',['docker','start','--attach',name],check=False)
            state=json.loads(command('readiness-final-state',['docker','inspect',name]).stdout)[0]['State'];destination=out/'readiness';destination.mkdir();command('export-readiness',['docker','cp',name+':/out/.',str(destination)])
            if result.returncode or state['Running'] or state['ExitCode'] or state['Error']:raise ValueError('native readiness failed')
            events=[json.loads(x) for x in (destination/'observer-exec.jsonl').read_text().splitlines()]
            if [e['kind'] for e in events]!=['entry','preexec_verified','self_check_passed'] or events[1]['collector_sha256']!=plan.CANDIDATE_SHA or events[1]['task_visibility'] is not True:raise ValueError('native readiness collector activation differs')
            require_role(events[1]['permissions'],1<<21)
        finally:
            if created:
                for label,args in [('readiness-logs',['docker','logs',name]),('remove-readiness',['docker','rm','--force',name])]:
                    try:command(label,args)
                    except BaseException as e:errors.append(str(e))
            if volume_created:
                try:command('remove-readiness-volume',['docker','volume','rm',volume])
                except BaseException as e:errors.append(str(e))
            if errors:raise ValueError('readiness cleanup failed: '+str(errors))
        return dict(status='passed',SDKROS_launched=False)
    def fixture():
        stage_verify();verify(freeze);target=out/'fixture';prefix=freeze['prefix']+'-sdkros';fresh_output(target)
        try:
            with (out/'fixture-host.log').open('x') as log:fixture_process([sys.executable,str(HERE/'workload_entry.py'),str(grant_path.resolve())],log)
            record=json.loads((target/'run.json').read_text())
            if record['source_sha256']!=freeze['source_sha256'] or record['runtime_layout']!=freeze['runtime_layout']:raise ValueError('SDKROS fixture provenance differs')
            proof=load('assess').assess(target,record,freeze['slot']);write(out/'SDKROS-assessment.json',proof)
            if proof['status']!='passed':raise ValueError('integrated SDKROS assessment failed: '+str(proof.get('error')))
            postflight_fixture(target,freeze,command);stage_verify();return proof
        except BaseException:
            load('emergency_cleanup').cleanup(target,prefix,lambda args,**kwargs:command('SDKROS-emergency-cleanup',args,check=False,timeout=15))
            raise
    report=dict(status='failed',scope=plan.SCOPE)
    try:report['stages']=sequence(readiness,fixture,lambda r:write(out/'stages.json',r));report['status']=report['stages']['status']
    except BaseException as error:report['error']=dict(type=type(error).__name__,message=str(error))
    finally:
        try:verify(freeze);write(out/'postflight.json',dict(frozen_integrity_verified=True,quiescent=True,owned_prefix_absent=True))
        except BaseException as error:report.update(status='failed',postflight_error=str(error))
        report.update(disabled_case_ids=plan.disabled_ids(),remaining_case_ids_disabled=plan.remaining_ids(),N1_2903_rerun=False,no_tuning=True,no_retries=True,stop_first_failed_gate=True,M3_complete=False);write(out/'calibration.json',report)
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--authorization',required=True,type=Path);args=parser.parse_args();return int(execute(args.authorization)['status']!='passed')
if __name__=='__main__':raise SystemExit(main())
