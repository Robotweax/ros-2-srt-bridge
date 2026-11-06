"""Bounded classic Ethernet/IPv4/UDP pcap accounting for the pinned SRT provider.

FEC parity is SRT DATA-shaped with message_number=0, not an ordinary source DATA
packet (pinned provider src/fec.cpp and src/codec.cpp). Never decrypts payloads.
"""
from collections import defaultdict
import ipaddress
from pathlib import Path
import struct


def classify(payload, source_port, destination_port):
    if payload.startswith(b'RTPS'):return 'dds_rtps'
    channel='control' if 10080 in (source_port,destination_port) else 'sensor' if 10081 in (source_port,destination_port) else None
    if not channel:return 'other_udp'
    if len(payload)<16:return 'short_srt'
    first,message=struct.unpack_from('!II',payload)
    if first&0x80000000:return channel+'_srt_control'
    if not message&0x03ffffff:return channel+'_fec_parity'
    return channel+'_source_data'


def summarize(paths, local_address, *, allow_udp_fragments=False, timestamp_window=None):
    counts=defaultdict(lambda:dict(packets=0,ethernet_bytes=0,udp_payload_bytes=0))
    issues=defaultdict(int);records=0;first=None;last=None
    buckets={key:dict(records=0,classes=defaultdict(lambda:dict(packets=0,ethernet_bytes=0,udp_payload_bytes=0))) for key in ('inside','boundary','outside')}
    if timestamp_window is not None:
        a,b,c,d=timestamp_window
        if not a<=b<c<=d:raise ValueError('invalid timestamp window envelope')
    def class_rows(name):
        rows=[counts[name]]
        if timestamp_window is not None:rows.append(buckets[bucket]['classes'][name])
        return rows
    for path in paths:
        with Path(path).open('rb') as file:
            header=file.read(24)
            if len(header)!=24:raise ValueError('truncated pcap header')
            formats={b'\xd4\xc3\xb2\xa1':('<',1000),b'\xa1\xb2\xc3\xd4':('>',1000),
                     b'\x4d\x3c\xb2\xa1':('<',1),b'\xa1\xb2\x3c\x4d':('>',1)}
            if header[:4] not in formats:raise ValueError('unsupported pcap magic')
            endian,multiplier=formats[header[:4]]
            if struct.unpack_from(endian+'I',header,20)[0]!=1:raise ValueError('expected Ethernet pcap')
            while True:
                record=file.read(16)
                if not record:break
                if len(record)!=16:raise ValueError('truncated pcap record')
                seconds,fraction,included,original=struct.unpack(endian+'IIII',record)
                if included>262144:raise ValueError('oversized capture record')
                frame=file.read(included)
                if len(frame)!=included:raise ValueError('truncated capture frame')
                records+=1;stamp=seconds*1000000000+fraction*multiplier
                if timestamp_window is not None:
                    a,b,c,d=timestamp_window
                    bucket='inside' if stamp-multiplier>=b and stamp+multiplier<c else 'outside' if stamp+multiplier<a or stamp-multiplier>=d else 'boundary'
                    buckets[bucket]['records']+=1
                first=stamp if first is None else min(first,stamp);last=stamp if last is None else max(last,stamp)
                if included<original:issues['snaplen_truncated']+=1;continue
                if len(frame)<34 or frame[12:14]!=b'\x08\x00':issues['non_ipv4_or_short']+=1;continue
                ip=frame[14:];length=(ip[0]&15)*4
                if ip[0]>>4!=4 or length<20 or len(ip)<length:issues['invalid_ip_header']+=1;continue
                if ip[9]!=17:issues['non_udp']+=1;continue
                source=str(ipaddress.ip_address(ip[12:16]));destination=str(ipaddress.ip_address(ip[16:20]))
                direction='out' if source==local_address else 'in' if destination==local_address else 'other'
                fragment=struct.unpack_from('!H',ip,6)[0]
                if fragment&0x3fff:
                    if not allow_udp_fragments:issues['fragmented']+=1;continue
                    # DDS discovery may produce IP fragments. Count every
                    # captured frame, without pretending continuation fragments
                    # expose UDP headers or RTPS payload classification.
                    total=struct.unpack_from('!H',ip,2)[0]
                    payload_length=total-length
                    if payload_length<=0 or total>len(ip) or (fragment&0x2000 and payload_length%8) or (not fragment&0x1fff and payload_length<8):issues['invalid_fragment_length']+=1;continue
                    if not fragment&0x1fff:
                        sp,dp=struct.unpack_from('!HH',ip,length)
                        if 10080 in (sp,dp) or 10081 in (sp,dp):issues['fragmented_srt']+=1
                    for row in class_rows(direction+'/ipv4_udp_fragment'):
                        row['packets']+=1;row['ethernet_bytes']+=original
                        row['udp_payload_bytes']=None
                        row['ip_fragment_payload_bytes']=row.get('ip_fragment_payload_bytes',0)+total-length
                    continue
                if len(ip)<length+8:issues['invalid_udp_length']+=1;continue
                udp=ip[length:];sp,dp,udp_length=struct.unpack_from('!HHH',udp)
                if udp_length<8 or udp_length>len(udp):issues['invalid_udp_length']+=1;continue
                payload=udp[8:udp_length];kind=classify(payload,sp,dp)
                for row in class_rows(direction+'/'+kind):
                    row['packets']+=1;row['ethernet_bytes']+=original;row['udp_payload_bytes']+=len(payload)
    fec={}
    for direction in ('in','out'):
        source=counts.get(direction+'/sensor_source_data',{}).get('ethernet_bytes',0)
        parity=counts.get(direction+'/sensor_fec_parity',{}).get('ethernet_bytes',0)
        fec[direction]=dict(parity_to_source_frame_bytes=parity/source if source else None,
                           source_frame_bytes=source,parity_frame_bytes=parity)
    result=dict(records=records,first_timestamp_ns=first,last_timestamp_ns=last,
        classes=dict(counts),unaccounted=dict(issues),fec=fec,
        byte_scope='captured Ethernet-shaped skb lengths; excludes preamble/FCS/physical-link overhead; qdisc/offload interpretation requires explicit environment qualification')

    if timestamp_window is not None:
        result['time_window']=dict(accounting_complete=not bool(issues),timestamp_bounds_ns=list(timestamp_window),buckets={key:dict(records=value['records'],classes=dict(value['classes'])) for key,value in buckets.items()},
            scope='certain inside + boundary gives conditional upper frame-byte bound; all UDP traffic, not source-population attribution; timestamp quantization included')
    return result


