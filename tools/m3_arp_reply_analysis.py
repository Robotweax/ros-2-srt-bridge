"""Closed synthetic ARP/UDP phase gates; no durable SRT command authority."""
from collections import Counter
import hashlib,json,socket,struct
from pathlib import Path
from m3_arp_gap_observations import parse_arp
from m3_udp_path_analysis import arp_kind
from m3_tap_probe import probe_id,MAGIC
from m3_monotonic_capture import records
from m3_capture import validate_tcpdump_footer


def frame_key(frame,length):
    if len(frame)<14:raise ValueError('short captured Ethernet')
    if frame[12:14]==b'\x08\x06':
        a=parse_arp(dict(prefix=frame,length=length,artifact_version=2,vlan_present=0,gso_size=0,gso_segs=1,packet_type=0,monotonic_ns=1))
        return ('arp',length,a['operation'],a['ethernet_source_mac'],a['ethernet_destination_mac'],a['sender_mac'],a['sender_ipv4'],a['target_mac'],a['target_ipv4'])
    if frame[12:14]!=b'\x08\x00' or len(frame)<42 or frame[23]!=17:return None
    if frame[14]!=0x45 or struct.unpack_from('!H',frame,20)[0]&0x3fff:raise ValueError('unsupported synthetic IP framing')
    identity=probe_id(frame)
    if identity is None:raise ValueError('unexpected UDP in isolated fixture')
    if length!=1242 or struct.unpack_from('!HH',frame,34)!=(10080,39781):raise ValueError('wrong probe size/ports')
    if len(frame)==length:
        expected=MAGIC+struct.pack('!II',*identity)+bytes(1184)
        if frame[42:]!=expected:raise ValueError('changed synthetic payload')
    return ('udp',length,*identity)


def pcap_keys(path):
    keys=[];count=0
    with path.open('rb') as f:
        h=f.read(24)
        if len(h)!=24 or h[:4]!=b'\xd4\xc3\xb2\xa1' or struct.unpack_from('<HH',h,4)!=(2,4) or struct.unpack_from('<I',h,20)[0]!=1:raise ValueError('unsupported synthetic pcap')
        while True:
            r=f.read(16)
            if not r:break
            if len(r)!=16:raise ValueError('short pcap record')
            _,_,size,original=struct.unpack('<IIII',r)
            if size!=original or not 42<=size<=262144:raise ValueError('truncated/oversized captured frame')
            frame=f.read(size)
            if len(frame)!=size:raise ValueError('short pcap frame')
            key=frame_key(frame,size)
            if key is None:raise ValueError('unaccounted synthetic pcap frame')
            keys.append(key);count+=1
    return Counter(keys),count


def selected_key(key,addresses):
    if key[0]=='udp':return True
    return key[0]=='arp' and key[2] in (1,2) and (key[6],key[8]) in ((addresses['operator'],addresses['robot']),(addresses['robot'],addresses['operator']))


def phase_gate(case,fault,installation,controller,sent,received,native):
    if controller['status']!='passed' or not received['complete']:raise ValueError('controller/receiver incomplete')
    start=installation['end_ns'];remove=controller['removal'];end=remove['begin_ns'];origin=sent['rows'][0]['before_ns']
    if not 0<start<origin or not origin+1250000000<=end<=remove['end_ns']<origin+2000000000:raise ValueError('unqualified active/restoration timing')
    if sent['count']!=3 or sent['case']!=case or [r['sequence'] for r in sent['rows']]!=[0,1,2] or not all(start<=r['before_ns']<=r['after_ns']<end for r in sent['rows']):raise ValueError('original sends were not once inside fault/control eligibility')
    count=controller['snapshots'][-1]['counters'];eligible=count['eligible'];verdict=count['verdict']
    if count['verdict_type']!=('drop' if fault else 'pass') or controller['snapshots'][0]['counters']!=count or not eligible['packets'] or any(eligible[k]!=verdict[k] for k in ('packets','bytes')) or eligible['drops'] or verdict['drops']!=(verdict['packets'] if fault else 0):raise ValueError('counter eligibility/verdict populations do not prove phase')
    wanted=Counter({(case,n):1 for n in range(3)}|{(case+1000,0):1})
    if Counter((r['case'],r['sequence']) for r in received['rows'])!=wanted:raise ValueError('receiver identity/duplicate population mismatch')
    for r in received['rows']:
        expected=MAGIC+struct.pack('!II',r['case'],r['sequence'])+bytes(1184)
        if r['sha256']!=hashlib.sha256(expected).hexdigest():raise ValueError('receiver payload hash mismatch')
    matched={}
    for role,rows in native.items():
        udp=[r for r in rows if r.get('probe')];main=[r for r in udp if r['probe'][0]==case]
        if Counter(tuple(r['probe']) for r in udp)!=wanted:raise ValueError('native original/fresh UDP identity mismatch')
        replies=[r for r in rows if r.get('arp',{}).get('identity_class')==('outgoing_local_reply' if role=='robot' else 'incoming_peer_reply')]
        active=[r for r in replies if start<=r['monotonic_ns']<end]
        if fault:
            if active or any(r['monotonic_ns']<end for r in main):raise ValueError('reply/UDP escaped controlled reply loss')
            if not any(r['monotonic_ns']>=remove['end_ns'] for r in replies):raise ValueError('no genuine reply observed after restoration')
        elif len(active)!=eligible['packets'] or not all(r['monotonic_ns']<end for r in main):raise ValueError('clean reply/UDP path not positively qualified')
        matched[role]=dict(original_udp=len(main),fresh_udp=len(udp)-len(main),replies_in_active=len(active),replies_after_remove=sum(r['monotonic_ns']>=remove['end_ns'] for r in replies))
    main_received=[r for r in received['rows'] if r['case']==case]
    if fault and any(r['monotonic_ns']<remove['end_ns'] for r in main_received):raise ValueError('application delivery preceded fault restoration')
    if not fault and any(r['monotonic_ns']>=end for r in main_received):raise ValueError('clean application delivery not within active observer phase')
    return dict(guaranteed_rule_active_ns=[start,end],source_origin_ns=origin,removal=remove,eligible_replies=eligible['packets'],dropped_replies=verdict['drops'],native=matched,original_udp_delivered_once=3,fresh_udp_delivered_once=1,scope='Synthetic kernel ARP reply eligibility/verdict counter versus post-classifier hooks and exact UDP identities; not N5 or SRT command execution proof.')


