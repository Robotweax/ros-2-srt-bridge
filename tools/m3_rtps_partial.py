"""Header-only inspection of incomplete first IPv4 fragments; never a binding."""
import xml.etree.ElementTree as ET
from m3_rtps_discovery import field,hex_value,MAX_BYTES,MAX_RECORDS


def inspect(path):
    if path.stat().st_size>MAX_BYTES:raise ValueError('PDML budget exceeded')
    rows=[];packets=0
    with path.open('rb') as stream:
        events=ET.iterparse(stream,events=('start','end'));_,root=next(events)
        if root.tag!='pdml' or root.get('creator')!='wireshark/4.2.2':raise ValueError('unexpected decoder')
        for event,p in events:
            if event!='end' or p.tag!='packet':continue
            packets+=1
            if packets>MAX_RECORDS:raise ValueError('packet budget exceeded')
            if field(p,'ip.frag_offset')!='0' or field(p,'ip.flags.mf') not in ('True','1'):raise ValueError('not an incomplete first-fragment selection')
            for proto in p.findall("proto[@name='rtps']"):
                prefix=hex_value(field(proto,'rtps.guidPrefix.src','value',required=True),12)
                if any(sm.get('show')=='0x0c' for sm in proto.findall("field[@name='rtps.sm.id']")):raise ValueError('INFO_SRC unsupported')
                for sm in proto.findall("field[@name='rtps.sm.id'][@show='0x15']"):
                    writer=int(field(sm,'rtps.sm.wrEntityId',required=True),0).to_bytes(4,'big').hex()
                    rows.append(dict(frame=int(field(p,'frame.number',required=True)),source=field(p,'ip.src',required=True),destination=field(p,'ip.dst',required=True),ip_id=field(p,'ip.id'),writer=prefix+writer,sequence=int(field(sm,'rtps.sm.seqNumber',required=True)),partial_topic=field(sm,'rtps.param.topicName'),complete_advertisement=False))
            p.clear();root.clear()
    return dict(packets=packets,rows=rows,scope='header-only decode with IPv4 defragmentation disabled for known non-reassembled first fragments; partial topic text is never a complete advertisement or GUID binding; malformed truncated bodies expected')
