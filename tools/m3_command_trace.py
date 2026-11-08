"""Read-only validation of opt-in command diagnostics, never outcome authority."""
import json

POINTS={1:'endpoint_started',2:'session_changed',3:'invalidate_requested',4:'invalidate_completed',
    5:'sender_admission',6:'submit_result',7:'worker_unknown',8:'endpoint_stopping',9:'endpoint_stopped',
    20:'mailbox_flushed',21:'input_dropped',22:'make_rejected',23:'queue_rejected',24:'outbound_dropped',
    25:'provider_sent',26:'provider_error',27:'outbound_flushed',28:'transport_stopping',29:'clock_deferred',30:'session_action',31:'link_lost',32:'control_admission',33:'peer_error_received',34:'receiver_worker_result',35:'receiver_deferred',36:'receiver_resumed',37:'receiver_retained_dropped',38:'receiver_capacity_rejected',39:'receiver_expiry_admission'}
REASONS={0:'none',1:'session_changed',2:'abandoned_submit',3:'context_mismatch',4:'proof_revoked',
    5:'deadline',6:'missing_proof',7:'session_rejected',8:'queue_rejected',9:'provider_error',10:'shutdown',11:'socket_state',12:'security_timeout',13:'epoll_error',14:'receive_error',15:'wire_decode',16:'session_decision'}


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
    for event in events:
        if event['point']==30 and (type(event.get('detail')) is not int or not 1<=event['detail']<=7):raise ValueError('invalid session action flags')
        if event['point']==31 and event.get('detail') not in (0,1):raise ValueError('invalid link channel')
        if event['point'] in (32,33,34,35,36,37,38,39):
            if type(event.get('detail')) is not int or event['detail'] not in (6,8):raise ValueError('invalid original request kind')
            for key in ('request_sequence','origin_ns','evaluated_ns','clock_deadline_ns','clock_error','age_error'):
                if type(event.get(key)) is not int or not 0<=event[key]<2**64:raise ValueError('invalid admission metadata')
            if not event['request_sequence']:raise ValueError('missing original request sequence')
            maximum={32:26,33:9,34:10,35:26,36:26,37:26,38:9,39:26}[event['point']]
            if event['point']>=35 and event['detail']!=6:raise ValueError('retention observation requires COMMAND')
            if type(event.get('value')) is not int or not (1 if event['point']==33 else 0)<=event['value']<=maximum:raise ValueError('invalid admission error enum')
            if event['point'] in (32,36) and (not 0<event['evaluated_ns']<=event['monotonic_ns'] or not 0<=event['clock_error']<=9 or not 0<=event['age_error']<=9):raise ValueError('invalid admission clock metadata')
        if event['point']==39:
            for key in ('age_lower_ns','age_upper_ns','expiry_deadline_ns','budget_ms'):
                if type(event.get(key)) is not int:raise ValueError('invalid expiry proof metadata')
            lower=event['age_lower_ns'];upper=event['age_upper_ns'];budget=event['budget_ms']*1000000
            if event['value']!=25 or event['clock_error'] or event['age_error'] or not 1<=event['budget_ms']<=60000 or not budget<lower<=upper<2**63:raise ValueError('unproven receiver expiry')
            if not 0<event['expiry_deadline_ns']==event['evaluated_ns']-(lower-budget)<event['evaluated_ns']<=event['monotonic_ns']:raise ValueError('invalid expiry deadline proof')
    phases={point:[e for e in events if e['point']==point] for point in (1,8,9,28)}
    complete=status['dropped']==0 and all(len(rows)==1 for rows in phases.values())
    if complete and phases[9][0]['monotonic_ns']<phases[8][0]['monotonic_ns']:raise ValueError('invalid endpoint lifecycle bracket')
    return dict(complete=complete,attempted=status['attempted'],dropped=status['dropped'],records=len(events),
        counts={name:sum(e['point']==point for e in events) for point,name in POINTS.items()},
        events=events,point_names=POINTS,reason_names=REASONS,detail_schema={'session_action':'bit flags: close control 1, close sensor 2, flush samples 4; value=SessionError','link_lost':'channel 0 CONTROL / 1 SENSOR; value=reason-specific socket state, provider error, epoll flags or wire error','transport_stopping':'value=TransportFault','control_admission':'detail=COMMAND6/QUERY8; value=SessionError; original request sequence/origin, local evaluated_ns and post-evaluation ClockError/deadline and AgeResult error (COMMAND freshness only)','peer_error_received':'detail=original COMMAND6/QUERY8; value=ControlErrorCode; request_sequence from matched ERROR; origin/clock fields unused','receiver_retention':'35 deferred,36 resumed,37 dropped value=SessionError,38 capacity value=ControlErrorCode; original request metadata;36 freshly revalidated; no outcome authority','receiver_worker_result':'detail=COMMAND6/QUERY8; value=JournalError; request_sequence/origin from original envelope; completion is not dispatch/execution proof'},
        scope='local lossy observations only; no replay/execution/absence authority; sequence order across producers is not causal order; provider_sent is SDK acceptance, not delivery')


def summarize_run(run):
    traces={p.name:summarize(p) for p in sorted(run.glob('*-bridge-*.log'))}
    # The scenario deliberately replaces the robot bridge during setup. Validate
    # every recorded incarnation, rather than requiring exactly two processes.
    if not all(any(name.startswith(role+'-bridge-') for name in traces) for role in ('robot','operator')):
        raise ValueError('missing endpoint command diagnostics')
    if not all(trace['complete'] for trace in traces.values()):raise ValueError('command diagnostics incomplete')
    return traces
