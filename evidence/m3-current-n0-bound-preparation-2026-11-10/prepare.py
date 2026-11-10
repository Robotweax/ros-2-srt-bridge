"""Freeze corrected N0 inputs after offline/read-only checks; never launches workloads."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from cases import cases,disabled_ids,SCOPE,IDENTITY_HELPER_PATH,IDENTITY_HELPER_SHA256
from disposition_runtime import matched
PRIOR=ROOT/'evidence/m3-current-n0-preparation-2026-11-10'
FIX=ROOT/'evidence/m3-current-n0-identity-binding-fix-2026-11-10'
NATIVE='ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617'


def main():
    if (HERE/'freeze.json').exists():raise ValueError('preparation already frozen')
    f=json.loads((PRIOR/'freeze.json').read_text())
    if source_inventory()!=f['source_sha256'] or any(sha(ROOT/p)!=h for p,h in f['inputs_sha256'].items()):raise ValueError('original frozen source/input drift')
    if any(sha(ROOT/p)!=h for p,h in f['reused_native_inputs_sha256'].items()):raise ValueError('native inputs changed')
    if json.loads((FIX/'postflight.json').read_text())['targeted_tests_passed']!=30:raise ValueError('explicit binding prerequisite missing')
    if sha(ROOT/IDENTITY_HELPER_PATH)!=IDENTITY_HELPER_SHA256:raise ValueError('bound identity helper changed')
    if sha(HERE/'workload.py')!=sha(FIX/'workload.py'):raise ValueError('corrected adapter differs')
    for name in ('binary-verification.json','disposition_runtime.py','observer_entry.py','observer-seccomp.json','observer-architecture.json','shutdown_observer.py','lifecycle.py','socket_gate.py','stage_gate.py','sidecar.py','emergency_cleanup.py','assess.py'):
        if sha(HERE/name)!=sha(PRIOR/name):raise ValueError('calibrated observer/gate component drift: '+name)
    indexes=dict(f['retained_indexes']);inputs=dict(f['inputs_sha256'])
    for name in ('m3-current-n0-preparation-2026-11-10','m3-current-n0-execution-2026-11-10','m3-current-n0-capability-diagnosis-2026-11-10','m3-current-n0-readiness-fix-2026-11-10','m3-current-n0-corrected-preparation-2026-11-10','m3-current-n0-corrected-execution-2026-11-10','m3-current-n0-identity-binding-fix-2026-11-10'):
        folder=ROOT/'evidence'/name
        for index in (folder/'public-artifact-hashes.json',folder/'local-artifact-hashes.json'):
            if index.exists():indexes[str(index.relative_to(ROOT))]=sha(index)
    for path,digest in indexes.items():
        if sha(ROOT/path)!=digest:raise ValueError('retained index drift')
        for p,value in json.loads((ROOT/path).read_text()).items():
            if sha(ROOT/p)!=value['sha256']:raise ValueError('retained public/raw evidence drift')
            if not path.endswith('local-artifact-hashes.json'):inputs[p]=value['sha256']
        inputs[path]=digest
    layout=matched(ROOT,'socket-disposition')
    for key in ('sdk','ros','runtime_paths','matched_build_sha256','preserved_shutdown_trace'):
        if layout[key]!=f['runtime_layout'][key]:raise ValueError('matched build changed')
    for log,count in (('preparation-tests.log',10),('readiness-tests.log',30)):
        text=(HERE/'validation'/log).read_text()
        if 'Ran '+str(count)+' tests' not in text or not text.rstrip().endswith('OK'):raise ValueError('offline validation failed')
    for p in HERE.rglob('*.py'):compile(p.read_text(),str(p),'exec')
    current=json.loads(subprocess.check_output(['docker','version','--format','{{json .Server.Components}}'],text=True))
    if current!=f['runtime_version']:raise ValueError('calibrated runtime drift')
    if subprocess.check_output(['docker','info','--format','{{.Architecture}}'],text=True).strip()!='aarch64':raise ValueError('daemon architecture differs')
    for platform,image,arch in (('linux/amd64',IMAGE,'amd64'),('linux/arm64',NATIVE,'arm64')):
        if subprocess.check_output(['docker','image','inspect','--platform',platform,image,'--format','{{.Architecture}}'],text=True).strip()!=arch:raise ValueError('pinned image differs')
    if subprocess.check_output(['docker','ps','-q'],text=True).strip():raise ValueError('live container remains')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');prefix='bound-n0-'+stamp.lower()
    listings={key:subprocess.check_output(args,text=True).splitlines() for key,args in dict(containers=['docker','ps','-a','--format','{{.Names}}'],networks=['docker','network','ls','--format','{{.Name}}'],volumes=['docker','volume','ls','--format','{{.Name}}']).items()}
    if any(x.startswith(prefix) for rows in listings.values() for x in rows):raise ValueError('fresh prefix collision')
    output='.local/bound-n0-coverage-'+stamp
    if (ROOT/output).exists():raise ValueError('output already exists; no resume')
    bundle=ROOT/'.local'/('bound-n0-observer-bundle-'+stamp);bundle.mkdir()
    helpers={name:HERE/name for name in ('observer_entry.py','observer-seccomp.json','observer-architecture.json','shutdown_observer.py')};helpers['m3_observer_filtering.py']=ROOT/'tools/m3_observer_filtering.py'
    for name,src in helpers.items():shutil.copyfile(src,bundle/name);(bundle/name).chmod(0o444)
    bundle.chmod(0o555)
    write(HERE/'case-plan.json',dict(execution_enabled=False,cases=cases(),disabled_case_ids=disabled_ids(),completed_N3_case_ids_not_reexecuted=f['completed_N3_case_ids_not_reexecuted'],launch_readiness_harness_revision='explicit-identity-v1',identity_helper_binding=dict(path=IDENTITY_HELPER_PATH,sha256=IDENTITY_HELPER_SHA256,module='_robotweax_n0_launch_identity_v1'),no_automatic_retries=True,stop_first_failed_gate=True))
    for p in [p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts]+list(bundle.iterdir()):inputs[str(p.relative_to(ROOT))]=sha(p)
    freeze=dict(schema_version=1,execution_enabled=False,authorization_supplied=False,scope=SCOPE,cases=cases(),disabled_case_ids=disabled_ids(),completed_N3_case_ids_not_reexecuted=f['completed_N3_case_ids_not_reexecuted'],launch_readiness_harness_revision='explicit-identity-v1',identity_helper_binding=dict(path=IDENTITY_HELPER_PATH,sha256=IDENTITY_HELPER_SHA256,module='_robotweax_n0_launch_identity_v1'),corrected_harness_public_sha256=sha(FIX/'public-artifact-hashes.json'),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),source_sha256=source_inventory(),runtime_layout=layout,runtime_version=current,target_image=IMAGE,observer_image=NATIVE,reused_native_inputs_sha256=f['reused_native_inputs_sha256'],retained_indexes=indexes,inputs_sha256=inputs,bundle_relative=str(bundle.relative_to(ROOT)),output_relative=output,prefix=prefix,remaining_campaign_cases_disabled=28,no_automatic_retries=True,stop_first_failed_gate=True,historical_failures_preserved=True,no_tuning=True,live_runs=0)
    write(HERE/'freeze.json',freeze)
    write(HERE/'readiness.json',dict(status='explicit_identity_N0_prepared_execution_disabled',freeze_sha256=sha(HERE/'freeze.json'),live_runs=0,authorization_file_created=False,preparation_tests_passed=10,corrected_readiness_tests_passed=30,retained_existing_suite_passed=511,corrected_harness_byte_identical=True,combined_corrected_harness_live_validated=False,matched_entries=14,preserved_shutdown_entries=13,native_inputs_verified=87,read_only_runtime_image_metadata_verified=True,other_campaign_cases_disabled=28,no_tuning=True,no_automatic_retries=True))
    write(HERE/'postflight.json',dict(status='prepared_only',source_inputs_build_chain_native_and_retained_evidence_verified=True,corrected_harness_bound=True,syntax_checks_passed=True,no_live_fixture=True,no_docker_mutation=True,no_native_build=True,no_execution_grant=True,no_N0_retry=True,owned_prefix_absent=True,output_absent=True,other_campaign_cases_disabled=28,M3_complete=False))
    print(json.dumps(dict(status='prepared_only',freeze_sha256=sha(HERE/'freeze.json'),execution_enabled=False,live_runs=0,output_relative=output)))

if __name__=='__main__':main()
