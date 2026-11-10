"""Exact nine-case dispatcher, separate grant, no resume/retry or other stages."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from m3_closure_assessor import evaluate_sequence
from disposition_runtime import matched
from cases import cases,disabled_ids,completed_ids,authorize,SCOPE,IDENTITY_HELPER_PATH,IDENTITY_HELPER_SHA256,LIFECYCLE_ASSESSMENT_PATH,LIFECYCLE_ASSESSMENT_SHA256
FLAGS=('--skip-build','--monotonic-capture','--command-diagnostics','--provider-diagnostics','--sensor-provider-diagnostics','--start-diagnostics','--sender-diagnostics')

def invocation(slot,out):
    if slot not in cases():raise ValueError('only exact nine declared settings')
    return ['--output',str(out),'--profile',slot['profile'],'--seed',str(slot['seed']),'--seconds',str(slot['source_seconds']),'--runtime-layout','socket-disposition','--image-reference',IMAGE,*FLAGS]
def fresh_output(path):
    if path.exists():raise ValueError('output exists; no resume or retry')
def sequence(produce,assess,record):return evaluate_sequence(cases(),produce,assess,record)
def case_prefix(freeze,slot):
    if slot not in cases():raise ValueError('case prefix scope differs')
    return freeze['prefix']+'-'+slot['id'].lower()
def verify(freeze):
    if freeze['lifecycle_assessment_binding']!=dict(path=LIFECYCLE_ASSESSMENT_PATH,sha256=LIFECYCLE_ASSESSMENT_SHA256) or freeze['identity_helper_binding']!=dict(path=IDENTITY_HELPER_PATH,sha256=IDENTITY_HELPER_SHA256,module='_robotweax_n0_launch_identity_v1') or freeze['launch_readiness_harness_revision']!='stabilized-lifecycle-v1':raise ValueError('lifecycle/identity binding differs')
    if source_inventory()!=freeze['source_sha256'] or matched(ROOT,'socket-disposition')!=freeze['runtime_layout']:raise ValueError('source/build drift')
    if any(sha(ROOT/p)!=h for p,h in freeze['inputs_sha256'].items()):raise ValueError('frozen input drift')
    for index,digest in freeze['retained_indexes'].items():
        if sha(ROOT/index)!=digest or any(sha(ROOT/p)!=v['sha256'] for p,v in json.loads((ROOT/index).read_text()).items()):raise ValueError('retained evidence drift')
    if json.loads(subprocess.check_output(['docker','version','--format','{{json .Server.Components}}'],text=True))!=freeze['runtime_version']:raise ValueError('runtime drift')
    if subprocess.check_output(['docker','info','--format','{{.Architecture}}'],text=True).strip()!='aarch64':raise ValueError('daemon architecture drift')
    for platform,image,arch in [('linux/amd64',IMAGE,'amd64'),('linux/arm64',freeze['observer_image'],'arm64')]:
        if subprocess.check_output(['docker','image','inspect','--platform',platform,image,'--format','{{.Architecture}}'],text=True).strip()!=arch:raise ValueError('image architecture drift')
    if subprocess.check_output(['docker','ps','-q'],text=True).strip():raise ValueError('live container remains')
    for argv in (['docker','ps','-a','--format','{{.Names}}'],['docker','network','ls','--format','{{.Name}}'],['docker','volume','ls','--format','{{.Name}}']):
        if any(x.startswith(freeze['prefix']) for x in subprocess.check_output(argv,text=True).splitlines()):raise ValueError('owned prefix remains')
def postflight(target,freeze,prefix):
    net=json.loads((target/'network.json').read_text())
    containers=set(subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines())
    networks=set(subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines())
    volumes=set(subprocess.check_output(['docker','volume','ls','--format','{{.Name}}'],text=True).splitlines())
    if (set(net['containers'].values())|{prefix+'-observer'})&containers or net['network'] in networks or prefix+'-observer-output' in volumes or (target/'passphrase').exists():raise ValueError('owned cleanup incomplete')
    verify(freeze);write(target/'postflight.json',dict(frozen_integrity_passed=True,owned_objects_absent=True,credential_deleted=True))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--authorization',required=True,type=Path);args=parser.parse_args()
    freeze=json.loads((HERE/'freeze.json').read_text());grant=json.loads(args.authorization.read_text());digest=sha(args.authorization)
    authorize(grant,sha(HERE/'freeze.json'))
    if freeze['execution_enabled'] is not False or freeze['cases']!=cases() or freeze['disabled_case_ids']!=disabled_ids() or freeze['completed_case_ids_not_reexecuted']!=completed_ids():raise ValueError('disabled nine-case scope differs')
    out=ROOT/freeze['output_relative'];fresh_output(out);verify(freeze);out.mkdir();write(out/'freeze.json',freeze);write(out/'authorization.json',grant)
    def produce(slot):
        if sha(args.authorization)!=digest:raise ValueError('grant changed')
        verify(freeze);target=out/slot['id'];fresh_output(target);prefix=case_prefix(freeze,slot)
        print('START '+slot['id'],flush=True)
        from workload import main as workload
        try:workload(invocation(slot,target),bundle=ROOT/freeze['bundle_relative'],prefix=prefix)
        except BaseException:
            from emergency_cleanup import cleanup
            cleanup(target,prefix,subprocess.run);raise
        return dict(run=str(target.relative_to(ROOT)),prefix=prefix)
    def assess(slot,produced):
        target=ROOT/produced['run'];proof=dict(status='failed')
        try:
            from assess import assess as check
            result=json.loads((target/'run.json').read_text())
            if result['runtime_layout']!=freeze['runtime_layout'] or result['source_sha256']!=freeze['source_sha256']:raise ValueError('case provenance differs')
            proof=check(target,result,slot)
        except Exception as error:proof['error']=str(error)
        try:postflight(target,freeze,produced['prefix'])
        except Exception as error:proof.update(status='failed',postflight_error=str(error))
        write(target/'strict-assessment.json',proof);print(proof['status'].upper()+' '+slot['id'],flush=True);return proof
    def record(report):
        report.update(scope=SCOPE,freeze_sha256=sha(HERE/'freeze.json'),disabled_case_ids=disabled_ids(),completed_case_ids_not_reexecuted=completed_ids(),completed_campaign_cases_excluded=29,no_tuning=True,no_automatic_retries=True,stop_first_failed_gate=True,historical_failures_preserved=True,M3_complete=False)
        write(out/'cohort.json',report)
    result=sequence(produce,assess,record);print('FINAL '+result['status'],flush=True);return int(result['status']!='passed')
if __name__=='__main__':raise SystemExit(main())
