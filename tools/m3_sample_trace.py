"""Validate bounded sample observations; SDK acceptance is not delivery authority."""
import json


def summarize(path,*,allow_inactive_admissions=False):
    events=[];statuses=[]
    for line in path.read_text().splitlines():
        if line.startswith('SAMPLE_TRACE '):events.append(json.loads(line[len('SAMPLE_TRACE '):]))
        elif line.startswith('SAMPLE_TRACE_STATUS '):statuses.append(json.loads(line[len('SAMPLE_TRACE_STATUS '):]))
        if len(events)>75000:raise ValueError('sample trace record budget exceeded')
    if len(statuses)!=1:raise ValueError('missing or duplicate final sample status')
    status=statuses[0]
    for key in ('attempted','dropped','limit'):
        if type(status.get(key)) is not int or status[key]<0:raise ValueError('invalid sample status')
    if not 1<=status['limit']<=75000 or status.get('exhausted') not in (0,1) or status['exhausted'] or status['attempted']>status['limit'] or status['dropped'] or len(events)!=status['attempted']:
        raise ValueError('sample trace incomplete, dropped or exhausted')
    ids=[]
    for e in events:
        for k in ('sequence','point','begin_ns','end_ns','origin_ns','control_generation','sensor_generation','envelope_sequence','callback_sequence','route','bytes','kind','result','stamp_sec','stamp_nanosec','socket','message_number','initial_sequence'):
            if type(e.get(k)) is not int:raise ValueError('invalid sample event integer')
        if not 1<=e['sequence']<=status['attempted'] or e['point'] not in (1,2,3,4) or not 0<e['begin_ns']<=e['end_ns'] or e['bytes']<=0:
            raise ValueError('invalid sample bracket/event')
        for key in ('owner_epoch','session'):
            if len(e[key])!=32 or len(bytes.fromhex(e[key]))!=16 or (not any(bytes.fromhex(e[key])) and not (allow_inactive_admissions and key=='session' and e['point']==1 and e['result'] in (2,4))):raise ValueError('invalid sample owner/session')
        if e['point']==1 and (e['kind']!=5 or e['result'] not in range(5) or not 0<e['origin_ns']<=e['begin_ns'] or not e['callback_sequence'] or not 0<=e['stamp_nanosec']<1000000000):
            raise ValueError('invalid ROS admission observation')
        if e['point'] in (2,3) and (e['kind'] not in (4,5) or e['socket']<0 or e['initial_sequence_available'] not in (0,1)):
            raise ValueError('invalid SDK observation')
        if e['point']==2 and (e['result'] or not 1<=e['message_number']<=0x03ffffff or not e['initial_sequence_available'] or not 0<=e['initial_sequence']<=0x7fffffff or e['bytes']>1024):
            raise ValueError('unqualified single-packet SENSOR SDK metadata')
        if e['point']==3 and (e['result']<=0 or e['message_number']):raise ValueError('invalid SDK error observation')
        if e['point']==4:
            epoch=e.get('source_epoch','')
            if status.get('schema_version')!=2 or len(epoch)!=32 or len(bytes.fromhex(epoch))!=16 or not any(bytes.fromhex(epoch)) or e['kind']!=5 or e['socket']<0 or not 1<=e['message_number']<=0x03ffffff or not 0<=e['result']<=26 or e['origin_ns']<=0 or e['envelope_sequence']<=0 or e['bytes']>1024:
                raise ValueError('invalid receiver decision metadata/schema')
        ids.append(e['sequence'])
    if len(set(ids))!=len(ids):raise ValueError('duplicate sample event sequence')
    return dict(complete=True,status=status,events=events,scope='loss-checked local observation; origin/route/owner/context joins; no delivery/absence or cryptographic identity authority, no cross-lane sequence causality; one ROS executor and one transport producer')


def correlate(trace):
    admissions={};handoffs={};errors=[];binding=[];messages=set();decisions=[]
    def key(e):return tuple(e[k] for k in ('owner_epoch','session','control_generation','sensor_generation','route','origin_ns'))
    for e in trace['events']:
        k=key(e)
        if e['point']==1:
            if k in admissions:raise ValueError('ambiguous admission origin/context')
            admissions[k]=e
        elif e['point']==2:
            wire=tuple(e[k] for k in ('owner_epoch','session','sensor_generation','socket','initial_sequence','message_number'))
            if wire in messages:raise ValueError('duplicate SDK accepted source identity')
            messages.add(wire)
            if e['kind']==4:binding.append(e);continue
            if k in handoffs:raise ValueError('sample accepted more than once')
            handoffs[k]=e
        elif e['point']==4:decisions.append(e)
        else:errors.append(e)
    joined=[]
    for k,e in handoffs.items():
        a=admissions.get(k)
        if not a or a['result']!=0:raise ValueError('SDK handoff without queued admission')
        # ROS records the result after submit returns; SDK progress may precede
        # that record. Compare to the call BEGIN, never require result-end order.
        if e['begin_ns']<a['begin_ns'] or e['bytes']!=a['bytes']+96:
            raise ValueError('handoff origin/size/bracket mismatch')
        joined.append(dict(admission=a,handoff=e,wire_sequence_candidate=(e['initial_sequence']+e['message_number']-1)&0x7fffffff))
    rejected=[e for e in admissions.values() if e['result']!=0]
    unmatched=[e for k,e in admissions.items() if e['result']==0 and k not in handoffs]
    return dict(joined=joined,rejected=rejected,queued_without_observed_handoff=unmatched,sdk_errors=errors,bindings=binding,receiver_decisions=decisions,
                scope='candidate sequence assumes pinned one-packet-per-message SENSOR and must be checked against native/PCAP headers; rejected admissions are retained, not retried; unmatched queued input has no absence/delivery conclusion')
