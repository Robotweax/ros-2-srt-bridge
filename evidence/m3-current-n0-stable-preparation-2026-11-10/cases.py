"""Only the predeclared current-build N0 case; all other stages disabled."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
IDENTITY_HELPER_PATH='evidence/m3-current-n0-preparation-2026-11-10/shutdown_observer.py'
IDENTITY_HELPER_SHA256='f4b2d9ed4f31bded2772d61081b7a9de8ac88ebfabc7ef690f24f149515868d3'
LIFECYCLE_ASSESSMENT_PATH='evidence/m3-current-n0-stable-preparation-2026-11-10/launch_assessment.py'
LIFECYCLE_ASSESSMENT_SHA256='6ec8d26e7b932db6ce7dd7bfe6f381244f594bdbcb35900bea267edc1b8afde3'
SCOPE='current-build-N0-combined-stabilized-lifecycle-v4-socket-disposition'

def cases():
    return [dict(id='N0-combined-1701',ordinal=10,stage='N0',profile='N0',seed=1701,source_seconds=300,runtime_layout='socket-disposition')]

def disabled_ids():
    plan=json.loads((ROOT/'evidence/m3-closure-plan-2026-11-09/plan.json').read_text())['proposed_future_cases']
    n0=[s for s in plan if s['stage']=='N0']
    if len(n0)!=1 or any(n0[0][k]!=cases()[0][k] for k in ('id','ordinal','stage','profile','seed','source_seconds')):raise ValueError('historical N0 scope differs')
    return [s['id'] for s in plan if s['stage'] not in ('N0','N3')]

def authorize(value,freeze_sha):
    expected=dict(scope=SCOPE,freeze_sha256=freeze_sha,execute=True,case_ids=[s['id'] for s in cases()],disabled_case_ids=disabled_ids(),launch_readiness_harness_revision='stabilized-lifecycle-v1',lifecycle_assessment_sha256=LIFECYCLE_ASSESSMENT_SHA256,identity_helper_sha256=IDENTITY_HELPER_SHA256,completed_N3_not_reexecuted=True,historical_failures_preserved=True,no_tuning=True,no_automatic_retries=True)
    if value!=expected:raise ValueError('grant must bind exactly N0/1701/300s and all28 disabled IDs')
