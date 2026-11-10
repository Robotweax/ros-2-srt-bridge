"""Exact fresh ordered seven-case grant; no subset, retries or old N1 cases."""
import hashlib
from pathlib import Path
from cases import SCOPE,cases,disabled_ids,completed_ids,historical_case_ids_excluded
HERE=Path(__file__).resolve().parent
CANDIDATE_SHA='6deab3c5e83e48b7c33dbbb4613c361469d9b62aa1bea86db0c1a8012cfae72e'
def authorize(value,digest):
    expected=dict(scope=SCOPE,freeze_sha256=digest,execute=True,case_ids=[s['id'] for s in cases()],disabled_case_ids=disabled_ids(),completed_case_ids_not_reexecuted=completed_ids(),historical_LONG_case_ids_excluded=historical_case_ids_excluded(),module_manifest_sha256=hashlib.sha256((HERE/'bindings.json').read_bytes()).hexdigest(),task_visibility=True,SDK_provider_visibility=True,N1_2903_rerun=False,historical_failures_preserved=True,no_tuning=True,no_retries=True,stop_first_failed_gate=True)
    if value!=expected:raise ValueError('exact ordered seven-case grant required; no old N1 case or subset')
