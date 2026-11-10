"""Closed-file diagnostic gates; never infer missing stages or replace failures."""
import importlib.util
import json
from pathlib import Path
from m3_observer_filtering import require_role
from m3_closure_assessor import assess_n3_result,validate_n3_artifacts,cleanup
ROOT=Path(__file__).resolve().parents[2]


from lifecycle import coverage


def assess(out,result,slot):
    proof=dict(status='failed',qualification=False,original_hang_cause='unknown',remaining_campaign_cases_disabled=29,fresh_N3_case=True,historical_4211_failure_preserved=True,no_tuning=True)
    try:
        reports={r:json.loads((out/(r+'-child-shutdown.json')).read_text()) for r in ('operator','robot')}
        child=next(c for c in reports['operator']['children'] if '-bridge-' in c['name'])
        ready=json.loads((out/'operator-observer-ready.json').read_text());info=json.loads((out/'operator-bridge-identity.json').read_text())
        if ready['ready_ns']>child['signal_begin_ns']:raise ValueError('observer ready after signal')
        require_role(info['permissions'],0)
        rows=[json.loads(x) for x in (out/'native-observer/blocked-target-shutdown-stacks.jsonl').read_text().splitlines()]
        if rows[0]['root']['start_ticks']!=info['start_ticks'] or rows[0]['boot_id']['text'].strip()!=info['boot_id']:raise ValueError('target/clock identity mismatch')
        stages=[json.loads(x) for x in (out/'operator-shutdown-stages.jsonl').read_text().splitlines()]
        proof['operator_observer']=coverage(rows,child,stages)
        proof['operator_stages_observed']=[x['point'] for x in stages]
        if not child['passed'] or child['forced_kill'] or child['returncode']!=0:raise ValueError('bridge shutdown failed; partial stages/stacks retained, no retry')
        # Preserve common stage gates; require explicit socket disposition evidence.
        import stage_gate as module
        proof['stages']={role:module.trace_check(out/(role+'-shutdown-stages.jsonl'),next(c for c in reports[role]['children'] if '-bridge-' in c['name'])['pid']) for role in reports}
        if result['status']!='passed':raise ValueError('workload failed: '+str(result.get('error')))
        proof['sensor']=assess_n3_result(result,slot);validate_n3_artifacts(out,result,slot);cleanup(out)
        proof.update(status='passed',qualification='strict_N3_case_with_shutdown_controls')
    except (OSError,ValueError,KeyError,IndexError,StopIteration) as error:proof['error']=str(error)
    return proof
