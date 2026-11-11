#!/usr/bin/env python3
"""Closed per-cookie joins, including lifetimes crossing counter/window edges."""
import argparse,json
from pathlib import Path
from m3_source_preflight import ROOT,sha
from m3_arp_packet_diagnostics import summarize


def membership(rows,start,end):
    if not 0<start<end:raise ValueError('invalid packet window')
    selected=[]
    for row in rows:
        c,t=row['created_ns'],row['terminal_ns']
        if not 0<c<t:raise ValueError('invalid lifecycle time')
        if t<start or c>end:continue
        selected.append(dict(cookie=row['cookie'],outcome=row['outcome'],created_ns=c,terminal_ns=t,created_inside=start<=c<=end,terminal_inside=start<=t<=end,carry_in=c<start,carry_out=t>end,residence=row['residence'],reason=row['reason']))
    return dict(window_ns=[start,end],lifetimes=selected,created_counts={k:sum(r['created_inside'] and r['outcome']==k for r in selected) for k in ('driver_start','qdisc_drop','other_free','consumed_before_driver')},carry_in_ids=[r['cookie'] for r in selected if r['carry_in']],carry_out_ids=[r['cookie'] for r in selected if r['carry_out']],scope='Inclusive boundaries; creation and terminal membership separate; carry-out is not a drop; actual lifecycle terminal class retained, no aggregate subtraction.')


def analyze(run,primary,steps,manifest):
    run=run.resolve();data=json.loads((run/'run.json').read_text());paths=[run/'run.json',run/'network.json']+[run/(r+s) for r in ('operator','robot') for s in ('.mono','-monotonic-capture.log','-arp-trace.log','-arp-trace-ready.json','-arp-trace.jsonl','-arp-trace-btf.log')];hashes={}
    for p in paths:
        name=str(p.relative_to(ROOT));h=sha(p)
        if manifest.get(name,{}).get('sha256')!=h:raise ValueError('packet window raw input changed')
        hashes[name]=h
    if primary.get('status')!='passed' or steps.get('status')!='passed':raise ValueError('primary/step analysis unavailable')
    for d in (primary['analysis'],steps['analysis']):
        if d['run']!=str(run.relative_to(ROOT)):raise ValueError('wrong packet source run')
    if data['arp_packet_configuration']['binary_sha256']!=sha(ROOT/'build/arp-packet-trace/arp_packet_trace'):raise ValueError('calibrated tracer changed')
    traces=summarize(run,json.loads((run/'network.json').read_text())['addresses'],data['neighbor_configuration']['peer_macs'])
    if traces!=data['arp_packet_diagnostics']:raise ValueError('closed lifecycle reanalysis disagrees with original')
    windows=[]
    for w in primary['analysis']['windows']:
        windows.append(dict(family=w['family'],requester=w['requester'],responder=w['responder'],window_ns=w['window_ns'],roles={r:membership(v['lifetimes'],*w['window_ns']) for r,v in traces.items()}))
    joined=[]
    for s in steps['analysis']['steps']:
        role=s['responder'];joined.append(dict(responder=role,requester=s['requester'],outer_read_envelope_ns=s['outer_read_envelope_ns'],counter_delta=s['delta'],witness=s['witness'],trace=membership(traces[role]['lifetimes'],*s['outer_read_envelope_ns'])))
    if any(sha(ROOT/n)!=h for n,h in hashes.items()):raise ValueError('packet raw inputs changed during analysis')
    return dict(run=str(run.relative_to(ROOT)),trace_summary=traces,primary_windows=windows,positive_steps=joined,selection='All primary >=1s CONTROL gaps/active loss windows and all adjacent positive reply counter steps inside publication, prospectively declared for this cohort',raw_sha256=hashes,scope='Per-cookie source TX queue/drop evidence only. No individual ARP-request/peer-tap nonce mapping, physical delivery or historical-cause inference. Other packet classes and pre-net_dev_queue drops outside scope. Added observer overhead; no tuning.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','primary','steps','hash-manifest','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():p.error('output exists')
    try:value=dict(status='passed',analysis=analyze(a.run,json.loads(a.primary.read_text()),json.loads(a.steps.read_text()),json.loads(a.hash_manifest.read_text())))
    except Exception as e:value=dict(status='failed',error=str(e))
    a.out.write_text(json.dumps(value,indent=2)+'\n');print(value['status'],value.get('error',''));raise SystemExit(value['status']!='passed')
