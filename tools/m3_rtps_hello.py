#!/usr/bin/env python3
"""Offline ROS generated-type validation of unbound DATA; never creates a node."""
import argparse
import hashlib
import json
import re
from rosidl_runtime_py.utilities import get_message
from pathlib import Path
import xml.etree.ElementTree as ET
from rclpy.serialization import deserialize_message,serialize_message
from robotweax_srt_bridge_msgs.msg import DdsCommandFrame
from m3_rtps_discovery import field,hex_value,MAX_BYTES,MAX_RECORDS


def semantic_mask(cls):
    # Derive alignment from generated field declarations; deserialize values
    # with ROS, never a guessed fixed-offset HELLO layout. This fixture is CDR1
    # with fixed primitive/array/nested-message fields only.
    mask=[True]*4
    sizes={'uint8':1,'boolean':1,'bool':1,'uint16':2,'uint32':4,'uint64':8}
    def walk(message_type):
        for name,type in message_type.get_fields_and_field_types().items():
            match=re.fullmatch(r'(uint8|uint16|uint32|uint64|boolean|bool)(?:\[(\d+)\])?',type)
            if match:
                size=sizes[match[1]];count=int(match[2] or 1)
                mask.extend([False]*((-(len(mask)-4))%size));mask.extend([True]*(size*count))
            elif '/' in type:walk(get_message(type))
            else:raise ValueError('unsupported CDR schema '+type)
    walk(cls)
    return mask


MASK=semantic_mask(DdsCommandFrame)


def decode(cdr,owner):
    expected=len(MASK)
    if len(cdr) not in (expected,(expected+3)//4*4) or cdr[:4]!=b'\x00\x01\x00\x00' or any(cdr[expected:]):return None
    try:message=deserialize_message(cdr[:expected],DdsCommandFrame)
    except Exception:return None
    encoded=serialize_message(message)
    if len(encoded)!=expected or any(a!=b for a,b,semantic in zip(cdr,encoded,MASK) if semantic):return None
    if bytes(message.process_epoch).hex()!=owner or message.kind!=DdsCommandFrame.HELLO or message.protocol_version!=DdsCommandFrame.PROTOCOL_VERSION:return None
    return dict(process_epoch=owner,kind=message.kind,protocol_version=message.protocol_version,app_sequence=message.sequence,sent_monotonic_ns=message.sent_monotonic_ns,owner_ready=message.owner_ready,cdr_sha256=hashlib.sha256(cdr).hexdigest())


def inspect(path,prefix,source,owner):
    if path.stat().st_size>MAX_BYTES:raise ValueError('PDML byte budget exceeded')
    rows=[];candidates=0;packets=0
    with path.open('rb') as stream:
        events=ET.iterparse(stream,events=('start','end'));_,root=next(events)
        if root.tag!='pdml' or root.get('creator')!='wireshark/4.2.2':raise ValueError('unexpected decoder')
        for event,packet in events:
            if event!='end' or packet.tag!='packet':continue
            packets+=1
            if packets>MAX_RECORDS:raise ValueError('packet budget exceeded')
            if field(packet,'ip.src')==source:
                for proto in packet.findall("proto[@name='rtps']"):
                    if field(proto,'rtps.guidPrefix.src','value')!=prefix:continue
                    if any(sm.get('show')=='0x0c' for sm in proto.findall("field[@name='rtps.sm.id']")):raise ValueError('INFO_SRC unsupported')
                    for sm in proto.findall("field[@name='rtps.sm.id'][@show='0x15']"):
                        writer=int(field(sm,'rtps.sm.wrEntityId',required=True),0).to_bytes(4,'big').hex()
                        if writer[-2:] not in ('02','03'):continue
                        raw=bytes.fromhex(sm.get('value',''))
                        encaps=[f for f in sm.iter('field') if f.get('name')=='rtps.param.serialize.encap_kind']
                        if len(raw)<24 or raw[1]&14!=4 or len(encaps)!=1:continue
                        offset=int(encaps[0].get('pos'))-int(sm.get('pos'))
                        if not 24<=offset<len(raw)-3:raise ValueError('invalid encapsulation offset')
                        candidates+=1;proof=decode(raw[offset:],owner)
                        if proof:rows.append(dict(proof,frame=int(field(packet,'frame.number',required=True)),writer=prefix+writer,rtps_sequence=int(field(sm,'rtps.sm.seqNumber',required=True))))
            packet.clear();root.clear()
    return dict(candidates=candidates,validated_hellos=len(rows),rows=rows,scope='offline generated DdsCommandFrame deserialization plus reflected CDR alignment plus semantic reserialization, protocol/kind and original process UUID match; not authenticated wire or live subscription callback evidence')


def self_test():
    frame=DdsCommandFrame();frame.kind=frame.HELLO;frame.protocol_version=frame.PROTOCOL_VERSION;frame.process_epoch=list(bytes.fromhex('01'*16));frame.sequence=1
    cdr=serialize_message(frame)
    assert decode(cdr,'01'*16) is not None
    assert decode(cdr,'02'*16) is None
    assert decode(cdr+b'\x01','01'*16) is None
    altered=bytearray(cdr)
    for i,semantic in enumerate(MASK):
        if not semantic:altered[i]=0xa5
    assert decode(bytes(altered),'01'*16) is not None
    assert decode(cdr+bytes((-len(cdr))%4),'01'*16) is not None
    frame.kind=frame.COMMAND
    assert decode(serialize_message(frame),'01'*16) is None
    return dict(status='passed',checks=['generated-type HELLO semantic roundtrip','wrong owner rejected','nonzero trailing byte rejected','reflected alignment padding accepted','zero RTPS end padding accepted','non-HELLO rejected'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--pdml',type=Path);p.add_argument('--prefix');p.add_argument('--source');p.add_argument('--owner');p.add_argument('--self-test',action='store_true');a=p.parse_args()
    print(json.dumps(self_test() if a.self_test else inspect(a.pdml,a.prefix,a.source,a.owner),indent=2))


if __name__=='__main__':main()
