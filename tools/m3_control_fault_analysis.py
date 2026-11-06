#!/usr/bin/env python3
"""Read-only triangulation for the deliberately installed CONTROL drop.

SDK handles equal protocol socket IDs only for the recorded pinned provider.
Tuple/socket association is routing evidence, not authenticated peer identity.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
from m3_control_liveness import digest, parse_control
from m3_dds_result_timeline import common_clock
from m3_monotonic_capture import records, decode
from m3_provider_stats import summarize_run, COUNTERS

PIN = '52be7c86ee1f303cbb0c8718c364217e4dd97a36'
ARCHIVE = '3fa56e487e6c6408d9e41779d18aba9ff866978892ddbe3b88ac12fc51141673'


def connection(row):return row['owner_epoch'], row['generation'], row['socket']


def baseline(stats, boundary):
    candidates=[]
    for name, result in stats.items():
        candidates.extend((row['end_ns'],name,row) for row in result['records']
                          if row['available'] and boundary-2000000000<=row['end_ns']<=boundary)
    if not candidates:raise ValueError('missing recent provider baseline')
    _, name, row = max(candidates,key=lambda item:item[0])
    return name,row


def inside_deltas(rows, identity, start, end):
    pairs=[]
    for previous, current in zip(rows,rows[1:]):
        if not all(row['available'] and connection(row)==identity and start<=row['begin_ns']<=row['end_ns']<=end for row in (previous,current)):continue
        delta={key:current[key]-previous[key] for key in COUNTERS}
        if any(n<0 for n in delta.values()):raise ValueError('counter regression')
        pairs.append(dict(previous_read_ns=[previous['begin_ns'],previous['end_ns']],current_read_ns=[current['begin_ns'],current['end_ns']],counters=delta))
    return dict(adjacent_pairs=pairs,totals={key:sum(pair['counters'][key] for pair in pairs) for key in COUNTERS})


def analyze(run):
    report=json.loads((run/'run.json').read_text())
    if report['status']=='running':raise ValueError('run not closed')
    if report.get('srt_archive_sha256')!=ARCHIVE:raise ValueError('unverified provider handle/wire-ID contract')
    fault=report['controlled_control_fault']
    if not fault['restored'] or fault['final_counters']['drops']<=0:raise ValueError('unverified fault/restoration')
    start,end=fault['guaranteed_active_ns'];role=fault['role'];peer=fault['peer']
    if not 0<start<end:raise ValueError('invalid fault interval')
    proof=common_clock(report['clock_namespace_proof'])
    stats=summarize_run(run); addresses=json.loads((run/'network.json').read_text())['addresses']
    selected={}
    for side in (role,peer):
        name,row=baseline({k:v for k,v in stats.items() if k.startswith(side+'-')},fault['install']['begin_ns'])
        selected[side]=dict(process=name,baseline=row,deltas=inside_deltas(stats[name]['records'],connection(row),start,end))
    capture={};parsed={}
    # Include pre-fault traffic and a restoration window. Coverage is mandatory.
    window=[start-2000000000,end+3000000000]
    for side in (role,peer):
        status=report['monotonic_captures']['statuses'][side]
        if status.get('complete') is not True or status.get('artifact_version')!=2 or status.get('clock')!='kernel_monotonic' or status.get('time_namespace_zero') is not True:
            raise ValueError('unqualified native capture')
        if not status['ready_ns']<=window[0]<window[1]<=status['stop_before_ns'] or status['reserve_failed'] or status['copy_failed']:
            raise ValueError('capture coverage/loss')
        path=run/(side+'.mono');before=digest(path);count=0;control=[];sensors=Counter()
        for row in records(path):
            count+=1
            if row['artifact_version']!=2 or row['ifindex']!=status['ifindex']:raise ValueError('capture identity changed')
            if not window[0]<=row['monotonic_ns']<window[1]:continue
            decoded=decode(row,addresses[side])
            if decoded and start<=row['monotonic_ns']<end and '/sensor_' in decoded[0]:sensors[decoded[0]]+=1
            value=parse_control(row,addresses[side],status['mtu'])
            if value:control.append(value)
        if count!=status['records'] or count!=status['seen'] or count!=status['submitted'] or digest(path)!=before:
            raise ValueError('capture count/hash mismatch')
        parsed[side]=control
        capture[side]=dict(native_sha256=before,sensor_observations_during_fault=dict(sensors))
    old_peer_id=selected[peer]['baseline']['socket'];old_local_id=selected[role]['baseline']['socket']
    flows={(r['source'],r['destination'],r['source_port'],r['destination_port'],r['destination_socket_id'])
           for r in parsed[role] if r['direction']=='out' and window[0]<=r['monotonic_ns']<fault['install']['begin_ns'] and r['destination_socket_id']==old_peer_id}
    if len(flows)!=1:raise ValueError('ambiguous pre-fault tuple/socket mapping')
    flow=next(iter(flows))
    if flow[:2]!=(addresses[role],addresses[peer]):raise ValueError('unexpected CONTROL peer addresses')
    old=lambda r:(r['source'],r['destination'],r['source_port'],r['destination_port'],r['destination_socket_id'])==flow
    for side in (role,peer):
        rows=parsed[side]
        capture[side].update(old_flow_during_fault=sum(old(r) and start<=r['monotonic_ns']<end for r in rows),
            all_control_out_during_fault=sum(r['direction']=='out' and start<=r['monotonic_ns']<end for r in rows),
            old_reverse_during_fault=sum(r['destination_socket_id']==old_local_id and r['source']==addresses[peer] and start<=r['monotonic_ns']<end for r in rows),
            control_out_after_restoration=sum(r['direction']=='out' and fault['remove']['end_ns']<=r['monotonic_ns']<window[1] for r in rows))
    delta=selected[role]['deltas']['totals']
    observed=(sum(delta[k] for k in ('data_sent','ack_sent','nak_sent'))>0 and capture[role]['all_control_out_during_fault']==0
              and capture[peer]['old_flow_during_fault']==0 and capture[role]['old_reverse_during_fault']>0
              and sum(capture[role]['sensor_observations_during_fault'].values())>0
              and all(capture[side]['control_out_after_restoration']>0 for side in (role,peer)))
    return dict(known_fault_signature_observed=observed,fault=fault,clock_proof=proof,selected=selected,captures=capture,
                old_flow=list(flow),provider_pin_contract=PIN,analysis_window_ns=window,
                scope='known filter drop only; provider selected send counters can grow with no post-filter CONTROL observation; no historical cause, physical delivery or command nonexecution inference; deltas exclude unavailable/identity-crossing pairs; handle/wire-ID association requires this provider pin')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--out',required=True,type=Path)
    args=p.parse_args();result=analyze(args.run);args.out.write_text(json.dumps(result,indent=2)+'\n')
    if not result['known_fault_signature_observed']:raise SystemExit('expected known-fault signature not observed; retain result')
