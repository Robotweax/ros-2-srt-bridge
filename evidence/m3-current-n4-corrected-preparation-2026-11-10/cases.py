"""The exact19 declared N4 cases only; no legacy batch or override entry point."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SCOPE='current-build-nineteen-N4-socket-disposition'
PLAN=ROOT/'evidence/m3-closure-plan-2026-11-09/plan.json'


def original():return json.loads(PLAN.read_text())['proposed_future_cases']

def cases():
    fields=('id','ordinal','stage','profile','seed','phase','direction','source_seconds','hold_seconds','expected_outcome')
    rows=[dict({k:s[k] for k in fields if k in s},runtime_layout='socket-disposition') for s in original() if s['stage']=='N4']
    if len(rows)!=19 or [s['ordinal'] for s in rows]!=list(range(11,30)):raise ValueError('N4 declared order differs')
    return rows

def disabled_ids():return [s['id'] for s in original() if s['stage'] not in ('N0','N3','N4')]
def completed_ids():return [s['id'] for s in original() if s['stage'] in ('N0','N3')]

def authorize(value,freeze_sha):
    expected=dict(scope=SCOPE,freeze_sha256=freeze_sha,execute=True,case_ids=[s['id'] for s in cases()],disabled_case_ids=disabled_ids(),completed_case_ids_not_reexecuted=completed_ids(),runtime_layout='socket-disposition',native_hold_seconds=2,historical_failures_preserved=True,no_tuning=True,no_automatic_retries=True,stop_first_failed_gate=True)
    if value!=expected:raise ValueError('grant must bind exact19 N4 cases,9 disabled IDs and10 completed exclusions')

def invocation(slot):
    if slot not in cases():raise ValueError('case settings differ from frozen19')
    if slot['id'].startswith('N4-ROS-'):
        return dict(adapter='ros',kwargs=dict(mode=slot.get('direction',slot.get('phase')),runtime_layout='socket-disposition'))
    return dict(adapter='native',kwargs=dict(phase=slot['phase'],direction=slot['direction'],hold_seconds=2,runtime_layout='socket-disposition'))
