"""Read-only validation of opt-in command diagnostics, never outcome authority."""
import json

POINTS={1:'endpoint_started',2:'session_changed',3:'invalidate_requested',4:'invalidate_completed',
    5:'sender_admission',6:'submit_result',7:'worker_unknown',8:'endpoint_stopping',9:'endpoint_stopped',
    20:'mailbox_flushed',21:'input_dropped',22:'make_rejected',23:'queue_rejected',24:'outbound_dropped',
    25:'provider_sent',26:'provider_error',27:'outbound_flushed',28:'transport_stopping',29:'clock_deferred'}
REASONS={0:'none',1:'session_changed',2:'abandoned_submit',3:'context_mismatch',4:'proof_revoked',
    5:'deadline',6:'missing_proof',7:'session_rejected',8:'queue_rejected',9:'provider_error',10:'shutdown'}


def summarize(path):
    events=[];statuses=[]
    with path.open() as file:
        for line in file:
            if line.startswith('COMMAND_TRACE '):events.append(json.loads(line[len('COMMAND_TRACE '):]))
            elif line.startswith('COMMAND_TRACE_STATUS '):statuses.append(json.loads(line[len('COMMAND_TRACE_STATUS '):]))
            if len(events)>250000:raise ValueError('command trace bound exceeded')
    if len(statuses)!=1:raise ValueError('missing or duplicate final command trace status')
    status=statuses[0];sequences=[e['sequence'] for e in events]
    if any(type(status.get(k)) is not int or status[k]<0 for k in ('attempted','dropped')):raise ValueError('invalid trace counters')
    if len(set(sequences))!=len(sequences) or any(type(s) is not int or not 1<=s<=status['attempted'] for s in sequences):raise ValueError('invalid trace sequences')
    if len(events)+status['dropped']!=status['attempted']:raise ValueError('unaccounted trace observations')
    for event in events:
        if event['point'] not in POINTS or event['reason'] not in REASONS or event['monotonic_ns']<=0:raise ValueError('invalid trace event')
        for key in ('request','session','owner_epoch','entry_owner_epoch'):
            if len(event[key])!=32 or len(bytes.fromhex(event[key]))!=16:raise ValueError('invalid trace identity')
    phases={point:[e for e in events if e['point']==point] for point in (1,8,9,28)}
    complete=status['dropped']==0 and all(len(rows)==1 for rows in phases.values())
    if complete and phases[9][0]['monotonic_ns']<phases[8][0]['monotonic_ns']:raise ValueError('invalid endpoint lifecycle bracket')
    return dict(complete=complete,attempted=status['attempted'],dropped=status['dropped'],records=len(events),
        counts={name:sum(e['point']==point for e in events) for point,name in POINTS.items()},
        events=events,point_names=POINTS,reason_names=REASONS,
        scope='local lossy observations only; no replay/execution/absence authority; sequence order across producers is not causal order; provider_sent is SDK acceptance, not delivery')


def summarize_run(run):
    traces={p.name:summarize(p) for p in sorted(run.glob('*-bridge-*.log'))}
    # The scenario deliberately replaces the robot bridge during setup. Validate
    # every recorded incarnation, rather than requiring exactly two processes.
    if not all(any(name.startswith(role+'-bridge-') for name in traces) for role in ('robot','operator')):
        raise ValueError('missing endpoint command diagnostics')
    if not all(trace['complete'] for trace in traces.values()):raise ValueError('command diagnostics incomplete')
    return traces
