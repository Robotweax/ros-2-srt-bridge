#!/usr/bin/env python3
"""Read-only CONTROL-flow gaps in qualified kernel-monotonic prefix captures.

SRT outer header types follow the pinned provider's packet.hpp. No payload is
decrypted. A hook observation is not authenticated SDK receipt or physical wire
delivery. Never merge reconnects solely because they share port 10080.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import ipaddress
import json
from pathlib import Path
import struct
from m3_monotonic_capture import records,decode
from m3_dds_result_timeline import common_clock

CONTROL_TYPES={0:'handshake',1:'keepalive',2:'ack',3:'nak',4:'congestion_warning',
               5:'shutdown',6:'ackack',7:'drop_request',8:'peer_error',32767:'extension'}


def parse_control(row,address,mtu):
    decoded=decode(row,address)
    if not decoded or '/control_' not in decoded[0]:return None
    if row['artifact_version']!=2 or row['gso_segs'] not in (0,1) or row['gso_size'] or row['vlan_present'] or row['length']>mtu+14:
        raise ValueError('CONTROL offload/frame representation not qualified')
    frame=row['prefix'];offset=14+(frame[14]&15)*4
    sp,dp,length=struct.unpack_from('!HHH',frame,offset)
    if length<24 or len(frame)<offset+24:raise ValueError('short SRT CONTROL header')
    first,_,_,socket_id=struct.unpack_from('!IIII',frame,offset+8)
    kind=CONTROL_TYPES.get((first>>16)&32767,'unknown_control') if first&0x80000000 else 'data'
    return dict(monotonic_ns=row['monotonic_ns'],direction=decoded[0].split('/')[0],
        source=str(ipaddress.ip_address(frame[26:30])),destination=str(ipaddress.ip_address(frame[30:34])),
        source_port=sp,destination_port=dp,destination_socket_id=socket_id,kind=kind)


FLOW_FIELDS=('direction','source','destination','source_port','destination_port','destination_socket_id')


def summarize_flows(rows,start,end,event_ns=None):
    if not 0<=start<end:raise ValueError('invalid analysis window')
    if event_ns is not None and not start<=event_ns<end:raise ValueError('event outside analysis window')
    groups=defaultdict(list)
    for row in rows:
        if start<=row['monotonic_ns']<end:groups[tuple(row[k] for k in FLOW_FIELDS)].append(row)
    result=[]
    for key,group in sorted(groups.items()):
        group.sort(key=lambda r:r['monotonic_ns'])
        pairs=list(zip(group,group[1:]))
        largest=max(pairs,key=lambda pair:pair[1]['monotonic_ns']-pair[0]['monotonic_ns'],default=None)
        result.append(dict(flow=dict(zip(FLOW_FIELDS,key)),nonzero_destination_socket_id=key[-1]!=0,observations=len(group),kinds=dict(Counter(r['kind'] for r in group)),
            first_ns=group[0]['monotonic_ns'],last_ns=group[-1]['monotonic_ns'],
            largest_gap=None if largest is None else dict(before_ns=largest[0]['monotonic_ns'],after_ns=largest[1]['monotonic_ns'],
                gap_ns=largest[1]['monotonic_ns']-largest[0]['monotonic_ns']),
            shutdown_ns=[r['monotonic_ns'] for r in group if r['kind']=='shutdown']))
        if event_ns is not None:
            previous=[r['monotonic_ns'] for r in group if r['monotonic_ns']<event_ns]
            following=[r['monotonic_ns'] for r in group if r['monotonic_ns']>=event_ns]
            last=previous[-1] if previous and key[-1]!=0 else None
            result[-1].update(last_before_event_ns=last,first_at_or_after_event_ns=following[0] if following else None,
                observed_quiet_to_event_ns=event_ns-last if last is not None else None)
    return result


def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda:file.read(1048576),b''):result.update(block)
    return result.hexdigest()


def analyze(run,event_ns,before_ns=6000000000,after_ns=2000000000):
    report=json.loads((run/'run.json').read_text())
    if report['status']=='running':raise ValueError('requires a closed run')
    proof=common_clock(report['clock_namespace_proof'])
    addresses=json.loads((run/'network.json').read_text())['addresses']
    start,end=event_ns-before_ns,event_ns+after_ns
    if not 0<=start<event_ns<end:raise ValueError('invalid event window')
    output=dict(event_ns=event_ns,window_ns=[start,end],clock_proof=proof,roles={},
        scope='fully observed consecutive CONTROL skb gaps within window, per UDP flow and destination socket; not authenticated SDK inactivity, root cause, physical delivery, execution or nonexecution proof; destination id zero is not established-flow identity; routing identifier reuse is not authenticated connection identity')
    for role in ('robot','operator'):
        status=report['monotonic_captures']['statuses'][role]
        if status.get('complete') is not True or status.get('clock')!='kernel_monotonic' or status.get('time_namespace_zero') is not True or status.get('artifact_version')!=2:
            raise ValueError('requires complete native v2 capture')
        if not status['ready_ns']<=start<end<=status['stop_before_ns'] or status['reserve_failed'] or status['copy_failed']:
            raise ValueError('incomplete capture coverage')
        path=run/(role+'.mono');before=digest(path);selected=[];count=0
        for row in records(path):
            count+=1
            if row['artifact_version']!=2 or row['ifindex']!=status['ifindex']:raise ValueError('capture version/interface changed')
            if start<=row['monotonic_ns']<end:
                parsed=parse_control(row,addresses[role],status['mtu'])
                if parsed:selected.append(parsed)
        if count!=status['records'] or count!=status['seen'] or count!=status['submitted'] or digest(path)!=before:
            raise ValueError('capture count/hash mismatch')
        qdisc={phase:json.loads((run/(phase+'-'+role+'.log')).read_text()) for phase in ('before','after')}
        roots={phase:next(q for q in qs if q.get('root')) for phase,qs in qdisc.items()}
        output['roles'][role]=dict(native_sha256=before,flows=summarize_flows(selected,start,end,event_ns),
            whole_run_root_qdisc_drop_delta=roots['after']['drops']-roots['before']['drops'],
            qdisc_scope='whole-run root counter only; child counters overlap and are not summed; no per-flow or event-window loss attribution')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',type=Path);parser.add_argument('--event-ns',type=int,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.write_text(json.dumps(analyze(args.run,args.event_ns),indent=2)+'\n')
