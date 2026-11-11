"""Offline retained-file audit and candidate assessment; never dispatches a run."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from task_assessment import assess_metadata

def sha(path):return hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
def load(path):return json.loads(path.read_text())
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def verify():
    diagnosis=module('retained_diagnosis',ROOT/'evidence/m3-n1-2903-thread-evidence-diagnosis-2026-11-10/analyze.py')
    indexes=diagnosis.integrity(load(ROOT/'evidence/m3-current-long-preparation-2026-11-10/freeze.json'))
    packages=['m3-n1-2903-thread-evidence-diagnosis-2026-11-10','m3-task-identity-visibility-2026-11-10','m3-task-visibility-calibration-preparation-2026-11-10','m3-task-visibility-calibration-corrected-preparation-2026-11-10','m3-task-visibility-calibration-execution-2026-11-10']
    for package in packages:
        for index in sorted((ROOT/'evidence'/package).glob('*artifact-hashes.json')):
            indexes[str(index.relative_to(ROOT))]=sha(index)
            for name,item in load(index).items():
                if sha(ROOT/name)!=item['sha256'] or (ROOT/name).stat().st_size!=item['bytes']:raise ValueError('retained artifact changed: '+name)
    execution=ROOT/'evidence/m3-task-visibility-calibration-execution-2026-11-10'
    raw=load(execution/'local-artifact-hashes.json')
    if len(raw)!=77 or sum(item['bytes'] for item in raw.values())!=600527:raise ValueError('calibration population differs')
    capture=execution/'run/data/blocked-target-shutdown-stacks.jsonl';rows=[json.loads(x) for x in capture.read_text().splitlines()]
    metadata=assess_metadata(rows)
    cohort_path=ROOT/'evidence/m3-current-long-execution-2026-11-10/cohort.json';cohort=load(cohort_path)
    if cohort['status']!='failed' or [r['status'] for r in cohort['rows']]!=['passed','failed']+['not_executed']*7:raise ValueError('original campaign outcomes changed')
    raw_long=ROOT/'.local/current-long-cohort-20261110T152312809927Z'
    for row in cohort['rows'][2:]:
        if (raw_long/row['slot']['id']).exists() or (cohort_path.parent/'cases'/row['slot']['id']).exists():raise ValueError('disabled later case directory exists')
    failed=cohort_path.parent/'cases/N1-combined-2903';strict_path=failed/'strict-assessment.json';launch=load(strict_path)['launches']['operator']['measurement']
    oldrows=[json.loads(x) for x in (failed/'native-observer/blocked-target-shutdown-stacks.jsonl').read_text().splitlines()]
    old=module('original_lifecycle',ROOT/'evidence/m3-current-long-preparation-2026-11-10/lifecycle.py')
    try:old.coverage(oldrows,launch['child'],launch['stages']['rows'])
    except ValueError as error:
        if str(error)!='live target kernel stack unavailable':raise
        original_failure=str(error)
    else:raise ValueError('original N1 failure no longer reproduced')
    try:assess_metadata(oldrows)
    except ValueError as error:
        if str(error)!='task visibility schema1 required':raise
        legacy_refusal=str(error)
    else:raise ValueError('legacy capture incorrectly accepted')
    return dict(status='passed_offline_only',verified_indexes=indexes,source_matched_build_native87_and_retained_archives_verified=True,calibration_capture_sha256=sha(capture),calibration_metadata=metadata,calibration_raw_files=77,calibration_raw_bytes=600527,original_N1_2903_assessment_sha256=sha(strict_path),original_failure_reproduced=original_failure,legacy_new_schema_refusal=legacy_refusal,original_results=dict(passed=1,failed=1,not_executed=7),disabled_case_ids=load(execution/'gate-report.json')['disabled_case_ids'],remaining_case_ids_disabled=[r['slot']['id'] for r in cohort['rows'][2:]],live_experiments=0,Docker_calls=0,live_procfs_reads=0,builds=0,tuning=False,retries=False,new_freeze=False,new_authorization=False,campaign_driver_or_frozen_assessor_changed=False,M3_complete=False)
if __name__=='__main__':print(json.dumps(verify(),indent=2))
