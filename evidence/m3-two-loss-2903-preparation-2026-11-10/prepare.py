"""Read-only provenance and disabled freeze; never creates or starts Docker objects."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from disposition_runtime import matched
HERE=Path(__file__).resolve().parent
CAL=ROOT/'evidence/m3-observer-bootstrap-calibration-2026-11-10'


def main():
    if (HERE/'freeze.json').exists():raise ValueError('preparation freeze already exists')
    calibration=json.loads((CAL/'gate-report.json').read_text())
    if calibration['status']!='passed' or calibration['post_signal_stack_reads']!=24:raise ValueError('kernel-stack calibration prerequisite missing')
    for name in ('observer-seccomp.json','observer-architecture.json','observer_entry.py'):
        if sha(HERE/name)!=sha(CAL/name):raise ValueError('calibrated observer input differs')
    for p,item in json.loads((CAL/'public-artifact-hashes.json').read_text()).items():
        if sha(ROOT/p)!=item['sha256']:raise ValueError('calibration evidence drift')
    for p,item in json.loads((CAL/'local-artifact-hashes.json').read_text()).items():
        if sha(ROOT/p)!=item['sha256']:raise ValueError('retained raw calibration drift')
    indexes={}
    for name in ('m3-n3-frozen-cohort-2026-11-09','m3-shutdown-live-calibration-2026-11-09','m3-observer-stack-permissions-2026-11-09','m3-observer-native-filter-2026-11-10','m3-observer-bootstrap-calibration-2026-11-10','m3-bridge-shutdown-diagnostic-2026-11-10','m3-bridge-shutdown-capability-fix-2026-11-10','m3-bridge-shutdown-lifecycle-2026-11-10','m3-socket-disposition-2026-11-10'):
        index=ROOT/'evidence'/name/'local-artifact-hashes.json'
        for path,item in json.loads(index.read_text()).items():
            if sha(ROOT/path)!=item['sha256']:raise ValueError('retained evidence drift')
        indexes[str(index.relative_to(ROOT))]=sha(index)
    previous=ROOT/'evidence/m3-socket-disposition-2026-11-10'
    candidate=json.loads((previous/'freeze.json').read_text())
    native={path:digest for path,digest in candidate['source_sha256'].items() if path.startswith(('src/','proto/','cmake/')) or path=='CMakeLists.txt' or (path.startswith('ros2/') and not path.endswith('.py'))}
    if any(sha(ROOT/path)!=digest for path,digest in native.items()):raise ValueError('native build inputs changed; must not reuse matched build')
    for name in ('binary-verification.json','observer-seccomp.json','observer-architecture.json','observer_entry.py','shutdown_observer.py','lifecycle.py','socket_gate.py','stage_gate.py','sidecar.py','bridge_exec.py','scenario.py'):
        if sha(HERE/name)!=sha(previous/name):raise ValueError('calibrated diagnostic component changed: '+name)
    provenance=json.loads((ROOT/candidate['output_relative']/'provenance.json').read_text())
    capture_paths=('build/m3-monotonic-capture/monotonic_capture','build/m3-netdev-features/netdev_features')
    for path in capture_paths:
        if sha(ROOT/path)!=provenance['runtime_sha256'][path]:raise ValueError('calibrated capture helper drift')
    layout=matched(ROOT,'socket-disposition')
    current=json.loads(subprocess.check_output(['docker','version','--format','{{json .Server.Components}}'],text=True))
    if current!=json.loads((CAL/'freeze.json').read_text())['runtime_version']:raise ValueError('calibrated runtime drift')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    bundle=ROOT/'.local'/('two-loss-2903-observer-bundle-'+stamp);bundle.mkdir()
    helpers={name:HERE/name for name in ('observer_entry.py','observer-seccomp.json','observer-architecture.json')}
    helpers.update({'shutdown_observer.py':HERE/'shutdown_observer.py','m3_observer_filtering.py':ROOT/'tools/m3_observer_filtering.py'})
    for name,src in helpers.items():shutil.copyfile(src,bundle/name);(bundle/name).chmod(0o444)
    bundle.chmod(0o555)
    inputs=[*(p for p in HERE.iterdir() if p.suffix in ('.py','.md','.json')),*(bundle/name for name in helpers),*(ROOT/path for path in capture_paths),ROOT/'tools/m3_ros_multiroute.py',CAL/'freeze.json',CAL/'gate-report.json',CAL/'public-artifact-hashes.json']
    freeze=dict(schema_version=1,execution_enabled=False,authorization_supplied=False,scope='one-two-loss-2903-30s-operator-bridge-shutdown-diagnostic',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256=source_inventory(),runtime_layout=layout,runtime_version=current,target_image=IMAGE,diagnostic_case=dict(seed=2903,source_seconds=30,losses=2,row=1,positions=[2,3],message_numbers=[7,8],observed_role='operator'),reused_native_inputs_sha256=native,retained_indexes=indexes,inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},bundle_relative=str(bundle.relative_to(ROOT)),output_relative='.local/two-loss-2903-shutdown-'+stamp,prefix='two-loss-2903-shutdown-'+stamp.lower(),remaining_campaign_cases_disabled=29,retry_two_loss_4211=False,no_tuning=True,live_runs=0)
    write(HERE/'freeze.json',freeze)
    write(HERE/'readiness.json',dict(status='offline_prepared_execution_disabled',python_tests=497,live_runs=0,native_observer_prior_calibration='passed_synthetic_and_healthy_N0',bridge_capability_wrapper_live_validated=True,bridge_sidecar_healthy_N0_validated=True,two_loss_bridge_integration_live_validated=False,matched_entries=len(layout['matched_build_sha256']),freeze_sha256=sha(HERE/'freeze.json'),authorization_file_created=False,remaining_campaign_cases_disabled=29,retry_two_loss_4211=False,no_tuning=True))
    print(json.dumps(dict(status='prepared_only',freeze_sha256=sha(HERE/'freeze.json'),execution_enabled=False,live_runs=0)))

if __name__=='__main__':main()
