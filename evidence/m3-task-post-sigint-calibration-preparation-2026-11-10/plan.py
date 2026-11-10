"""One readiness check and one controlled target; no campaign dispatch."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCOPE='one-readiness-one-native-post-sigint-task-assessment-calibration'
CANDIDATE_SHA='6deab3c5e83e48b7c33dbbb4613c361469d9b62aa1bea86db0c1a8012cfae72e'
def disabled_ids():return [r['id'] for r in json.loads((ROOT/'evidence/m3-closure-plan-2026-11-09/plan.json').read_text())['proposed_future_cases']]
def remaining_ids():return [r['slot']['id'] for r in json.loads((ROOT/'evidence/m3-current-long-execution-2026-11-10/cohort.json').read_text())['rows'] if r['status']=='not_executed']
def assessment_hashes():
    import hashlib
    return {name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in ('task_assessment.py','lifecycle.py')}
def authorize(value,digest):
    expected=dict(scope=SCOPE,freeze_sha256=digest,execute=True,candidate_collector_sha256=CANDIDATE_SHA,readiness_checks=1,controlled_target_limit=1,task_visibility=True,post_sigint_calibration=True,assessment_candidate_sha256=assessment_hashes(),disabled_case_ids=disabled_ids(),remaining_case_ids_disabled=remaining_ids(),N1_2903_rerun=False,historical_failure_preserved=True,no_tuning=True,no_retries=True,stop_first_failed_gate=True)
    if value!=expected:raise ValueError('exact one-readiness/one-target calibration grant required')
