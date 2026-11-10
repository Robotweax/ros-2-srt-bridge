"""Prepare disabled single-fixture calibration; never starts any container."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from m3_observer_filtering import profile
from disposition_runtime import matched
from plan import SCOPE,CANDIDATE_SHA,disabled_ids,remaining_ids
NATIVE='ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617'
PRIOR=ROOT/'evidence/m3-current-long-preparation-2026-11-10'
EXEC=ROOT/'evidence/m3-current-long-execution-2026-11-10'
CANDIDATE=ROOT/'evidence/m3-task-identity-visibility-2026-11-10'
DIAG=ROOT/'evidence/m3-n1-2903-thread-evidence-diagnosis-2026-11-10'
def main():
    if (HERE/'freeze.json').exists():raise ValueError('already frozen; no replacement')
    f=json.loads((PRIOR/'freeze.json').read_text());inputs=dict(f['inputs_sha256']);indexes=dict(f['retained_indexes'])
    if source_inventory()!=f['source_sha256']:raise ValueError('frozen source drift')
    FAILED_PREPARATION=ROOT/'evidence/m3-task-visibility-calibration-preparation-2026-11-10'
    rejected=json.loads((FAILED_PREPARATION/'freeze.json').read_text());inputs.update(rejected['inputs_sha256'])
    for folder in (PRIOR,EXEC,DIAG,CANDIDATE,FAILED_PREPARATION):
        for name in ('public-artifact-hashes.json','local-artifact-hashes.json'):
            path=folder/name
            if path.exists():indexes[str(path.relative_to(ROOT))]=sha(path)
        path=folder/'input-hashes.json'
        if path.exists():inputs.update(json.loads(path.read_text()))
    for path,digest in inputs.items():
        if sha(ROOT/path)!=digest:raise ValueError('frozen input drift: '+path)
    for path,digest in f['reused_native_inputs_sha256'].items():
        if sha(ROOT/path)!=digest:raise ValueError('native source drift')
    for path,digest in indexes.items():
        if sha(ROOT/path)!=digest:raise ValueError('retained index drift')
        for name,item in json.loads((ROOT/path).read_text()).items():
            if sha(ROOT/name)!=item['sha256']:raise ValueError('retained raw/public drift: '+name)
            if not path.endswith('local-artifact-hashes.json'):inputs[name]=item['sha256']
        inputs[path]=digest
    cohort=json.loads((EXEC/'cohort.json').read_text())
    if [r['status'] for r in cohort['rows']]!=['passed','failed']+['not_executed']*7:raise ValueError('stopped cohort changed')
    if sha(HERE/'shutdown_observer.py')!=CANDIDATE_SHA or sha(CANDIDATE/'shutdown_observer.py')!=CANDIDATE_SHA:raise ValueError('candidate collector differs')
    for name in ('observer-seccomp.json','observer-architecture.json','binary-verification.json','disposition_runtime.py'):
        if sha(HERE/name)!=sha(PRIOR/name):raise ValueError('unchanged policy/build component differs: '+name)
    for name,count in (('preparation-tests.log',23),('candidate-tests.log',28),('existing-suite.log',511)):
        text=(HERE/'validation'/name).read_text()
        if 'Ran '+str(count)+' tests' not in text or not text.rstrip().endswith('OK'):raise ValueError('offline tests failed')
    for path in HERE.rglob('*.py'):compile(path.read_text(),str(path),'exec')
    layout=matched(ROOT,'socket-disposition')
    if layout!=dict(f['runtime_layout'],calibration=layout['calibration']):raise ValueError('matched build changed')
    def query(args):return subprocess.check_output(args,text=True,timeout=20).strip()
    current=json.loads(query(['docker','version','--format','{{json .Server.Components}}']))
    if current!=f['runtime_version']:raise ValueError('runtime drift')
    daemon=query(['docker','info','--format','{{.Architecture}}'])
    if daemon!='aarch64' or profile(daemon,'arm64')!=json.loads((HERE/'observer-seccomp.json').read_text()):raise ValueError('native observer policy differs')
    for platform,image,arch in [('linux/amd64',IMAGE,'amd64'),('linux/arm64',NATIVE,'arm64')]:
        if query(['docker','image','inspect','--platform',platform,image,'--format','{{.Architecture}}'])!=arch:raise ValueError('image architecture differs')
    if query(['docker','ps','-q']):raise ValueError('live containers present')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');prefix='tvis-cal-'+stamp.lower();output='.local/task-visibility-calibration-'+stamp
    for argv in (['docker','ps','-a','--format','{{.Names}}'],['docker','volume','ls','--format','{{.Name}}']):
        if any(n.startswith(prefix) for n in query(argv).splitlines()):raise ValueError('prefix collision')
    if (ROOT/output).exists():raise ValueError('future output exists')
    write(HERE/'collector-binding.json',dict(sha256=CANDIDATE_SHA,task_visibility=True,scope=SCOPE,candidate_source=str((CANDIDATE/'shutdown_observer.py').relative_to(ROOT))))
    bundle=ROOT/'.local'/('task-visibility-calibration-bundle-'+stamp);bundle.mkdir()
    files={name:HERE/name for name in ('shutdown_observer.py','observer_entry.py','target_entry.py','task_target.py','observer-seccomp.json','observer-architecture.json','collector-binding.json')}
    files['scenario_processes.py']=ROOT/'ros2/robotweax_srt_bridge_demo/scripts/scenario_processes.py';files['m3_observer_filtering.py']=ROOT/'tools/m3_observer_filtering.py'
    for name,src in files.items():shutil.copyfile(src,bundle/name);(bundle/name).chmod(0o444);inputs[str(src.relative_to(ROOT))]=sha(src);inputs[str((bundle/name).relative_to(ROOT))]=sha(bundle/name)
    bundle.chmod(0o555)
    write(HERE/'calibration-plan.json',dict(scope=SCOPE,execution_enabled=False,stages=['observer-readiness','controlled-task-visibility'],readiness_checks=1,controlled_target_limit=1,candidate_collector_sha256=CANDIDATE_SHA,task_visibility=True,minimum_live_worker_samples=2,controlled_absence_records_required=1,observer_limits=dict(processes=8,threads=64,samples=48,period_seconds=.25,time_seconds=12,bytes_per_read=16384),host_phase_deadline_seconds=6,max_snapshot_bytes=8*1024*1024,child_wait_seconds=5,disabled_case_ids=disabled_ids(),remaining_case_ids_disabled=remaining_ids(),N1_2903_rerun=False,no_tuning=True,no_retries=True,stop_first_failed_gate=True,scope_limits=['no exact enumeration/read race guarantee','no native overhead equivalence','no SRT/ROS/campaign qualification','no assessor acceptance change']))
    for path in HERE.rglob('*'):
        if path.is_file() and '__pycache__'not in path.parts:inputs[str(path.relative_to(ROOT))]=sha(path)
    freeze=dict(schema_version=1,execution_enabled=False,authorization_supplied=False,scope=SCOPE,source_commit=query(['git','rev-parse','HEAD']),source_sha256=source_inventory(),inputs_sha256=inputs,retained_indexes=indexes,reused_native_inputs_sha256=f['reused_native_inputs_sha256'],runtime_layout=layout,runtime_version=current,daemon_architecture=daemon,target_image=IMAGE,observer_image=NATIVE,bundle_relative=str(bundle.relative_to(ROOT)),output_relative=output,prefix=prefix,readiness_checks=1,controlled_target_limit=1,candidate_collector_sha256=CANDIDATE_SHA,task_visibility=True,disabled_case_ids=disabled_ids(),remaining_case_ids_disabled=remaining_ids(),N1_2903_rerun=False,original_failed_assessment_sha256=sha(EXEC/'cases/N1-combined-2903/strict-assessment.json'),no_tuning=True,no_retries=True,stop_first_failed_gate=True,historical_failure_preserved=True,live_runs=0)
    write(HERE/'freeze.json',freeze)
    write(HERE/'readiness.json',dict(status='bounded_task_visibility_calibration_prepared_execution_disabled',freeze_sha256=sha(HERE/'freeze.json'),readiness_checks_planned=1,controlled_targets_planned=1,candidate_collector_sha256=CANDIDATE_SHA,activation_explicit_and_hash_bound=True,preparation_tests_passed=23,candidate_tests_passed=28,existing_tests_passed=511,live_runs=0,authorization_created=False,builds=0,policy_unchanged=True,observer_budget_unchanged=True,all38_campaign_case_ids_disabled=True,N1_2903_rerun=False))
    write(HERE/'postflight.json',dict(status='prepared_only',source_inputs_matched_build_native87_prior_public_raw_archives_verified=True,stopped_cohort_unchanged=dict(passed=1,failed=1,not_executed=7),readonly_nine_file_bundle_created=True,live_runs=0,no_Docker_mutation=True,no_build=True,no_tuning=True,no_retries=True,future_output_absent=True,new_grant_absent=True,N1_2903_rerun=False,all_campaign_cases_disabled=True,M3_complete=False))
    print(json.dumps(dict(status='prepared_only',freeze_sha256=sha(HERE/'freeze.json'),output_relative=output,bundle_relative=str(bundle.relative_to(ROOT)),readiness_checks=1,controlled_target_limit=1,live_runs=0)))
if __name__=='__main__':main()
