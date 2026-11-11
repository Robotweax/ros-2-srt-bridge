"""Prepare one disabled fresh N1/2903 qualification; read-only runtime queries only."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import source_inventory,IMAGE,sha,write
from m3_observer_filtering import profile
from campaign_binding import load
NATIVE='ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617'
INTEGRATED=ROOT/'evidence/m3-sdkros-task-calibration-preparation-2026-11-10'
PRIOR=ROOT/'evidence/m3-current-remaining-preparation-2026-11-10'
SEVEN=ROOT/'evidence/m3-current-remaining-execution-2026-11-11'
ACCEPTANCE=ROOT/'evidence/m3-acceptance-consolidation-2026-11-11'
EXEC=ROOT/'evidence/m3-current-long-execution-2026-11-10'
def campaign_state():
    cases=load('cases');cohort=json.loads((EXEC/'cohort.json').read_text())
    if [r['status'] for r in cohort['rows']]!=['passed','failed']+['not_executed']*7 or cases.enabled_ids()!=[] or len(cases.disabled_ids())!=37 or len(cases.cases())!=1:raise ValueError('one prepared/37 excluded campaign state differs')
    cases.original_failure_reference()
    latest=json.loads((SEVEN/'gate-report.json').read_text())
    if latest['passed']!=7 or latest['failed']!=0 or latest['not_executed']!=0 or latest['freeze_sha256']!=sha(PRIOR/'freeze.json'):raise ValueError('seven passing prerequisite differs')
    return cohort
def main():
    if (HERE/'freeze.json').exists():raise ValueError('already frozen; no replacement')
    f=json.loads((PRIOR/'freeze.json').read_text());inputs=dict(f['inputs_sha256']);indexes=dict(f['retained_indexes'])
    for folder in (INTEGRATED,PRIOR,ROOT/'evidence/m3-sdkros-task-calibration-execution-2026-11-10',SEVEN,ACCEPTANCE):
        for index in folder.glob('*artifact-hashes.json'):indexes[str(index.relative_to(ROOT))]=sha(index)
    layout=load('disposition_runtime').matched(ROOT,'socket-disposition')
    if source_inventory()!=f['source_sha256'] or layout!=dict(f['runtime_layout'],calibration=layout['calibration']):raise ValueError('source/matched build drift')
    for name,digest in {**inputs,**f['reused_native_inputs_sha256']}.items():
        if sha(ROOT/name)!=digest:raise ValueError('prior input drift: '+name)
    for name,digest in indexes.items():
        if sha(ROOT/name)!=digest:raise ValueError('prior index drift: '+name)
        for path,item in json.loads((ROOT/name).read_text()).items():
            if sha(ROOT/path)!=item['sha256'] or (ROOT/path).stat().st_size!=item['bytes']:raise ValueError('prior artifact drift: '+path)
            if not name.endswith('local-artifact-hashes.json'):inputs[path]=item['sha256']
        inputs[name]=digest
    preserved=['task_assessment.py','lifecycle.py','shutdown_observer.py','observer_entry.py','observer-seccomp.json','observer-architecture.json','scenario.py','bridge_exec.py','launch_assessment.py','launch_readiness.py','launch_records.py','socket_gate.py','stage_gate.py','profile_gate.py']
    for name in preserved:
        if sha(HERE/name)!=sha(INTEGRATED/name):raise ValueError('preserved integration component differs: '+name)
    for name,count in [('preparation-tests.log',27)]:
        text=(HERE/'validation'/name).read_text()
        if f'Ran {count} tests' not in text or not text.rstrip().endswith('OK'):raise ValueError('offline tests not passing: '+name)
    for path in HERE.rglob('*.py'):compile(path.read_text(),str(path),'exec')
    cases=load('cases');plan=load('plan');cohort=campaign_state()
    for row in cohort['rows'][2:]:
        for parent in (EXEC/'cases',ROOT/'.local/current-long-cohort-20261110T152312809927Z'):
            if(parent/row['slot']['id']).exists():raise ValueError('disabled later output exists')
    def query(args):return subprocess.check_output(args,text=True,timeout=20).strip()
    runtime=json.loads(query(['docker','version','--format','{{json .Server.Components}}']));daemon=query(['docker','info','--format','{{.Architecture}}'])
    if runtime!=f['runtime_version'] or daemon!=f['daemon_architecture'] or profile(daemon,'arm64')!=json.loads((HERE/'observer-seccomp.json').read_text()):raise ValueError('runtime/policy drift')
    for platform,image,arch in [('linux/amd64',IMAGE,'amd64'),('linux/arm64',NATIVE,'arm64')]:
        if query(['docker','image','inspect','--platform',platform,image,'--format','{{.Architecture}}'])!=arch:raise ValueError('image architecture differs')
    active=query(['docker','ps','-q']).splitlines();stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');prefix='fresh-n1-2903-'+stamp.lower();output='.local/fresh-n1-2903-qualification-'+stamp
    for argv in (['docker','ps','-a','--format','{{.Names}}'],['docker','volume','ls','--format','{{.Name}}']):
        if any(n.startswith(prefix) for n in query(argv).splitlines()):raise ValueError('prefix exists')
    if (ROOT/output).exists():raise ValueError('future output exists')
    bundle=ROOT/'.local'/('fresh-n1-2903-observer-bundle-'+stamp);bundle.mkdir()
    for name,path in load('observer_bundle').sources().items():
        shutil.copyfile(path,bundle/name);(bundle/name).chmod(0o444);inputs[str(path.relative_to(ROOT))]=sha(path);inputs[str((bundle/name).relative_to(ROOT))]=sha(bundle/name)
    bundle.chmod(0o555)
    sdk_execution=ROOT/'evidence/m3-sdkros-task-calibration-execution-2026-11-10'
    prerequisite=json.loads((sdk_execution/'gate-report.json').read_text())
    if prerequisite['status']!='passed_bounded_native_SDKROS_calibration_only' or prerequisite['freeze_sha256']!=sha(INTEGRATED/'freeze.json') or prerequisite['SDKROS_fixture_runs']!=1 or prerequisite['driver_exit_code']!=0:raise ValueError('native SDKROS calibration prerequisite differs')
    write(HERE/'case-plan.json',dict(scope=cases.SCOPE,execution_enabled=False,enabled_case_ids=[],prepared_cases=cases.cases(),disabled_case_ids=cases.disabled_ids(),completed_case_ids_not_reexecuted=cases.completed_ids(),historical_LONG_case_ids_excluded=cases.historical_case_ids_excluded(),original_historical_LONG_outcomes={'N1-combined-1701':'passed','N1-combined-2903':'failed'},stage_state={'N0':'disabled','N3':'disabled','N4':'disabled','LONG':'prepared_execution_disabled'},nominal_source_seconds=600,per_case_host_watchdog_seconds={s['id']:s['source_seconds']+240 for s in cases.cases()},original_child_wait_seconds=5,fresh_N1_2903_qualification=True,resume_original_run=False,original_failure_reference=cases.original_failure_reference(),no_tuning=True,no_retries=True,stop_first_failed_gate=True))
    shutil.copyfile(ROOT/'evidence/m3-current-long-preparation-2026-11-10/settings.json',HERE/'settings.json')
    for path in HERE.rglob('*'):
        if path.is_file() and '__pycache__'not in path.parts:inputs[str(path.relative_to(ROOT))]=sha(path)
    freeze=dict(schema_version=1,execution_enabled=False,authorization_supplied=False,scope=cases.SCOPE,cases=cases.cases(),source_commit=query(['git','rev-parse','HEAD']),source_sha256=source_inventory(),inputs_sha256=inputs,retained_indexes=indexes,reused_native_inputs_sha256=f['reused_native_inputs_sha256'],runtime_layout=layout,runtime_version=runtime,daemon_architecture=daemon,target_image=IMAGE,observer_image=NATIVE,bundle_relative=str(bundle.relative_to(ROOT)),output_relative=output,prefix=prefix,task_assessment_binding=load('observer_bundle').binding(),preparation_active_containers=active,execution_requires_quiescent_runtime=True,disabled_case_ids=cases.disabled_ids(),completed_case_ids_not_reexecuted=cases.completed_ids(),historical_LONG_case_ids_excluded=cases.historical_case_ids_excluded(),SDKROS_calibration_prerequisite=dict(freeze_sha256=sha(INTEGRATED/'freeze.json'),gate_report_sha256=sha(sdk_execution/'gate-report.json'),public_index_sha256=sha(sdk_execution/'public-artifact-hashes.json')),fresh_N1_2903_qualification=True,resume_original_run=False,original_failure_reference=cases.original_failure_reference(),seven_case_prerequisite=dict(freeze_sha256=sha(PRIOR/'freeze.json'),gate_report_sha256=sha(SEVEN/'gate-report.json')),acceptance_record_binding=dict(path=str((ACCEPTANCE/'acceptance.json').relative_to(ROOT)),sha256=sha(ACCEPTANCE/'acceptance.json'),public_index_sha256=sha(ACCEPTANCE/'public-artifact-hashes.json')),original_failed_assessment_sha256=sha(EXEC/'cases/N1-combined-2903/strict-assessment.json'),original_cohort_sha256=sha(EXEC/'cohort.json'),no_tuning=True,no_retries=True,stop_first_failed_gate=True,historical_failures_preserved=True,nominal_source_seconds=600,live_runs=0)
    write(HERE/'freeze.json',freeze)
    write(HERE/'readiness.json',dict(status='fresh_N1_2903_600s_prepared_execution_disabled',freeze_sha256=sha(HERE/'freeze.json'),prepared_cases=1,N1_cases=1,N2_cases=0,N5_cases=0,N1_N2_source_seconds=600,N5_source_seconds=300,nominal_source_seconds=600,wall_clock_estimate=False,preparation_tests=27,unchanged_logs_reused=dict(SDKROS_preparation=28,integration=25,assessment=42,existing=511),native_SDKROS_calibration_pass_preserved=True,preparation_active_containers=active,execution_requires_quiescent_runtime=True,authorization_created=False,live_runs=0,disabled_case_ids=cases.disabled_ids(),all_other_campaign_stages_disabled=True))
    write(HERE/'postflight.json',dict(status='prepared_only',source_full_build_native87_and_all_prior_indexes_verified=True,preserved_calibrated_components=preserved,original_profile_settings_unchanged=True,readonly_six_file_bundle_created=True,future_output_absent=True,authorization_absent=True,original_historical_results=dict(passed=1,failed=1,not_executed=7),N1_2903_failure_preserved=True,seven_later_case_directories_still_absent=True,other_campaign_stages_disabled=True,live_runs=0,Docker_mutations=0,builds=0,tuning=False,retries=False,M3_complete=False))
    print(json.dumps(dict(status='prepared_only',freeze_sha256=sha(HERE/'freeze.json'),output_relative=output,bundle_relative=str(bundle.relative_to(ROOT)),prepared_cases=1,nominal_source_seconds=600,preparation_active_containers=active,live_runs=0)))
if __name__=='__main__':main()
