"""Closed-file diagnostic gates; never infer missing stages or replace failures."""
import importlib.util
import json
from pathlib import Path
from m3_observer_filtering import require_role
from m3_closure_assessor import assess_combined,cleanup
ROOT=Path(__file__).resolve().parents[2]


from lifecycle import coverage
from launch_assessment import assess_launches


def assess(out,result,slot):
    proof=dict(status='failed',qualification=False,original_hang_cause='unknown',remaining_campaign_cases_disabled=28,fresh_N0_case=True,historical_4211_failure_preserved=True,no_tuning=True)
    try:
        reports={r:json.loads((out/(r+'-child-shutdown.json')).read_text()) for r in ('operator','robot')}
        launches=assess_launches(out,reports);proof['launches']=launches
        final=launches['operator']['measurement'];child=final['child']
        ready=json.loads((out/'operator-observer-ready.json').read_text());info=final['identity']
        if ready['ready_ns']>child['signal_begin_ns']:raise ValueError('observer ready after signal')
        require_role(info['permissions'],0)
        rows=[json.loads(x) for x in (out/'native-observer/blocked-target-shutdown-stacks.jsonl').read_text().splitlines()]
        if rows[0]['root']['start_ticks']!=info['start_ticks'] or rows[0]['boot_id']['text'].strip()!=info['boot_id']:raise ValueError('target/clock identity mismatch')
        stages=final['stages']['rows']
        proof['operator_observer']=coverage(rows,child,stages)
        proof['operator_stages_observed']=[x['point'] for x in stages]
        if not child['passed'] or child['forced_kill'] or child['returncode']!=0:raise ValueError('bridge shutdown failed; partial stages/stacks retained, no retry')
        # Preserve common stage gates; require explicit socket disposition evidence.
        proof['stages']={role:{purpose:item['stages'] for purpose,item in values.items()} for role,values in launches.items()}
        if result['status']!='passed':raise ValueError('workload failed: '+str(result.get('error')))
        proof['combined']=assess_combined(result,out,slot);cleanup(out)
        proof.update(status='passed',qualification='strict_N0_combined_case_with_shutdown_controls')
    except (OSError,ValueError,KeyError,IndexError,StopIteration,TypeError) as error:proof['error']=str(error)
    return proof
