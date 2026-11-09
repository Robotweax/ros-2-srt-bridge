"""Validate opt-in start diagnostics; missing/cross-context observations never infer a branch."""
NUMBERS=('check_token','worker_token','grant_slot','grant_generation','grant_deadline_ns','command_deadline_ns','consume_ns','consume_deadline_ns','consume_result','second_gate_ns','second_gate_deadline_ns','terminal_state','terminal_reason')
BOOLEANS=('start_granted','worker_observation_available','second_gate_checked','handler_invoked')


def validate(event):
    point=event['point']
    if event.get('start_trace_version')!=1 or event.get('detail')!=6:raise ValueError('invalid start trace version/kind')
    for key in NUMBERS:
        if type(event.get(key)) is not int or not 0<=event[key]<2**64:raise ValueError('invalid start number '+key)
    if any(type(event.get(key)) is not bool for key in BOOLEANS):raise ValueError('invalid start boolean')
    if not event['check_token'] or not event['command_deadline_ns'] or not event.get('request_sequence') or not event.get('origin_ns'):raise ValueError('missing original start identity/deadline')
    if not 0<=event['value']<={40:4,41:26,42:4,43:10,44:26}[point]:raise ValueError('invalid start result enum')
    if event['grant_slot']!=2**32-1 and not event['grant_slot']<64:raise ValueError('invalid start slot')
    if event['start_granted']:
        if event['grant_slot']>=64 or not event['grant_generation'] or not 0<event['grant_deadline_ns']<=event['command_deadline_ns']:raise ValueError('missing actual start grant')
    elif event['grant_deadline_ns']:raise ValueError('denied check has a grant deadline')
    if point==41:
        if event['grant_slot']>=64 or not event['grant_generation'] or event['start_granted']!=(event['value']==0):raise ValueError('inconsistent owner start decision')
        if event['start_granted'] and not 0<event['evaluated_ns']<event['grant_deadline_ns']<=event['clock_deadline_ns']:raise ValueError('invalid owner grant/clock bound')
    if point in (42,43) and (not event['start_granted'] or not event['worker_token']):raise ValueError('execute without granted identity/token')
    if point!=43 and (event['worker_observation_available'] or any(event[k] for k in ('consume_ns','consume_deadline_ns','consume_result','second_gate_ns','second_gate_deadline_ns','terminal_state','terminal_reason')) or event['second_gate_checked'] or event['handler_invoked']):raise ValueError('worker metadata on nonworker event')
    if point==43 and event['worker_observation_available']:
        if event['consume_result'] not in (1,2,3,4) or not 0<event['consume_ns']<=event['monotonic_ns']:raise ValueError('invalid worker consume observation')
        if event['consume_deadline_ns']!=event['grant_deadline_ns']:raise ValueError('worker grant identity/deadline mismatch')
        if event['consume_result']==1 and not event['consume_ns']<event['consume_deadline_ns']:raise ValueError('started at/past deadline')
        if event['consume_result']==2 and event['consume_ns']<event['consume_deadline_ns']:raise ValueError('expiry before deadline')
        if event['second_gate_checked']!=(event['consume_result']==1):raise ValueError('inconsistent second gate availability')
        if event['second_gate_checked']:
            if not event['consume_ns']<=event['second_gate_ns']<=event['monotonic_ns'] or event['second_gate_deadline_ns']!=event['grant_deadline_ns']:raise ValueError('invalid second gate identity/time')
        elif event['second_gate_ns'] or event['second_gate_deadline_ns']:raise ValueError('unavailable gate has timestamps')
        if event['handler_invoked'] and (not event['second_gate_checked'] or event['second_gate_ns']>=event['second_gate_deadline_ns']):raise ValueError('handler crossed failed gate')
    elif point==43 and (any(event[k] for k in ('consume_ns','consume_deadline_ns','consume_result','second_gate_ns','second_gate_deadline_ns')) or event['second_gate_checked'] or event['handler_invoked']):raise ValueError('unavailable worker has observations')


def analyze(events):
    groups={}
    for e in events:
        if e['point'] not in range(40,45):continue
        validate(e)
        key=tuple(e[k] for k in ('owner_epoch','session','request','route','origin_ns','request_sequence','check_token'))
        groups.setdefault(key,[]).append(e)
    result=[]
    for key,rows in groups.items():
        stages={p:[e for e in rows if e['point']==p] for p in range(40,45)}
        if any(len(v)>1 for v in stages.values()):raise ValueError('duplicate start stage')
        submission=stages[40];decision=stages[41];execute=stages[42];worker=stages[43];declined=stages[44]
        if len(submission)!=1:raise ValueError('missing start submission')
        if any(e.get('control_generation')!=submission[0].get('control_generation') for e in rows):raise ValueError('changed original control generation')
        if any(e['command_deadline_ns']!=submission[0]['command_deadline_ns'] for e in rows):raise ValueError('changed original start deadline')
        if submission[0]['value']==0 and not decision:raise ValueError('missing owner start decision')
        if submission[0]['value']!=0 and decision:raise ValueError('owner decision without queued start')
        if declined:
            if execute or worker or (decision and decision[0]['start_granted']):raise ValueError('decline mixed with execution/grant')
            branch='coordinator_start_declined'
        else:
            if not decision or not decision[0]['start_granted'] or not execute or not worker:raise ValueError('incomplete granted start lifecycle')
            d,x,w=decision[0],execute[0],worker[0]
            if x['value']!=0 or x['worker_token']!=w['worker_token']:raise ValueError('execute token mismatch')
            for e in (x,w):
                if any(e[k]!=d[k] for k in ('grant_slot','grant_generation','grant_deadline_ns')):raise ValueError('cross-generation start join')
            if not w['worker_observation_available']:raise ValueError('worker observation unavailable')
            if w['consume_result']!=1:branch={2:'worker_consume_expired',3:'worker_consume_revoked',4:'worker_consume_invalid'}[w['consume_result']]
            elif w['second_gate_ns']>=w['second_gate_deadline_ns']:branch='worker_second_gate_elapsed'
            else:branch='worker_handler_invoked' if w['handler_invoked'] else 'worker_gate_passed_without_handler'
        result.append(dict(identity=dict(zip(('owner_epoch','session','request','route','origin_ns','request_sequence','check_token'),key)),branch=branch,events=sorted(rows,key=lambda e:e['monotonic_ns']),scope='Observed start branch only; journal/effect authority remains separate; revoked alone does not identify revocation cause.'))
    return result
