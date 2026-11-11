"""Source/hash, local SDK metadata, receiver freshness and conservation for N4."""
from collections import Counter
from m3_source_trace import qualify
from m3_sample_trace import correlate
from m3_accounting import summarize_window


def assess(source,sender,receiver,local,remote,outage,restored,direction):
    resume=sender['resume'];pause=sender['pause'];rows=receiver['rows']
    cadence=qualify(source,dict(resume=resume,pause=pause,observed=rows))
    if not cadence['passed'] or not 15e9<=cadence['duration_ns']<=16e9:raise ValueError('source cadence/duration')
    for role in (sender,receiver):
        if role['bad'] or role['direct']:raise ValueError('typed/isolation error')
        for side in ('begin','end'):
            m=role[side]['bridge']
            if not all(m[k] for k in ('ready','clock_qualified','sensor_qos_verified')) or m['fault'] or m['worker_fault']:raise ValueError('unqualified/faulted checkpoint')
    for side in ('begin','end'):
        if sender[side]['bridge']['session_id']!=receiver[side]['bridge']['session_id']:raise ValueError('peer checkpoint sessions differ')
    if source['status']['attempted']>4000 or local['status']['attempted']>20000:raise ValueError('declared15s trace allowance exceeded')
    def point(side):return dict(sender=sender[side]['bridge'],receiver=receiver[side]['bridge'],device=resume if side=='begin' else pause,observer=dict(imu=0 if side=='begin' else sum(r['route']==1 for r in rows),joints=0 if side=='begin' else sum(r['route']==2 for r in rows)))
    window=summarize_window(point('begin'),point('end'),dict(resume_monotonic_ns=resume['monotonic_ns'],pause_monotonic_ns=pause['monotonic_ns']))
    if window['losses']['validation']:raise ValueError('invalid source input')
    joined=correlate(local);by_stamp={(r['route'],r['stamp_sec'],r['stamp_nanosec']):r for r in source['events']};admissions={};by_identity={}
    source_owner=bytes(sender['begin']['bridge']['owner_epoch']).hex();remote_owner=bytes(receiver['begin']['bridge']['owner_epoch']).hex()
    for e in local['events']:
        if e['owner_epoch']!=source_owner or e['point'] not in (1,2,3):raise ValueError('source trace owner/point')
        if e['point']!=1:continue
        src=by_stamp.get((e['route'],e['stamp_sec'],e['stamp_nanosec']))
        if not src or e['begin_ns']<src['begin_ns'] or (src['route'],src['counter']) in admissions:raise ValueError('ambiguous source admission')
        admissions[src['route'],src['counter']]=e
    def delta(role,key):return role['end']['bridge'][key]-role['begin']['bridge'][key]
    if len(admissions)!=delta(sender,'samples_ingress') or sum(e['result']!=0 for e in admissions.values())!=window['losses']['admission']:raise ValueError('admission trace/counter mismatch')
    rejected=Counter(e['result'] for e in joined['rejected'])
    if set(rejected)-{1,4} or rejected[1]!=delta(sender,'samples_submit_busy') or rejected[4]!=delta(sender,'samples_submit_obsolete'):raise ValueError('unexpected admission rejection')
    def identity(e):return e['session'],e['route'],e['origin_ns'],e['envelope_sequence']
    for p in joined['joined']:
        a=p['admission'];h=p['handoff'];src=by_stamp[a['route'],a['stamp_sec'],a['stamp_nanosec']];key=identity(h)
        if key in by_identity:raise ValueError('duplicate handoff identity')
        by_identity[key]=(src,h)
    if len(by_identity)!=delta(sender,'sensor_sent'):raise ValueError('SDK counter mismatch')
    queued_losses=sum(window['losses'][k] for k in ('ingress_replaced','ingress_flushed','input_rejected','outbound_replaced','outbound_expired','outbound_flushed'))
    if len(joined['queued_without_observed_handoff'])!=queued_losses:raise ValueError('unmatched queued population mismatch')
    accepted={};decisions=set()
    for e in remote['events']:
        pair=by_identity.get(identity(e))
        if e['point']!=4 or not pair or e['owner_epoch']!=remote_owner or e['source_epoch']!=source_owner or e['message_number']!=pair[1]['message_number'] or identity(e) in decisions:raise ValueError('receiver/context SDK join mismatch')
        decisions.add(identity(e))
        if e['result']==0:accepted[pair[0]['route'],pair[0]['counter']]=pair
    if len(decisions)!=delta(receiver,'transport_samples_received') or sum(e['result']!=0 for e in remote['events'])!=window['losses']['receiver_rejected']:raise ValueError('receiver trace population')
    max_lag=0
    for row in rows:
        pair=accepted.get((row['route'],row['counter']))
        if not pair:raise ValueError('typed output without accepted source')
        lag=row['observed_ns']-pair[1]['origin_ns']
        if not 0<=lag<=250_000_000:raise ValueError('typed observer ingress age exceeds250ms')
        max_lag=max(max_lag,lag)
    fresh={}
    for route,name in ((1,'imu'),(2,'joint')):
        post=[r for r in rows if r['route']==route and r['observed_ns']>=restored+250_000_000 and accepted[r['route'],r['counter']][1]['origin_ns']>=restored]
        pre=[r for r in rows if r['route']==route and r['observed_ns']<outage[0]]
        if len(post)<5 or len(pre)<5 or receiver['end']['bridge'][name+'_age_upper_max_ns']>250_000_000:raise ValueError('no fresh route progress or invalid publication age')
        fresh[str(route)]=dict(before=len(pre),fresh_after=len(post))
    forbidden=[r for r in rows if outage[0]+500_000_000<=r['observed_ns']<=outage[1]] if direction in ('both','to-operator') else []
    if forbidden:raise ValueError('publication continued beyond250ms under robot egress blackout')
    return dict(passed=True,cadence=cadence,window=window,progress=fresh,maximum_shared_VM_ingress_to_observer_ns=max_lag,source_trace_status=source['status'],sender_trace_status=local['status'],receiver_trace_status=remote['status'],sdk_errors=joined['sdk_errors'],sdk_without_decision=len(by_identity)-len(decisions),contexts=dict(sender=sender['contexts'],receiver=receiver['contexts']),scope='instrumented same-VM callback ingress/ROS observer and bridge age gates, no physical sensor age or independent packet capture; expected context changes and counted losses retained')
