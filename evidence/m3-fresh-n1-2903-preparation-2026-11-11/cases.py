"""One separately frozen fresh N1 qualification; historical failure immutable."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCOPE='one-fresh-N1-2903-600s-calibrated-qualification'
EXPECTED_IDS=['N1-combined-2903']
FAILURE_PATH='evidence/m3-current-long-execution-2026-11-10/cases/N1-combined-2903/strict-assessment.json'
FAILURE_SHA256='e9cf84c7b6beffe584cfc06134d44c263b4884fcf166b3e113a7430cdedd7d30'
COHORT_PATH='evidence/m3-current-long-execution-2026-11-10/cohort.json'
COHORT_SHA256='3277c483ed49e5c806875d1988ec6f7f03593a155da98c8531c5ca9200ccd325'
def original():return json.loads((ROOT/'evidence/m3-closure-plan-2026-11-09/plan.json').read_text())['proposed_future_cases']
def original_failure_reference():return dict(path=FAILURE_PATH,sha256=FAILURE_SHA256,cohort_path=COHORT_PATH,cohort_sha256=COHORT_SHA256)
def cases():
    if hashlib.sha256((ROOT/FAILURE_PATH).read_bytes()).hexdigest()!=FAILURE_SHA256 or hashlib.sha256((ROOT/COHORT_PATH).read_bytes()).hexdigest()!=COHORT_SHA256:raise ValueError('original N1 failure/cohort changed')
    fields=('id','ordinal','stage','profile','seed','source_seconds');rows=[dict({k:s[k] for k in fields},runtime_layout='socket-disposition') for s in original() if s['id'] in EXPECTED_IDS]
    if len(rows)!=1 or rows[0]['id']!=EXPECTED_IDS[0] or (rows[0]['ordinal'],rows[0]['profile'],rows[0]['seed'],rows[0]['source_seconds'])!=(31,'N1',2903,600):raise ValueError('single fresh N1/2903/600s scope differs')
    return rows
def allowed(profile,seed,seconds):return (profile,seed,seconds)==('N1',2903,600)
def disabled_ids():return [s['id'] for s in original() if s['id'] not in EXPECTED_IDS]
def completed_ids():return disabled_ids()
def historical_case_ids_excluded():return [s['id'] for s in original() if s['stage']=='LONG' and s['id'] not in EXPECTED_IDS]
def enabled_ids():return []
