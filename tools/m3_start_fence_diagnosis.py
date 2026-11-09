#!/usr/bin/env python3
"""Read-only start-stage diagnosis; admission clock samples never become grants."""
import argparse,json,subprocess
from pathlib import Path
from m3_source_preflight import ROOT,sha
from m3_n5_progress import command_progress
from m3_command_trace import summarize_run
from m3_dds_result_timeline import common_clock

SOURCES=['src/robotweax_srt_bridge_transport/endpoint.cpp','src/robotweax_srt_bridge_core/src/transport/transport.cpp','src/robotweax_srt_bridge_core/src/worker/runtime.cpp','src/robotweax_srt_bridge_core/src/worker/execution_pool.cpp','src/robotweax_srt_bridge_core/src/journal/journal.cpp','src/robotweax_srt_bridge_core/include/robotweax/srt_bridge/clock.hpp','src/robotweax_srt_bridge_core/include/robotweax/srt_bridge/command_trace.hpp','proto/commands_v1.proto','ros2/robotweax_srt_bridge/include/robotweax_srt_bridge/ros_rate_backend.hpp']


def join(entry,command,admissions):
    number=entry['number'];identity=number.to_bytes(16,'little').hex();a=entry['sender'];b=entry['receiver']
    if command['number']!=number or entry['terminal']!=command.get('terminal') or a['state']!=b['state'] or a['state']!=entry['terminal'] or a['reason']!=b['reason'] or b['reason']!=command.get('reason'):raise ValueError('outcome mismatch')
    if (b['state'],b['reason']) not in ((4,0),(6,1)):raise ValueError('outcome outside success/context-rejection scope')
    for field in ('route','payload_hash','session','source_epoch','source_ns'):
        if a[field]!=b[field]:raise ValueError('journal context mismatch: '+field)
    if a['owner_epoch']!=a['source_epoch'] or not b['owner_epoch'] or a['owner_epoch']==b['owner_epoch']:raise ValueError('journal owner scope')
    if any(e.get('request')!=identity or e.get('session')!=a['session'] or e.get('route')!=a['route'] or e.get('origin_ns')!=a['source_ns'] or e.get('detail')!=6 for e in admissions):raise ValueError('admission identity/context mismatch')
    if not admissions:raise ValueError('no original COMMAND admission')
    for e in admissions:
        if e.get('point') not in (32,36) or e.get('value')!=0 or e.get('clock_error')!=0 or e.get('age_error')!=0:raise ValueError('unqualified admission')
        if any(type(e.get(k)) is not int or e[k]<=0 for k in ('evaluated_ns','monotonic_ns','clock_deadline_ns','request_sequence')) or not e['evaluated_ns']<=e['monotonic_ns'] or e['clock_deadline_ns']<=e['evaluated_ns']:raise ValueError('admission clock bracket')
    last=max(admissions,key=lambda e:e['monotonic_ns'])
    times=[a['source_ns'],a['admitted_ns'],b['admitted_ns'],b['dispatched_ns'],b['finished_ns'],a['finished_ns'],command['result_observed_monotonic_ns']]
    if any(type(t) is not int or t<=0 for t in times) or times!=sorted(times):raise ValueError('journal timeline invalid')
    if not a['source_ns']<=last['evaluated_ns']<=last['monotonic_ns']<=b['dispatched_ns'] or b['finished_ns']>=b['deadline_ns'] or a['finished_ns']>=a['deadline_ns']:raise ValueError('start-stage timeline/budget scope')
    if b['state']==6 and (a['result_valid'] or b['result_valid'] or command.get('result_valid')):raise ValueError('rejection with valid result')
    if b['state']==4 and not(a['result_valid'] and b['result_valid'] and command.get('result_valid')):raise ValueError('success without result')
    lease=last['clock_deadline_ns']
    return dict(number=number,request_id=identity,terminal=b['state'],reason=b['reason'],sender=a,receiver=b,admissions=admissions,last_admission=last,
        admission_clock_margin_ns=lease-last['evaluated_ns'],dispatch_minus_observed_clock_deadline_ns=b['dispatched_ns']-lease,
        receiver_admission_to_dispatch_ns=b['dispatched_ns']-b['admitted_ns'],dispatch_to_receiver_finish_ns=b['finished_ns']-b['dispatched_ns'],receiver_finish_to_sender_observation_ns=a['finished_ns']-b['finished_ns'],sender_observation_to_driver_observation_ns=command['result_observed_monotonic_ns']-a['finished_ns'],original_budget_remaining_at_receiver_finish_ns=b['deadline_ns']-b['finished_ns'],
        actual_start_grant_deadline_ns=None,worker_consume_result=None,execute_submitted=None,branch='not_recorded',
        scope='Journal timestamps precede commit; dispatched is not handler start. Admission clock deadline is an earlier observation, not actual grant. No branch identity, no replay or nonexecution authority.')


