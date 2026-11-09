"""Strict packet lifecycle joins; no loss inference from counter subtraction."""
from collections import defaultdict
import json,socket
from pathlib import Path
from m3_monotonic_capture import records
from m3_capture import validate_tcpdump_footer
from m3_arp_reply_analysis import pcap_keys
from m3_arp_trace_stimulus import request_frame


def lifecycles(events,status,ready,reasons):
    if status.get('complete') is not True or status.get('deadline') is not False or status.get('time_namespace_zero') is not True or status.get('detached_hooks')!=6:raise ValueError('trace incomplete')
    for field in ('reserve_failed','map_failed','read_failed','collision','pending'):
        if status.get(field)!=0:raise ValueError('trace loss or censored '+field)
    if status.get('records')!=len(events) or status.get('emitted')!=len(events):raise ValueError('trace event population mismatch')
    if ready.get('hooks')!=6 or ready.get('clock')!='kernel_monotonic' or ready.get('ready_ns')!=status.get('ready_ns'):raise ValueError('trace readiness')
    groups=defaultdict(list)
    for event in events:
        if set(event)!=set(('ns','cookie','kind','aux','handle','parent')) or any(type(v)!=int or v<0 for v in event.values()):raise ValueError('trace event schema')
        if event['kind'] not in range(1,7) or not status['ready_ns']<=event['ns']<=status['detach_before_ns'] or not event['cookie']:raise ValueError('trace event scope')
        if event['kind'] in (1,4,6) and any(event[k] for k in ('aux','handle','parent')):raise ValueError('unexpected stage metadata')
        if event['kind']==5 and (event['handle'] or event['parent']):raise ValueError('unexpected free metadata')
        if event['kind']==2 and event['aux']:raise ValueError('unexpected enqueue metadata')
        groups[event['cookie']].append(event)
    if set(groups)!=set(range(1,status['created']+1)) or status['created']!=status['retired']:raise ValueError('trace lifetime population mismatch')
    result=[]
    for cookie,unsorted in sorted(groups.items()):
        rows=sorted(unsorted,key=lambda e:e['ns']);kinds=[r['kind'] for r in rows]
        if kinds[0]!=1 or kinds.count(1)!=1 or sum(k in (4,5,6) for k in kinds)!=1 or kinds[-1] not in (4,5,6):raise ValueError('invalid lifecycle boundaries')
        if any(a['ns']>=b['ns'] for a,b in zip(rows,rows[1:])):raise ValueError('ambiguous lifecycle ordering')
        terminal=rows[-1];reason=reasons.get(str(terminal['aux'])) if terminal['kind']==5 else None
        if terminal['kind']==5 and reason is None:raise ValueError('unknown BTF drop reason')
        outcome='driver_start' if terminal['kind']==4 else 'qdisc_drop' if reason=='SKB_DROP_REASON_QDISC_DROP' else 'other_free' if terminal['kind']==5 else 'consumed_before_driver'
        residence=[];ambiguous=[];enqueued={}
        for event in rows[1:-1]:
            if event['kind'] not in (2,3):raise ValueError('unexpected nonterminal stage')
            key=(event['handle'],event['parent'])
            if event['kind']==2:
                if key in enqueued:ambiguous.append('repeated_enqueue')
                enqueued[key]=event
            else:
                if event['aux']!=1:ambiguous.append('bulk_dequeue')
                elif key not in enqueued:ambiguous.append('dequeue_without_enqueue')
                else:residence.append(dict(handle=key[0],parent=key[1],enqueue_ns=enqueued.pop(key)['ns'],dequeue_ns=event['ns']))
        for r in residence:r['residence_ns']=r['dequeue_ns']-r['enqueue_ns']
        result.append(dict(cookie=cookie,outcome=outcome,reason=reason,reason_code=terminal['aux'] if terminal['kind']==5 else None,created_ns=rows[0]['ns'],terminal_ns=terminal['ns'],stage_kinds=kinds,residence=residence,ambiguities=ambiguous,unmatched_enqueues=len(enqueued)))
    return result


def last_json(path):
    return json.loads(Path(path).read_text().strip().splitlines()[-1])


