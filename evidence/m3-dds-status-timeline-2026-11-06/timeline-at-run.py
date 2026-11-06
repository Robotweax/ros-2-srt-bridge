#!/usr/bin/env python3
"""Read-only correlation of closed DDS command journals on a proven common VM clock.

Recorded journal timestamps are arguments to state mutations, before SQLite
commit. They are not fsync completion, handler-start or physical delivery times.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import uuid


def common_clock(proofs):
    if set(proofs)!= {'robot','operator'} or proofs['robot']!=proofs['operator']:raise ValueError('common VM/time namespace proof mismatch')
    lines=proofs['robot'].splitlines()
    if len(lines)!=3:raise ValueError('invalid clock proof')
    uuid.UUID(lines[0])
    if [line.split() for line in lines[1:]]!=[['monotonic','0','0'],['boottime','0','0']]:raise ValueError('requires zero time namespace offsets')
    return proofs['robot']


def read_journal(path,side):
    path=Path(path)
    wal=Path(str(path)+'-wal')
    if wal.exists() and wal.stat().st_size:raise ValueError('requires closed, checkpointed journal')
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    entries={}
    # Immutable avoids creating/writing SQLite sidecars. A nonempty WAL is
    # refused above; callers must supply quiescent artifacts, never live DBs.
    with sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        if db.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:raise ValueError('journal integrity check failed')
        if db.execute('PRAGMA application_id').fetchone()[0]!=0x52574a31 or db.execute('PRAGMA user_version').fetchone()[0]!=1:raise ValueError('journal schema mismatch')
        identities=db.execute('SELECT local,remote,side FROM identity').fetchall()
        if len(identities)!=1 or identities[0][2]!=side:raise ValueError('journal side mismatch')
        for id,route,state,b in db.execute('SELECT id,route,state,record FROM entries ORDER BY id'):
            get=lambda at,n=8:int.from_bytes(b[at:at+n],'big')
            if len(id)!=16 or len(b)!=512 or b[:6]!=b'RWJ1\x00\x01' or state!=10+b[6] or route!=get(8,4):raise ValueError('invalid journal record')
            digest=hashlib.sha256(struct.pack('!IIIIQQ',0x52574331,route,get(104,4),get(12,4),get(112),get(120))).digest()
            if b[72:104]!=digest:raise ValueError('journal command hash mismatch')
            entries[id.hex()]=dict(state=b[6],reason=b[7],revision=get(176),route=route,payload_hash=digest.hex(),source_epoch=b[16:32].hex(),session=b[40:56].hex(),owner_epoch=b[56:72].hex(),
                source_ns=get(32),admitted_ns=get(128),dispatched_ns=get(136),finished_ns=get(144),deadline_ns=get(152),result_valid=bool(b[164]),result_generation=get(168))
    if hashlib.sha256(path.read_bytes()).hexdigest()!=before or (wal.exists() and wal.stat().st_size):raise ValueError('journal changed during read')
    return dict(sha256=before,entries=entries)


def correlate(commands,sender,receiver):
    """Absent/unresolved/changed-context records remain unqualified, never nonexecution."""
    rows=[];seen=set()
    for command in commands:
        number=command['number'];id=number.to_bytes(16,'little').hex()
        if id in seen:raise ValueError('duplicate workload intent')
        seen.add(id)
        a=sender.get(id);b=receiver.get(id)
        row=dict(number=number,request_id=id,sender=a,receiver=b,qualified=False)
        rows.append(row)
        if not a or not b:row['why']='missing journal entry; no nonexecution inferred';continue
        if any(a[k]!=b[k] for k in ('route','payload_hash','source_epoch','source_ns','deadline_ns','session')):raise ValueError('command/context mismatch')
        if a['owner_epoch']!=a['source_epoch']:row['why']='sender owner changed; local observation timestamp unavailable';continue
        if not (a['state']==b['state']==command.get('terminal')==4 and a['revision']==b['revision']==3 and a['result_valid'] and b['result_valid'] and a['result_generation']==b['result_generation']==command['new_generation']):
            row['why']='not a matching confirmed success; timing decomposition withheld';continue
        times=[command['submitted_monotonic_ns'],a['source_ns'],a['admitted_ns'],b['admitted_ns'],b['dispatched_ns'],b['finished_ns'],a['finished_ns'],command.get('result_observed_monotonic_ns',0)]
        if any(t<=0 for t in times) or times!=sorted(times):raise ValueError('inconsistent common-clock timeline')
        if b['dispatched_ns']>=b['deadline_ns']:raise ValueError('dispatch timestamp beyond start deadline')
        names=('invocation_to_origin','origin_to_sender_admission','sender_to_receiver_admission','receiver_admission_to_dispatch','dispatch_to_receiver_finish','receiver_finish_to_sender_observation','sender_observation_to_driver_observation')
        row.update(qualified=True,deltas_ms={k:(y-x)/1e6 for k,x,y in zip(names,times,times[1:])},total_ms=(times[-1]-times[0])/1e6,
            status_polls=command.get('status_observations'),status_history=command.get('status_observation_history'),status_history_omitted=command.get('status_observations_omitted',0))
    return rows


def analyze(run):
    run=Path(run);report=json.loads((run/'run.json').read_text())
    if report.get('status')!='passed' or report.get('sensor_only',False) or 'dds_transport_profile' not in report:raise ValueError('requires completed combined DDS run')
    proof=common_clock(report['clock_namespace_proof'])
    sender=read_journal(run/'operator.sqlite',1);receiver=read_journal(run/'robot.sqlite',2)
    return dict(run=str(run),clock_proof=proof,sender_sha256=sender['sha256'],receiver_sha256=receiver['sha256'],rows=correlate(report['results']['commands'],sender['entries'],receiver['entries']),
        scope='closed original-owner DDS journals under runner common-VM/time-namespace proof; timestamps sampled before journal mutations/commits, not durable-commit completion, atomic handler claim or physical delivery; receiver-finish to sender-observation includes journal, middleware, scheduling and reconciliation; missing/unknown records retain uncertainty')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=analyze(args.run)
    with args.out.open('x') as file:json.dump(result,file,indent=2);file.write('\n')


if __name__=='__main__':main()
