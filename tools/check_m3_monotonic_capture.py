#!/usr/bin/env python3
"""Run inside a network-none Linux container with CAP_BPF and CAP_NET_RAW."""
import argparse
import json
from pathlib import Path
import signal
import socket
import struct
import subprocess
import time
from m3_monotonic_capture import records


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--native',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    path=args.out/'packets.bin';ready=args.out/'ready.json';log=(args.out/'capture.log').open('w')
    process=subprocess.Popen([str(args.native.resolve()),'lo',str(path),str(ready)],stdout=log,stderr=subprocess.STDOUT)
    packets=[]
    try:
        deadline=time.monotonic()+5
        while not ready.exists():
            if process.poll() is not None:raise RuntimeError('capture exited before ready')
            if time.monotonic()>deadline:raise RuntimeError('capture readiness timeout')
            time.sleep(.01)
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as receiver,socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
            receiver.bind(('127.0.0.1',0));receiver.settimeout(1)
            for sequence,size in enumerate([24,64,128,1200,1400]*8):
                payload=b'M3MONO01'+struct.pack('!I',sequence)+bytes(size-12)
                before=time.monotonic_ns();sender.sendto(payload,receiver.getsockname());actual,_=receiver.recvfrom(65536);after=time.monotonic_ns()
                assert actual==payload;packets.append(dict(sequence=sequence,payload_bytes=size,before_ns=before,after_ns=after))
        time.sleep(.1)
    finally:
        process.send_signal(signal.SIGINT) if process.poll() is None else None
        code=process.wait(timeout=5);log.close()
    status=json.loads((args.out/'capture.log').read_text().splitlines()[-1]);assert code==0 and status['complete']
    seen={p['sequence']:[] for p in packets}
    for row in records(path):
        frame=row['prefix']
        if len(frame)<54 or frame[12:14]!=b'\x08\x00' or frame[23]!=17:continue
        ihl=(frame[14]&15)*4;payload=frame[14+ihl+8:]
        if not payload.startswith(b'M3MONO01'):continue
        seq=struct.unpack_from('!I',payload,8)[0];seen[seq].append(row)
    for packet in packets:
        rows=seen[packet['sequence']];assert len(rows)==2 and {r['packet_type'] for r in rows}=={0,4}
        assert all(packet['before_ns']<=r['monotonic_ns']<=packet['after_ns'] and r['length']==packet['payload_bytes']+42 for r in rows)
    result=dict(status='passed',packets=len(packets),observations=sum(map(len,seen.values())),all_kernel_timestamps_inside_userspace_send_receive_brackets=True,lengths_checked=True,capture=status,scope='isolated loopback selftest, not eth0/transport or physical-wire qualification')
    (args.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');(args.out/'send-brackets.json').write_text(json.dumps(packets,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
