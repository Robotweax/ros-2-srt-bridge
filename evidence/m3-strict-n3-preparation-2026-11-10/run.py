"""Prepared N3-only cohort; cannot launch without a separate exact authorization."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import source_inventory,sha,write
from m3_closure_assessor import evaluate_sequence
from disposition_runtime import matched
from cases import cases,disabled_ids,authorize,SCOPE
HERE=Path(__file__).resolve().parent


def fresh_output(path):
    if path.exists():raise ValueError('cohort output exists; resume/retry/splicing forbidden')


def sequence(produce,assess,record):
    return evaluate_sequence(cases(),produce,assess,record)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--authorization',required=True,type=Path);args=parser.parse_args()
    freeze=json.loads((HERE/'freeze.json').read_text());grant_sha=sha(args.authorization);grant=json.loads(args.authorization.read_text());authorize(grant,sha(HERE/'freeze.json'))
    if freeze['execution_enabled'] is not False or freeze['cases']!=cases() or freeze['disabled_case_ids']!=disabled_ids():raise ValueError('disabled prospective N3 plan differs')
    output=ROOT/freeze['output_relative'];fresh_output(output)
    def verify():
        if sha(args.authorization)!=grant_sha:raise ValueError('authorization changed')
        if source_inventory()!=freeze['source_sha256'] or matched(ROOT,'socket-disposition')!=freeze['runtime_layout']:raise ValueError('source/build drift')
        if any(sha(ROOT/p)!=h for p,h in freeze['inputs_sha256'].items()):raise ValueError('input drift')
        for index,digest in freeze['retained_indexes'].items():
            if sha(ROOT/index)!=digest:raise ValueError('retained index drift')
            if any(sha(ROOT/p)!=v['sha256'] for p,v in json.loads((ROOT/index).read_text()).items()):raise ValueError('retained raw drift')
        if json.loads(subprocess.check_output(['docker','version','--format','{{json .Server.Components}}'],text=True))!=freeze['runtime_version']:raise ValueError('calibrated runtime drift')
        if subprocess.check_output(['docker','info','--format','{{.Architecture}}'],text=True).strip()!='aarch64':raise ValueError('native daemon drift')
        image='ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617'
        if subprocess.check_output(['docker','image','inspect','--platform','linux/arm64',image,'--format','{{.Architecture}}'],text=True).strip()!='arm64':raise ValueError('observer image drift')
        if subprocess.check_output(['docker','ps','-q'],text=True).strip():raise ValueError('live container remains; no next case')
        names=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines()
        volumes=subprocess.check_output(['docker','volume','ls','--format','{{.Name}}'],text=True).splitlines()
        if any(name.startswith(freeze['prefix']) for name in names+volumes):raise ValueError('cohort prefix objects already exist; refuse mutation or next case')
    verify();output.mkdir();write(output/'freeze.json',freeze);write(output/'authorization.json',grant)
    from workload import run
    from assess import assess as assess_case
    def produce(slot):
        verify();target=output/slot['id'];fresh_output(target);print('START '+slot['id'],flush=True)
        prefix=freeze['prefix']+'-'+slot['id'].lower()
        try:
            result=run(target,capture=True,losses=slot['losses'],seed=slot['seed'],seconds=30,runtime_layout='socket-disposition',shutdown_diagnostics=True,shutdown_stacks=False,shutdown_stack_mode='procfs',bundle=ROOT/freeze['bundle_relative'],prefix=prefix)
        except BaseException:
            from emergency_cleanup import cleanup
            cleanup(target,prefix,subprocess.run)
            raise
        return dict(run=str(target.relative_to(ROOT)),status=result['status'],primary_workload_error=result.get('error'))
    def assess(slot,produced):
        target=ROOT/produced['run'];result=json.loads((target/'result.json').read_text());proof=assess_case(target,result,slot)
        # Cleanup/absence/integrity are part of this case, before the next produce.
        try:
            net=json.loads((target/'network.json').read_text());prefix=freeze['prefix']+'-'+slot['id'].lower()
            containers=set(subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines())
            networks=set(subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines())
            volumes=set(subprocess.check_output(['docker','volume','ls','--format','{{.Name}}'],text=True).splitlines())
            if (set(net['containers'].values())|{prefix+'-observer'})&containers or net['network'] in networks or prefix+'-observer-output' in volumes or (target/'passphrase').exists():raise ValueError('case cleanup incomplete')
            verify();write(target/'postflight.json',dict(frozen_source_inputs_and_build_match=True,retained_evidence_unchanged=True,owned_objects_absent=True))
        except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:proof.update(status='failed',postflight_error=str(error))
        write(target/'strict-assessment.json',proof)
        if proof['status']!='passed':raise ValueError('strict case failed: '+str(proof.get('error',proof.get('postflight_error'))))
        print('PASS '+slot['id'],flush=True);return proof
    def record(report):
        report.update(scope=SCOPE,freeze_sha256=sha(HERE/'freeze.json'),disabled_case_ids=disabled_ids(),remaining_campaign_cases_disabled=29,no_automatic_retries=True,no_tuning=True,historical_failures_preserved=True,M3_complete=False)
        write(output/'cohort.json',report)
    result=sequence(produce,assess,record);print('FINAL '+result['status'],flush=True);return 0 if result['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
