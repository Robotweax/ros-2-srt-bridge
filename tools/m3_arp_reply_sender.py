#!/usr/bin/env python3
"""Send each labeled synthetic identity once, atomically publish completed brackets."""
import argparse
from pathlib import Path
from m3_tap_probe import send


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--peer',required=True);p.add_argument('--case',type=int,required=True);p.add_argument('--count',type=int,choices=(1,3),required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    target=a.out
    if target.exists():p.error('source result exists')
    a.out=target.with_suffix('.tmp');a.bind_port=10080;a.gso=False;send(a);a.out.replace(target)
