"""Per-probe local lifecycle observations; never command or delivery authority."""


def validate(e):
    p=e['point']
    if p not in range(50,55) or type(e.get('probe_trace_version')) is not int or e['probe_trace_version']!=1:raise ValueError('invalid probe version/point')
    for k in ('probe_t1','probe_t2','probe_t3','probe_pending_before','probe_pending_after','probe_end_ns','evaluated_ns','request_sequence','origin_ns','clock_error','clock_deadline_ns','probe_anchor_ns','probe_message_bytes','value'):
        if type(e.get(k)) is not int or not 0<=e[k]<2**64:raise ValueError('invalid probe field '+k)
    for k in ('probe_fields_available','probe_mapper_submitted','clock_observed'):
        if type(e.get(k)) is not bool:raise ValueError('invalid probe availability '+k)
    for k in ('offset_lower_ns','offset_upper_ns'):
        if type(e.get(k)) is not int or not -(2**63)<=e[k]<2**63:raise ValueError('invalid probe offset')
    if e['detail'] not in (9,10) or e['route'] or e['request']!='00'*16 or e['clock_error']>9:raise ValueError('invalid probe kind/context')
    if not 0<e['evaluated_ns']<=e['monotonic_ns']:raise ValueError('invalid probe evaluation time')
    if e['probe_fields_available']:
        if not e['probe_t1'] or (e['detail']==9 and (e['probe_t2'] or e['probe_t3'])) or (e['detail']==10 and not 0<e['probe_t2']<=e['probe_t3']):raise ValueError('invalid decoded probe fields')
    elif any(e[k] for k in ('probe_t1','probe_t2','probe_t3')):raise ValueError('unavailable probe fields invented')
    if e['probe_mapper_submitted']:
        if p!=53 or e['detail']!=10 or not e['probe_fields_available'] or e['probe_pending_before']!=e['probe_t1'] or e['probe_pending_after'] or not 0<=e['evaluated_ns']-e['probe_t1']<2000000000 or e['value'] not in (0,13,14):raise ValueError('invalid mapper submission')
        if e['clock_error'] in (0,1) and (not e['clock_observed'] or e['probe_anchor_ns']!=e['evaluated_ns']):raise ValueError('missing mapper anchor')
    if p in (50,54) and e['detail']!=9:raise ValueError('invalid initiator point')
    if p==50:
        if e['value']==0 and (not e['probe_fields_available'] or not e['request_sequence'] or e['origin_ns']!=e['probe_t1'] or e['probe_pending_after']!=e['probe_t1']):raise ValueError('missing emitted attempt context')
        if e['value']!=0 and e['probe_fields_available']:raise ValueError('failed attempt invented payload')
        if e['value']==16 and (not e['probe_pending_before'] or e['probe_pending_after']!=e['probe_pending_before']):raise ValueError('invalid busy attempt')
    if p in (50,53,54) and e['value']>26:raise ValueError('invalid probe SessionError')
    if p==51 and (e['value']>10 or not e['probe_fields_available']):raise ValueError('invalid probe queue result')
    if p==51 and e['origin_ns']!=(e['probe_t1'] if e['detail']==9 else e['probe_t3']):raise ValueError('probe queue origin mismatch')
    if p==53 and e['detail']==10 and e['value']==0 and not e['probe_mapper_submitted']:raise ValueError('successful reply without mapper observation')
    if p in (51,52,53) and not e['request_sequence']:raise ValueError('missing management sequence')
    if p==52:
        if type(e.get('probe_sdk_bytes')) is not int or not 0<e['probe_message_bytes']<=4096 or not e['evaluated_ns']<=e['probe_end_ns']<=e['monotonic_ns'] or e['probe_fields_available']:raise ValueError('invalid SDK bracket')
        if (e['value']==0 and e['probe_sdk_bytes']!=e['probe_message_bytes']) or (e['value']!=0 and e['probe_sdk_bytes']!=-1):raise ValueError('invalid SDK byte result')
    elif e.get('probe_sdk_bytes')!=0 or e['probe_end_ns']:raise ValueError('unexpected SDK fields')
    if p==54 and (not e['probe_fields_available'] or e['probe_pending_before']!=e['probe_t1'] or e['probe_pending_after'] or e['reason'] not in (3,5)):raise ValueError('invalid pending clear')


