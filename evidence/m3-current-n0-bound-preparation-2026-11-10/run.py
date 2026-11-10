"""One N0 case only; a separate exact execution authorization is mandatory."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from m3_closure_assessor import evaluate_sequence
from disposition_runtime import matched
from cases import cases,disabled_ids,authorize,SCOPE,IDENTITY_HELPER_PATH,IDENTITY_HELPER_SHA256
HERE=Path(__file__).resolve().parent
FLAGS=('--skip-build','--monotonic-capture','--command-diagnostics','--provider-diagnostics','--sensor-provider-diagnostics','--start-diagnostics','--sender-diagnostics')

def invocation(out):
    return ['--output',str(out),'--profile','N0','--seed','1701','--seconds','300','--runtime-layout','socket-disposition','--image-reference',IMAGE,*FLAGS]

def fresh_output(path):
    if path.exists():raise ValueError('output exists; no resume or retry')

def sequence(produce,assess,record):
    return evaluate_sequence(cases(),produce,assess,record)

def verify(freeze):
    if freeze['launch_readiness_harness_revision']!='explicit-identity-v1' or freeze['identity_helper_binding']!=dict(path=IDENTITY_HELPER_PATH,sha256=IDENTITY_HELPER_SHA256,module='_robotweax_n0_launch_identity_v1'):raise ValueError('explicit identity binding differs')
    if source_inventory()!=freeze['source_sha256'] or matched(ROOT,'socket-disposition')!=freeze['runtime_layout']:raise ValueError('source/build drift')
    if any(sha(ROOT/p)!=h for p,h in freeze['inputs_sha256'].items()):raise ValueError('frozen input drift')
    for index,digest in freeze['retained_indexes'].items():
        if sha(ROOT/index)!=digest or any(sha(ROOT/p)!=v['sha256'] for p,v in json.loads((ROOT/index).read_text()).items()):raise ValueError('retained evidence drift')
    if json.loads(subprocess.check_output(['docker','version','--format','{{json .Server.Components}}'],text=True))!=freeze['runtime_version']:raise ValueError('runtime drift')
    if subprocess.check_output(['docker','info','--format','{{.Architecture}}'],text=True).strip()!='aarch64':raise ValueError('daemon architecture drift')
    if subprocess.check_output(['docker','image','inspect','--platform','linux/arm64','ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617','--format','{{.Architecture}}'],text=True).strip()!='arm64':raise ValueError('observer image drift')
    if subprocess.check_output(['docker','ps','-q'],text=True).strip():raise ValueError('live containers; no launch')
    for command in (['docker','ps','-a','--format','{{.Names}}'],['docker','volume','ls','--format','{{.Name}}']):
        if any(x.startswith(freeze['prefix']) for x in subprocess.check_output(command,text=True).splitlines()):raise ValueError('owned output exists; no resume/retry')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--authorization',type=Path,required=True);args=parser.parse_args()
    freeze=json.loads((HERE/'freeze.json').read_text());grant=json.loads(args.authorization.read_text());grant_sha=sha(args.authorization)
    authorize(grant,sha(HERE/'freeze.json'))
    if freeze['execution_enabled'] is not False or freeze['cases']!=cases() or freeze['disabled_case_ids']!=disabled_ids():raise ValueError('disabled N0 plan differs')
    out=ROOT/freeze['output_relative'];fresh_output(out);verify(freeze)
    out.mkdir();write(out/'freeze.json',freeze);write(out/'authorization.json',grant)
    def produce(slot):
        if sha(args.authorization)!=grant_sha:raise ValueError('authorization changed')
        verify(freeze);target=out/slot['id'];fresh_output(target)
        from workload import main as run
        try:run(invocation(target),bundle=ROOT/freeze['bundle_relative'],prefix=freeze['prefix'])
        except BaseException:
            from emergency_cleanup import cleanup
            cleanup(target,freeze['prefix'],subprocess.run);raise
        return dict(run=str(target.relative_to(ROOT)))
    def assess(slot,produced):
        from assess import assess as check
        target=ROOT/produced['run'];result=json.loads((target/'run.json').read_text())
        if result['runtime_layout']!=freeze['runtime_layout'] or result['source_sha256']!=freeze['source_sha256']:raise ValueError('case provenance drift')
        proof=check(target,result,slot)
        try:
            net=json.loads((target/'network.json').read_text());prefix=freeze['prefix']
            containers=set(subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines())
            networks=set(subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines())
            volumes=set(subprocess.check_output(['docker','volume','ls','--format','{{.Name}}'],text=True).splitlines())
            if (set(net['containers'].values())|{prefix+'-observer'})&containers or net['network'] in networks or prefix+'-observer-output' in volumes or (target/'passphrase').exists():raise ValueError('owned cleanup incomplete')
            verify(freeze);write(target/'postflight.json',dict(frozen_integrity_passed=True,owned_objects_absent=True))
        except Exception as error:proof.update(status='failed',postflight_error=str(error))
        write(target/'strict-assessment.json',proof);return proof
    def record(report):
        report.update(scope=SCOPE,freeze_sha256=sha(HERE/'freeze.json'),disabled_case_ids=disabled_ids(),remaining_campaign_cases_disabled=28,no_automatic_retries=True,no_tuning=True,historical_failures_preserved=True,M3_complete=False)
        write(out/'cohort.json',report)
    result=sequence(produce,assess,record);return int(result['status']!='passed')

if __name__=='__main__':raise SystemExit(main())
