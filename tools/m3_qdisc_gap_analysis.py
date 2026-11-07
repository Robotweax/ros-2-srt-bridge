#!/usr/bin/env python3
"""Locate selected counter/tap differences, not individual datagram drop causes."""
import argparse,json
from pathlib import Path
from m3_qdisc_diagnostics import summarize
from m3_control_liveness import digest,parse_control
from m3_monotonic_capture import records
from m3_provider_stats import summarize_run
from m3_control_fault_analysis import connection
from m3_dds_result_timeline import common_clock


def inside_deltas(rows,start,end):
    totals=dict(pass_packets=0,pass_bytes=0,root_packets=0,root_bytes=0,root_drops=0,root_overlimits=0);pairs=[]
    for before,after in zip(rows,rows[1:]):
        if not all(start<r['begin_ns']<=r['end_ns']<end for r in (before,after)):continue
        delta={name:after[group][key]-before[group][key] for name,group,key in [('pass_packets','pass_counter','packets'),('pass_bytes','pass_counter','bytes'),('root_packets','root','packets'),('root_bytes','root','bytes'),('root_drops','root','drops'),('root_overlimits','root','overlimits')]}
        if any(n<0 for n in delta.values()):raise ValueError('counter regression')
        pairs.append(dict(previous_read_ns=[before['begin_ns'],before['end_ns']],current_read_ns=[after['begin_ns'],after['end_ns']],delta=delta))
        for key,value in delta.items():totals[key]+=value
    inside=[r for r in rows if start<r['begin_ns']<=r['end_ns']<end]
    return dict(totals=totals,pairs=pairs,first=inside[0] if inside else None,last=inside[-1] if inside else None,max_root_backlog_bytes=max((r['root']['backlog'] for r in inside),default=None),max_root_qlen=max((r['root']['qlen'] for r in inside),default=None))


def classify(gap,delta,all_control_out,identity_stable):
    if not delta['pairs']:return 'insufficient_counter_pairs'
    if not identity_stable:return 'selector_socket_association_withheld'
    if all_control_out:return 'other_source_control_observations_present'
    if delta['totals']['pass_packets']>0:return 'pass_counter_growth_without_source_control_tap'
    if gap['classification']=='selected_send_counters_increased_without_old_flow_egress_observation':return 'provider_growth_without_pass_counter_growth'
    return 'selected_counters_flat_not_udp_absence_proof'


def analyze(run,flow):
    report=json.loads((run/'run.json').read_text());common_clock(report['clock_namespace_proof'])
    if report['status']=='running' or report['clock_namespace_proof']['operator']!=flow['clock_proof']:raise ValueError('requires closed common-clock-associated run')
    peers=json.loads((run/'network.json').read_text())['addresses'];providers=summarize_run(run);summaries={};rows={};hashes={}
    for role in ('operator','robot'):
        if digest(run/(role+'.mono'))!=flow['native_sha256'][role]:raise ValueError('native hash mismatch')
        p=run/(role+'-qdisc-samples.jsonl');before=digest(p);summaries[role]=summarize(p);rows[role]=[json.loads(line) for line in p.read_text().splitlines()]
        if rows[role][0]['begin_ns']>flow['active_ns'][0] or rows[role][-1]['end_ns']<flow['active_ns'][1]:raise ValueError('qdisc observer coverage insufficient')
        if digest(p)!=before:raise ValueError('qdisc file changed')
        hashes[role]=dict(samples_sha256=before,status_sha256=digest(p.with_suffix('.status.json')))
    gaps=[]
    for gap in flow['gaps']:
        role=gap['sender_role'];start,end=gap['window_ns'];delta=inside_deltas(rows[role],start,end);all_out=0
        for row in records(run/(role+'.mono')):
            if start<row['monotonic_ns']<end:
                value=parse_control(row,peers[role],report['monotonic_captures']['statuses'][role]['mtu'])
                if value and value['direction']=='out':all_out+=1
        observed=[r for name,result in providers.items() if name.startswith(role+'-') for r in result['records'] if r['begin_ns']<end and r['end_ns']>start]
        identity=gap.get('sender_identity');stable=bool(identity and observed and all(r['available'] and list(connection(r))==identity for r in observed))
        gaps.append(dict(sender=role,window_ns=[start,end],gap_ns=end-start,provider_classification=gap['classification'],identity_stable=stable,all_source_control_out=all_out,qdisc=delta,classification=classify(gap,delta,all_out,stable)))
    if any(digest(run/(role+'.mono'))!=flow['native_sha256'][role] for role in ('operator','robot')):raise ValueError('native file changed during analysis')
    return dict(summaries=summaries,qdisc_sha256=hashes,gaps=gaps,
                scope='aggregate UDP CONTROL peer/port software PASS executions, not authenticated socket/per-packet identity; placement only qualified in recorded synthetic fixture; root counters whole-interface, backlog/qlen gauges; paired reads wholly inside gaps; observer changes processing path and adds work; no unique drop, physical delivery, nonexecution or performance proof')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--flow',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();args.out.write_text(json.dumps(analyze(args.run,json.loads(args.flow.read_text())),indent=2)+'\n')
