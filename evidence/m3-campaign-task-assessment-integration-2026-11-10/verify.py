"""Filesystem-only integration/provenance audit. No Docker/procfs or dispatch."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
from campaign_binding import load,PINNED

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def verify():
    old=ROOT/'evidence/m3-task-metadata-assessment-2026-11-10';audit=module('original_filesystem_audit',old/'verify.py');prior=audit.verify()
    indexes=dict(prior['verified_indexes'])
    for folder in (old,ROOT/'evidence/m3-task-post-sigint-calibration-preparation-2026-11-10',ROOT/'evidence/m3-task-post-sigint-calibration-execution-2026-11-10'):
        for index in folder.glob('*artifact-hashes.json'):
            indexes[str(index.relative_to(ROOT))]=sha(index)
            for path,item in json.loads(index.read_text()).items():
                if sha(ROOT/path)!=item['sha256'] or (ROOT/path).stat().st_size!=item['bytes']:raise ValueError('retained file drift: '+path)
    calibration=ROOT/'evidence/m3-task-post-sigint-calibration-preparation-2026-11-10';freeze=json.loads((calibration/'freeze.json').read_text())
    for path,digest in {**freeze['inputs_sha256'],**freeze['reused_native_inputs_sha256']}.items():
        if sha(ROOT/path)!=digest:raise ValueError('calibrated input drift: '+path)
    manifest=json.loads((HERE/'bindings.json').read_text());candidate={}
    for name,digest in manifest['modules'].items():
        if sha(HERE/(name+'.py'))!=digest:raise ValueError('prospective module differs: '+name)
    for name,digest in PINNED.items():
        if sha(HERE/(name+'.py'))!=digest or sha(calibration/(name+'.py'))!=digest:raise ValueError('calibrated candidate differs')
        candidate[name]=digest
    preserved=['launch_readiness.py','launch_records.py','launch_assessment.py','bridge_exec.py','scenario.py','stage_gate.py','socket_gate.py','profile_gate.py','disposition_runtime.py','emergency_cleanup.py']
    for name in preserved:
        if sha(HERE/name)!=sha(ROOT/'evidence/m3-current-long-preparation-2026-11-10'/name):raise ValueError('unchanged campaign gate differs: '+name)
    cases=load('cases');assert len(cases.disabled_ids())==38 and not cases.enabled_ids()
    missing_files=['freeze.json','authorization.json','readiness.json']
    if any((HERE/name).exists() for name in missing_files):raise ValueError('unexpected freeze/grant/readiness')
    for name,count in [('integration-tests.log',25),('assessment-tests.log',42),('existing-suite.log',511)]:
        text=(HERE/'validation'/name).read_text()
        if f'Ran {count} tests' not in text or not text.rstrip().endswith('OK'):raise ValueError('offline suite failed: '+name)
    return dict(status='passed_offline_campaign_task_assessment_integration_only',calibrated_candidate_sha256=candidate,private_module_manifest_sha256=sha(HERE/'bindings.json'),native_bundle_binding=load('observer_bundle').binding(),unchanged_gate_files=preserved,verified_retained_indexes=indexes,original_N1_2903_failure=prior['original_failure_reproduced'],legacy_schema_refusal=prior['legacy_new_schema_refusal'],original_N1_2903_assessment_sha256=prior['original_N1_2903_assessment_sha256'],original_results=prior['original_results'],disabled_case_ids=cases.disabled_ids(),remaining_case_ids_disabled=prior['remaining_case_ids_disabled'],execution_enabled=False,all_stages_disabled=True,new_freeze=False,new_authorization=False,live_runs=0,Docker_calls=0,live_procfs_reads=0,tuning=False,retries=False,builds=0,tests=dict(integration=25,assessment=42,existing=511),M3_complete=False)
if __name__=='__main__':print(json.dumps(verify(),indent=2))
