"""Fail-closed source trace and fenced cadence checks; no delivery authority."""
import json
import re
from collections import Counter


def summarize(path):
    events=[];statuses=[]
    for line in path.read_text().splitlines():
        if line.startswith('SOURCE_TRACE '):events.append(json.loads(line[13:]))
        elif line.startswith('SOURCE_TRACE_STATUS '):statuses.append(json.loads(line[20:]))
        if len(events)>10000:raise ValueError('source trace budget exceeded')
    if len(statuses)!=1:raise ValueError('expected one completed source window')
    s=statuses[0]
    for k in ('window','attempted','recorded','printed','dropped','encoding_failed','hash_failed','limit'):
        if type(s.get(k)) is not int or s[k]<0:raise ValueError('invalid source status')
    if s.get('schema_version')!=1 or s.get('complete') is not True or s['window']!=1 or not 0<len(events)<=s['limit']<=10000 or any(s[k] for k in ('dropped','encoding_failed','hash_failed')) or any(s[k]!=len(events) for k in ('attempted','recorded','printed')):
        raise ValueError('incomplete source window')
    keys=set();counters=Counter()
    for seq,e in enumerate(events,1):
        for k in ('window','sequence','route','counter','stamp_sec','stamp_nanosec','begin_ns','end_ns','due_ns','period_ns','skipped_slots','payload_bytes'):
            if type(e.get(k)) is not int:raise ValueError('invalid source integer')
        if e['window']!=1 or e['sequence']!=seq or e['route'] not in (1,2) or not 0<e['due_ns']<=e['begin_ns']<=e['end_ns'] or not 0<=e['stamp_nanosec']<1_000_000_000 or not -(2**31)<=e['stamp_sec']<2**31 or e['period_ns']<=0 or e['skipped_slots']<0 or not 0<e['payload_bytes']<=928 or not re.fullmatch('[0-9a-f]{64}',e.get('payload_sha256','')):
            raise ValueError('invalid source event')
        key=(e['route'],e['stamp_sec'],e['stamp_nanosec'])
        if key in keys:raise ValueError('ambiguous source stamp')
        keys.add(key);counters[e['route']]+=1
        if e['counter']!=counters[e['route']]:raise ValueError('source counter discontinuity')
    return dict(status=s,events=events)


def qualify(trace, result, tolerance=.01):
    """Whole-window count rate, not requested period or short interval median."""
    begin=result['resume'];end=result['pause'];duration=end['monotonic_ns']-begin['monotonic_ns']
    if not begin['enabled'] or end['enabled'] or duration<=0:raise ValueError('invalid source fences')
    if any(v['rate_hz']!=200 or v['generation'] or v['effects'] for v in (begin,end)):raise ValueError('unexpected source rate/effects')
    if any(begin[k] for k in ('imu_published','joints_published')):raise ValueError('source not initially empty')
    routes={};source={}
    for route,field,rate in ((1,'imu_published',200),(2,'joints_published',50)):
        rows=[e for e in trace['events'] if e['route']==route];period=1_000_000_000//rate
        if len(rows)!=end[field] or not rows:raise ValueError('source count/fence mismatch')
        due=begin['monotonic_ns']
        for e in rows:
            if e['period_ns']!=period or e['due_ns']!=due or e['end_ns']>end['monotonic_ns'] or e['due_ns']+e['skipped_slots']*period>e['begin_ns']:
                raise ValueError('source phase/fence mismatch')
            due+=(e['skipped_slots']+1)*period
            source[(route,e['counter'])]=e
        actual=len(rows)*1e9/duration
        routes[str(route)]=dict(published=len(rows),target_hz=rate,actual_hz=actual,skipped_slots=sum(e['skipped_slots'] for e in rows),cadence_pass=abs(actual/rate-1)<=tolerance)
    seen=set();last=Counter()
    for row in result['observed']:
        key=(row['route'],row['counter']);e=source.get(key)
        if key in seen or not e or row['counter']<=last[row['route']] or row['payload_sha256']!=e['payload_sha256'] or (row['stamp_sec'],row['stamp_nanosec'])!=(e['stamp_sec'],e['stamp_nanosec']):
            raise ValueError('observer duplicate/order/payload mismatch')
        last[row['route']]=row['counter'];seen.add(key)
    missing=sorted(set(source)-seen)
    for route in routes:
        routes[route]['observed']=sum(k[0]==int(route) for k in seen)
        routes[route]['unobserved']=sum(k[0]==int(route) for k in missing)
    return dict(passed=all(v['cadence_pass'] for v in routes.values()),duration_ns=duration,tolerance_fraction=tolerance,routes=routes,unobserved=[list(k) for k in missing],scope='isolated source preflight; observer gaps retained; no bridge admission, transport, FEC, physical sensor-age or M3 qualification')
