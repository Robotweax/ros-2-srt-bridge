#!/usr/bin/env python3
"""Opt-in bounded Linux tcpdump observations, never a capture acceptance waiver.

Counters are non-atomic /proc reads bracketed by kernel monotonic time. Samples
can suggest follow-up experiments; neither wchan nor scheduler/I/O deltas alone
identify the cause of packet loss. No payloads, argv or environment are read.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

INTERVAL_SECONDS = .1
MAX_SAMPLES = 75000
IO_KEYS = ('rchar', 'wchar', 'syscr', 'syscw', 'read_bytes', 'write_bytes', 'cancelled_write_bytes')


def read_process(path):
    stat = (path/'stat').read_text()
    fields = stat[stat.rindex(')')+2:].split()  # comm can contain spaces/parentheses
    row = dict(pid=int(path.name), state=fields[0], start_ticks=int(fields[19]),
               cpu_ticks=int(fields[11])+int(fields[12]))
    for name in ('schedstat', 'io', 'wchan', 'status'):
        try:
            value = (path/name).read_text()
            if name == 'schedstat':
                runtime, wait, slices = map(int, value.split())
                row['scheduler'] = dict(runtime_ns=runtime, runqueue_wait_ns=wait, timeslices=slices)
            elif name == 'io':
                values = dict(line.split(':', 1) for line in value.splitlines())
                row['io'] = {key:int(values[key]) for key in IO_KEYS}
            elif name == 'wchan': row['wchan'] = value.strip()
            else:
                values = dict(line.split(':', 1) for line in value.splitlines() if ':' in line)
                row['context_switches'] = {key:int(values[key]) for key in
                    ('voluntary_ctxt_switches', 'nonvoluntary_ctxt_switches')}
        except (OSError, ValueError, KeyError) as error:
            row.setdefault('unavailable', []).append(dict(field=name, error=type(error).__name__))
    # A torn identity is not evidence of a counter regression in one process.
    after = (path/'stat').read_text()
    if int(after[after.rindex(')')+2:].split()[19]) != row['start_ticks']:
        raise ValueError('process identity changed while sampling')
    return row


def observe(proc=Path('/proc')):
    begin = time.monotonic_ns(); rows = []; errors = []
    for path in proc.glob('[0-9]*'):
        try:
            if (path/'comm').read_text().strip() == 'tcpdump': rows.append(read_process(path))
        except FileNotFoundError: pass  # Exit races are represented by missing identities.
        except (OSError, ValueError) as error:
            errors.append(dict(pid=int(path.name), error=type(error).__name__))
    return dict(begin_ns=begin, end_ns=time.monotonic_ns(), processes=rows, errors=errors)


def summarize(rows):
    if not rows: raise ValueError('no recorder diagnostic samples')
    if any(row['end_ns'] < row['begin_ns'] for row in rows): raise ValueError('invalid sample bracket')
    if any(b['begin_ns'] < a['end_ns'] for a,b in zip(rows,rows[1:])): raise ValueError('overlapping samples')
    groups = {}
    for row in rows:
        for process in row['processes']:
            key = (process['pid'], process['start_ticks'])
            groups.setdefault(key, []).append(process)
    processes = []
    for (pid,start), samples in sorted(groups.items()):
        processes.append(dict(pid=pid, start_ticks=start, observations=len(samples),
            states={state:sum(s['state']==state for s in samples) for state in sorted({s['state'] for s in samples})},
            first=samples[0], last=samples[-1]))
    return dict(samples=len(rows), processes=processes,
        missing_process_samples=sum(not r['processes'] for r in rows),
        sample_errors=sum(len(r['errors']) for r in rows),
        unavailable_field_observations={field:sum(item['field']==field for row in rows for p in row['processes'] for item in p.get('unavailable',[]))
            for field in sorted({item['field'] for row in rows for p in row['processes'] for item in p.get('unavailable',[])})},
        maximum_sample_gap_ns=max((b['begin_ns']-a['end_ns'] for a,b in zip(rows,rows[1:])),default=0),
        maximum_read_span_ns=max(r['end_ns']-r['begin_ns'] for r in rows),
        scope='sampled process state and non-atomic cumulative counters; identities never merged across start times; wchan=0 can mean restricted/unavailable; scheduler counters depend on kernel configuration; no root-cause or capture-completeness inference')


def sample(out, ready, stop):
    with out.open('x') as file:
        for _ in range(MAX_SAMPLES):
            row = observe(); file.write(json.dumps(row)+'\n'); file.flush()
            if row['processes'] and not ready.exists(): ready.write_text(json.dumps(dict(ready_ns=row['end_ns'])))
            if stop.exists(): return
            time.sleep(INTERVAL_SECONDS)
    raise RuntimeError('recorder diagnostic sample bound exhausted')


def start(lab, run, inside, processes):
    for role,name in lab.containers.items():
        log = (run/(role+'-recorder-diagnostics.log')).open('w')
        argv = ['docker','exec',name,'python3','tools/m3_recorder_diagnostics.py',
                '--out',inside+'/'+role+'-recorder-samples.jsonl',
                '--ready',inside+'/'+role+'-recorder-ready.json','--stop',inside+'/recorder-stop']
        processes.append((subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT),log))
    deadline = time.monotonic()+10
    while time.monotonic()<deadline:
        if any(p.poll() is not None for p,_ in processes): raise RuntimeError('recorder diagnostic exited before ready')
        if all((run/(role+'-recorder-ready.json')).exists() for role in lab.containers): return
        time.sleep(.1)
    raise RuntimeError('recorder diagnostic readiness timeout')


def stop(run, processes):
    (run/'recorder-stop').touch()
    errors = []
    for process,log in processes:
        try:
            if process.wait(timeout=5): errors.append('recorder diagnostic exited unsuccessfully')
        except subprocess.TimeoutExpired:
            process.terminate(); process.wait(timeout=5); errors.append('recorder diagnostic stop timeout')
        finally: log.close()
    if errors: raise RuntimeError('; '.join(errors))
    return {role:summarize([json.loads(line) for line in (run/(role+'-recorder-samples.jsonl')).read_text().splitlines()])
            for role in ('robot','operator')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('out','ready','stop'): parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args(); sample(args.out,args.ready,args.stop)
