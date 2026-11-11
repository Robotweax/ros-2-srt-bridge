#!/usr/bin/env python3
"""Bounded synthetic UDP receiver; snapshots are not durable command authority."""
import argparse,hashlib,json,socket,struct,time
from pathlib import Path
from m3_tap_probe import MAGIC,PORT


def receive(args):
    rows=[];result=dict(complete=False,rows=rows,limit=8);deadline=time.monotonic()+20
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as server:
            server.bind(('0.0.0.0',PORT));server.settimeout(.025);args.ready.write_text(json.dumps(dict(ready_ns=time.monotonic_ns()))+'\n')
            while not args.stop.exists():
                if time.monotonic()>deadline:raise ValueError('synthetic receiver timeout')
                try:payload,peer=server.recvfrom(65536)
                except socket.timeout:continue
                if len(rows)>=8 or len(payload)!=1200 or not payload.startswith(MAGIC):raise ValueError('unexpected/budget-exhausted synthetic payload')
                case,sequence=struct.unpack_from('!II',payload,8);rows.append(dict(case=case,sequence=sequence,monotonic_ns=time.monotonic_ns(),bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest(),peer=list(peer)))
                temporary=args.progress.with_suffix('.tmp');temporary.write_text(json.dumps(dict(rows=rows))+'\n');temporary.replace(args.progress)
            result['complete']=True
    except Exception as e:result['error']=str(e)
    finally:
        result['finished_ns']=time.monotonic_ns()
        with args.out.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    return result['complete']


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('out','ready','stop','progress'):p.add_argument('--'+key,type=Path,required=True)
    raise SystemExit(not receive(p.parse_args()))
