"""Read-only provenance checks and disabled N0 freeze; never launches fixtures."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from cases import cases,disabled_ids,SCOPE
from disposition_runtime import matched


def main():
    if (HERE/'freeze.json').exists():raise ValueError('preparation already frozen')
    prior=ROOT/'evidence/m3-strict-n3-preparation-2026-11-10';f=json.loads((prior/'freeze.json').read_text())
    if source_inventory()!=f['source_sha256']:raise ValueError('frozen source changed')
    if any(sha(ROOT/p)!=h for p,h in f['inputs_sha256'].items()):raise ValueError('previous prepared input drift')
    for name in ('binary-verification.json','disposition_runtime.py','bridge_exec.py','observer_entry.py','observer-seccomp.json','observer-architecture.json','shutdown_observer.py','lifecycle.py','socket_gate.py','stage_gate.py','sidecar.py','emergency_cleanup.py'):
        if sha(HERE/name)!=sha(prior/name):raise ValueError('calibrated component differs: '+name)
    latest=ROOT/'evidence/m3-strict-n3-execution-2026-11-10';gate=json.loads((latest/'gate-report.json').read_text())
    if gate['status']!='passed_fresh_strict_N3_9_of_9':raise ValueError('fresh N3 prerequisite missing')
    indexes=dict(f['retained_indexes']);index=latest/'local-artifact-hashes.json';indexes[str(index.relative_to(ROOT))]=sha(index)
    for path,digest in indexes.items():
        if sha(ROOT/path)!=digest:raise ValueError('retained index drift')
        for item,value in json.loads((ROOT/path).read_text()).items():
            if sha(ROOT/item)!=value['sha256']:raise ValueError('retained raw evidence drift')
    public=json.loads((latest/'public-artifact-hashes.json').read_text())
    if any(sha(ROOT/p)!=v['sha256'] for p,v in public.items()):raise ValueError('fresh N3 public evidence drift')
    layout=matched(ROOT,'socket-disposition')
    if layout['matched_build_sha256']!=f['runtime_layout']['matched_build_sha256']:raise ValueError('frozen matched build differs')
    current=json.loads(subprocess.check_output(['docker','version','--format','{{json .Server.Components}}'],text=True))
    if current!=f['runtime_version']:raise ValueError('runtime changed')
    if subprocess.check_output(['docker','info','--format','{{.Architecture}}'],text=True).strip()!='aarch64':raise ValueError('native daemon differs')
    for platform,image,arch in [('linux/amd64',IMAGE,'amd64'),('linux/arm64','ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617','arm64')]:
        if subprocess.check_output(['docker','image','inspect','--platform',platform,image,'--format','{{.Architecture}}'],text=True).strip()!=arch:raise ValueError('image differs')
    if subprocess.check_output(['docker','ps','-q'],text=True).strip():raise ValueError('live container remains')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    prefix='current-n0-'+stamp.lower();bundle=ROOT/'.local'/('current-n0-observer-bundle-'+stamp);bundle.mkdir()
    helpers={name:HERE/name for name in ('observer_entry.py','observer-seccomp.json','observer-architecture.json','shutdown_observer.py')};helpers['m3_observer_filtering.py']=ROOT/'tools/m3_observer_filtering.py'
    for name,path in helpers.items():shutil.copyfile(path,bundle/name);(bundle/name).chmod(0o444)
    bundle.chmod(0o555)
    completed=[x['id'] for x in f['cases']]
    write(HERE/'case-plan.json',dict(execution_enabled=False,cases=cases(),disabled_case_ids=disabled_ids(),completed_N3_case_ids_not_reexecuted=completed,no_automatic_retries=True,stop_first_failed_gate=True))
    inputs={**f['inputs_sha256'],**{p:v['sha256'] for p,v in public.items()}}
    inputs[str(latest.relative_to(ROOT)/'public-artifact-hashes.json')]=sha(latest/'public-artifact-hashes.json')
    for path in [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+list(bundle.iterdir()):inputs[str(path.relative_to(ROOT))]=sha(path)
    freeze=dict(schema_version=1,execution_enabled=False,authorization_supplied=False,scope=SCOPE,cases=cases(),disabled_case_ids=disabled_ids(),completed_N3_case_ids_not_reexecuted=completed,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256=source_inventory(),runtime_layout=layout,runtime_version=current,target_image=IMAGE,reused_native_inputs_sha256=f['reused_native_inputs_sha256'],retained_indexes=indexes,inputs_sha256=inputs,bundle_relative=str(bundle.relative_to(ROOT)),output_relative='.local/current-n0-coverage-'+stamp,prefix=prefix,remaining_campaign_cases_disabled=28,no_automatic_retries=True,stop_first_failed_gate=True,historical_failures_preserved=True,no_tuning=True,live_runs=0)
    write(HERE/'freeze.json',freeze)
    write(HERE/'readiness.json',dict(status='offline_prepared_execution_disabled',live_runs=0,authorization_file_created=False,existing_python_tests_passed=511,targeted_offline_tests_passed=8,matched_entries=14,preserved_shutdown_entries=13,reused_native_inputs_verified=len(f['reused_native_inputs_sha256']),fresh_strict_N3_precedent='9/9 passed; no replacement credit for N0',combined_shutdown_adapter_live_calibrated=False,freeze_sha256=sha(HERE/'freeze.json'),remaining_campaign_cases_disabled=28,all29_previously_unexecuted_cases_still_unexecuted=True,no_tuning=True,no_automatic_retries=True))
    write(HERE/'postflight.json',dict(status='prepared_only',source_matches_prior_freeze=True,prior_inputs_verified=True,prior_raw_and_public_evidence_verified=True,matched_binaries_unchanged=True,no_native_build=True,no_live_fixture=True,no_docker_mutation=True,execution_enabled=False,live_runs=0))
    print(json.dumps(dict(status='prepared_only',freeze_sha256=sha(HERE/'freeze.json'),execution_enabled=False,live_runs=0)))

if __name__=='__main__':main()
