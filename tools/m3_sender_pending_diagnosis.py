"""Retrospective sender deferral audit. Never opens a bridge or submits a command."""
import argparse
import json
from pathlib import Path

from m3_command_trace import summarize_run
from m3_dds_result_timeline import read_journal
from m3_runtime_layout import matched
from m3_source_preflight import ROOT, sha


def reconcile(events, sender, row, fenced_end):
    """Require an observed drop and a successful, later session invalidation chain.

    Events are from one complete sender incarnation, sorted by local timestamp.
    This explains local state; it does not prove peer nonexecution.
    """
    identity=row['number'].to_bytes(16,'little').hex()
    own=[e for e in events if e['request']==identity]
    def one(point):
        found=[e for e in own if e['point']==point]
        if len(found)!=1:raise ValueError('missing or ambiguous sender stage '+str(point))
        return found[0]
    admission,queued,deferred,dropped=(one(p) for p in (5,6,29,21))
    if any(e['session']!=sender['session'] or e['owner_epoch']!=sender['owner_epoch'] or e['route']!=sender['route'] for e in (admission,queued,deferred,dropped)):
        raise ValueError('original sender context mismatch')
    if (admission['value'],queued['value'],deferred['value'],deferred['reason'],dropped['reason'])!=(1,0,13,7,5):
        raise ValueError('not the queued clock-deferral/deadline-drop path')
    origin=sender['source_ns'];deadline=sender['deadline_ns']
    stamps=[e['monotonic_ns'] for e in (admission,queued,deferred,dropped)]
    if not origin<stamps[0]<stamps[1]<stamps[2]<deadline<=stamps[3]<fenced_end:
        raise ValueError('invalid original deadline or observation boundary')
    if any(e['point']==25 for e in own):raise ValueError('original SDK handoff observed')
    if (sender['state'],sender['reason'],sender['revision'],sender['result_valid'])!=(8,2,0,False):
        raise ValueError('closed sender is not provisional UNKNOWN')
    relevant=[e for e in events if e['session']==sender['session'] and e['point'] in (2,3,4)]
    if any(origin<=e['monotonic_ns']<=fenced_end for e in relevant):
        raise ValueError('session invalidation inside observation window')
    chain=[]
    for point in (2,3,4):
        found=[e for e in relevant if e['point']==point and e['monotonic_ns']>fenced_end and e['reason']==1]
        if len(found)!=1:raise ValueError('missing or ambiguous teardown invalidation')
        chain.append(found[0])
    if not chain[0]['monotonic_ns']<=chain[1]['monotonic_ns']<chain[2]['monotonic_ns'] or chain[2]['value']!=0:
        raise ValueError('unsuccessful teardown invalidation')
    last=row['last_status_observation']
    if not dropped['monotonic_ns']<last['observed_monotonic_ns']<fenced_end or last['state']!=1 or row.get('terminal') is not None:
        raise ValueError('unexpected terminal or cached status')
    return dict(identity=identity,source_stages=[admission,queued,deferred,dropped],
        original_budget_ns=deadline-origin,deferral_after_origin_ns=stamps[2]-origin,
        drop_after_deadline_ns=stamps[3]-deadline,
        last_observed_status=last,observation_end_ns=fenced_end,
        teardown_invalidation=chain,
        invalidate_completed_after_drop_ns=chain[-1]['monotonic_ns']-stamps[3],
        exact_sender_clock_error=None,source_compatible_clock_errors=['unqualified','expired'],
        clock_scope='Point29 records SessionError13, not ClockError. Its zero clock fields are unused defaults. No historical probe-age versus interval-width attribution.',
        reconciliation='Volatile pending input is released without a journal RPC. GET/QUERY do not mint tickets; NOT_FOUND does not overwrite durable state. Later session invalidation explains closed UNKNOWN/reconcile_required.',
        outcome_authority=False,replay_authority=False)


def diagnose(run, manifest):
    hashes=json.loads(manifest.read_text())
    def verify_raw():
        for name,value in hashes.items():
            if sha(ROOT/name)!=value['sha256']:raise ValueError('retained evidence changed: '+name)
    verify_raw();runtime=matched(ROOT,'start-trace')
    data=json.loads((run/'run.json').read_text())
    rows=[c for c in data['results']['commands'] if c.get('terminal')!=4]
    if len(rows)!=1:raise ValueError('expected one original unresolved attempt')
    row=rows[0];identity=row['number'].to_bytes(16,'little').hex()
    sender=read_journal(run/'operator.sqlite',1)['entries'][identity]
    receiver=read_journal(run/'robot.sqlite',2)['entries'].get(identity)
    if receiver is not None:raise ValueError('receiver journal entry exists')
    traces=summarize_run(run)
    sources=[t for name,t in traces.items() if name.startswith('operator-') and any(e['request']==identity for e in t['events'])]
    if len(sources)!=1:raise ValueError('ambiguous sender incarnation')
    for name,t in traces.items():
        if name.startswith('robot-') and any(e['request']==identity and (e['point'] in range(40,45) or (e['point']==32 and e['detail']==6)) for e in t['events']):
            raise ValueError('receiver COMMAND/start observed')
    result=reconcile(sources[0]['events'],sender,row,data['results']['endpoint_fenced_interval_ns'][1])
    names=['src/robotweax_srt_bridge_core/src/'+p for p in ('session.cpp','clock.cpp','transport/transport.cpp','journal/journal.cpp','worker/supervisor.cpp','worker/runtime.cpp')]
    names+=['src/robotweax_srt_bridge_transport/endpoint.cpp','ros2/robotweax_srt_bridge_demo/scripts/scenario_journal.py','ros2/robotweax_srt_bridge_demo/scripts/m3_scenario.py']
    source={n:sha(ROOT/n) for n in names}
    if any(value!=data['source_sha256'][n] for n,value in source.items()):raise ValueError('diagnosed source differs from captured source')
    verify_raw()
    if runtime!=matched(ROOT,'start-trace'):raise ValueError('runtime changed during audit')
    result.update(run=str(run.relative_to(ROOT)),closed_sender=sender,receiver_entry=None,
        source_sha256=source,raw_files_verified=len(hashes),raw_manifest_sha256=sha(manifest),
        runtime=runtime,trace_complete=True,
        scope='Retrospective read-only evidence and source audit; no new execution, tuning, forced expiry, command replay or journal recovery. UNKNOWN remains unresolved.')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    # Refuse to overwrite an evidence artifact or place output in the source run.
    out=args.out.resolve();run=args.run.resolve()
    if out.exists() or out.is_relative_to(run):raise ValueError('output must be a new artifact outside the retained run')
    result=diagnose(run,args.manifest.resolve());out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as file:json.dump(result,file,indent=2);file.write('\n')
    print('Verified original sender deferral, deadline drop and teardown reconciliation; UNKNOWN retained')
