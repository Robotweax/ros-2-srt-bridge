"""One readiness plus one SDKROS N0/1701/10s diagnostic, never a campaign grant."""
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SCOPE='one-native-readiness-one-SDKROS-N0-1701-10s-task-calibration'
CANDIDATE_SHA='6deab3c5e83e48b7c33dbbb4613c361469d9b62aa1bea86db0c1a8012cfae72e'
def disabled_ids():return [r['id'] for r in json.loads((ROOT/'evidence/m3-closure-plan-2026-11-09/plan.json').read_text())['proposed_future_cases']]
def remaining_ids():return [r['slot']['id'] for r in json.loads((ROOT/'evidence/m3-current-long-execution-2026-11-10/cohort.json').read_text())['rows'] if r['status']=='not_executed']
def authorize(grant,digest):
    expected=dict(scope=SCOPE,freeze_sha256=digest,execute=True,readiness_checks=1,SDKROS_fixture_limit=1,profile='N0',seed=1701,source_seconds=10,task_visibility=True,module_manifest_sha256=hashlib.sha256((HERE/'bindings.json').read_bytes()).hexdigest(),disabled_case_ids=disabled_ids(),remaining_case_ids_disabled=remaining_ids(),N1_2903_rerun=False,historical_failure_preserved=True,no_tuning=True,no_retries=True,stop_first_failed_gate=True)
    if grant!=expected:raise ValueError('exact one-readiness/one-SDKROS calibration grant required')
