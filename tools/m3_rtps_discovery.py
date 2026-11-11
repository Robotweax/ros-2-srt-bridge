#!/usr/bin/env python3
"""Bounded submessage-scoped adapter for pinned tshark4.2.2 PDML, not a DDS stack."""
import argparse
from collections import Counter,defaultdict
import hashlib
import ipaddress
import json
from pathlib import Path
import secrets
import subprocess
import xml.etree.ElementTree as ET
from m3_source_preflight import ROOT,sha,write
from m3_capture import summarize,validate_tcpdump_footer

TOPICS=['rt/dds/commands/'+suffix for suffix in ('operator','robot','operator_hello','robot_hello')]
MAX_BYTES=512<<20
MAX_RECORDS=200000


def field(element,name,attribute='show',required=False):
    values={f.get(attribute) for f in element.iter('field') if f.get('name')==name}
    if len(values)>1:raise ValueError('ambiguous field '+name)
    value=next(iter(values),None)
    if required and value is None:raise ValueError('missing field '+name)
    return value


def hex_value(value,length):
    if value is None:return None
    if len(value)!=length*2 or len(bytes.fromhex(value))!=length:raise ValueError('invalid GUID width')
    return value.lower()


def parse(path):
    if path.stat().st_size>MAX_BYTES:raise ValueError('PDML byte budget exceeded')
    rows=[];packets=0;submessages=Counter();fragment_frames=0;last_frame=0;fragments=[]
    with path.open('rb') as stream:
        events=ET.iterparse(stream,events=('start','end'));_,root=next(events)
        if root.tag!='pdml' or root.get('creator')!='wireshark/4.2.2':raise ValueError('unexpected PDML decoder/schema')
        for event,packet in events:
            if event!='end' or packet.tag!='packet':continue
            packets+=1
            if packets>MAX_RECORDS or sum(1 for _ in packet.iter())>20000:raise ValueError('PDML record/field budget exceeded')
            number=int(field(packet,'frame.number',required=True))
            if number<=last_frame:raise ValueError('duplicate/regressed capture frame')
            last_frame=number
            if any(p.get('name')=='_ws.malformed' for p in packet.iter('proto')):raise ValueError('malformed decoded packet')
            source=field(packet,'ip.src',required=True);destination=field(packet,'ip.dst',required=True)
            ipaddress.ip_address(source);ipaddress.ip_address(destination)
            is_fragment=field(packet,'ip.frag_offset') not in (None,'0') or field(packet,'ip.flags.mf') in ('1','True')
            fragment_frames+=int(is_fragment)
            if is_fragment:fragments.append(dict(frame=number,source=source,destination=destination,ip_id=field(packet,'ip.id'),offset=field(packet,'ip.frag_offset'),more=field(packet,'ip.flags.mf'),reassembled_in=field(packet,'ip.reassembled_in'),reassembled_length=field(packet,'ip.reassembled.length')))
            for proto in packet.findall("proto[@name='rtps']"):
                prefix=hex_value(field(proto,'rtps.guidPrefix.src','value',required=True),12)
                destination_prefix=None
                for sm in proto.findall("field[@name='rtps.sm.id']"):
                    kind=int(sm.get('show'),0);submessages[hex(kind)]+=1
                    if kind==0x0c:raise ValueError('INFO_SRC context unsupported; attribution withheld')
                    if kind==0x0e:
                        destination_prefix=hex_value(field(sm,'rtps.guidPrefix.dst','value',required=True),12);continue
                    if kind not in (0x15,0x16,0x06,0x07):continue
                    w=field(sm,'rtps.sm.wrEntityId');r=field(sm,'rtps.sm.rdEntityId')
                    if w is None or r is None:raise ValueError('missing scoped endpoint ID')
                    writer=int(w,0).to_bytes(4,'big').hex();reader=int(r,0).to_bytes(4,'big').hex()
                    # HEARTBEAT carries first/last sequence values; ACKNACK
                    # carries a set. Neither is a DATA sample sequence.
                    seq=field(sm,'rtps.sm.seqNumber',required=True) if kind in (0x15,0x16) else None
                    topic=field(sm,'rtps.param.topicName');endpoint=hex_value(field(sm,'rtps.param.endpoint_guid','value'),16)
                    if bool(topic)!=bool(endpoint):
                        # Non-endpoint built-in payloads can have topic/type without
                        # a GUID. They cannot establish an application binding.
                        topic=None;endpoint=None
                    raw=sm.get('value')
                    if raw is None or len(raw)>131078:raise ValueError('missing/oversized raw submessage identity')
                    rows.append(dict(frame=number,source=source,destination=destination,source_prefix=prefix,destination_prefix=destination_prefix,kind=kind,writer=prefix+writer,reader_entity=reader,sequence=int(seq) if seq else None,topic=topic,endpoint=endpoint,submessage_sha256=hashlib.sha256(bytes.fromhex(raw)).hexdigest()))
                    if len(rows)>MAX_RECORDS:raise ValueError('submessage budget exceeded')
            packet.clear();root.clear()
    return dict(packets=packets,fragment_frames=fragment_frames,fragments=fragments,submessages=dict(submessages),rows=rows)