def analyze_case(run,result):
    run=Path(run);native={};captures={};arps={};addresses=result['addresses'];macs=result['neighbor_configuration']['peer_macs']
    for role in ('operator','robot'):
        rows=list(records(run/(role+'.mono')));status=json.loads((run/(role+'-monotonic-capture.log')).read_text().splitlines()[-1])
        if status.get('artifact_version')!=2 or status.get('clock')!='kernel_monotonic' or not status.get('time_namespace_zero') or not status.get('complete') or not status['records']==status['seen']==status['submitted']==len(rows) or status['reserve_failed'] or status['copy_failed']:raise ValueError('native capture incomplete')
        if not status['ready_ns']<=result['installation']['begin_ns']<result['controller']['removal']['end_ns']<=status['stop_before_ns']:raise ValueError('native phase coverage not qualified')
        keys=[];selected=[];peer='robot' if role=='operator' else 'operator'
        for r in rows:
            if r['ifindex']!=status['ifindex']:raise ValueError('native interface changed')
            key=frame_key(r['prefix'],r['length'])
            if key is None:continue
            if r['gso_size'] or r['gso_segs'] not in (0,1) or r['vlan_present'] or r['length']>status['mtu']+14:raise ValueError('unqualified native framing')
            keys.append(key);value=dict(monotonic_ns=r['monotonic_ns'],packet_type=r['packet_type'])
            if key[0]=='udp':
                f=r['prefix']
                if r['packet_type']!=(4 if role=='operator' else 0) or f[26:30]!=socket.inet_aton(addresses['operator']) or f[30:34]!=socket.inet_aton(addresses['robot']) or f[6:12].hex(':')!=macs['operator'] or f[:6].hex(':')!=macs['robot']:raise ValueError('synthetic UDP owned direction/identity mismatch')
                value['probe']=key[2:]
            else:
                a=parse_arp(r);a['identity_class']=arp_kind(a,addresses[role],addresses[peer],macs[role],macs[peer]);value['arp']=a
            selected.append(value)
        pcap,count=pcap_keys(run/(role+'.pcap'));footer=validate_tcpdump_footer((run/(role+'-capture.log')).read_text(),count)
        all_native=Counter(keys);native_selected=Counter({k:v for k,v in all_native.items() if selected_key(k,addresses)});pcap_selected=Counter({k:v for k,v in pcap.items() if selected_key(k,addresses)})
        if not footer['tcpdump_population_reconciled'] or pcap_selected!=native_selected:raise ValueError('native/pcap owned-peer ARP and UDP identity multiset mismatch')
        captures[role]=dict(status=status,pcap=footer,all_native_selected_link_records=len(keys),owned_peer_records=sum(native_selected.values()),background_native=[dict(key=list(k),count=v) for k,v in all_native.items() if not selected_key(k,addresses)],background_pcap=[dict(key=list(k),count=v) for k,v in pcap.items() if not selected_key(k,addresses)],background_identity_equal=Counter({k:v for k,v in all_native.items() if not selected_key(k,addresses)})==Counter({k:v for k,v in pcap.items() if not selected_key(k,addresses)}),scope='All native/file/filter populations retained; only predeclared cross-owned-peer ARP and labeled UDP identities compared across recorder spans. Background gratuitous/other ARP retained, not assigned to the controlled path.');native[role]=selected;arps[role]=[r for r in selected if 'arp' in r]
    sent=json.loads((run/'sent.json').read_text());received=json.loads((run/'received.json').read_text())
    result['phase_proof']=phase_gate(result['number'],result['fault'],result['installation'],result['controller'],sent,received,native)
    result['captures']=captures;result['arp_observations']=arps;result['udp_observations']={r:[x for x in v if 'probe' in x] for r,v in native.items()}
    return result
