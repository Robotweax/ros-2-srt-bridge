"""Kernel-monotonic AF_PACKET prefix accounting, independent of realtime clocks."""
from collections import defaultdict
import ipaddress
from pathlib import Path
import struct
from m3_capture import classify

HEADER=struct.Struct('<IIII')
RECORD=struct.Struct('<QIIII128s')


def records(path):
    with Path(path).open('rb') as file:
        if file.read(HEADER.size)!=HEADER.pack(0x314d5253,1,RECORD.size,1):raise ValueError('invalid monotonic capture header')
        while True:
            data=file.read(RECORD.size)
            if not data:break
            if len(data)!=RECORD.size:raise ValueError('truncated monotonic record')
            ns,length,captured,kind,index,prefix=RECORD.unpack(data)
            if not ns or not index or kind not in range(5) or captured!=min(length,128) or any(prefix[captured:]):raise ValueError('invalid monotonic record fields')
            yield dict(monotonic_ns=ns,length=length,prefix=prefix[:captured],packet_type=kind,ifindex=index)


def decode(row,local_address,allow_udp_fragments=False):
    frame=row['prefix'];original=row['length']
    if len(frame)<14:raise ValueError('short Ethernet prefix')
    if frame[12:14]==b'\x86\xdd':
        if len(frame)<54 or frame[14]>>4!=6 or 54+struct.unpack_from('!H',frame,18)[0]>original:raise ValueError('invalid IPv6 header')
        protocol=frame[20];offset=54;end=54+struct.unpack_from('!H',frame,18)[0]
        for _ in range(8):
            if protocol in (6,58,59):return None # Known non-UDP terminal protocol.
            if protocol not in (0,43,60) or offset+2>min(len(frame),end):break
            size=(frame[offset+1]+1)*8
            if offset+size>min(len(frame),end):break
            protocol=frame[offset];offset+=size
        raise ValueError('IPv6 UDP/unsupported extension chain outside qualified parser')
    if frame[12:14]!=b'\x08\x00':return None
    if len(frame)<34:raise ValueError('short IPv4 prefix')
    ip=frame[14:];ihl=(ip[0]&15)*4
    if ip[0]>>4!=4 or ihl<20 or len(ip)<ihl:raise ValueError('invalid IPv4 header')
    total=struct.unpack_from('!H',ip,2)[0]
    if not ihl<=total<=original-14:raise ValueError('invalid IPv4 total length')
    if ip[9]!=17:return None
    source=str(ipaddress.ip_address(ip[12:16]));destination=str(ipaddress.ip_address(ip[16:20]))
    direction='out' if source==local_address else 'in' if destination==local_address else 'other'
    if (row['packet_type']==4)!=(direction=='out'):raise ValueError('packet direction disagrees with local address')
    fragment=struct.unpack_from('!H',ip,6)[0]
    if fragment&0x3fff:
        if not allow_udp_fragments:raise ValueError('fragmented UDP outside SRT capture scope')
        payload=total-ihl
        if payload<=0 or (fragment&0x2000 and payload%8) or (not fragment&0x1fff and payload<8):raise ValueError('invalid IPv4 fragment')
        if not fragment&0x1fff:
            sp,dp=struct.unpack_from('!HH',ip,ihl)
            if 10080 in (sp,dp) or 10081 in (sp,dp):raise ValueError('fragmented SRT')
        return direction+'/ipv4_udp_fragment',None
    if len(ip)<ihl+8 or total<ihl+8:raise ValueError('missing UDP header')
    sp,dp,length=struct.unpack_from('!HHH',ip,ihl)
    if not 8<=length<=total-ihl:raise ValueError('invalid UDP length')
    payload=ip[ihl+8:ihl+min(length,24)]
    # 128 prefix bytes cover max IPv4 header + UDP header + 16 SRT bytes.
    if len(payload)<min(16,length-8):raise ValueError('insufficient protocol prefix')
    return direction+'/'+classify(payload,sp,dp),length-8


