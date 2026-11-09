#!/usr/bin/env python3
"""Bounded synthetic stimuli, exclusively inside a caller-owned M3 namespace."""
import argparse,hashlib,json,socket,struct,time
from pathlib import Path


def save(path,row):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(row,indent=2)+'\n');temp.replace(path)


def request_frame(source,target,source_mac,target_mac):
    sm=bytes.fromhex(source_mac.replace(':',''));tm=bytes.fromhex(target_mac.replace(':',''))
    if len(sm)!=6 or len(tm)!=6 or sm==tm or sm[0]&1 or tm[0]&1 or source==target:raise ValueError('owned unicast endpoints required')
    return tm+sm+bytes.fromhex('08060001080006040001')+sm+socket.inet_aton(source)+bytes(6)+socket.inet_aton(target)


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=('requests','flood','receive'),required=True);p.add_argument('--source',required=True);p.add_argument('--target',required=True);p.add_argument('--source-mac');p.add_argument('--target-mac');p.add_argument('--count',type=int,choices=(5,20));p.add_argument('--out',type=Path,required=True);p.add_argument('--ready',type=Path);p.add_argument('--stop',type=Path);a=p.parse_args()
    if a.out.exists() or (a.ready and a.ready.exists()):raise ValueError('output exists')
    before=time.monotonic_ns();row=dict(mode=a.mode,before_ns=before,rows=[])
    if a.mode=='requests':
        frame=request_frame(a.source,a.target,a.source_mac,a.target_mac)
        if not a.count:raise ValueError('count required')
        if Path('/sys/class/net/eth0/address').read_text().strip()!=a.source_mac:raise ValueError('owned source MAC mismatch')
        with socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(0x0806)) as s:
            s.bind(('eth0',0))
            for i in range(a.count):
                start=time.monotonic_ns();n=s.send(frame);end=time.monotonic_ns()
                if n!=len(frame):raise ValueError('short ARP request send')
                row['rows'].append(dict(sequence=i,before_ns=start,after_ns=end,bytes=n));time.sleep(.1)
        row['frame_sha256']=hashlib.sha256(frame).hexdigest()
    elif a.mode=='flood':
        if a.ready is None:raise ValueError('ready required')
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            s.bind((a.source,39783));s.connect((a.target,39782));s.setblocking(False);start=time.monotonic_ns();save(a.ready,dict(ready_ns=start));sent=0;blocked=0
            for i in range(15000):
                if time.monotonic_ns()-start>=3000000000:break
                payload=b'ARPTRACE'+struct.pack('!I',i)+bytes(1188)
                try:
                    if s.send(payload)!=1200:raise ValueError('short UDP send')
                    sent+=1
                except BlockingIOError:blocked+=1
                target=start+(i+1)*200000
                delay=(target-time.monotonic_ns())/1e9
                if delay>0:time.sleep(delay)
            row.update(sent=sent,blocked=blocked,offered_spacing_ns=200000,max_packets=15000,payload_bytes=1200)
    else:
        if a.ready is None or a.stop is None:raise ValueError('receive markers required')
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
            s.bind((a.source,39782));s.settimeout(.1);save(a.ready,dict(ready_ns=time.monotonic_ns()));received=0
            while time.monotonic_ns()-before<20000000000 and not a.stop.exists():
                try:payload,addr=s.recvfrom(1500)
                except socket.timeout:continue
                if addr!=(a.target,39783) or len(payload)!=1200 or payload[:8]!=b'ARPTRACE':raise ValueError('unexpected fixture UDP')
                received+=1
                if received>15000:raise ValueError('receiver bound')
            if not a.stop.exists():raise ValueError('receiver deadline')
            row['received']=received
    row.update(after_ns=time.monotonic_ns(),complete=True);save(a.out,row)


if __name__=='__main__':main()
