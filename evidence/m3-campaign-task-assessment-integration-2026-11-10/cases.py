"""Exact final nine current-build cases; all completed stages excluded."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PLAN=ROOT/'evidence/m3-closure-plan-2026-11-09/plan.json'
SCOPE='current-build-nine-N1-N2-N5-stabilized-lifecycle-socket-disposition'
IDENTITY_HELPER_PATH='evidence/m3-current-n0-preparation-2026-11-10/shutdown_observer.py'
IDENTITY_HELPER_SHA256='f4b2d9ed4f31bded2772d61081b7a9de8ac88ebfabc7ef690f24f149515868d3'
LIFECYCLE_ASSESSMENT_PATH='evidence/m3-current-n0-stable-preparation-2026-11-10/launch_assessment.py'
LIFECYCLE_ASSESSMENT_SHA256='6ec8d26e7b932db6ce7dd7bfe6f381244f594bdbcb35900bea267edc1b8afde3'

def original():return json.loads(PLAN.read_text())['proposed_future_cases']
def cases():
    fields=('id','ordinal','stage','profile','seed','source_seconds')
    rows=[dict({k:s[k] for k in fields},runtime_layout='socket-disposition') for s in original() if s['stage']=='LONG']
    expected=[(p,s,600 if p in ('N1','N2') else 300) for p in ('N1','N2','N5') for s in (1701,2903,4211)]
    if [(s['profile'],s['seed'],s['source_seconds']) for s in rows]!=expected or [s['ordinal'] for s in rows]!=list(range(30,39)):raise ValueError('nine declared cases differ')
    return rows
def allowed(profile,seed,seconds):return False
def completed_ids():return [s['id'] for s in original() if s['stage']!='LONG']
def disabled_ids():return [s['id'] for s in original()]
def enabled_ids():return []
def authorize(value,freeze_sha):raise ValueError('offline integration only; no campaign grant accepted')
