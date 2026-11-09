"""Predeclared sustained fixture windows within unchanged diagnostic budgets."""
SOURCE_LIMIT=10000
SAMPLE_LIMIT=75000


def budget(seconds):
    if type(seconds) is not int or seconds not in (10,30):
        raise ValueError('only predeclared10/30-second windows are supported')
    # One second of scheduling/fence allowance, both routes. This is admission
    # budgeting, not evidence that actual rates or diagnostic populations pass.
    source_records=(seconds+1)*250
    sender_records=source_records*2+1
    if source_records>SOURCE_LIMIT or sender_records>SAMPLE_LIMIT:
        raise ValueError('window exceeds diagnostic budgets')
    return dict(nominal_seconds=seconds,fence_allowance_seconds=1,source_record_allowance=source_records,sender_record_allowance=sender_records,source_limit=SOURCE_LIMIT,sample_limit=SAMPLE_LIMIT,scope='predeclared allowance only; actual counters, complete footers and recorder gates remain mandatory')


def verify_window(assessment,seconds,losses):
    limits=budget(seconds)
    if type(losses) is not int or losses not in (0,1,2):raise ValueError('invalid fault count')
    routes=assessment['cadence'].get('routes',{})
    if set(routes)!={'1','2'} or any(type(r.get('skipped_slots')) is not int or r['skipped_slots']!=0 for r in routes.values()):
        raise ValueError('source scheduling skipped slots or missing route evidence')
    elapsed=assessment['cadence']['duration_ns']
    if not seconds*10**9<=elapsed<=(seconds+1)*10**9:raise ValueError('actual source window outside predeclared duration allowance')
    if assessment['source_trace_status']['attempted']>limits['source_record_allowance'] or assessment['sender_trace_status']['attempted']>limits['sender_record_allowance']:raise ValueError('actual diagnostic population exceeds window allowance')
    expected=[7,8] if losses==2 else []
    stage=assessment['window']['losses']
    if assessment['sdk_without_receiver_decision']!=expected or stage['srt_accept_to_receiver_gap']!=len(expected) or stage['receiver_rejected']:
        raise ValueError('receiver boundary differs from predeclared source fault')
    return limits
