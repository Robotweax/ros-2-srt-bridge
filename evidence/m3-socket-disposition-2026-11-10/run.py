"""Prepared only: execution requires a separate, hash-bound authorization file."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import source_inventory,sha,write
from disposition_runtime import matched
HERE=Path(__file__).resolve().parent
SCOPE='one-N0-1701-10s-operator-bridge-shutdown-diagnostic'


def authorize(value,freeze_sha):
    expected=dict(scope=SCOPE,freeze_sha256=freeze_sha,execute=True,remaining_campaign_cases_disabled=29,retry_two_loss_4211=False,no_tuning=True)
    if value!=expected:raise ValueError('authorization must match exactly this disabled preparation freeze and scope')


def main():
    p=argparse.ArgumentParser();p.add_argument('--authorization',type=Path,required=True);a=p.parse_args()
    freeze=json.loads((HERE/'freeze.json').read_text());authorize(json.loads(a.authorization.read_text()),sha(HERE/'freeze.json'))
    if freeze['execution_enabled'] is not False:raise ValueError('preparation record must remain disabled; separate authorization only')
    if source_inventory()!=freeze['source_sha256'] or matched(ROOT,'socket-disposition')!=freeze['runtime_layout']:raise ValueError('source or matched build drift')
    if any(sha(ROOT/path)!=digest for path,digest in freeze['inputs_sha256'].items()):raise ValueError('prepared inputs drift')
    components=json.loads(subprocess.check_output(['docker','version','--format','{{json .Server.Components}}'],text=True))
    if components!=freeze['runtime_version']:raise ValueError('calibrated runtime version drift')
    if subprocess.check_output(['docker','info','--format','{{.Architecture}}'],text=True).strip()!='aarch64':raise ValueError('calibrated native architecture drift')
    image='ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617'
    if subprocess.check_output(['docker','image','inspect','--platform','linux/arm64',image,'--format','{{.Architecture}}'],text=True).strip()!='arm64':raise ValueError('native observer image drift')
    if subprocess.check_output(['docker','ps','-q'],text=True).strip():raise ValueError('unrelated live containers present')
    out=ROOT/freeze['output_relative']
    if out.exists():raise ValueError('one-shot output already exists; retry refused')
    # Recheck all retained evidence before creating the lab and again afterward.
    def verify():
        if source_inventory()!=freeze['source_sha256'] or matched(ROOT,'socket-disposition')!=freeze['runtime_layout']:raise ValueError('source/build freeze drift')
        if any(sha(ROOT/path)!=digest for path,digest in freeze['inputs_sha256'].items()):raise ValueError('input freeze drift')
        for index,digest in freeze['retained_indexes'].items():
            if sha(ROOT/index)!=digest:raise ValueError('retained index drift')
            for path,item in json.loads((ROOT/index).read_text()).items():
                if sha(ROOT/path)!=item['sha256']:raise ValueError('retained evidence drift')
    verify()
    from workload import run
    result=run(out,capture=True,losses=0,seed=1701,seconds=10,runtime_layout='socket-disposition',shutdown_diagnostics=True,shutdown_stacks=False,shutdown_stack_mode='procfs',bundle=ROOT/freeze['bundle_relative'],prefix=freeze['prefix'])
    # Retain failed child/trace evidence without inferring missing measurement gates.
    from assess import assess
    assessment=assess(out,result)
    try:
        verify()
        network=json.loads((out/'network.json').read_text())
        names=set(network['containers'].values())|{freeze['prefix']+'-observer'}
        containers=set(subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines())
        networks=set(subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines())
        volumes=set(subprocess.check_output(['docker','volume','ls','--format','{{.Name}}'],text=True).splitlines())
        if names&containers or network['network'] in networks or freeze['prefix']+'-observer-output' in volumes:raise ValueError('owned lab/observer objects remain')
        write(out/'postflight.json',dict(frozen_inputs_unchanged=True,matched_build_unchanged=True,retained_evidence_unchanged=True,owned_objects_absent=True))
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as error:assessment.update(status='failed',postflight_error=str(error))
    write(out/'diagnostic-assessment.json',assessment)
    return 0 if assessment['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
