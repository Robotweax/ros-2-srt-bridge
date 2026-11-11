"""Disabled N4 freeze after fixture compile/static audit; never executes a case."""
import datetime
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from disposition_runtime import matched
from n4_fixture import native_layout
from cases import cases,disabled_ids,completed_ids,SCOPE,PLAN


def main():
    if (HERE/'freeze.json').exists():raise ValueError('N4 preparation already frozen')
    prior=ROOT/'evidence/m3-current-n0-stable-preparation-2026-11-10';f=json.loads((prior/'freeze.json').read_text())
    if source_inventory()!=f['source_sha256'] or any(sha(ROOT/p)!=h for p,h in f['inputs_sha256'].items()):raise ValueError('frozen source/input drift')
    if any(sha(ROOT/p)!=h for p,h in f['reused_native_inputs_sha256'].items()):raise ValueError('native source drift')
    selected=native_layout(ROOT,'socket-disposition');layout=selected['layout']
    for key in ('sdk','ros','runtime_paths','matched_build_sha256','preserved_shutdown_trace'):
        if layout[key]!=f['runtime_layout'][key]:raise ValueError('matched SDK/ROS changed')
    if selected['binding']!=json.loads((HERE/'fixture-binding.json').read_text()):raise ValueError('fixture binding differs')
    link=json.loads((HERE/'link-proof.json').read_text())
    if link['status']!='passed_static_build_link_only' or link['peer_executed'] or link['worker_executed']:raise ValueError('static fixture prerequisite differs')
    if any(sha(ROOT/p)!=h for p,h in link['local_build_artifacts'].items()):raise ValueError('fixture build artifact drift')
    for header,source in link['installed_header_source_matches'].items():
        if sha(ROOT/header)!=sha(ROOT/source):raise ValueError('installed header/source mismatch')
    latest=ROOT/'evidence/m3-current-n0-stable-execution-2026-11-10'
    if json.loads((latest/'gate-report.json').read_text())['status']!='passed_single_current_build_stabilized_N0':raise ValueError('N0 prerequisite missing')
    inputs=dict(f['inputs_sha256']);indexes=dict(f['retained_indexes'])
    for folder in (prior,latest):
        for index in (folder/'public-artifact-hashes.json',folder/'local-artifact-hashes.json'):
            if index.exists():indexes[str(index.relative_to(ROOT))]=sha(index)
    for index,digest in indexes.items():
        if sha(ROOT/index)!=digest:raise ValueError('retained index drift')
        for path,value in json.loads((ROOT/index).read_text()).items():
            if sha(ROOT/path)!=value['sha256']:raise ValueError('retained raw/public drift')
            if not index.endswith('local-artifact-hashes.json'):inputs[path]=value['sha256']
        inputs[index]=digest
    # Earlier fixture/build evidence is also preserved, not rebuilt or relabelled.
    old=ROOT/'evidence/m3-dispatcher-fixture-validation-2026-11-09'
    for path,digest in json.loads((old/'evidence-index.json').read_text()).items():
        if sha(old/path)!=digest:raise ValueError('old fixture public drift')
        inputs[str((old/path).relative_to(ROOT))]=digest
    old_binding=json.loads((old/'fixture-binding.json').read_text())
    for path,digest in old_binding['files'].items():
        if sha(ROOT/path)!=digest:raise ValueError('old fixture build drift')
        inputs[path]=digest
    for path,digest in json.loads((old/'link-proof.json').read_text())['local_build_artifacts'].items():
        if sha(ROOT/path)!=digest:raise ValueError('old fixture compile/link artifact drift')
        inputs[path]=digest
    for value in json.loads((old/'raw-log-manifest.json').read_text()).values():
        if sha(ROOT/value['raw_path'])!=value['raw_sha256']:raise ValueError('old raw build log drift')
        inputs[value['raw_path']]=value['raw_sha256']
    for path,item in json.loads((HERE/'local-build-log-hashes.json').read_text()).items():
        if sha(ROOT/path)!=item['sha256']:raise ValueError('new raw build log drift')
        inputs[path]=item['sha256']
    for name,count in (('unit-tests.log',20),('existing-suite.log',511)):
        text=(HERE/'validation'/name).read_text()
        if 'Ran '+str(count)+' tests' not in text or not text.rstrip().endswith('OK'):raise ValueError('offline tests failed')
    for path in HERE.rglob('*.py'):compile(path.read_text(),str(path),'exec')
    current=json.loads(subprocess.check_output(['docker','version','--format','{{json .Server.Components}}'],text=True))
    if current!=f['runtime_version']:raise ValueError('calibrated runtime drift')
    if subprocess.check_output(['docker','info','--format','{{.Architecture}}'],text=True).strip()!='aarch64':raise ValueError('daemon architecture differs')
    if subprocess.check_output(['docker','image','inspect','--platform','linux/amd64',IMAGE,'--format','{{.Architecture}}'],text=True).strip()!='amd64':raise ValueError('target image differs')
    if subprocess.check_output(['docker','ps','-q'],text=True).strip():raise ValueError('live container remains; no freeze')
    if 'm3-n4-current-fixture-build' in subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines():raise ValueError('build container remains')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');output='.local/current-n4-cohort-'+stamp
    if (ROOT/output).exists():raise ValueError('output exists; no resume')
    write(HERE/'case-plan.json',dict(execution_enabled=False,cases=cases(),disabled_case_ids=disabled_ids(),completed_case_ids_not_reexecuted=completed_ids(),no_automatic_retries=True,stop_first_failed_gate=True))
    inputs.update(selected['runtime_sha256']);inputs.update(link['local_build_artifacts']);inputs[str(PLAN.relative_to(ROOT))]=sha(PLAN)
    for path in [q for q in HERE.rglob('*') if q.is_file() and '__pycache__' not in q.parts]:inputs[str(path.relative_to(ROOT))]=sha(path)
    freeze=dict(schema_version=1,execution_enabled=False,authorization_supplied=False,scope=SCOPE,cases=cases(),disabled_case_ids=disabled_ids(),completed_case_ids_not_reexecuted=completed_ids(),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256=source_inventory(),runtime_layout=layout,candidate_manifest_sha256=layout['calibration_sha256'],native_fixture_binding=selected['binding'],runtime_version=current,target_image=IMAGE,reused_native_inputs_sha256=f['reused_native_inputs_sha256'],retained_indexes=indexes,inputs_sha256=inputs,output_relative=output,prefix='current-n4-'+stamp.lower(),other_unexecuted_cases_disabled=9,completed_cases_excluded=10,no_tuning=True,no_automatic_retries=True,stop_first_failed_gate=True,historical_failures_preserved=True,live_runs=0)
    write(HERE/'freeze.json',freeze)
    write(HERE/'readiness.json',dict(status='current_build_N4_prepared_execution_disabled',freeze_sha256=sha(HERE/'freeze.json'),cases_prepared=19,native_cases=13,ROS_freshness_cases=3,ROS_crash_cases=3,live_runs=0,authorization_file_created=False,offline_tests_passed=20,existing_tests_passed=511,matched_entries=14,preserved_shutdown_entries=13,native_source_inputs_unchanged=87,fixture_bound_files=len(selected['binding']['files']),fixture_compile_and_static_link_passed=True,fixture_or_worker_executed=False,fixture_and_ROS_current_build_runtime_validated=False,other_unexecuted_cases_disabled=9,completed_cases_excluded=10,no_tuning=True,no_automatic_retries=True,stop_first_failed_gate=True))
    write(HERE/'postflight.json',dict(status='prepared_only',frozen_source_inputs_build_chain_provider_native87_unchanged=True,old_fixture_and_evidence_preserved=True,isolated_fixture_only_compiled=True,no_live_case_or_network_experiment=True,no_production_build=True,build_container_removed=True,future_output_absent=True,authorization_absent=True,other_unexecuted_cases_disabled=9,completed_cases_excluded=10,M3_complete=False))
    print(json.dumps(dict(status='prepared_only',freeze_sha256=sha(HERE/'freeze.json'),live_runs=0,cases=19,output_relative=output)))

if __name__=='__main__':main()
