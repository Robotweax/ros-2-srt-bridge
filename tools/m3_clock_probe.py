#!/usr/bin/env python3
"""Read-only Linux clock diagnosis, not a transport/clock qualification waiver.

Run inside the pinned lab image with a separately compiled clock_probe binary.
No network or capabilities are needed. Exit 2 means the observed clock model
failed; exit 0 means only that this finite diagnostic found no violation.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

CHANNELS=('python_realtime','libc_realtime','syscall_realtime','syscall_raw','syscall_boottime')


def analyze(rows):
    report={}
    for channel in CHANNELS:
        violations=[];previous=None;max_width=0
        for index,row in enumerate(rows):
            s=row[channel];begin,value,end=(s[k] for k in ('begin_ns','value_ns','end_ns'))
            width=end-begin;max_width=max(max_width,width)
            if not 0<=width<=1000000:violations.append(dict(index=index,reason='invalid/wide read bracket',width_ns=width))
            interval=(value-end,value-begin)
            if previous is not None:
                prior,prior_begin=previous;elapsed=end-prior_begin
                distance=max(0,prior[0]-interval[1],interval[0]-prior[1])
                if begin<=prior_begin or not 0<elapsed<=1000000000:
                    violations.append(dict(index=index,reason='invalid/over-one-second sample gap',elapsed_ns=elapsed))
                elif distance>(elapsed+999)//1000:
                    violations.append(dict(index=index,reason='offset change exceeds 1000ppm',minimum_change_ns=distance,elapsed_ns=elapsed,begin_ns=begin))
            previous=interval,begin
        report[channel]=dict(observed_model_passed=bool(len(rows)>=4 and not violations),samples=len(rows),maximum_read_width_ns=max_width,violations=violations)
    return dict(channels=report,realtime_model_passed=all(report[c]['observed_model_passed'] for c in CHANNELS[:3]),
        scope='finite read-only diagnostic; no hidden-step guarantee, no automatic clock correction or qualification of later workload; raw/boottime are diagnostics only')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native',required=True,type=Path)
    parser.add_argument('--seconds',type=int,default=95)
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args()
    if not 1<=args.seconds<=600:parser.error('seconds must be 1..600')
    args.out.mkdir(parents=True,exist_ok=False)
    rows=[]
    with (args.out/'samples.jsonl').open('w') as log:
        child=subprocess.Popen([str(args.native.resolve()),str(args.seconds)],stdout=subprocess.PIPE,text=True)
        try:
            for line in child.stdout:
                begin=time.monotonic_ns();wall=time.time_ns();end=time.monotonic_ns()
                row=json.loads(line);row['python_realtime']=dict(begin_ns=begin,value_ns=wall,end_ns=end)
                rows.append(row);log.write(json.dumps(row)+'\n');log.flush()
            if child.wait()!=0:raise RuntimeError('native probe failed')
        finally:
            if child.poll() is None:child.terminate();child.wait(timeout=5)
    report=analyze(rows)
    report['requested_seconds']=args.seconds
    report['clock_implementations']={name:vars(time.get_clock_info(name)) for name in ('time','monotonic')}
    (args.out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return 0 if report['realtime_model_passed'] else 2


if __name__=='__main__':raise SystemExit(main())
