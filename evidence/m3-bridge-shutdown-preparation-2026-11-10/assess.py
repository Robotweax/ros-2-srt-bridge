"""Closed-file diagnostic gates; never infer missing stages or replace failures."""
import importlib.util
import json
from pathlib import Path
from m3_observer_filtering import require_role
from m3_closure_assessor import assess_n3_result,validate_n3_artifacts,cleanup
ROOT=Path(__file__).resolve().parents[2]


def coverage(rows,child):
    begin,footer=rows[0],rows[-1]
    if begin['kind']!='begin' or begin['mode']!='procfs' or not begin['observer_independent'] or begin['root']['pid']!=child['pid'] or begin['pid']==child['pid']:raise ValueError('observer identity/mode failure')
    if footer.get('kind')!='status' or not footer['completed'] or footer['budget_exhausted']:raise ValueError('observer finalization/budget failure')
    samples=[s for s in rows if s['kind']=='sample' and s['end_ns']<=child['end_ns']]
    post=[s for s in samples if child['signal_end_ns']<=s['begin_ns']]
    available=0
    for s in samples:
        if s['process_limit_hit']:raise ValueError('observer process budget exceeded')
        for process in s['processes']:
            if process['status']!='sampled' or not process['identity_still_matches'] or process['threads_truncated']:raise ValueError('live target observation incomplete')
            for t in process['threads']:
                k=t['kernel_stack']
                if k['status']!='ok' or k['truncated']:raise ValueError('live target kernel stack unavailable')
                if k['text'].strip():available+=1
    if available==0:raise ValueError('no real bridge kernel-stack sample')
    if child['forced_kill'] and (len(post)<2 or not any(t['kernel_stack'].get('text','').strip() for s in post for p in s['processes'] for t in p.get('threads',[]))):raise ValueError('shutdown failure lacks bounded post-signal stack coverage')
    return dict(samples=len(samples),post_signal_samples=len(post),nonempty_kernel_stacks=available,clean_fast_exit_may_have_no_post_signal_sample=True)


def assess(out,result):
    proof=dict(status='failed',qualification=False,original_hang_cause='unknown',remaining_campaign_cases_disabled=29,retry_two_loss_4211=False,no_tuning=True)
    try:
        reports={r:json.loads((out/(r+'-child-shutdown.json')).read_text()) for r in ('operator','robot')}
        child=next(c for c in reports['operator']['children'] if '-bridge-' in c['name'])
        ready=json.loads((out/'operator-observer-ready.json').read_text());info=json.loads((out/'operator-bridge-identity.json').read_text())
        if ready['ready_ns']>child['signal_begin_ns']:raise ValueError('observer ready after signal')
        require_role(info['permissions'],0)
        rows=[json.loads(x) for x in (out/'native-observer/blocked-target-shutdown-stacks.jsonl').read_text().splitlines()]
        if rows[0]['root']['start_ticks']!=info['start_ticks'] or rows[0]['boot_id']['text'].strip()!=info['boot_id']:raise ValueError('target/clock identity mismatch')
        proof['operator_observer']=coverage(rows,child)
        stages=[json.loads(x) for x in (out/'operator-shutdown-stages.jsonl').read_text().splitlines()]
        proof['operator_stages_observed']=[x['point'] for x in stages]
        if not child['passed'] or child['forced_kill'] or child['returncode']!=0:raise ValueError('bridge shutdown failed; partial stages/stacks retained, no retry')
        # Reuse exact calibrated stage requirements for a healthy bridge only.
        spec=importlib.util.spec_from_file_location('prior_shutdown_calibration',ROOT/'evidence/m3-shutdown-live-calibration-2026-11-09/calibrate.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        proof['stages']={role:module.trace_check(out/(role+'-shutdown-stages.jsonl'),next(c for c in reports[role]['children'] if '-bridge-' in c['name'])['pid']) for role in reports}
        if result['status']!='passed':raise ValueError('workload failed: '+str(result.get('error')))
        slot=dict(source_seconds=10,seed=1701,losses=0)
        proof['sensor']=assess_n3_result(result,slot);validate_n3_artifacts(out,result,slot);cleanup(out)
        proof['status']='passed'
    except (OSError,ValueError,KeyError,IndexError,StopIteration) as error:proof['error']=str(error)
    return proof
