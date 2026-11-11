#!/usr/bin/env python3
"""Closed capture identities and layered telemetry counters; no payload decryption."""
import argparse
from collections import Counter,defaultdict
import hashlib
import ipaddress
import json
from pathlib import Path
import struct
from m3_capture import classify,summarize,validate_tcpdump_footer
from m3_source_preflight import ROOT

CONTROL_TYPES={0:'handshake',1:'keepalive',2:'ack',3:'nak',4:'congestion',5:'shutdown',6:'ackack',7:'drop_request',8:'peer_error',32767:'user_defined'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def udp_records(paths):
    for path in paths:
        with Path(path).open('rb') as f:
            h=f.read(24)
            formats={b'\xd4\xc3\xb2\xa1':'<',b'\xa1\xb2\xc3\xd4':'>',b'\x4d\x3c\xb2\xa1':'<',b'\xa1\xb2\x3c\x4d':'>'}
            if len(h)!=24 or h[:4] not in formats:raise ValueError('invalid classic pcap header')
            endian=formats[h[:4]]
            if struct.unpack_from(endian+'HH',h,4)!=(2,4) or struct.unpack_from(endian+'I',h,20)[0]!=1:raise ValueError('unsupported pcap version/link')
            while True:
                r=f.read(16)
                if not r:break
                if len(r)!=16:raise ValueError('truncated record header')
                _,_,size,original=struct.unpack(endian+'IIII',r)
                if not 42<=size<=262144 or size!=original:raise ValueError('truncated/invalid frame length')
                frame=f.read(size)
                if len(frame)!=size:raise ValueError('truncated frame')
                if frame[12:14]!=b'\x08\x00':raise ValueError('non IPv4 frame')
                ip=frame[14:];ihl=(ip[0]&15)*4;total=struct.unpack_from('!H',ip,2)[0]
                if ip[0]>>4!=4 or not 20<=ihl<=60 or not ihl+8<=total<=len(ip) or ip[9]!=17 or struct.unpack_from('!H',ip,6)[0]&0x3fff:raise ValueError('invalid/fragmented/nonUDP IP')
                sp,dp,length=struct.unpack_from('!HHH',ip,ihl)
                if length!=total-ihl or length<8:raise ValueError('invalid UDP length')
                yield str(ipaddress.ip_address(ip[12:16])),str(ipaddress.ip_address(ip[16:20])),sp,dp,ip[ihl+8:total]


def packet_view(paths,local):
    identities={'out':Counter(),'in':Counter()};groups={};controls=Counter();classes=Counter()
    for source,dest,sp,dp,payload in udp_records(paths):
        direction='out' if source==local else 'in' if dest==local else None
        if direction is None:raise ValueError('capture packet does not involve owned endpoint')
        category=classify(payload,sp,dp);classes[direction+'/'+category]+=1
        identities[direction][(source,dest,sp,dp,sha_bytes(payload))]+=1
        if category.endswith('_srt_control'):
            kind=(struct.unpack_from('!I',payload)[0]>>16)&0x7fff;controls[direction+'/'+category+'/'+CONTROL_TYPES.get(kind,str(kind))]+=1
        if category not in ('sensor_source_data','sensor_fec_parity'):continue
        word0,word1,_,socket=struct.unpack_from('!IIII',payload)
        key=(direction,category,source,dest,sp,dp,socket)
        g=groups.setdefault(key,dict(packets=0,bytes=0,seqs=set(),messages=set(),retransmitted=0,boundaries=Counter()))
        g['packets']+=1;g['bytes']+=len(payload);g['seqs'].add(word0&0x7fffffff);g['messages'].add(word1&0x03ffffff);g['retransmitted']+=(word1>>26)&1;g['boundaries'][(word1>>30)&3]+=1
    result=[]
    for key,g in groups.items():
        lo=min(g['messages']);hi=max(g['messages']);span=hi-lo+1 if hi-lo<2**25 else None
        result.append(dict(direction=key[0],category=key[1],source=key[2],destination=key[3],source_port=key[4],destination_port=key[5],destination_socket=key[6],packets=g['packets'],udp_payload_bytes=g['bytes'],unique_sequences=len(g['seqs']),unique_message_numbers=len(g['messages']),retransmitted_packets=g['retransmitted'],boundaries=dict(g['boundaries']),numeric_message_span=span,unobserved_numbers_inside_span=span-len(g['messages']) if span is not None else None,scope='outer-header observations per socket/flow, not typed SAMPLE counts or proof of packet/message loss'))
    return dict(identities=identities,classes=dict(classes),control_types=dict(controls),sensor_connections=result)


def sha_bytes(value):return hashlib.sha256(value).hexdigest()


def compare(source,sink):
    missing=source-sink;extra=sink-source
    return dict(source_records=sum(source.values()),sink_records=sum(sink.values()),matched_records=sum((source&sink).values()),source_not_at_sink=sum(missing.values()),sink_not_at_source=sum(extra.values()),equal_multisets=source==sink,scope='exact UDP tuple+payload-hash MULTISETS over closed captures; not pre-tap emission/delivery, application mapping or latency')


def qdisc_delta(run,role):
    first=json.loads((run/('before-'+role+'.log')).read_text());last=json.loads((run/('after-'+role+'.log')).read_text());result=[]
    for a in first:
        matches=[b for b in last if (b['kind'],b['handle'],b.get('parent'))==(a['kind'],a['handle'],a.get('parent'))]
        if len(matches)!=1:raise ValueError('qdisc identity changed')
        b=matches[0]
        if b.get('options')!=a.get('options'):raise ValueError('qdisc options changed')
        delta={k:b.get(k,0)-a.get(k,0) for k in ('bytes','packets','drops','overlimits','requeues')}
        if any(v<0 for v in delta.values()):raise ValueError('qdisc counters regressed')
        result.append(dict(kind=a['kind'],handle=a['handle'],parent=a.get('parent'),options=a.get('options'),delta=delta,end_backlog=b.get('backlog'),end_qlen=b.get('qlen')))
    return dict(layers=result,scope='hierarchical counters; root/child may mirror same drops, NEVER sum; different snapshot tails from captures/app window; no per-flow loss allocation')


def analyze(run,expected=None):
    run=Path(run).resolve();d=json.loads((run/'run.json').read_text())
    if d['status']!='passed' or d.get('pcap_population_reconciled') is not True:raise ValueError('original harness/capture integrity did not pass')
    addresses=json.loads((run/'network.json').read_text())['addresses'];views={};inputs={};captures={}
    for role in ('robot','operator'):
        paths=sorted(run.glob(role+'.pcap*'))
        if not paths:raise ValueError('missing capture rotations')
        for p in paths:
            key=str(p.relative_to(ROOT));digest=sha(p)
            if expected is not None and (key not in expected or expected[key]['sha256']!=digest):raise ValueError('original capture hash mismatch')
            inputs[key]=dict(bytes=p.stat().st_size,sha256=digest)
        summary=summarize(paths,addresses[role]);footer=validate_tcpdump_footer((run/(role+'-capture.log')).read_text(),summary['records'])
        if summary['unaccounted'] or not footer['tcpdump_population_reconciled'] or summary['records']!=d['captures'][role]['records']:raise ValueError('unreconciled capture population/parse')
        views[role]=packet_view(paths,addresses[role]);captures[role]=dict(records=summary['records'],classes=summary['classes'],footer=footer)
    identities=dict(robot_to_operator=compare(views['robot']['identities']['out'],views['operator']['identities']['in']),operator_to_robot=compare(views['operator']['identities']['out'],views['robot']['identities']['in']))
    for role in views:views[role].pop('identities')
    result=dict(run=str(run.relative_to(ROOT)),original_status=d['status'],profile=d['profile'],seed=d['seed'],measurement_seconds=d['seconds'],application=d['measurement_window'],window_rejections={k:d['results']['checkpoints']['end']['receiver'][k]-d['results']['checkpoints']['begin']['receiver'][k] for k in ('transport_samples_received','transport_samples_rejected','transport_samples_unknown_age','transport_samples_stale')},captures=captures,identity_comparison=identities,outer_headers=views,qdisc={r:qdisc_delta(run,r) for r in views},raw_capture_hashes=inputs,limitations=['Whole closed capture includes setup/teardown, not application measurement window; no PCAP timing/age authority.','SDK acceptance != packet emission or decoded application delivery; source/parity/fragment/retransmission counts are not one-to-one SAMPLEs.','Equal tap identities cannot exclude loss before source tap; qdisc layers cannot be summed/assigned to individual flows.','No SENSOR provider internals or encrypted typed-source mapping observed; packet counts do not uniquely establish an internal cause.'])
    if any(sha(ROOT/p)!=v['sha256'] for p,v in inputs.items()):raise ValueError('capture changed during analysis')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--hash-manifest',type=Path);a=p.parse_args()
    if a.out.exists():raise FileExistsError('analysis output reuse refused')
    try:result=dict(status='passed',analysis=analyze(a.run,json.loads(a.hash_manifest.read_text()) if a.hash_manifest else None))
    except Exception as e:result=dict(status='failed',error=str(e))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],str(a.run));return 0 if result['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
