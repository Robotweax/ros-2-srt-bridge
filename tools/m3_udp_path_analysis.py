#!/usr/bin/env python3
"""Hash-guarded CONTROL/ARP/neighbor/PASS associations, without tuning or cause authority."""
import argparse,json
from collections import Counter
from pathlib import Path
from m3_source_preflight import ROOT,sha
from m3_control_provider_liveness import analyze as control_analysis
from m3_control_liveness import parse_control
from m3_monotonic_capture import records
from m3_arp_gap_observations import parse_arp
from m3_neighbor_diagnostics import summarize as neighbor_summary,valid_mac
from m3_neighbor_gap_analysis import window_rows
from m3_qdisc_diagnostics import summarize as qdisc_summary
from m3_qdisc_gap_analysis import inside_deltas,classify
from m3_provider_stats import summarize_run
from m3_control_fault_analysis import connection


def arp_kind(arp,local_ip,peer_ip,local_mac,peer_mac):
    """Incoming reflected own broadcasts are not peer requests/replies."""
    if arp['operation'] not in (1,2):return 'unsupported_operation'
    if arp['ethernet_source_mac']!=arp['sender_mac']:return 'unexpected_identity'
    request=arp['operation']==1;kind='request' if request else 'reply'
    local=arp['sender_ipv4']==local_ip and arp['sender_mac']==local_mac and arp['target_ipv4']==peer_ip
    peer=arp['sender_ipv4']==peer_ip and arp['sender_mac']==peer_mac and arp['target_ipv4']==local_ip
    if local:
        if arp['ethernet_destination_mac'] not in (peer_mac,'ff:ff:ff:ff:ff:ff') or arp['target_mac'] not in ((peer_mac,'00:00:00:00:00:00') if request else (peer_mac,)):return 'unexpected_identity'
        return ('outgoing_local_' if arp['outgoing'] else 'reflected_local_')+kind
    if peer:
        if arp['ethernet_destination_mac'] not in (local_mac,'ff:ff:ff:ff:ff:ff') or arp['target_mac'] not in ((local_mac,'00:00:00:00:00:00') if request else (local_mac,)):return 'unexpected_identity'
        return ('unexpected_outgoing_peer_' if arp['outgoing'] else 'incoming_peer_')+kind
    return 'unrelated_or_unexpected_identity'


def selected_windows(flow,addresses):
    result=[]
    for family,items in [('adjacent_gap',flow['gaps']),('loss_window',flow['loss_windows'])]:
        for g in items:
            start,end=g['window_ns']
            if not 0<start<end:raise ValueError('invalid primary window')
            roles=[r for r,ip in addresses.items() if ip==g['flow']['source']]
            if len(roles)!=1:raise ValueError('primary source is not an owned endpoint')
            result.append(dict(family=family,sender=roles[0],window_ns=[start,end],primary=g))
    return result


def stable_identity(provider,role,window,identity):
    start,end=window
    rows=[r for name,v in provider.items() if name.startswith(role+'-') for r in v['records'] if r['begin_ns']<end and r['end_ns']>start]
    return bool(identity and rows and all(r['available'] and list(connection(r))==identity for r in rows))