def key(e):return tuple(e[k] for k in ('owner_epoch','session','control_generation','request_sequence','detail'))


def summarize(traces):
    if not traces or not all(t['complete'] for t in traces.values()):raise ValueError('incomplete probe capture')
    rows=[dict(file=n,**e) for n,t in traces.items() for e in t['events'] if e['point'] in range(50,55)]
    for e in rows:validate(e)
    for role in ('operator','robot'):
        if any(not any(e['file'].startswith(role) and e['point']==p for e in rows) for p in (50,51,52,53)):raise ValueError('probe diagnostics enabled but lifecycle records missing')
    queues={}
    for e in rows:
        if e['point']==51:
            if key(e) in queues:raise ValueError('duplicate probe queue observation')
            queues[key(e)]=e
    sdk=[e for e in rows if e['point']==52]
    for e in sdk:
        q=queues.get(key(e))
        if q is None or q['value'] or e['evaluated_ns']<q['evaluated_ns'] or e['origin_ns']!=q['origin_ns'] or e['entry_owner_epoch']!=q['entry_owner_epoch']:raise ValueError('SDK/queue correlation mismatch')
    lifecycles=[]
    for attempt in (e for e in rows if e['point']==50 and e['probe_fields_available']):
        q=queues.get(key(attempt))
        if q is None or q['probe_t1']!=attempt['probe_t1']:raise ValueError('attempt/queue correlation mismatch')
        handoffs=[e for e in sdk if key(e)==key(q)];accepted=[e for e in handoffs if e['value']==0]
        if len(accepted)>1:raise ValueError('multiple accepted probe handoffs')
        peer=[e for e in rows if e['point']==53 and e['detail']==9 and e['probe_fields_available'] and e['probe_t1']==attempt['probe_t1'] and e['session']==attempt['session'] and e['entry_owner_epoch']==attempt['owner_epoch']]
        reply_queues=[e for e in rows if e['point']==51 and e['detail']==10 and e['probe_t1']==attempt['probe_t1'] and e['session']==attempt['session'] and any(e['owner_epoch']==r['owner_epoch'] and e['probe_t2']==r['evaluated_ns'] for r in peer)]
        reply_sdk=[e for e in sdk if any(key(e)==key(q) for q in reply_queues)]
        admissions=[e for e in rows if e['point']==53 and e['detail']==10 and e['probe_fields_available'] and e['probe_t1']==attempt['probe_t1'] and e['owner_epoch']==attempt['owner_epoch'] and e['session']==attempt['session']]
        for e in admissions:
            if not any(e['entry_owner_epoch']==q['owner_epoch'] and (e['probe_t1'],e['probe_t2'],e['probe_t3'])==(q['probe_t1'],q['probe_t2'],q['probe_t3']) for q in reply_queues):raise ValueError('reply echo correlation mismatch')
        lifecycles.append(dict(attempt=attempt,queue=q,sdk=handoffs,peer_admission=peer,reply_queue=reply_queues,reply_sdk=reply_sdk,reply_admission=admissions,qualified_mapper_admissions=sum(e['probe_mapper_submitted'] and e['clock_error']==0 for e in admissions),missing_reply_observation=not admissions))
    return dict(version=1,counts={str(p):sum(e['point']==p for e in rows) for p in range(50,55)},lifecycles=lifecycles,events=rows,
        scope='Lossless local observations only. SDK acceptance is not delivery; mapper submission/result is not command authority. Tail/absent probes stay unavailable. Repeated EASYNCSND suppressed until final SDK result; not retry counts.')