def summarize(path,status,local_address,window,*,allow_udp_fragments=False):
    start,end=window
    if end<=start:raise ValueError('invalid monotonic window')
    if status.get('clock')!='kernel_monotonic' or status.get('complete') is not True or status.get('time_namespace_zero') is not True:raise ValueError('capture did not complete')
    if not status['ready_ns']<=start<end<=status['stop_before_ns']:raise ValueError('capture does not cover window')
    rows=list(records(path))
    if not rows or len(rows)!=status['records'] or status['seen']!=status['submitted'] or status['submitted']!=len(rows) or status['reserve_failed'] or status['copy_failed']:raise ValueError('incomplete monotonic capture counters')
    indexes={r['ifindex'] for r in rows}
    if indexes!={status['ifindex']}:raise ValueError('capture interface changed')
    counts=defaultdict(lambda:dict(packets=0,ethernet_bytes=0,udp_payload_bytes=0));inside=0;ignored=0
    for row in rows:
        decoded=decode(row,local_address,allow_udp_fragments)
        if not start<=row['monotonic_ns']<end:continue
        inside+=1
        if decoded is None:ignored+=1;continue
        key,payload=decoded;c=counts[key];c['packets']+=1;c['ethernet_bytes']+=row['length']
        if payload is None:c['udp_payload_bytes']=None
        elif c['udp_payload_bytes'] is not None:c['udp_payload_bytes']+=payload
    return dict(qualified=True,clock='kernel_monotonic',window_monotonic_ns=[start,end],total_records=len(rows),inside_records=inside,ignored_non_udp_records=ignored,classes=dict(counts),
        scope='AF_PACKET observation timestamps and skb frame lengths; 128-byte validated header prefixes; not physical wire overhead/delivery or source-population attribution; capture process excluded from endpoint CPU; kernel observer work may be charged to endpoint tasks; observer changes host load')


def prepare(root,run,image,execute,skip_build):
    import hashlib
    if not skip_build:
        execute('monotonic-capture-build',['docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none',
            '-v',str(root)+':/workspace','-w','/workspace',image,'bash','-c',
            'mkdir -p build/m3-monotonic-capture && g++ -std=c++20 -O2 -Wall -Wextra -Wpedantic -Werror tools/monotonic_capture/main.cpp -lbpf -o build/m3-monotonic-capture/monotonic_capture'])
    binary=Path(root)/'build/m3-monotonic-capture/monotonic_capture'
    if not binary.is_file():raise ValueError('monotonic capture binary missing; run without --skip-build')
    return dict(enabled=True,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),source_sha256=hashlib.sha256((Path(root)/'tools/monotonic_capture/main.cpp').read_bytes()).hexdigest(),extra_capability='BPF on owned endpoints only',scope='experimental passive AF_PACKET observation; zero time-namespace offsets required; not physical wire delivery')


def start(run,inside,lab,captures):
    import subprocess
    import time
    running=[]
    for role,name in lab.containers.items():
        log=(Path(run)/(role+'-monotonic-capture.log')).open('w')
        p=subprocess.Popen(['docker','exec',name,'build/m3-monotonic-capture/monotonic_capture','eth0',inside+'/'+role+'.mono',inside+'/'+role+'-monotonic-ready.json'],stdout=log,stderr=subprocess.STDOUT)
        captures.append((p,log));running.append((role,p))
    deadline=time.monotonic()+10
    while not all((Path(run)/(role+'-monotonic-ready.json')).exists() for role,_ in running):
        if any(p.poll() is not None for _,p in running):raise RuntimeError('monotonic capture exited before ready')
        if time.monotonic()>deadline:raise RuntimeError('monotonic capture readiness timeout')
        time.sleep(.01)


def summarize_run(run,addresses,measurements,*,allow_udp_fragments):
    import json
    run=Path(run)
    statuses={role:json.loads((run/(role+'-monotonic-capture.log')).read_text().splitlines()[-1]) for role in addresses}
    windows={name:{role:summarize(run/(role+'.mono'),statuses[role],address,window['monotonic_ns'],allow_udp_fragments=allow_udp_fragments) for role,address in addresses.items()} for name,window in measurements['windows'].items()}
    if not windows:raise ValueError('no workload windows for monotonic capture')
    return dict(statuses=statuses,windows=windows)
