"""Correlate sustained source/admission/SDK/receiver observations without lossless assumptions."""
from collections import Counter
from m3_accounting import summarize_window
from m3_source_trace import qualify
from m3_sample_trace import correlate


def assess(source,sender,receiver,local,remote):
    a=sender['begin']['bridge'];b=receiver['begin']['bridge']
    for side in (sender,receiver):
        if side['bad'] or side['direct']:raise ValueError('typed/session/isolation failure')
        for point in ('begin','end'):
            if not all(side[point]['bridge'][k] for k in ('ready','clock_qualified','sensor_qos_verified')):raise ValueError('unqualified checkpoint')
        for k in ('session_id','owner_epoch','control_generation','sensor_generation'):
            if side['begin']['bridge'][k]!=side['end']['bridge'][k]:raise ValueError('endpoint context changed')
    if a['session_id']!=b['session_id']:raise ValueError('peer session mismatch')
    resume=sender['resume'];pause=sender['pause'];seen=receiver['rows']
    cadence=qualify(source,dict(resume=resume,pause=pause,observed=seen))
    cadence['scope']='measured source cadence and remote typed hashes; unobserved IDs have no individual loss-stage inference'
    def checkpoint(side):
        return dict(sender=sender[side]['bridge'],receiver=receiver[side]['bridge'],device=resume if side=='begin' else pause,observer=dict(imu=0 if side=='begin' else sum(e['route']==1 for e in seen),joints=0 if side=='begin' else sum(e['route']==2 for e in seen)))
    window=summarize_window(checkpoint('begin'),checkpoint('end'),dict(resume_monotonic_ns=resume['monotonic_ns'],pause_monotonic_ns=pause['monotonic_ns']))
    def delta(role,k):return role['end']['bridge'][k]-role['begin']['bridge'][k]
    if window['losses']['validation']:raise ValueError('source validation unexpectedly failed')
    by_stamp={(e['route'],e['stamp_sec'],e['stamp_nanosec']):e for e in source['events']}
    joined=correlate(local)
    if joined['sdk_errors']:raise ValueError('SDK send errors in N0 preflight')
    admissions={};handoffs={};by_message={}
    for e in local['events']:
        if e['point'] not in (1,2):raise ValueError('unexpected source trace point')
        if e['session']!=bytes(a['session_id']).hex() or e['owner_epoch']!=bytes(a['owner_epoch']).hex() or any(e[k]!=a[k] for k in ('control_generation','sensor_generation')):raise ValueError('source trace context mismatch')
        if e['point']!=1:continue
        src=by_stamp.get((e['route'],e['stamp_sec'],e['stamp_nanosec']))
        if not src or e['begin_ns']<src['begin_ns']:raise ValueError('admission without source identity/bracket')
        key=(src['route'],src['counter'])
        if key in admissions:raise ValueError('source admitted multiple times')
        admissions[key]=e
    if len(admissions)!=delta(sender,'samples_ingress'):raise ValueError('admission trace population mismatch')
    rejected=Counter(e['result'] for e in joined['rejected'])
    if set(rejected)-{1,2} or rejected[1]!=delta(sender,'samples_submit_busy') or rejected[2]!=delta(sender,'samples_submit_obsolete') or sum(rejected.values())!=window['losses']['admission']:raise ValueError('rejected admission counters mismatch')
    for pair in joined['joined']:
        e=pair['admission'];src=by_stamp[(e['route'],e['stamp_sec'],e['stamp_nanosec'])];key=(src['route'],src['counter']);h=pair['handoff']
        handoffs[key]=h
        if h['message_number'] in by_message:raise ValueError('duplicate SDK message')
        by_message[h['message_number']]=(key,h)
    sdk=[e for e in local['events'] if e['point']==2]
    if len(joined['bindings'])!=1 or joined['bindings'][0]['message_number']!=1 or sorted(e['message_number'] for e in sdk)!=list(range(1,len(sdk)+1)) or len({e['initial_sequence'] for e in sdk})!=1 or len(handoffs)!=delta(sender,'sensor_sent'):raise ValueError('SDK acceptance/binding population mismatch')
    queued_losses=sum(window['losses'][k] for k in ('ingress_replaced','ingress_flushed','input_rejected','outbound_replaced','outbound_expired','outbound_flushed'))
    if len(joined['queued_without_observed_handoff'])!=queued_losses:raise ValueError('queued unmatched aggregate mismatch')
    decisions={};accepted=set()
    for e in remote['events']:
        pair=by_message.get(e['message_number'])
        if e['point']!=4 or not pair or e['message_number'] in decisions:raise ValueError('receiver decision population/identity mismatch')
        key,h=pair
        if e['source_epoch']!=bytes(a['owner_epoch']).hex() or e['owner_epoch']!=bytes(b['owner_epoch']).hex() or e['session']!=bytes(b['session_id']).hex() or any(e[k]!=b[k] for k in ('control_generation','sensor_generation')) or any(e[k]!=h[k] for k in ('route','origin_ns','envelope_sequence')):raise ValueError('receiver decision context mismatch')
        decisions[e['message_number']]=e
        if e['result']==0:accepted.add(key)
    if len(decisions)!=delta(receiver,'transport_samples_received') or sum(e['result']!=0 for e in decisions.values())!=window['losses']['receiver_rejected']:raise ValueError('receiver trace counter mismatch')
    if any((e['route'],e['counter']) not in accepted for e in seen):raise ValueError('typed observer without accepted receiver decision')
    for route,name in ((1,'imu'),(2,'joint')):
        if sum(e['route']==route for e in seen)>window['age_upper_histograms'][name]['count'] or receiver['end']['bridge'][name+'_age_upper_max_ns']>250000000:raise ValueError('route publication/age mismatch')
    source_keys={(e['route'],e['counter']) for e in source['events']}
    upstream=sorted(source_keys-set(admissions))
    if len(upstream)!=window['losses']['upstream_dds']:raise ValueError('upstream observation population mismatch')
    return dict(passed=cadence['passed'],cadence=cadence,window=window,source_without_admission=[list(k) for k in upstream],rejected_admissions=[dict(route=k[0],counter=k[1],result=e['result']) for k,e in admissions.items() if e['result']],queued_without_observed_handoff=joined['queued_without_observed_handoff'],sdk_without_receiver_decision=sorted(set(by_message)-set(decisions)),accepted_without_typed_observation=[list(k) for k in sorted(accepted-{(e['route'],e['counter']) for e in seen})],source_trace_status=source['status'],sender_trace_status=local['status'],receiver_trace_status=remote['status'],scope='ten-second N0 accounting preflight; aggregate loss stages balance; no packet identity/capture, FEC, seed matrix, per-ID stage proof, physical age or M3 acceptance')
