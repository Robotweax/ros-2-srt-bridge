"""Posthoc capture-order retirement observations; never provider acceptance authority."""
from collections import Counter
import hashlib,json,struct
from pathlib import Path
from m3_telemetry_diagnosis import udp_records,sha


class RetirementOrder:
    def __init__(self):self.groups={}
    def observe(self,flow,payload):
        if len(payload)<16:raise ValueError('short SRT header')
        word0,word1,_,socket=struct.unpack_from('!IIII',payload);key=tuple(flow)+(socket,)
        g=self.groups.setdefault(key,dict(data_packets=0,retirement_controls=0,repeated_retirement_controls=0,unsupported_controls=0,retired=set(),data=set(),after_retirement=set(),late_packets=0,boundaries=Counter(),keys=Counter()))
        if word0&0x80000000:
            if (word0>>16)&0x7fff!=7:return
            # Pinned SENSOR accepts only sequence-only singleton retirements.
            if len(payload)!=24 or word1&0x03ffffff:
                g['unsupported_controls']+=1;return
            first,last=struct.unpack_from('!II',payload,16)
            if first!=last or first&0x80000000:
                g['unsupported_controls']+=1;return
            g['retirement_controls']+=1;g['repeated_retirement_controls']+=first in g['retired'];g['retired'].add(first)
        elif word1&0x03ffffff:
            seq=word0&0x7fffffff;g['data_packets']+=1;g['data'].add(seq);g['boundaries'][(word1>>30)&3]+=1;g['keys'][(word1>>27)&3]+=1
            if seq in g['retired']:g['late_packets']+=1;g['after_retirement'].add(seq)
    def summary(self):
        return [dict(flow=list(key),data_packets=g['data_packets'],unique_data_sequences=len(g['data']),retirement_controls=g['retirement_controls'],unique_retired_sequences=len(g['retired']),repeated_retirement_controls=g['repeated_retirement_controls'],unsupported_controls=g['unsupported_controls'],data_packets_after_prior_same_sequence_retirement=g['late_packets'],unique_data_sequences_after_prior_retirement=len(g['after_retirement']),data_sequences_eventually_named_by_retirement=len(g['data']&g['retired']),boundaries=dict(g['boundaries']),encryption_key_flags=dict(g['keys'])) for key,g in self.groups.items() if g['data_packets'] or g['retirement_controls'] or g['unsupported_controls']]


def analyze(root,telemetry):
    d=telemetry['analysis'];run=root/d['run'];network=json.loads((run/'network.json').read_text());robot=network['addresses']['robot'];operator=network['addresses']['operator']
    paths=sorted(root/p for p in d['raw_capture_hashes'] if Path(p).name.startswith('operator.pcap'))
    if not paths:raise ValueError('missing operator tap rotations')
    for p in paths:
        if sha(p)!=d['raw_capture_hashes'][str(p.relative_to(root))]['sha256']:raise ValueError('original tap hash changed')
    view=RetirementOrder()
    for src,dst,sp,dp,payload in udp_records(paths):
        if src==robot and dst==operator and 10081 in (sp,dp):view.observe((src,dst,sp,dp),payload)
    for p in paths:
        if sha(p)!=d['raw_capture_hashes'][str(p.relative_to(root))]['sha256']:raise ValueError('tap changed during order analysis')
    return dict(run=d['run'],scope='whole operator capture FILE order, same UDP flow/destination socket and exact sequence; not realtime/socket processing order, authenticated acceptance, typed SAMPLE mapping or unique internal cause',flows=view.summary(),limitations=['A cleartext DROP_REQUEST can be rejected or remain pending until the peer send horizon permits it.','Prior capture control is not proof the provider applied retirement before an application read.','Later DATA with a previously retired sequence is consistent with late/discarded data; no decryption/provider-internal observation here.'])
