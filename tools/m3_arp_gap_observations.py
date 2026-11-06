#!/usr/bin/env python3
"""Exploratory ARP associations in previously selected CONTROL gaps; not cause proof."""
import argparse,json,socket
from pathlib import Path
from m3_monotonic_capture import records
from m3_control_liveness import digest


def parse_arp(row):
    frame=row['prefix']
    if len(frame)<14:raise ValueError('short Ethernet prefix')
    if frame[12:14]!=b'\x08\x06':return None
    if len(frame)<42 or row['length']<42 or frame[14:20]!=b'\x00\x01\x08\x00\x06\x04':raise ValueError('unsupported ARP header shape')
    if row['artifact_version']!=2 or row['vlan_present'] or row['gso_size'] or row['gso_segs'] not in (0,1):raise ValueError('unqualified ARP representation')
    return dict(monotonic_ns=row['monotonic_ns'],packet_type=row['packet_type'],outgoing=row['packet_type']==4,
                operation=int.from_bytes(frame[20:22],'big'),sender_ipv4=socket.inet_ntoa(frame[28:32]),target_ipv4=socket.inet_ntoa(frame[38:42]))


def analyze(run,analysis):
    checks=[dict(sender=g['sender_role'],window_ns=g['window_ns'],roles={'operator':[],'robot':[]}) for g in analysis['gaps']]
    for role in ('operator','robot'):
        path=run/(role+'.mono');sha=digest(path)
        if sha!=analysis['native_sha256'][role]:raise ValueError('capture differs from primary qualified analysis')
        for row in records(path):
            t=row['monotonic_ns']
            if not any(c['window_ns'][0]<t<=c['window_ns'][1] for c in checks):continue
            value=parse_arp(row)
            if value:
                for c in checks:
                    if c['window_ns'][0]<t<=c['window_ns'][1]:c['roles'][role].append(dict(value,offset_from_start_ns=t-c['window_ns'][0],time_to_gap_end_ns=c['window_ns'][1]-t))
        if digest(path)!=sha:raise ValueError('capture changed during read')
    return dict(gaps=checks,native_sha256=analysis['native_sha256'],extractor_sha256=digest(Path(__file__)),
                scope='exploratory post-closure ARP decoding in all previously selected gaps, including trailing packet time; non-outgoing duplicates retained, not extra peer probes/replies; neighbor-table state/kernel pre-qdisc/drop stages were not sampled; association is not cause attribution')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--analysis',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();args.out.write_text(json.dumps(analyze(args.run,json.loads(args.analysis.read_text())),indent=2)+'\n')
