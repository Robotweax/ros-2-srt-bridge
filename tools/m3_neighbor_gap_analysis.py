#!/usr/bin/env python3
"""Correlate sampled neighbor reads with preselected CONTROL gaps, not state causality."""
import argparse,json
from collections import Counter
from pathlib import Path
from m3_neighbor_diagnostics import summarize
from m3_control_liveness import digest
from m3_dds_result_timeline import common_clock


def window_rows(rows,start,end):
    if not 0<start<end:raise ValueError('invalid neighbor analysis window')
    before=[r for r in rows if r['end_ns']<=start];after=[r for r in rows if r['begin_ns']>=end]
    inside=[r for r in rows if start<=r['begin_ns'] and r['end_ns']<=end]
    crossing=[r for r in rows if r['begin_ns']<end and r['end_ns']>start and r not in inside]
    states=Counter('ABSENT' if not r['entries'] else '+'.join(sorted(r['entries'][0]['state'])) for r in inside)
    return dict(before=before[-1] if before else None,after=after[0] if after else None,inside=inside,crossing=crossing,inside_states=dict(states))


def analyze(run,flow):
    report=json.loads((run/'run.json').read_text())
    if report['status']=='running':raise ValueError('requires closed run')
    proof=common_clock(report['clock_namespace_proof'])
    if proof!=flow['clock_proof']:raise ValueError('neighbor/native clock association mismatch')
    peers=json.loads((run/'network.json').read_text())['addresses'];rows={};summary={};hashes={}
    start,end=flow['active_ns']
    for role in ('operator','robot'):
        if digest(run/(role+'.mono'))!=flow['native_sha256'][role]:raise ValueError('primary native artifact mismatch')
        peer='robot' if role=='operator' else 'operator';p=run/(role+'-neighbor-samples.jsonl');before=digest(p)
        summary[role]=summarize(p,peers[peer]);rows[role]=[json.loads(line) for line in p.read_text().splitlines()]
        if rows[role][0]['begin_ns']>start or rows[role][-1]['end_ns']<end:raise ValueError('neighbor observations do not cover source window')
        if digest(p)!=before:raise ValueError('neighbor file changed during read')
        hashes[role]=dict(samples_sha256=before,status_sha256=digest(p.with_suffix('.status.json')))
        if report['neighbor_mode']=='permanent':
            expected=report['neighbor_configuration']['peer_macs'][peer]
            if summary[role]['states']!={'PERMANENT':summary[role]['records']} or summary[role]['lladdrs']!={expected:summary[role]['records']}:raise ValueError('permanent candidate state/MAC changed')
    gaps=[dict(sender=g['sender_role'],window_ns=g['window_ns'],gap_ns=g['gap_ns'],provider_classification=g['classification'],neighbors={role:window_rows(rows[role],*g['window_ns']) for role in rows}) for g in flow['gaps']]
    return dict(neighbor_mode=report['neighbor_mode'],active_ns=flow['active_ns'],clock_proof=proof,neighbor_sha256=hashes,summaries=summary,gaps=gaps,
                scope='sampled states wholly inside each preselected gap, edge-crossing reads retained separately; no exact transition, queue/drop, physical-delivery or causal proof; observer adds netlink/subprocess work')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--flow',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();args.out.write_text(json.dumps(analyze(args.run,json.loads(args.flow.read_text())),indent=2)+'\n')
