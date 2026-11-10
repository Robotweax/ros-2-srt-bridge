"""Prepare one disabled native SDKROS calibration; read-only runtime queries only."""
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
INTEGRATED=ROOT/'evidence/m3-campaign-task-assessment-integration-2026-11-10'
PRIOR=ROOT/'evidence/m3-task-post-sigint-calibration-preparation-2026-11-10'
EXEC=ROOT/'evidence/m3-current-long-execution-2026-11-10'
def main():
    if (HERE/'freeze.json').exists():raise ValueError('already frozen; no replacement')
    f=json.loads((PRIOR/'freeze.json').read_text());inputs=dict(f['inputs_sha256']);indexes=dict(f['retained_indexes'])
    indexes.update(json.loads((INTEGRATED/'verification.json').read_text())['verified_retained_indexes'])
    for folder in (INTEGRATED,PRIOR,ROOT/'evidence/m3-task-post-sigint-calibration-execution-2026-11-10'):
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
    for name,count in [('preparation-tests.log',28),('integration-tests.log',25),('assessment-tests.log',42),('existing-suite.log',511)]:
        text=(HERE/'validation'/name).read_text()
        if f'Ran {count} tests' not in text or not text.rstrip().endswith('OK'):raise ValueError('offline tests not passing: '+name)
    for path in HERE.rglob('*.py'):compile(path.read_text(),str(path),'exec')
    cases=load('cases');plan=load('plan');cohort=json.loads((EXEC/'cohort.json').read_text())
    if [r['status'] for r in cohort['rows']]!=['passed','failed']+['not_executed']*7 or cases.enabled_ids()!=[] or len(cases.disabled_ids())!=38:raise ValueError('campaign state differs')
    for row in cohort['rows'][2:]:
        for parent in (EXEC/'cases',ROOT/'.local/current-long-cohort-20261110T152312809927Z'):
            if(parent/row['slot']['id']).exists():raise ValueError('disabled later output exists')
    def query(args):return subprocess.check_output(args,text=True,timeout=20).strip()
    runtime=json.loads(query(['docker','version','--format','{{json .Server.Components}}']));daemon=query(['docker','info','--format','{{.Architecture}}'])
    if runtime!=f['runtime_version'] or daemon!=f['daemon_architecture'] or profile(daemon,'arm64')!=json.loads((HERE/'observer-seccomp.json').read_text()):raise ValueError('runtime/policy drift')
    for platform,image,arch in [('linux/amd64',IMAGE,'amd64'),('linux/arm64',NATIVE,'arm64')]:
        if query(['docker','image','inspect','--platform',platform,image,'--format','{{.Architecture}}'])!=arch:raise ValueError('image architecture differs')
    active=query(['docker','ps','-q']).splitlines();stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');prefix='sdkros-cal-'+stamp.lower();output='.local/sdkros-task-calibration-'+stamp
    for argv in (['docker','ps','-a','--format','{{.Names}}'],['docker','volume','ls','--format','{{.Name}}']):
        if any(n.startswith(prefix) for n in query(argv).splitlines()):raise ValueError('prefix exists')
    if (ROOT/output).exists():raise ValueError('future output exists')
    bundle=ROOT/'.local'/('sdkros-task-calibration-bundle-'+stamp);bundle.mkdir()
    for name,path in load('observer_bundle').sources().items():
        shutil.copyfile(path,bundle/name);(bundle/name).chmod(0o444);inputs[str(path.relative_to(ROOT))]=sha(path);inputs[str((bundle/name).relative_to(ROOT))]=sha(bundle/name)
    bundle.chmod(0o555)
    write(HERE/'calibration-plan.json',dict(scope=plan.SCOPE,execution_enabled=False,stages=['observer-readiness','SDKROS-fixture'],slot=cases.cases()[0],readiness_checks=1,SDKROS_fixture_limit=1,minimum_pre_signal_SDK_provider_samples=2,SDK_provider_names=sorted(load('sdk_visibility').PROVIDER_NAMES),observer_limits=dict(processes=8,threads_per_process=64,history=512,read_bytes=16384,samples=48,period_seconds=.25,total_seconds=12),SDK_visibility_deadline_seconds=6,max_snapshot_bytes=8*1024*1024,host_fixture_watchdog_seconds=240,owned_host_group_failure_cleanup_seconds=[2,5],original_child_wait_seconds=5,source_seconds=10,original_scenario_deadline_seconds=130,disabled_case_ids=plan.disabled_ids(),remaining_case_ids_disabled=plan.remaining_ids(),campaign_stage_enabled={stage:False for stage in ('N3','N0','N4','LONG')},N1_2903_rerun=False,no_tuning=True,no_retries=True,stop_first_failed_gate=True,limitations=['not a 300s N0 campaign case','no forced post-SIGINT task absence or exact mid-read ENOENT guarantee','no unseen reuse or observer overhead equivalence','no M3 acceptance']))
    for path in HERE.rglob('*'):
        if path.is_file() and '__pycache__'not in path.parts:inputs[str(path.relative_to(ROOT))]=sha(path)
    freeze=dict(schema_version=1,execution_enabled=False,authorization_supplied=False,scope=plan.SCOPE,source_commit=query(['git','rev-parse','HEAD']),source_sha256=source_inventory(),inputs_sha256=inputs,retained_indexes=indexes,reused_native_inputs_sha256=f['reused_native_inputs_sha256'],runtime_layout=layout,runtime_version=runtime,daemon_architecture=daemon,target_image=IMAGE,observer_image=NATIVE,bundle_relative=str(bundle.relative_to(ROOT)),output_relative=output,prefix=prefix,readiness_checks=1,SDKROS_fixture_limit=1,slot=cases.cases()[0],task_assessment_binding=load('observer_bundle').binding(),preparation_active_containers=active,execution_requires_quiescent_runtime=True,disabled_case_ids=plan.disabled_ids(),remaining_case_ids_disabled=plan.remaining_ids(),N1_2903_rerun=False,original_failed_assessment_sha256=sha(EXEC/'cases/N1-combined-2903/strict-assessment.json'),no_tuning=True,no_retries=True,stop_first_failed_gate=True,historical_failure_preserved=True,live_runs=0)
    write(HERE/'freeze.json',freeze)
    write(HERE/'readiness.json',dict(status='bounded_native_SDKROS_calibration_prepared_execution_disabled',freeze_sha256=sha(HERE/'freeze.json'),readiness_checks_planned=1,SDKROS_fixtures_planned=1,source_seconds=10,preparation_tests=28,unchanged_logs_reused=dict(integration=25,assessment=42,existing=511),preparation_active_containers=active,execution_requires_quiescent_runtime=True,authorization_created=False,live_runs=0,all38_campaign_ids_disabled=True))
    write(HERE/'postflight.json',dict(status='prepared_only',source_full_build_native87_and_all_prior_indexes_verified=True,preserved_integration_components=preserved,readonly_six_file_bundle_created=True,future_output_absent=True,authorization_absent=True,original_results=dict(passed=1,failed=1,not_executed=7),all38_campaign_ids_disabled=True,all_campaign_stages_disabled=True,live_runs=0,Docker_mutations=0,tuning=False,retries=False,M3_complete=False))
    print(json.dumps(dict(status='prepared_only',freeze_sha256=sha(HERE/'freeze.json'),output_relative=output,bundle_relative=str(bundle.relative_to(ROOT)),preparation_active_containers=active,live_runs=0)))
if __name__=='__main__':main()
