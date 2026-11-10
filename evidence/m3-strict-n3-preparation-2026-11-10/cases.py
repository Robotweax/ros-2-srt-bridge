"""Fixed N3-only plan; no dispatcher, case override or retry entry point."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCOPE='fresh-strict-nine-case-N3-socket-disposition'


def cases():
    return [dict(id='N3-'+label+'-'+str(seed),ordinal=i*3+losses+1,stage='N3',seed=seed,losses=losses,source_seconds=30,runtime_layout='socket-disposition') for i,seed in enumerate((1701,2903,4211)) for losses,label in enumerate(('baseline','one-loss','two-loss'))]


def disabled_ids():
    # Historical ID list is read only; its old execution grant is never used.
    data=json.loads((ROOT/'evidence/m3-n3-frozen-cohort-2026-11-09/authorization.json').read_text())
    if data['case_ids']!=[s['id'] for s in cases()] or len(data['disabled_case_ids'])!=29:raise ValueError('historical case identity/order differs')
    return data['disabled_case_ids']


def authorize(value,freeze_sha):
    expected=dict(scope=SCOPE,freeze_sha256=freeze_sha,execute=True,case_ids=[s['id'] for s in cases()],disabled_case_ids=disabled_ids(),seed4211_execution_authorized=True,historical_failures_preserved=True,no_tuning=True,no_automatic_retries=True)
    if value!=expected:raise ValueError('grant must bind exactly nine fresh ordered N3 cases and all29 disabled IDs')