def assess(decoded,addresses):
    # Union is a retrospective GUID directory, not proof a live peer processed it.
    bindings=defaultdict(set);adverts=[]
    for role,data in decoded.items():
        for row in data['rows']:
            if row['topic'] in TOPICS and row['endpoint']:
                if row['writer'][-8:] not in ('000003c2','000004c2'):raise ValueError('endpoint topic outside known SEDP writer')
                if row['endpoint'][:24]!=row['source_prefix']:raise ValueError('advertised endpoint/source participant differs')
                side='publication' if row['writer'].endswith('000003c2') else 'subscription'
                bindings[row['endpoint']].add((row['topic'],side))
                adverts.append(dict(row,capture=role,side=side))
    if any(len(v)!=1 for v in bindings.values()):raise ValueError('ambiguous endpoint/topic binding')
    topics={topic:dict(advertisements={},data={}) for topic in TOPICS}
    for topic in TOPICS:
        for role,data in decoded.items():
            local=addresses[role];peer=addresses['operator' if role=='robot' else 'robot']
            selected=[r for r in adverts if r['capture']==role and r['topic']==topic]
            topics[topic]['advertisements'][role]=dict(observations=len(selected),rows=selected)
            messages=[]
            for row in data['rows']:
                binding=bindings.get(row['writer'])
                if binding=={(topic,'publication')} and row['kind'] in (0x15,0x16):
                    direction='own_source' if row['source']==local else 'peer_source' if row['source']==peer else 'other_source'
                    messages.append(dict(row,direction=direction))
            available=any(v=={(topic,'publication')} for v in bindings.values())
            topics[topic]['data'][role]=dict(publication_binding_available=available,observations=len(messages) if available else None,by_direction=dict(Counter(r['direction'] for r in messages)),unique_writer_sequences=len({(r['writer'],r['sequence']) for r in messages}) if available else None,rows=messages)
    # Presence by complete submessage identity, not a paired datagram loss count.
    cross={}
    for role in ('operator','robot'):
        peer='robot' if role=='operator' else 'operator'
        def relevant(row):
            return row['source']==addresses[role] and (row['destination']==addresses[peer] or ipaddress.ip_address(row['destination']).is_multicast)
        own=[r for r in adverts if r['capture']==role and relevant(r)]
        other=[r for r in adverts if r['capture']==peer and relevant(r)]
        key=lambda r:(r['writer'],r['sequence'],r['submessage_sha256'],r['topic'],r['endpoint'],r['side'])
        a={key(r) for r in own};b={key(r) for r in other}
        cross[role]=dict(source_unique=len(a),peer_unique=len(b),present_both=len(a&b),source_only=[dict(writer=k[0],sequence=k[1],submessage_sha256=k[2],topic=k[3],endpoint=k[4],side=k[5]) for k in sorted(a-b)],peer_only=[dict(writer=k[0],sequence=k[1],submessage_sha256=k[2],topic=k[3],endpoint=k[4],side=k[5]) for k in sorted(b-a)])
    return dict(topics=topics,cross_capture_advertisement_presence=cross,binding_count=len(bindings),unbound_data_submessages={role:sum(r['kind'] in (0x15,0x16) and r['writer'] not in bindings for r in data['rows']) for role,data in decoded.items()},scope='retrospective decoded capture observations and union GUID directory; missing observations never prove middleware absence, execution outcome or unique kernel loss cause; DATA_FRAG counts are submessages, not reconstructed application callbacks')


