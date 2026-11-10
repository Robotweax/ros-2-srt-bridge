"""Fresh seven-case sequential cohort; exact grant, stop first failed gate."""
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
from campaign_binding import load
plan=load('plan');cases=load('cases');integrity=load('integrity')
def fresh_output(path):
    if path.exists():raise ValueError('output exists; no resume or retry')
def verify(freeze):
    if freeze['scope']!=cases.SCOPE or freeze['execution_enabled'] is not False or freeze['authorization_supplied'] is not False or freeze['cases']!=cases.cases() or freeze['disabled_case_ids']!=cases.disabled_ids() or freeze['completed_case_ids_not_reexecuted']!=cases.completed_ids() or freeze['historical_LONG_case_ids_excluded']!=cases.historical_case_ids_excluded():raise ValueError('exact remaining seven scope differs')
    integrity.verify_files(freeze)
    def query(args):return subprocess.check_output(args,text=True,timeout=20).strip()
    if json.loads(query(['docker','version','--format','{{json .Server.Components}}']))!=freeze['runtime_version'] or query(['docker','info','--format','{{.Architecture}}'])!=freeze['daemon_architecture']:raise ValueError('runtime drift')
    if query(['docker','ps','-q']):raise ValueError('live containers remain')
    for platform,image,arch in [('linux/amd64',IMAGE,'amd64'),('linux/arm64',freeze['observer_image'],'arm64')]:
        if query(['docker','image','inspect','--platform',platform,image,'--format','{{.Architecture}}'])!=arch:raise ValueError('image architecture differs')
    for argv in (['docker','ps','-a','--format','{{.Names}}'],['docker','volume','ls','--format','{{.Name}}']):
        if any(n.startswith(freeze['prefix']) for n in query(argv).splitlines()):raise ValueError('owned prefix exists')
def sequence(produce,assess,record):return evaluate_sequence(cases.cases(),produce,assess,record)
def case_process(argv,log,slot,popen=subprocess.Popen):
    process=popen(argv,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,start_new_session=True)
    try:
        code=process.wait(timeout=slot['source_seconds']+240)
        if code:raise ValueError('case workload failed; retained host log')
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=2)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.wait(timeout=5)
        raise ValueError('case host watchdog exceeded; no retry')
def postflight_case(target,freeze,prefix):
    net=json.loads((target/'network.json').read_text())
    def names(args):return set(subprocess.check_output(args,text=True,timeout=20).splitlines())
    containers=names(['docker','ps','-a','--format','{{.Names}}']);networks=names(['docker','network','ls','--format','{{.Name}}']);volumes=names(['docker','volume','ls','--format','{{.Name}}'])
    if (set(net['containers'].values())|{prefix+'-observer'})&containers or net['network'] in networks or prefix+'-observer-output' in volumes or(target/'passphrase').exists():raise ValueError('case owned cleanup incomplete')
    verify(freeze);write(target/'postflight.json',dict(frozen_integrity_passed=True,owned_objects_absent=True,credential_deleted=True))
def execute(grant_path):
    freeze=json.loads((HERE/'freeze.json').read_text());grant=json.loads(grant_path.read_text());digest=sha(grant_path);plan.authorize(grant,sha(HERE/'freeze.json'))
    out=ROOT/freeze['output_relative'];fresh_output(out);verify(freeze);out.mkdir();write(out/'freeze.json',freeze);write(out/'authorization.json',grant)
    def produce(slot):
        if sha(grant_path)!=digest:raise ValueError('grant changed')
        verify(freeze);target=out/slot['id'];fresh_output(target);prefix=freeze['prefix']+'-'+slot['id'].lower();print('START '+slot['id'],flush=True)
        try:
            with (out/(slot['id']+'-host.log')).open('x') as log:case_process([sys.executable,str(HERE/'workload_entry.py'),str(grant_path.resolve()),slot['id']],log,slot)
        except BaseException:
            load('emergency_cleanup').cleanup(target,prefix,subprocess.run);raise
        return dict(run=str(target.relative_to(ROOT)),prefix=prefix)
    def assess(slot,produced):
        target=ROOT/produced['run'];proof=dict(status='failed')
        try:
            result=json.loads((target/'run.json').read_text())
            if result['source_sha256']!=freeze['source_sha256'] or result['runtime_layout']!=freeze['runtime_layout']:raise ValueError('case source/runtime provenance differs')
            proof=load('assess').assess(target,result,slot)
        except Exception as error:proof['error']=str(error)
        try:postflight_case(target,freeze,produced['prefix'])
        except Exception as error:proof.update(status='failed',postflight_error=str(error))
        write(target/'strict-assessment.json',proof);print(proof['status'].upper()+' '+slot['id'],flush=True);return proof
    def record(report):
        report.update(scope=cases.SCOPE,freeze_sha256=sha(HERE/'freeze.json'),disabled_case_ids=cases.disabled_ids(),completed_case_ids_not_reexecuted=cases.completed_ids(),historical_LONG_case_ids_excluded=cases.historical_case_ids_excluded(),original_N1_2903_failure_preserved=True,no_tuning=True,no_retries=True,stop_first_failed_gate=True,M3_complete=False);write(out/'cohort.json',report)
    report=sequence(produce,assess,record)
    try:verify(freeze);write(out/'postflight.json',dict(frozen_integrity_passed=True,quiescent=True,owned_prefix_absent=True))
    except Exception as error:report.update(status='failed',postflight_error=str(error));record(report)
    print('FINAL '+report['status'],flush=True);return report
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--authorization',required=True,type=Path);args=parser.parse_args();return int(execute(args.authorization)['status']!='passed')
if __name__=='__main__':raise SystemExit(main())