def reply_header(addresses,macs):
    src=bytes.fromhex(macs['robot'].replace(':',''));dst=bytes.fromhex(macs['operator'].replace(':',''))
    return dst+src+bytes.fromhex('08060001080006040002')+src+socket.inet_aton(addresses['robot'])+dst+socket.inet_aton(addresses['operator'])


def analyze(run,result):
    run=Path(run);trace_status=last_json(run/'trace.log');trace_ready=json.loads((run/'trace-ready.json').read_text());events=[json.loads(s) for s in (run/'trace.jsonl').read_text().splitlines()]
    reasons=json.loads((run/'btf.json').read_text())['drop_reasons'];rows=lifecycles(events,trace_status,trace_ready,reasons)
    if not rows:raise ValueError('no calibrated reply lifetimes')
    addresses=result['addresses'];macs=result['macs'];header=reply_header(addresses,macs);request=request_frame(addresses['operator'],addresses['robot'],macs['operator'],macs['robot']);captures={}
    for role in ('operator','robot'):
        native=list(records(run/(role+'.mono')));status=last_json(run/(role+'-monotonic-capture.log'))
        if not status.get('complete') or status.get('artifact_version')!=2 or not status.get('time_namespace_zero') or status.get('reserve_failed') or status.get('copy_failed') or not status['records']==status['seen']==status['submitted']==len(native):raise ValueError('native incomplete')
        if not status['ready_ns']<=trace_ready['ready_ns']<trace_status['detach_before_ns']<=status['stop_before_ns']:raise ValueError('native coverage')
        selected=[r for r in native if r['prefix'][:42]==header]
        request_rows=[r for r in native if r['prefix'][:42]==request]
        for r in selected+request_rows:
            if r['ifindex']!=status['ifindex'] or r['vlan_present'] or r['gso_size'] or r['gso_segs'] not in (0,1):raise ValueError('native scope/offload')
        if any(r['packet_type']!=(4 if role=='robot' else 0) for r in selected):raise ValueError('reply direction')
        if any(r['packet_type']!=(0 if role=='robot' else 4) for r in request_rows):raise ValueError('request direction')
        keys,count=pcap_keys(run/(role+'.pcap'));footer=validate_tcpdump_footer((run/(role+'-capture.log')).read_text(),count)
        if not footer['tcpdump_population_reconciled']:raise ValueError('pcap population')
        pc_replies=sum(v for k,v in keys.items() if k[0]=='arp' and k[2]==2 and k[3]==macs['robot'] and k[4]==macs['operator'] and k[5]==macs['robot'] and k[6]==addresses['robot'] and k[7]==macs['operator'] and k[8]==addresses['operator'])
        pc_requests=sum(v for k,v in keys.items() if k[0]=='arp' and k[2]==1 and k[3]==macs['operator'] and k[4]==macs['robot'] and k[6]==addresses['operator'] and k[8]==addresses['robot'])
        if pc_replies!=len(selected) or pc_requests!=len(request_rows):raise ValueError('ARP native/pcap population mismatch')
        captures[role]=dict(native=status,pcap=footer,replies=len(selected),requests=len(request_rows),other_arp_pcap=count-pc_replies-pc_requests)
    driver=sum(r['outcome']=='driver_start' for r in rows)
    if driver!=captures['robot']['replies'] or driver!=captures['operator']['replies']:raise ValueError('driver/native source/peer reply population mismatch')
    if any(c['requests']!=30 for c in captures.values()):raise ValueError('request count mismatch')
    if result['profile']=='N0' and (len(rows)!=30 or driver!=30):raise ValueError('clean calibration failed')
    if any(r['ambiguities'] or r['outcome'] in ('other_free','consumed_before_driver') for r in rows):raise ValueError('unqualified lifecycle branch')
    return dict(status='passed',trace=trace_status,captures=captures,lifetimes=rows,counts={k:sum(r['outcome']==k for r in rows) for k in ('driver_start','qdisc_drop','other_free','consumed_before_driver')},queued_and_dequeued=sum(bool(r['residence']) for r in rows),scope='Per-cookie source TX lifecycle through driver-start or pre-driver free; no physical-wire or per-reply peer matching claim; repeated ARP headers have no nonce. No inference from counter subtraction.')