def analyze(run,manifest,number):
    run=run.resolve();files={str(p.relative_to(ROOT)):p for p in run.rglob('*') if p.is_file()};hashes={}
    for name,p in files.items():
        h=sha(p)
        if manifest.get(name,{}).get('sha256')!=h:raise ValueError('original raw hash mismatch: '+name)
        hashes[name]=h
    report=json.loads((run/'run.json').read_text());clock=common_clock(report['clock_namespace_proof']);progress=command_progress(report,run);traces=summarize_run(run)
    if not all(t['complete'] for t in traces.values()):raise ValueError('incomplete original diagnostics')
    receiver_events=[dict(file=name,**e) for name,t in traces.items() if name.startswith('robot-') for e in t['events']]
    commands={c['number']:c for c in report['results']['commands']};rows=[]
    for entry in progress['entries']:
        identity=entry['number'].to_bytes(16,'little').hex();admissions=[e for e in receiver_events if e['request']==identity and e['detail']==6 and e['point'] in (32,36) and e['value']==0]
        rows.append(join(entry,commands[entry['number']],admissions))
    matching=[r for r in rows if r['number']==number]
    if len(matching)!=1 or (matching[0]['terminal'],matching[0]['reason'])!=(6,1):raise ValueError('target is not one context-rejected command')
    target=matching[0];begin=target['sender']['source_ns'];end=commands[number]['result_observed_monotonic_ns'];identity=target['request_id']
    context=[dict(file=n,**e) for n,t in traces.items() for e in t['events'] if begin<=e['monotonic_ns']<=end and e['point'] in (2,3,4,30,31)]
    queries=[e for e in receiver_events if e['request']==identity and e['detail']==8 and e['point']==32 and begin<=e['monotonic_ns']<=end]
    source_verification={}
    for name in SOURCES:
        expected=report['source_sha256'][name];current=sha(ROOT/name)
        if current!=expected:raise ValueError('runtime decision source changed: '+name)
        source_verification[name]=dict(sha256=current,original_live_sha256=expected,unchanged=True)
    if any(sha(ROOT/n)!=h for n,h in hashes.items()):raise ValueError('raw inputs changed during read-only analysis')
    return dict(run=str(run.relative_to(ROOT)),target=target,all_attempts=rows,audit=progress['audit'],skipped=progress['skipped_slots'],common_clock_proof=clock,
        target_query_clock_observations=queries,context_events_during_target=context,
        receiver_point34=[e for e in receiver_events if e['request']==identity and e['point']==34],
        dispatch_after_observed_clock_deadline=[r['number'] for r in rows if r['dispatch_minus_observed_clock_deadline_ns']>=0],
        smallest_observed_admission_clock_margins=[dict(number=r['number'],terminal=r['terminal'],margin_ns=r['admission_clock_margin_ns']) for r in sorted(rows,key=lambda r:r['admission_clock_margin_ns'])[:5]],
        source_verification=source_verification,raw_sha256=hashes,
        candidates=['coordinator post-dispatch start submission/check denied -> worker finish REJECTED/context_lost','worker consume expired/revoked/invalid while original command budget remains -> REJECTED/context_lost','worker consumed grant then second pre-handler deadline check elapsed -> REJECTED/context_lost'],
        missing_evidence=['post-dispatch start-check error and evaluated/clock/grant deadline','execute submission and actual slot/generation','worker consume outcome and both gate timestamps'],
        conclusion='Only target34 crosses its last logged admission clock deadline before dispatch in this cohort; original budget remains. Clock qualification lapse at the start stage is strongly supported, but actual grant/consume/decline branch is unrecorded. ROS handler itself cannot produce6/1; coordinator may decline before execute submission. No transport session loss is established by the reason name.',
        scope='Historical read-only correlation, no unique branch or ARP root-cause claim; all original outcomes retained; no tuning/replay/new N5 cohort.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--hash-manifest',type=Path,required=True);p.add_argument('--number',type=int,default=34);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('output exists')
    try:value=dict(status='passed',analysis=analyze(a.run,json.loads(a.hash_manifest.read_text()),a.number))
    except Exception as e:value=dict(status='failed',error=str(e))
    a.out.write_text(json.dumps(value,indent=2)+'\n');print(value['status'],value.get('error',''));raise SystemExit(value['status']!='passed')
