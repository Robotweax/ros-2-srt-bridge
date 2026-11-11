"""Closed-cohort joins only. Never execute, recover, replay or alter a command."""
import json,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_loaded_start_analysis import analyze as starts
from m3_loaded_arp_analysis import analyze as arp
from m3_loaded_arp_steps import analyze as steps
from m3_arp_packet_windows import analyze as packets
from m3_command_trace import summarize_run
from m3_sender_trace_analysis import summarize as sender

out=ROOT/'evidence/m3-sender-loaded-repair-cohort-2026-11-09';base=ROOT/'.local/m3-sender-loaded-repair-cohort-2026-11-09'
execution=json.loads((base/'execution.json').read_text());manifest=json.loads((out/'local-artifact-hashes.json').read_text());(out/'analysis').mkdir(exist_ok=True)
assert all(r['status']=='passed' for r in execution['rows']) and execution['runtime_unchanged']
summaries=[]
for slot in execution['rows']:
    label=slot['slot']['label'];run=ROOT/slot['run'];data=json.loads((run/'run.json').read_text())
    assert all(sha(ROOT/n)==h for n,h in data['source_sha256'].items())
    all_starts=starts(run,manifest);write(out/'analysis'/(label+'-starts.json'),dict(status='passed',analysis=all_starts))
    primary=dict(status='passed',analysis=arp(run,manifest));write(out/'analysis'/(label+'-arp.json'),primary)
    increments=dict(status='passed',analysis=steps(run,primary,manifest));write(out/'analysis'/(label+'-steps.json'),increments)
    lifetimes=packets(run,primary,increments,manifest);write(out/'analysis'/(label+'-packets.json'),dict(status='passed',analysis=lifetimes))
    traces=summarize_run(run);observations=sender(traces);assert observations==data['sender_diagnostics']
    events=[dict(file=n,**e) for n,t in traces.items() for e in t['events']]
    proof=slot['analysis']['progress']['entries'];known={p['number'].to_bytes(16,'little').hex():p for p in proof}
    # Every original request is kept, not just the one with a clock observation.
    joined=[]
    for identity,p in known.items():
        local=[e for e in observations['events'] if e['request']==identity];a=p['sender'];assert a is not None
        for e in local:
            assert e['owner_epoch']==a['owner_epoch'] and e['route']==a['route']
            if e['point'] in (45,46) or e['journal_entry_available']:
                assert e['session']==a['session'] and e['origin_ns']==a['source_ns'] and e['command_deadline_ns']==a['deadline_ns'] and e['entry_owner_epoch']==a['owner_epoch']
        joined.append(dict(number=p['number'],proof=p,sender_events=local))
    assert all(e['request'] in known or (e['point']==47 and e['detail']==5 and not e['journal_entry_available']) for e in observations['events'])
    write(out/'analysis'/(label+'-sender-all-attempts.json'),dict(all_attempts=joined,counts=observations['counts'],scope=observations['scope']))
    clock_groups=[]
    for row in joined:
        clock=[e for e in row['sender_events'] if e['point']==45]
        if not clock:continue
        checks=[]
        for e in clock:
            check=dict(event=e,probe_age_ns=None,probe_age_excess_ns=None,offset_width_at_probe_ns=None,drift_expanded_width_ns=None)
            if e['clock_observed']:
                age=e['evaluated_ns']-e['probe_anchor_ns'];width=e['offset_upper_ns']-e['offset_lower_ns'];c=data['clock_assumptions']
                expanded=width+2*((age*c['relative_drift_ppm']+999999)//1000000)
                check.update(probe_age_ns=age,probe_age_excess_ns=age-c['max_probe_age_ns'],offset_width_at_probe_ns=width,drift_expanded_width_ns=expanded)
                expected=2 if age>c['max_probe_age_ns'] else 1 if expanded>data['max_clock_interval_ms']*1000000 else 0
                assert e['clock_error']==expected
            else:assert e['clock_error']==1
            checks.append(check)
        related=[e for e in events if e['request']==row['proof']['number'].to_bytes(16,'little').hex()]
        sdk=[e for e in related if e['file'].startswith('operator-') and e['point']==25]
        releases=[e for e in row['sender_events'] if e['point']==46]
        # The observed successful case must keep the same original proof/deadline.
        assert [e['detail'] for e in clock]==[1,2] and len(releases)==1 and releases[0]['value']==4 and len(sdk)==1
        assert row['proof']['terminal']==4 and row['proof']['sender']['state']==row['proof']['receiver']['state']==4
        assert not any(e['point'] in (21,24,27) and e['file'].startswith('operator-') for e in related)
        clock_groups.append(dict(number=row['number'],proof=row['proof'],clock_checks=checks,
            deferral_to_recovery_ns=clock[1]['evaluated_ns']-clock[0]['evaluated_ns'],
            original_budget_remaining_at_recovery_ns=clock[1]['command_deadline_ns']-clock[1]['evaluated_ns'],
            sender_events=row['sender_events'],all_original_request_events=related,sdk_handoffs=sdk,
            scope='New intent only: natural probe-lease expiration and recovery, same original command budget, authoritative matching closed success. No historical118 ClockError or causal ARP/probe-delay attribution.'))
    write(out/'analysis'/(label+'-deferrals.json'),dict(run=slot['run'],clock_groups=clock_groups,counts=observations['counts'],clock_assumptions=data['clock_assumptions'],max_clock_interval_ms=data['max_clock_interval_ms']))
    actual=[r for r in all_starts['all_attempts'] if r.get('actual_slack_ns')]
    minima={k:min(r['actual_slack_ns'][k] for r in actual if r['actual_slack_ns'][k] is not None) for k in ('consume','second_gate','command_budget_at_consume')}
    summaries.append(dict(label=label,run=slot['run'],harness_status=data['status'],audit=slot['analysis']['progress']['audit'],skipped=slot['analysis']['progress']['skipped_slots'],durable=slot['analysis']['durable_outcomes'],active_context_events=len(slot['analysis']['active_context_events']),sender_counts=observations['counts'],clock_groups=[dict(number=g['number'],deferral_to_recovery_ns=g['deferral_to_recovery_ns'],original_budget_remaining_at_recovery_ns=g['original_budget_remaining_at_recovery_ns']) for g in clock_groups],start_branches=all_starts['branch_counts'],unavailable_starts=all_starts['unavailable_starts'],minimum_actual_slack_ns=minima,primary_packet_windows=lifetimes['primary_windows'],positive_reply_steps=len(lifetimes['positive_steps']),missing_source_reply_steps=[s for s in lifetimes['positive_steps'] if not s['witness']['source_replies_in_outer_envelope']],packet_counts={r:v['counts'] for r,v in data['arp_packet_diagnostics'].items()},measurement=data['measurement_window']))
    print(label,'all-attempt/start/sender/packet joins passed; clock groups',len(clock_groups),flush=True)
assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest.items())
write(out/'summary.json',summaries)
