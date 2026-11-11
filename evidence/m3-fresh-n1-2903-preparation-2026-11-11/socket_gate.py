"""Explicit final-slot ownership gates plus every traced close/result pair."""
SLOTS=('control_fd_disposition','control_listener_disposition','sensor_fd_disposition','sensor_listener_disposition')

def check(rows):
    if not rows or sorted(r['sequence'] for r in rows)!=list(range(1,len(rows)+1)) or len({r['pid'] for r in rows})!=1 or any(r['dropped_before'] for r in rows):raise ValueError('socket trace sequence/identity/drop failure')
    begins=[r for r in rows if r['point']=='transport_shutdown_begin']
    if len(begins)!=1:raise ValueError('transport shutdown boundary missing/duplicate')
    tid=begins[0]['tid'];events=sorted((r for r in rows if r['tid']==tid),key=lambda r:r['sequence'])
    for r in rows:
        if r['point'] in SLOTS or r['point'].startswith('socket_'):
            if r['tid']!=tid:raise ValueError('socket evidence from wrong thread')
    closes=[];consumed=set()
    for i,r in enumerate(events):
        if r['point']=='socket_epoll_remove_begin':
            group=events[i:i+4]
            if [g['point'] for g in group]!=['socket_epoll_remove_begin','socket_close_begin','socket_close_result','socket_close_end']:raise ValueError('incomplete socket close bracket/result')
            if r['detail']<0 or group[1]['detail']!=r['detail'] or group[3]['detail']!=r['detail']:raise ValueError('socket close fd mismatch')
            if group[2]['detail']!=0:raise ValueError('srt_close returned error')
            if any(group[j]['monotonic_ns']>group[j+1]['monotonic_ns'] for j in range(3)):raise ValueError('socket close time reversal')
            closes.append(r['detail']);consumed.update(g['sequence'] for g in group)
    if any(r['point'] in ('socket_close_begin','socket_close_result','socket_close_end') and r['sequence'] not in consumed for r in events):raise ValueError('orphan socket close marker')
    positions=[];proof={}
    for slot in SLOTS:
        hits=[i for i,r in enumerate(events) if r['point']==slot]
        if len(hits)!=1:raise ValueError('missing/duplicate disposition: '+slot)
        i=hits[0];r=events[i];fd=r['detail'];positions.append(i)
        if fd < -1:raise ValueError('invalid socket disposition value')
        tail=events[i+1:];next_boundary=next((j for j,e in enumerate(tail) if e['point'] in SLOTS or e['point'] in ('control_close_end','sensor_close_end')),None)
        if next_boundary is None:raise ValueError('slot has no closing phase boundary')
        between=tail[:next_boundary]
        expected=[] if fd==-1 else ['socket_epoll_remove_begin','socket_close_begin','socket_close_result','socket_close_end']
        if [x['point'] for x in between]!=expected or (fd!=-1 and between[0]['detail']!=fd):raise ValueError('disposition does not match actual close records')
        proof[slot]=dict(fd=fd,disposition='already_invalid' if fd==-1 else 'closed',close_result=None if fd==-1 else between[2]['detail'])
    if positions!=sorted(positions):raise ValueError('slot order changed')
    expected_order=['control_close_begin',SLOTS[0],SLOTS[1],'control_close_end','sensor_close_begin',SLOTS[2],SLOTS[3],'sensor_close_end']
    if [r['point'] for r in events if r['point'] in expected_order]!=expected_order:raise ValueError('dispositions outside channel phase')
    return dict(slots=proof,traced_successful_close_fds=closes,scope='final slot disposition and traced srt_close return; no earlier close outcome or leak-freedom assertion')