def analyze(run,manifest,arp_only=False):
    run=run.resolve();names=['run.json','network.json','operator.mono','robot.mono','before-operator-links.log','before-robot-links.log']
    names+=[p.name for p in run.glob('*-bridge-*.log')]
    if not arp_only:
        names += [role+'-'+kind+suffix for role in ('operator','robot') for kind in ('neighbor','qdisc') for suffix in ('-samples.jsonl','-samples.status.json')]
    hashes={}
    for name in names:
        p=run/name;key=str(p.relative_to(ROOT));h=sha(p)
        if manifest.get(key,{}).get('sha256')!=h:raise ValueError('original input hash mismatch: '+name)
        hashes[key]=h
    report=json.loads((run/'run.json').read_text())
    if report['status']!='passed' or not report.get('pcap_population_reconciled'):raise ValueError('requires original harness/capture integrity PASS')
    if not arp_only and (report.get('neighbor_mode')!='dynamic' or not report.get('neighbor_diagnostics_enabled') or not report.get('control_qdisc_diagnostics_enabled')):raise ValueError('requires dynamic neighbor and qdisc observers')
    flow=control_analysis(run);addresses=json.loads((run/'network.json').read_text())['addresses'];windows=selected_windows(flow,addresses);providers=summarize_run(run)
    macs={};neighbor={};qdisc={};observers={};arps={};native={}
    for role in ('operator','robot'):
        peer='robot' if role=='operator' else 'operator'
        links=json.loads((run/('before-'+role+'-links.log')).read_text())
        if len(links)!=1 or links[0].get('ifname')!='eth0' or not valid_mac(links[0].get('address')):raise ValueError('unverified owned MAC')
        macs[role]=links[0]['address']
    for role in ('operator','robot'):
        peer='robot' if role=='operator' else 'operator';status=report['monotonic_captures']['statuses'][role];arps[role]=[];native[role]=[]
        for row in records(run/(role+'.mono')):
            if not any(w['window_ns'][0]<row['monotonic_ns']<=w['window_ns'][1] for w in windows):continue
            a=parse_arp(row)
            if a:
                a['identity_class']=arp_kind(a,addresses[role],addresses[peer],macs[role],macs[peer]);arps[role].append(a)
            c=parse_control(row,addresses[role],status['mtu'])
            if c and c['direction']=='out' and c['destination']==addresses[peer] and ((role=='operator' and c['source_port']==10080) or (role=='robot' and c['destination_port']==10080)):native[role].append(c)
        if not arp_only:
            n=run/(role+'-neighbor-samples.jsonl');q=run/(role+'-qdisc-samples.jsonl')
            observers[role]=dict(neighbor=neighbor_summary(n,addresses[peer]),qdisc=qdisc_summary(q))
            neighbor[role]=[json.loads(l) for l in n.read_text().splitlines()];qdisc[role]=[json.loads(l) for l in q.read_text().splitlines()]
            for rows in (neighbor[role],qdisc[role]):
                if rows[0]['begin_ns']>flow['active_ns'][0] or rows[-1]['end_ns']<flow['active_ns'][1]:raise ValueError('observer does not cover source window')
    joined=[]
    for w in windows:
        start,end=w['window_ns'];role=w['sender'];g=w['primary'];item=dict(family=w['family'],sender=role,window_ns=[start,end],primary_classification=g['classification'],primary_mapping_reason=g.get('why'),flow=g['flow'],provider=g.get('provider'),arp={r:[a for a in arps[r] if start<a['monotonic_ns']<=end] for r in arps})
        item['arp_counts']={r:dict(Counter(a['identity_class'] for a in items)) for r,items in item['arp'].items()}
        if not arp_only:
            item['neighbors']={r:window_rows(neighbor[r],start,end) for r in neighbor};item['qdisc']=inside_deltas(qdisc[role],start,end)
            item['all_selected_source_control_observations']=sum(start<a['monotonic_ns']<end for a in native[role])
            item['identity_stable']=stable_identity(providers,role,[start,end],g.get('sender_identity'))
            item['stage_classification']=classify(g,item['qdisc'],item['all_selected_source_control_observations'],item['identity_stable'])
        else:item['stage_classification']='neighbor_and_qdisc_not_observed_in_original_run'
        joined.append(item)
    if any(sha(ROOT/p)!=v for p,v in hashes.items()):raise ValueError('input changed during analysis')
    return dict(run=str(run.relative_to(ROOT)),arp_only=arp_only,primary_control=flow,owned_addresses=addresses,owned_macs=macs,observer_summaries=observers,windows=joined,raw_sha256=hashes,scope='All primary >=1s gaps and active CONTROL loss windows; hashes/native/clock identities qualified by primary analysis. ARP tuple presence is not authenticated neighbor acceptance or request/reply nonce pairing; reflected local copies kept separate. Sampled netlink/TC read brackets are not exact transitions or flow-specific drops; root counters cannot be summed with child. Stage classification is association, not unique cause, nonexecution, latency or tuning authority.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True,type=Path);p.add_argument('--hash-manifest',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--arp-only',action='store_true');a=p.parse_args()
    if a.out.exists():p.error('output already exists')
    try:d=dict(status='passed',analysis=analyze(a.run,json.loads(a.hash_manifest.read_text()),a.arp_only))
    except Exception as e:d=dict(status='failed',error=str(e))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(d['status']);raise SystemExit(d['status']!='passed')