def validate_tcpdump_footer(footer,records,*,require_nonempty=True):
    """Validate written-record integrity; retain ambiguous filter population counts."""
    import re
    def counter(pattern):
        matches=re.findall(pattern,footer)
        if not matches:raise ValueError('missing tcpdump counter')
        return int(matches[-1])
    captured=counter(r'(\d+) packets? captured')
    filtered=counter(r'(\d+) packets? received by filter')
    dropped=counter(r'(\d+) packets? dropped by kernel')
    if dropped or captured!=records or (require_nonempty and not records):raise ValueError('unreconciled tcpdump counters: captured/filter/file counts differ or drops present')
    return dict(tcpdump_reported_packets=captured,tcpdump_reported_filtered_packets=filtered,tcpdump_kernel_drops=dropped,tcpdump_file_integrity_valid=True,tcpdump_population_reconciled=filtered==captured)


def stop_captures(lab):
    """Stop the owned UDP load first, allow buffered dispatch, then close taps."""
    import time
    def stop(role,label,names):
        code='import pathlib,os,signal\nfor p in pathlib.Path("/proc").glob("[0-9]*/comm"):\n try:\n  if p.read_text().strip() in '+repr(tuple(names))+':os.kill(int(p.parent.name),signal.SIGINT)\n except (FileNotFoundError,ProcessLookupError):pass\n'
        lab.inside(role,label,['python3','-c',code])
    errors=[]
    if 'robot' in lab.containers:
        try:stop('robot','competitor-stop',('iperf3',))
        except Exception as error:errors.append(str(error))
    time.sleep(1.25) # Allow in-flight traffic to settle; immediate dispatch counters still fail closed.
    for role in lab.containers:
        try:stop(role,role+'-capture-stop',('tcpdump','m3_mono_cap'))
        except Exception as error:errors.append(str(error))
    if errors:raise RuntimeError('; '.join(errors))
