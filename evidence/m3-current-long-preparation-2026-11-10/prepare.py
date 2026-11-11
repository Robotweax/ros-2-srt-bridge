"""Freeze exactly nine disabled cases after offline and read-only metadata checks."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from m3_network import PROFILES
from m3_capture import pcap_configuration
from disposition_runtime import matched
from cases import cases,disabled_ids,completed_ids,SCOPE,IDENTITY_HELPER_PATH,IDENTITY_HELPER_SHA256,LIFECYCLE_ASSESSMENT_PATH,LIFECYCLE_ASSESSMENT_SHA256
PRIOR=ROOT/'evidence/m3-current-n4-corrected-preparation-2026-11-10'
PASSED=ROOT/'evidence/m3-current-n4-corrected-execution-2026-11-10'
N0=ROOT/'evidence/m3-current-n0-stable-preparation-2026-11-10'
FIX=ROOT/'evidence/m3-current-n0-lifecycle-stabilization-2026-11-10'
NATIVE='ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617'

def prerequisites():
    gate=json.loads((PASSED/'gate-report.json').read_text())
    if gate['status']!='passed_fresh19_current_build_N4' or gate['passed']!=19:raise ValueError('N4 prerequisite differs')
    n0=json.loads((ROOT/'evidence/m3-current-n0-stable-execution-2026-11-10/gate-report.json').read_text())
    if n0['status']!='passed_single_current_build_stabilized_N0':raise ValueError('N0 prerequisite differs')
    n3=json.loads((ROOT/'evidence/m3-strict-n3-execution-2026-11-10/gate-report.json').read_text())
    if n3['status']!='passed_fresh_strict_N3_9_of_9' or n3['passed_cases']!=9:raise ValueError('N3 prerequisite differs')
    return dict(N0='passed',N3_passed=9,N4_passed=19)

def main():
    if (HERE/'freeze.json').exists():raise ValueError('already frozen; no replacement')
    f=json.loads((PRIOR/'freeze.json').read_text())
    if source_inventory()!=f['source_sha256']:raise ValueError('frozen source drift')
    inputs=dict(f['inputs_sha256']);indexes=dict(f['retained_indexes'])
    for path,digest in inputs.items():
        if sha(ROOT/path)!=digest:raise ValueError('prior input drift: '+path)
    for path,digest in f['reused_native_inputs_sha256'].items():
        if sha(ROOT/path)!=digest:raise ValueError('native input drift')
    for folder in (PRIOR,PASSED):
        for name in ('public-artifact-hashes.json','local-artifact-hashes.json'):
            path=folder/name
            if path.exists():indexes[str(path.relative_to(ROOT))]=sha(path)
    for path,digest in indexes.items():
        if sha(ROOT/path)!=digest:raise ValueError('retained index drift')
        for name,item in json.loads((ROOT/path).read_text()).items():
            if sha(ROOT/name)!=item['sha256']:raise ValueError('retained raw/public drift: '+name)
            if not path.endswith('local-artifact-hashes.json'):inputs[name]=item['sha256']
        inputs[path]=digest
    prerequisites()
    for name in ('launch_readiness.py','launch_records.py','launch_assessment.py','lifecycle.py','sidecar.py','stage_gate.py','socket_gate.py','shutdown_observer.py','observer_entry.py','observer-seccomp.json','observer-architecture.json','emergency_cleanup.py','binary-verification.json','disposition_runtime.py'):
        if sha(HERE/name)!=sha(N0/name):raise ValueError('calibrated lifecycle component changed: '+name)
    for name in ('scenario.py','bridge_exec.py'):
        if sha(HERE/name)!=sha(FIX/name):raise ValueError('stabilized scenario changed: '+name)
    if sha(ROOT/IDENTITY_HELPER_PATH)!=IDENTITY_HELPER_SHA256 or sha(ROOT/LIFECYCLE_ASSESSMENT_PATH)!=LIFECYCLE_ASSESSMENT_SHA256 or sha(HERE/'launch_assessment.py')!=LIFECYCLE_ASSESSMENT_SHA256:raise ValueError('explicit lifecycle/identity binding differs')
    layout=matched(ROOT,'socket-disposition')
    if layout!=dict(f['runtime_layout'],calibration=layout['calibration']):raise ValueError('matched build differs')
    for name,count in (('preparation-tests.log',21),('lifecycle-tests.log',39),('runtime-import-tests.log',4),('existing-suite.log',511)):
        text=(HERE/'validation'/name).read_text()
        if 'Ran '+str(count)+' tests' not in text or not text.rstrip().endswith('OK'):raise ValueError('offline validation failed: '+name)
    for path in HERE.rglob('*.py'):compile(path.read_text(),str(path),'exec')
    current=json.loads(subprocess.check_output(['docker','version','--format','{{json .Server.Components}}'],text=True))
    if current!=f['runtime_version']:raise ValueError('runtime drift')
    if subprocess.check_output(['docker','info','--format','{{.Architecture}}'],text=True).strip()!='aarch64':raise ValueError('daemon architecture differs')
    for platform,image,arch in [('linux/amd64',IMAGE,'amd64'),('linux/arm64',NATIVE,'arm64')]:
        if subprocess.check_output(['docker','image','inspect','--platform',platform,image,'--format','{{.Architecture}}'],text=True).strip()!=arch:raise ValueError('pinned image differs')
    if subprocess.check_output(['docker','ps','-q'],text=True).strip():raise ValueError('live container remains')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');prefix='current-long-'+stamp.lower();output='.local/current-long-cohort-'+stamp
    for argv in (['docker','ps','-a','--format','{{.Names}}'],['docker','network','ls','--format','{{.Name}}'],['docker','volume','ls','--format','{{.Name}}']):
        if any(name.startswith(prefix) for name in subprocess.check_output(argv,text=True).splitlines()):raise ValueError('fresh prefix collision')
    if (ROOT/output).exists():raise ValueError('future output exists')
    bundle=ROOT/'.local'/('current-long-observer-bundle-'+stamp);bundle.mkdir()
    helpers={name:HERE/name for name in ('observer_entry.py','observer-seccomp.json','observer-architecture.json','shutdown_observer.py')};helpers['m3_observer_filtering.py']=ROOT/'tools/m3_observer_filtering.py'
    for name,source in helpers.items():shutil.copyfile(source,bundle/name);(bundle/name).chmod(0o444)
    bundle.chmod(0o555)
    identity=dict(path=IDENTITY_HELPER_PATH,sha256=IDENTITY_HELPER_SHA256,module='_robotweax_n0_launch_identity_v1');lifecycle=dict(path=LIFECYCLE_ASSESSMENT_PATH,sha256=LIFECYCLE_ASSESSMENT_SHA256)
    write(HERE/'case-plan.json',dict(execution_enabled=False,cases=cases(),disabled_case_ids=disabled_ids(),completed_case_ids_not_reexecuted=completed_ids(),no_tuning=True,no_automatic_retries=True,stop_first_failed_gate=True))
    write(HERE/'settings.json',dict(profiles={name:vars(PROFILES[name]) for name in ('N1','N2','N5')},N5_competitor=dict(protocol='UDP',bitrate_cli='128K',target_bitrate=128000,payload_bytes=1024,duration='source_seconds+60',must_remain_alive=True),imu_hz=200,joint_hz=50,command_period_seconds=2,command_budget_ms=5000,sensor_budget_ms=250,clock_width_ms=200,neighbor_mode='dynamic',pcap=pcap_configuration(),shutdown_child_wait_seconds=5,scope='original settings recorded, not changed; capture/trace exhaustion remains failure, no retention or performance guarantee'))
    for path in [q for q in HERE.rglob('*') if q.is_file() and '__pycache__'not in q.parts]+list(bundle.iterdir()):inputs[str(path.relative_to(ROOT))]=sha(path)
    freeze=dict(schema_version=1,execution_enabled=False,authorization_supplied=False,scope=SCOPE,cases=cases(),disabled_case_ids=disabled_ids(),completed_case_ids_not_reexecuted=completed_ids(),completed_campaign_cases_excluded=29,launch_readiness_harness_revision='stabilized-lifecycle-v1',lifecycle_assessment_binding=lifecycle,identity_helper_binding=identity,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_sha256=source_inventory(),runtime_layout=layout,runtime_version=current,target_image=IMAGE,observer_image=NATIVE,reused_native_inputs_sha256=f['reused_native_inputs_sha256'],retained_indexes=indexes,inputs_sha256=inputs,bundle_relative=str(bundle.relative_to(ROOT)),output_relative=output,prefix=prefix,no_tuning=True,no_automatic_retries=True,stop_first_failed_gate=True,historical_failures_preserved=True,live_runs=0,nominal_source_seconds=4500,wall_clock_estimate=False)
    write(HERE/'freeze.json',freeze)
    write(HERE/'readiness.json',dict(status='nine_current_build_N1_N2_N5_prepared_execution_disabled',freeze_sha256=sha(HERE/'freeze.json'),cases_prepared=9,N1_cases=3,N2_cases=3,N5_cases=3,N1_N2_source_seconds=600,N5_source_seconds=300,nominal_source_seconds=4500,wall_clock_estimate=False,live_runs=0,authorization_file_created=False,native_rebuild=False,preparation_tests_passed=21,lifecycle_tests_passed=39,runtime_import_tests_passed=4,existing_tests_passed=511,matched_entries=14,preserved_shutdown_entries=13,native_inputs_verified=87,completed_campaign_cases_excluded=29,no_tuning=True,no_automatic_retries=True,stop_first_failed_gate=True))
    write(HERE/'postflight.json',dict(status='prepared_only_no_execution',frozen_source_inputs_build_chain_native_and_retained_evidence_verified=True,stabilized_lifecycle_and_observer_policy_preserved=True,syntax_verified=True,no_live_case_or_experiment=True,no_Docker_mutation=True,no_build=True,no_execution_grant=True,owned_prefix_absent=True,future_output_absent=True,completed_campaign_cases_excluded=29,M3_complete=False))
    print(json.dumps(dict(status='prepared_only',freeze_sha256=sha(HERE/'freeze.json'),cases=9,live_runs=0,output_relative=output,prefix=prefix)))
if __name__=='__main__':main()
