"""Exactly seven never-executed LONG cases; stopped N1 verdicts are immutable."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCOPE='seven-remaining-N1-N2-N5-calibrated-task-lifecycle'
EXPECTED_IDS=['N1-combined-4211','N2-combined-1701','N2-combined-2903','N2-combined-4211','N5-combined-1701','N5-combined-2903','N5-combined-4211']
IDENTITY_HELPER_PATH='evidence/m3-current-n0-preparation-2026-11-10/shutdown_observer.py'
IDENTITY_HELPER_SHA256='f4b2d9ed4f31bded2772d61081b7a9de8ac88ebfabc7ef690f24f149515868d3'
LIFECYCLE_ASSESSMENT_PATH='evidence/m3-current-n0-stable-preparation-2026-11-10/launch_assessment.py'
LIFECYCLE_ASSESSMENT_SHA256='6ec8d26e7b932db6ce7dd7bfe6f381244f594bdbcb35900bea267edc1b8afde3'
def original():return json.loads((ROOT/'evidence/m3-closure-plan-2026-11-09/plan.json').read_text())['proposed_future_cases']
def cases():
    fields=('id','ordinal','stage','profile','seed','source_seconds');rows=[dict({k:s[k] for k in fields},runtime_layout='socket-disposition') for s in original() if s['id'] in EXPECTED_IDS]
    if [s['id'] for s in rows]!=EXPECTED_IDS or [s['ordinal'] for s in rows]!=list(range(32,39)) or [s['source_seconds'] for s in rows]!=[600]*4+[300]*3:raise ValueError('seven remaining cases differ')
    prior=json.loads((ROOT/'evidence/m3-current-long-execution-2026-11-10/cohort.json').read_text())
    if [s['status'] for s in prior['rows']]!=['passed','failed']+['not_executed']*7 or [s['slot']['id'] for s in prior['rows'][2:]]!=EXPECTED_IDS:raise ValueError('stopped cohort differs')
    return rows
def allowed(profile,seed,seconds):return (profile,seed,seconds) in [(s['profile'],s['seed'],s['source_seconds']) for s in cases()]
def disabled_ids():return [s['id'] for s in original() if s['id'] not in EXPECTED_IDS]
def completed_ids():return [s['id'] for s in original() if s['stage']!='LONG']
def historical_case_ids_excluded():return ['N1-combined-1701','N1-combined-2903']

def enabled_ids():return []
