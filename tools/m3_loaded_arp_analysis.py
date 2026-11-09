#!/usr/bin/env python3
"""Closed reply eligibility and tap associations in prospectively selected CONTROL windows."""
import argparse,json
from pathlib import Path
from m3_source_preflight import ROOT,sha
from m3_udp_path_analysis import analyze as path_analysis
from m3_arp_reply_diagnostics import summarize
from m3_arp_gap_observations import parse_arp
from m3_udp_path_analysis import arp_kind
from m3_monotonic_capture import records


def interval(rows,start,end):
    inside=[r for r in rows if start<=r['begin_ns'] and r['end_ns']<=end]
    before=[r for r in rows if r['end_ns']<=start];after=[r for r in rows if r['begin_ns']>=end]
    crossing=[r for r in rows if r['begin_ns']<end and r['end_ns']>start and r not in inside]
    r=dict(before=before[-1] if before else None,after=after[0] if after else None,crossing=crossing,inside_records=len(inside),first=inside[0] if inside else None,last=inside[-1] if inside else None,delta=None,outer_read_envelope_ns=None,inner_read_gap_ns=None)
    if len(inside)>=2:
        a,b=inside[0],inside[-1];r['outer_read_envelope_ns']=[a['read_ns'][0],b['read_ns'][1]];r['inner_read_gap_ns']=[a['read_ns'][1],b['read_ns'][0]]
        r['delta']={kind:{k:b['counters'][kind][k]-a['counters'][kind][k] for k in ('packets','bytes','drops')} for kind in ('eligible','verdict')}
        if any(v<0 for d in r['delta'].values() for v in d.values()):raise ValueError('ARP counters regressed')
        if any(a['counters'][kind]['index']!=b['counters'][kind]['index'] for kind in ('eligible','verdict')):raise ValueError('ARP action identity changed')
    return r


def reply_witness(value,source_replies,peer_replies):
    envelope=value['outer_read_envelope_ns'];inner=value['inner_read_gap_ns'];delta=value['delta']
    if envelope is None:return dict(classification='insufficient_contained_reply_reads')
    a,b=envelope;source=[r for r in source_replies if a<=r['monotonic_ns']<=b];peer=[r for r in peer_replies if a<=r['monotonic_ns']<=b]
    grew=delta['eligible']['packets']>0 and delta['verdict']['packets']>0
    return dict(classification='reply_eligibility_and_pass_growth_without_source_reply_observation' if grew and not source else 'reply_growth_with_source_observation' if grew else 'no_positive_contained_reply_growth_not_generation_absence_proof',source_replies_in_outer_envelope=len(source),peer_replies_in_outer_envelope=len(peer),source_replies_between_reads=sum(inner[0]<=r['monotonic_ns']<=inner[1] for r in source_replies),outer_read_envelope_ns=envelope,inner_read_gap_ns=inner,delta=delta,scope='Reported cumulative reply growth versus observations over wider read envelope; non-atomic PIPE/PASS, no counter-minus-tap drop count, exact cause or generation absence inference.')


def analyze(run,manifest):
    run=run.resolve();report=json.loads((run/'run.json').read_text())
    if not report.get('arp_reply_diagnostics_enabled'):raise ValueError('requires loaded ARP instrumentation')
    primary=path_analysis(run,manifest);summaries={};rows={};hashes={};arps={r:[] for r in ('operator','robot')}
    for role in arps:
        p=run/(role+'-arp-reply-samples.jsonl');q=p.with_suffix('.status.json')
        for f in (p,q):
            key=str(f.relative_to(ROOT));h=sha(f)
            if manifest.get(key,{}).get('sha256')!=h:raise ValueError('original reply observation hash mismatch')
            hashes[key]=h
        summaries[role]=summarize(p);rows[role]=[json.loads(l) for l in p.read_text().splitlines()]
        start,end=primary['primary_control']['active_ns']
        if rows[role][0]['begin_ns']>start or rows[role][-1]['end_ns']<end:raise ValueError('ARP observer source-window coverage insufficient')
        native_status=report['monotonic_captures']['statuses'][role];peer='robot' if role=='operator' else 'operator'
        for raw in records(run/(role+'.mono')):
            a=parse_arp(raw)
            if a:
                if raw['ifindex']!=native_status['ifindex']:raise ValueError('ARP native interface changed')
                a['identity_class']=arp_kind(a,primary['owned_addresses'][role],primary['owned_addresses'][peer],primary['owned_macs'][role],primary['owned_macs'][peer]);arps[role].append(a)
    joined=[]
    for w in primary['windows']:
        start,end=w['window_ns'];requester=w['sender'];responder='robot' if requester=='operator' else 'operator';comparisons={}
        for role in arps:
            peer='robot' if role=='operator' else 'operator';v=interval(rows[role],start,end)
            if v['outer_read_envelope_ns'] is not None:
                a,b=v['outer_read_envelope_ns'];status=report['monotonic_captures']['statuses'][role]
                if not status['ready_ns']<=a<b<=status['stop_before_ns']:raise ValueError('reply envelope outside native coverage')
            source=[r for r in arps[role] if r['identity_class']=='outgoing_local_reply'];sink=[r for r in arps[peer] if r['identity_class']=='incoming_peer_reply']
            comparisons[role]=dict(reads=v,witness=reply_witness(v,source,sink),arp_inside_window={r:[a for a in arps[r] if start<=a['monotonic_ns']<=end] for r in (role,peer)})
        joined.append(dict(family=w['family'],requester=requester,responder=responder,window_ns=w['window_ns'],control_stage=w['stage_classification'],control_primary_classification=w['primary_classification'],identity_stable=w['identity_stable'],neighbors=w['neighbors'],control_qdisc=w['qdisc'],reply_comparisons=comparisons))
    if any(sha(ROOT/name)!=h for name,h in hashes.items()):raise ValueError('ARP inputs changed during analysis')
    for role in arps:
        if sha(run/(role+'.mono'))!=primary['primary_control']['native_sha256'][role]:raise ValueError('native changed during reply analysis')
    return dict(run=str(run.relative_to(ROOT)),path_analysis=primary,reply_observer_summaries=summaries,reply_raw_sha256=hashes,windows=joined,scope='All primary CONTROL source gaps/loss windows; opposite peer is responder for requester neighbor resolution. Reply PIPE/PASS growth with no reply source hook in the wider contained read envelope localizes after reply eligibility, not unique root-drop reason, physical delivery, authenticated ARP acceptance or historical cause. Zero growth cannot exclude generation at omitted boundaries/gaps. Added observer work; no tuning or mitigation.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--hash-manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('output exists')
    try:d=dict(status='passed',analysis=analyze(a.run,json.loads(a.hash_manifest.read_text())))
    except Exception as e:d=dict(status='failed',error=str(e))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(d['status']);raise SystemExit(d['status']!='passed')
