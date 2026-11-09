"""Validate local sender observations; never infer expiry, execution or replay."""


def validate(e):
    point=e['point']
    if point not in range(45,49) or e.get('sender_trace_version')!=1:raise ValueError('invalid sender trace version/point')
    for k in ('origin_ns','evaluated_ns','clock_deadline_ns','clock_error','command_deadline_ns','clock_previous_deadline_ns','probe_anchor_ns','worker_token','journal_revision','terminal_state','terminal_reason','detail','value'):
        if type(e.get(k)) is not int or not 0<=e[k]<2**64:raise ValueError('invalid sender field '+k)
    for k in ('clock_observed','journal_entry_available'):
        if type(e.get(k)) is not bool:raise ValueError('invalid sender availability '+k)
    for k in ('offset_lower_ns','offset_upper_ns'):
        if type(e.get(k)) is not int or not -(2**63)<=e[k]<2**63:raise ValueError('invalid sender offset')
    if e['clock_error']>9 or e['terminal_state']>8 or e['terminal_reason']>6:raise ValueError('invalid sender enum')
    if point in (45,46) and (not 0<e['origin_ns']<e['command_deadline_ns'] or e['request']=='00'*16):raise ValueError('missing original sender context')
    if point==45:
        if not 0<e['evaluated_ns']<=e['monotonic_ns'] or e['detail'] not in (1,2):raise ValueError('invalid sender clock evaluation')
        if e['detail']==1 and (e['value']!=13 or e['clock_error'] not in (1,2) or e['clock_deadline_ns']!=0):raise ValueError('invalid clock deferral')
        if e['detail']==2 and (e['value']!=0 or e['clock_error']!=0 or not e['clock_deadline_ns']>=e['evaluated_ns']):raise ValueError('invalid clock recovery')
        if e['clock_observed']:
            if not 0<e['probe_anchor_ns']<=e['evaluated_ns'] or e['offset_lower_ns']>e['offset_upper_ns']:raise ValueError('invalid observed probe')
        elif any(e[k] for k in ('probe_anchor_ns','offset_lower_ns','offset_upper_ns')) or e['clock_error']!=1:raise ValueError('unavailable probe invented')
    if point==46:
        reasons={1:(3,4,5),2:(7,),3:(8,),4:(0,),5:(3,10)}
        if e['value'] not in reasons or e['reason'] not in reasons[e['value']]:raise ValueError('invalid sender release branch')
    if point in (47,48):
        if e['value']>10 or (point==47 and (not 1<=e['detail']<=10 or not e['worker_token'])) or (point==48 and (e['detail']>9 or e['worker_token'])):raise ValueError('invalid sender journal/event metadata')
        if e['journal_entry_available']:
            if not 1<=e['terminal_state']<=8 or not 0<e['origin_ns']<e['command_deadline_ns'] or e['entry_owner_epoch']=='00'*16:raise ValueError('invalid journal entry snapshot')
        elif any(e[k] for k in ('terminal_state','terminal_reason','journal_revision','origin_ns','command_deadline_ns')) or e['entry_owner_epoch']!='00'*16:raise ValueError('unavailable journal entry invented')


def summarize(traces):
    if not traces or not all(t['complete'] for t in traces.values()):raise ValueError('incomplete sender capture')
    rows=[dict(file=name,**e) for name,t in traces.items() for e in t['events'] if e['point'] in range(45,49)]
    for e in rows:validate(e)
    # Positive new-version observations guard against silently ignored ROS overrides.
    if any(not any(e['point']==p and e['file'].startswith('operator') for e in rows) for p in (46,47,48)):
        raise ValueError('sender diagnostics enabled but release/journal/event observations missing')
    return dict(version=1,counts={str(p):sum(e['point']==p for e in rows) for p in range(45,49)},events=rows,
        scope='Lossless local diagnostic population only; no end-to-end receipt, journal mutation, nonexecution, expiry or replay authority. Missing clock45 means no deferral/recovery observed, not continuous qualification.')
