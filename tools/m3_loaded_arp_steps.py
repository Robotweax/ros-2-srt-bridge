#!/usr/bin/env python3
"""Posthoc ALL positive reply-counter steps, separate from primary CONTROL windows."""
import argparse,json
from pathlib import Path
from m3_source_preflight import ROOT,sha
from m3_loaded_arp_analysis import reply_witness
from m3_qdisc_gap_analysis import inside_deltas
from m3_neighbor_gap_analysis import window_rows
from m3_monotonic_capture import records
from m3_arp_gap_observations import parse_arp
from m3_udp_path_analysis import arp_kind


def positive_steps(rows,start,end):
    result=[]
    for a,b in zip(rows,rows[1:]):
        if not all(start<=r['begin_ns']<=r['end_ns']<=end for r in (a,b)):continue
        delta={kind:{k:b['counters'][kind][k]-a['counters'][kind][k] for k in ('packets','bytes','drops')} for kind in ('eligible','verdict')}
        if any(v<0 for d in delta.values() for v in d.values()):raise ValueError('counter regression')
        if not any(delta[k]['packets']>0 for k in delta):continue
        result.append(dict(previous=a,current=b,outer_read_envelope_ns=[a['read_ns'][0],b['read_ns'][1]],inner_read_gap_ns=[a['read_ns'][1],b['read_ns'][0]],delta=delta))
    return result


def root_context(rows,start,end):
    before=[r for r in rows if r['end_ns']<=start];after=[r for r in rows if r['begin_ns']>=end]
    if not before or not after:return dict(available=False,why='censored root context')
    a,b=before[-1],after[0]
    return dict(available=True,window_ns=[a['begin_ns'],b['end_ns']],before=a,after=b,contained=inside_deltas(rows,a['begin_ns']-1,b['end_ns']+1),scope='Wider bracketing reply-source root context; not same reply interval or specific ARP drops.')


def analyze(run,report,manifest):
    if report['status']!='passed':raise ValueError('requires qualified loaded primary analysis')
    run=run.resolve();d=report['analysis'];primary=d['path_analysis'];active=primary['primary_control']['active_ns']
    if d['run']!=str(run.relative_to(ROOT)):raise ValueError('wrong source run')
    paths=[run/'run.json',run/'operator.mono',run/'robot.mono']+[run/(role+'-'+kind+suffix) for role in ('operator','robot') for kind in ('arp-reply','qdisc','neighbor') for suffix in ('-samples.jsonl','-samples.status.json')];hashes={}
    for p in paths:
        key=str(p.relative_to(ROOT));h=sha(p)
        if manifest.get(key,{}).get('sha256')!=h:raise ValueError('original step input changed')
        hashes[key]=h
    arps={};rows={};qdiscs={};neighbors={};steps=[]
    for role in ('operator','robot'):
        peer='robot' if role=='operator' else 'operator';arps[role]=[]
        for raw in records(run/(role+'.mono')):
            a=parse_arp(raw)
            if a:a['identity_class']=arp_kind(a,primary['owned_addresses'][role],primary['owned_addresses'][peer],primary['owned_macs'][role],primary['owned_macs'][peer]);arps[role].append(a)
        def read(kind):return [json.loads(l) for l in (run/(role+'-'+kind+'-samples.jsonl')).read_text().splitlines()]
        rows[role]=read('arp-reply');qdiscs[role]=read('qdisc');neighbors[role]=read('neighbor')
    for role in ('operator','robot'):
        peer='robot' if role=='operator' else 'operator';source=[r for r in arps[role] if r['identity_class']=='outgoing_local_reply'];sink=[r for r in arps[peer] if r['identity_class']=='incoming_peer_reply']
        for value in positive_steps(rows[role],*active):
            start,end=value['outer_read_envelope_ns'];value.update(responder=role,requester=peer,witness=reply_witness(value,source,sink),requester_neighbors=window_rows(neighbors[peer],start,end),reply_source_root=root_context(qdiscs[role],start,end));steps.append(value)
    if any(sha(ROOT/p)!=h for p,h in hashes.items()):raise ValueError('step inputs changed during analysis')
    return dict(run=d['run'],active_ns=active,selection='POSTHOC all adjacent positive eligibility OR PASS packet increments wholly inside the source publication window; no primary window/outcome changed',steps=steps,raw_sha256=hashes,analysis_source_sha256=sha(Path(__file__)),scope='Positive generated/PASS reply accounting versus source/peer native observation in wider read envelopes. Missing source observation can mean delay or loss after eligibility; no subtraction as packet drops, per-request nonce mapping, exact root cause or historical proof. Root context is explicitly wider than reply interval; added observer work remains.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('run','primary','hash-manifest','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():p.error('output exists')
    try:d=dict(status='passed',analysis=analyze(a.run,json.loads(a.primary.read_text()),json.loads(a.hash_manifest.read_text())))
    except Exception as e:d=dict(status='failed',error=str(e))
    a.out.write_text(json.dumps(d,indent=2)+'\n');print(d['status']);raise SystemExit(d['status']!='passed')
