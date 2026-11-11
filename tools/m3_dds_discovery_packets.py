"""Closed-capture identities for the standalone28-byte native HELLO fixture."""
import hashlib
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
from m3_rtps_discovery import field,MAX_BYTES,MAX_RECORDS

TOPICS={'M3FragmentHelloRobot','M3FragmentHelloOperator'}


def decode(payload,role):
    if len(payload)!=28:raise ValueError('native HELLO payload size differs')
    header,magic,source,sequence,stamp=struct.unpack('!4sIIQQ',payload)
    if header!=bytes(4) or magic!=0x48454c31 or source!=role or not sequence or not stamp:raise ValueError('native HELLO content mismatch')
    return dict(sequence=sequence,sent_ns=stamp,payload_sha256=hashlib.sha256(payload).hexdigest())


def hellos(path,writers):
    if path.stat().st_size>MAX_BYTES:raise ValueError('PDML budget exceeded')
    rows=[];count=0
    with path.open('rb') as stream:
        it=ET.iterparse(stream,events=('start','end'));_,root=next(it)
        if root.tag!='pdml' or root.get('creator')!='wireshark/4.2.2':raise ValueError('unexpected decoder')
        for event,p in it:
            if event!='end' or p.tag!='packet':continue
            count+=1
            if count>MAX_RECORDS:raise ValueError('PDML record budget exceeded')
            for proto in p.findall("proto[@name='rtps']"):
                prefix=field(proto,'rtps.guidPrefix.src','value',required=True)
                if any(sm.get('show')=='0x0c' for sm in proto.findall("field[@name='rtps.sm.id']")):raise ValueError('INFO_SRC unsupported')
                for sm in proto.findall("field[@name='rtps.sm.id'][@show='0x15']"):
                    writer=prefix+int(field(sm,'rtps.sm.wrEntityId',required=True),0).to_bytes(4,'big').hex()
                    if writer not in writers:continue
                    raw=bytes.fromhex(sm.get('value',''));encap=[f for f in sm.iter('field') if f.get('name')=='rtps.param.serialize.encap_kind']
                    if len(encap)!=1 or len(raw)<24 or raw[1]&14!=4:raise ValueError('native HELLO payload not explicit DATA')
                    offset=int(encap[0].get('pos'))-int(sm.get('pos'))
                    if not 24<=offset<len(raw):raise ValueError('invalid payload offset')
                    proof=decode(raw[offset:],writers[writer])
                    rows.append(dict(proof,frame=int(field(p,'frame.number',required=True)),writer=writer,source=field(p,'ip.src',required=True),destination=field(p,'ip.dst',required=True)))
            p.clear();root.clear()
    return rows


def assess(result,parsed,payloads):
    expected={result['initial'][r]['writer']:1 if r=='operator' else 2 for r in ('operator','robot')}
    bindings={}
    for role,data in parsed.items():
        directory={e['endpoint'] for e in data['rows'] if e['topic'] in TOPICS and e['endpoint']}
        bindings[role]=sorted(directory)
        if not set(expected).issubset(directory):raise ValueError('final complete publication advertisements missing')
        if data['fragment_frames']<=0:raise ValueError('deliberately enlarged discovery did not fragment')
    key=lambda r:(r['writer'],r['sequence'],r['payload_sha256'])
    sets={role:{key(e) for e in rows} for role,rows in payloads.items()}
    if sets['operator']!=sets['robot']:raise ValueError('native HELLO identities differ between captures')
    output=dict(bindings=bindings,matched_native_hello_identities=len(sets['operator']),scope='closed full-run packet identities; capture order and encoded VM origins, not realtime PCAP latency authority, original ROS/N5 cause or middleware delivery for every DATA')
    if result['case']=='fragment-cut':
        start=result['hold']['begin_ns'];end=result['remove']['begin_ns'];writer=result['initial']['robot']['writer']
        selected={role:[r for r in rows if r['writer']==writer and start<=r['sent_ns']<=end] for role,rows in payloads.items()}
        if len(selected['operator'])<20 or {key(e) for e in selected['operator']}!={key(e) for e in selected['robot']}:raise ValueError('insufficient matching robot HELLO origins during cut')
        ads=[e for e in parsed['operator']['rows'] if e['endpoint']==writer]
        if not ads:raise ValueError('robot publication never observed after restore')
        first=min(e['frame'] for e in ads);earlier=[r for r in selected['operator'] if r['frame']<first]
        if len(earlier)<20:raise ValueError('no unknown-writer DATA-before-complete-advertisement signature')
        output.update(robot_hello_origins_in_cut={r:len(v) for r,v in selected.items()},robot_hellos_before_first_complete_advertisement=len(earlier),first_complete_robot_publication_frame=first)
    return output