def docker(tool,argv,path):
    name='ros2-srt-rtps-analysis-'+secrets.token_hex(5)
    command=['docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none','--cap-drop','ALL','--memory','1g','--name',name,'-w','/workspace','-v',str(ROOT)+':/workspace:ro',tool]+argv
    try:
        with path.open('xb') as output,path.with_suffix(path.suffix+'.stderr').open('x') as error:
            subprocess.run(command,cwd=ROOT,stdout=output,stderr=error,check=True,timeout=180)
    finally:subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return command


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--tool-image',default='ros2-srt-rtps-tools:20261108');a=p.parse_args()
    run=a.run.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    report=dict(status='running',retrospective=True,original_run=str(run.relative_to(ROOT)),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),adapter_sha256=sha(Path(__file__)),commands=[])
    try:
        original=json.loads((run/'run.json').read_text());net=json.loads((run/'network.json').read_text());addresses=net['addresses']
        info=json.loads(subprocess.check_output(['docker','image','inspect',a.tool_image],text=True))[0]
        if info['Architecture']!='amd64' or info['Os']!='linux':raise ValueError('unexpected decoder platform')
        tool=info['Id'];report.update(tool_image_id=tool,original_status=original['status'],addresses=addresses)
        report['commands'].append(docker(tool,['sh','-c','tshark --version; dpkg-query -W tshark libwireshark17t64; sha256sum /usr/bin/tshark /usr/lib/x86_64-linux-gnu/libwireshark.so.17'],out/'decoder.txt'))
        recorded=json.loads((ROOT/'evidence/m3-n5-progress-2026-11-08/local-artifact-hashes.json').read_text());decoded={};report['inputs']={}
        for role in ('operator','robot'):
            paths=sorted(run.glob(role+'.pcap*'))
            if not paths or sum(f.stat().st_size for f in paths)>256<<20:raise ValueError('missing/oversized capture population')
            integrity=summarize(paths,addresses[role],allow_udp_fragments=True)
            integrity.update(validate_tcpdump_footer((run/(role+'-capture.log')).read_text(),integrity['records']))
            if not integrity['tcpdump_population_reconciled'] or integrity['unaccounted']:raise ValueError('capture integrity gate failed')
            if len(paths)!=1:raise ValueError('rotated captures require explicit merge provenance; withheld')
            path=paths[0];key=str(path.relative_to(ROOT));digest=sha(path)
            if digest!=recorded[key]['sha256']:raise ValueError('original capture hash changed')
            report['inputs'][role]=dict(path=key,sha256=digest,integrity=integrity)
            report['commands'].append(docker(tool,['tshark','-n','-2','-o','ip.defragment:TRUE','-r','/workspace/'+key,'-Y','rtps || ip.flags.mf || ip.frag_offset > 0','-T','pdml'],out/(role+'.pdml')))
            decoded[role]=parse(out/(role+'.pdml'))
            if sha(path)!=digest:raise ValueError('original capture changed during analysis')
        report['decoded_summary']={r:{k:v for k,v in d.items() if k!='rows'} for r,d in decoded.items()}
        report['assessment']=assess(decoded,addresses);report['status']='completed'
    except Exception as error:report.update(status='failed',error=str(error));raise
    finally:write(out/'analysis.json',report)


if __name__=='__main__':main()
