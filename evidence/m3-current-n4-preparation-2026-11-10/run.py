"""Exact sequential19-case N4 dispatcher; separate grant required, no batch/overrides."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory
from m3_closure_assessor import evaluate_sequence
from disposition_runtime import matched
from n4_fixture import native_layout
from cases import cases,disabled_ids,completed_ids,authorize,invocation,SCOPE


def fresh_output(path):
    if path.exists():raise ValueError('output exists; no resume or automatic retry')

def sequence(produce,assess,record):return evaluate_sequence(cases(),produce,assess,record)

def verify(freeze):
    if source_inventory()!=freeze['source_sha256'] or matched(ROOT,'socket-disposition')!=freeze['runtime_layout']:raise ValueError('source/build drift')
    if native_layout(ROOT,'socket-disposition')['binding']!=freeze['native_fixture_binding']:raise ValueError('native fixture binding drift')
    if any(sha(ROOT/p)!=h for p,h in freeze['inputs_sha256'].items()):raise ValueError('frozen input drift')
    for index,digest in freeze['retained_indexes'].items():
        if sha(ROOT/index)!=digest or any(sha(ROOT/p)!=v['sha256'] for p,v in json.loads((ROOT/index).read_text()).items()):raise ValueError('retained evidence drift')
    if json.loads(subprocess.check_output(['docker','version','--format','{{json .Server.Components}}'],text=True))!=freeze['runtime_version']:raise ValueError('runtime drift')
    if subprocess.check_output(['docker','ps','-q'],text=True).strip():raise ValueError('live container remains; no next case')


def dispatch(slot,target):
    spec=invocation(slot)
    if spec['adapter']=='native':from native_adapter import run_case
    else:from ros_adapter import run_case
    return run_case(target,**spec['kwargs'])


def postflight(target,freeze):
    net=json.loads((target/'network.json').read_text())
    names=set(subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines())
    networks=set(subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines())
    if set(net['containers'].values())&names or net['network'] in networks or (target/'passphrase').exists():raise ValueError('owned cleanup incomplete')
    verify(freeze)
    write(target/'postflight.json',dict(source_input_build_fixture_and_retained_hashes_verified=True,owned_objects_absent=True,credential_deleted=True))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--authorization',required=True,type=Path);args=parser.parse_args()
    freeze=json.loads((HERE/'freeze.json').read_text());grant=json.loads(args.authorization.read_text());grant_sha=sha(args.authorization)
    authorize(grant,sha(HERE/'freeze.json'))
    if freeze['execution_enabled'] is not False or freeze['cases']!=cases() or freeze['disabled_case_ids']!=disabled_ids() or freeze['completed_case_ids_not_reexecuted']!=completed_ids():raise ValueError('disabled N4 scope differs')
    out=ROOT/freeze['output_relative'];fresh_output(out);verify(freeze);out.mkdir();write(out/'freeze.json',freeze);write(out/'authorization.json',grant)
    def produce(slot):
        if sha(args.authorization)!=grant_sha:raise ValueError('grant changed')
        verify(freeze);target=out/slot['id'];fresh_output(target);print('START '+slot['id'],flush=True)
        try:result=dispatch(slot,target)
        except BaseException:
            from emergency_cleanup import cleanup
            cleanup(target,subprocess.run);raise
        return dict(run=str(target.relative_to(ROOT)),inner_status=result['status'],error=result.get('error'))
    def assess(slot,produced):
        from assess import assess_case
        target=ROOT/produced['run'];proof=dict(status='failed')
        try:proof=assess_case(target,slot,freeze)
        except Exception as error:proof['error']=str(error)
        try:postflight(target,freeze)
        except Exception as error:proof.update(status='failed',postflight_error=str(error))
        write(target/'strict-assessment.json',proof);print(proof['status'].upper()+' '+slot['id'],flush=True);return proof
    def record(report):
        report.update(scope=SCOPE,freeze_sha256=sha(HERE/'freeze.json'),disabled_case_ids=disabled_ids(),completed_case_ids_not_reexecuted=completed_ids(),other_unexecuted_cases_disabled=9,no_tuning=True,no_automatic_retries=True,stop_first_failed_gate=True,historical_failures_preserved=True,M3_complete=False)
        write(out/'cohort.json',report)
    result=sequence(produce,assess,record);print('FINAL '+result['status'],flush=True);return int(result['status']!='passed')

if __name__=='__main__':raise SystemExit(main())
