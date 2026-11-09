"""Read-only fixed-window diagnosis; outer headers never identify probe echoes."""
import json,struct,subprocess,sys
from collections import Counter
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_monotonic_capture import records
from m3_control_liveness import parse_control,summarize_flows
from m3_provider_stats import summarize_run
from m3_control_fault_analysis import baseline,connection,inside_deltas
from m3_runtime_layout import matched
from m3_dds_result_timeline import common_clock
from m3_qdisc_gap_analysis import inside_deltas as root_deltas


def prefix_bounds(groups):
    """Necessary native prefix availability, not application delivery times.

    Caller must establish the first current-flow DATA sequence/message from both
    native captures. No wrap interpolation or inference through missing packets.
    """
    if not groups:return []
    low,high=min(groups),max(groups)
    if high-low>100000:raise ValueError('wrap or excessive sequence span')
    maximum=0;limiting=None;missing=[];result=[]
    for seq in range(low,high+1):
        if seq not in groups:missing.append(seq);continue
        value=groups[seq]
        if value['first_ns']>maximum:maximum=value['first_ns'];limiting=seq
        result.append(dict(sequence=seq,**value,prefix_available_ns=None if missing else maximum,
            limiting_sequence=None if missing else limiting,missing_predecessors=list(missing),
            minimum_native_prefix_wait_ns=None if missing else maximum-value['first_ns']))
    return result


def guards():
    a=prefix_bounds({1:dict(first_ns=10),2:dict(first_ns=40),3:dict(first_ns=20)})
    assert a[-1]['prefix_available_ns']==40 and a[-1]['minimum_native_prefix_wait_ns']==20 and a[-1]['limiting_sequence']==2
    b=prefix_bounds({1:dict(first_ns=10),3:dict(first_ns=20)})
    assert b[-1]['prefix_available_ns'] is None and b[-1]['missing_predecessors']==[2]
    try:prefix_bounds({0:dict(first_ns=1),2**31-1:dict(first_ns=2)})
    except ValueError:pass
    else:raise AssertionError('wrap interpolation accepted')


guards()
out=ROOT/'evidence/m3-intent3-probe-gap-2026-11-09';cohort=ROOT/'evidence/m3-sender-loaded-repair-cohort-2026-11-09'
manifest=json.loads((cohort/'local-artifact-hashes.json').read_text());run=ROOT/'.local/m3/20261109T135531879199Z';data=json.loads((run/'run.json').read_text())
layout=matched(ROOT,'sender-visibility');assert layout==data['runtime_layout']
assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest.items())
assert all(sha(ROOT/n)==h for n,h in data['source_sha256'].items())
clock=json.loads((cohort/'analysis/sender-N5-1701-deferrals.json').read_text())['clock_groups'][0];assert clock['number']==3
old,new=[c['event']['probe_anchor_ns'] for c in clock['clock_checks']];deferred,recovered=[c['event']['evaluated_ns'] for c in clock['clock_checks']]
start,end=old-2000000000,new+2000000000;common_clock(data['clock_namespace_proof'])
addresses=json.loads((run/'network.json').read_text())['addresses'];stats=summarize_run(run)
selected={role:baseline({n:v for n,v in stats.items() if n.startswith(role+'-')},old) for role in addresses}
assert selected['operator'][1]['session']==selected['robot'][1]['session']==clock['proof']['sender']['session']
controls={};groups={};provider={}
for role,address in addresses.items():
    status=data['monotonic_captures']['statuses'][role];assert status['complete'] and status['artifact_version']==2 and status['time_namespace_zero'] and not status['reserve_failed'] and not status['copy_failed']
    assert status['ready_ns']<start<end<status['stop_before_ns'];mtu=status['mtu'];rows=[];incoming={};outgoing={};count=0
    peer='robot' if role=='operator' else 'operator';local_socket=selected[role][1]['socket'];peer_socket=selected[peer][1]['socket']
    for raw in records(run/(role+'.mono')):
        count+=1
        if raw['monotonic_ns']>end:continue
        value=parse_control(raw,address,mtu)
        if not value:continue
        if value['direction']=='in':valid=value['source']==addresses[peer] and value['destination']==address and value['destination_socket_id']==local_socket
        else:valid=value['source']==address and value['destination']==addresses[peer] and value['destination_socket_id']==peer_socket
        if not valid:continue
        if value['kind']=='data':
            offset=14+(raw['prefix'][14]&15)*4+8;seq,msg,stamp,_=struct.unpack_from('!IIII',raw['prefix'],offset)
            value.update(sequence=seq,message_number=msg&0x3ffffff,boundary=(msg>>30)&3,in_order=bool(msg&(1<<29)),retransmitted=bool(msg&(1<<26)),wire_timestamp_us=stamp,udp_bytes=struct.unpack_from('!H',raw['prefix'],offset-4)[0])
            assert value['in_order']
            group=incoming if value['direction']=='in' else outgoing
            g=group.setdefault(seq,dict(first_ns=value['monotonic_ns'],last_ns=value['monotonic_ns'],message_number=value['message_number'],udp_bytes=value['udp_bytes'],boundary=value['boundary'],observations=0,retransmission_observations=0))
            assert g['message_number']==value['message_number'] and g['udp_bytes']==value['udp_bytes'] and g['boundary']==value['boundary']
            g['last_ns']=value['monotonic_ns'];g['observations']+=1;g['retransmission_observations']+=value['retransmitted']
        if start<=value['monotonic_ns']<=end:rows.append(value)
    assert count==status['records']==status['seen']==status['submitted'];controls[role]=rows;groups[role]=dict(incoming=incoming,outgoing=outgoing)
    name,base=selected[role];reads=[r for r in stats[name]['records'] if start<=r['begin_ns'] and r['end_ns']<=end]
    assert reads and all(r['available'] and connection(r)==connection(base) and r['session']==base['session'] for r in reads)
    provider[role]=dict(process=name,identity=list(connection(base)),reads=reads,
        maximum_sample_start_gap_ns=max(b['begin_ns']-a['begin_ns'] for a,b in zip(reads,reads[1:])),
        renewal_interval=inside_deltas(stats[name]['records'],connection(base),old,new))
for role in addresses:
    peer='robot' if role=='operator' else 'operator';a=groups[role]['incoming'];b=groups[peer]['outgoing']
    assert min(a)==min(b) and a[min(a)]['message_number']==b[min(b)]['message_number']==1
    groups[role]['ordered_prefix_bounds']=prefix_bounds(a)
candidates=[r for r in groups['operator']['ordered_prefix_bounds'] if r['udp_bytes']==157 and start<=r['first_ns']<=end]
blocked=[r for r in candidates if r['minimum_native_prefix_wait_ns'] is not None and r['minimum_native_prefix_wait_ns']>=2000000000]
assert len(blocked)==1 and blocked[0]['sequence']==608997443 and blocked[0]['minimum_native_prefix_wait_ns']==2210035668
recovery_candidates=[r for r in candidates if 0<new-r['first_ns']<=5000000];assert len(recovery_candidates)==1 and recovery_candidates[0]['sequence']==608997455
arp={role:[x for x in v['lifetimes'] if x['created_ns']<=end and x['terminal_ns']>=start] for role,v in data['arp_packet_diagnostics'].items()};assert all(not v for v in arp.values())
neighbors={};qdisc={}
for role in addresses:
    peer='robot' if role=='operator' else 'operator'
    rows=[json.loads(line) for line in (run/(role+'-neighbor-samples.jsonl')).read_text().splitlines()]
    rows=[r for r in rows if start<=r['begin_ns'] and r['end_ns']<=end]
    assert rows and all(r['error'] is None for r in rows)
    entries=[e for r in rows for e in r['entries'] if e['dst']==addresses[peer]]
    assert len(entries)==len(rows)
    neighbors[role]=dict(reads=rows,states=sorted({s for e in entries for s in e['state']}),macs=sorted({e['lladdr'] for e in entries}),scope='Sampled neighbor identity/state only; no continuous kernel-state proof')
    qrows=[json.loads(line) for line in (run/(role+'-qdisc-samples.jsonl')).read_text().splitlines()]
    qdisc[role]=dict(context=root_deltas(qrows,start,end),scope='Whole-interface root counters; contained pairs only, not per-probe drops or a sum of parent/child counters')
activity=[dict(file=n,**e) for n,t in data['command_diagnostics'].items() for e in t['events'] if start<=e['monotonic_ns']<=end]
assert not any(e['point'] in (2,3,4,31) or (e['point']==30 and e['detail']&1) for e in activity)
source_names=['src/robotweax_srt_bridge_core/src/session.cpp','src/robotweax_srt_bridge_core/src/transport/transport.cpp','src/robotweax_srt_bridge_core/src/clock.cpp','src/robotweax_srt_bridge_core/src/queues.cpp','proto/management_v1.proto','.deps/srt/src/codec.cpp','.deps/srt/src/compat/transport_runtime.cpp','.deps/srt/src/receive_buffer.cpp','.deps/srt/docs/control-profile.md','.deps/srt/include/robotweax/srt/crypto.hpp']
assert subprocess.check_output(['git','-C',str(ROOT/'.deps/srt'),'rev-parse','HEAD'],text=True).strip()=='52be7c86ee1f303cbb0c8718c364217e4dd97a36'
assert not subprocess.check_output(['git','-C',str(ROOT/'.deps/srt'),'status','--porcelain'],text=True).strip()
write(out/'analysis.json',dict(run=str(run.relative_to(ROOT)),window_ns=[start,end],accepted_probe_anchor_gap_ns=new-old,age_at_first_deferral_ns=deferred-old,deferral_to_recovery_ns=recovered-deferred,
    clock_group=clock,control_outer_headers=controls,flow_summaries={r:summarize_flows(v,start,end,deferred) for r,v in controls.items()},sequence_groups=groups,provider=provider,
    reply_length_candidates=candidates,reply_length_candidate_blocked_beyond_probe_timeout=blocked,recovery_length_candidate=recovery_candidates,
    arp_lifetimes_intersecting_window=arp,neighbor_context=neighbors,qdisc_context=qdisc,command_activity_counts={str(p):sum(e['point']==p for e in activity) for p in sorted({e['point'] for e in activity})},source_sha256={n:sha(ROOT/n) for n in source_names},
    scope='Outer-header/length-compatible candidates only: no decryption, echo binding, actual SDK delivery/read timestamp or exact probe_not_pending count. Native prefix bound is necessary availability, not authenticated packet admission. Owner samples exclude a whole-gap stall, not shorter scheduling/receive backpressure. No unique network or historical118 cause.'))
assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest.items()) and layout==matched(ROOT,'sender-visibility')
prior_count=0
for folder in ('m3-start-broader-seeds-2026-11-09','m3-sender-visibility-2026-11-09','m3-sender-loaded-cohort-2026-11-09'):
    prior=json.loads((ROOT/'evidence'/folder/'local-artifact-hashes.json').read_text());assert all(sha(ROOT/n)==v['sha256'] for n,v in prior.items());prior_count+=len(prior)
write(out/'validation.json',dict(raw_manifest=str((cohort/'local-artifact-hashes.json').relative_to(ROOT)),raw_manifest_sha256=sha(cohort/'local-artifact-hashes.json'),raw_files_verified_before_and_after=len(manifest),other_prior_raw_verified=prior_count,source_matches_captured=True,provider_clean=True,runtime_unchanged=True,ordering_contract_guards_passed=True,new_runs=0,tuning=False,forced_expiry=False,command_replay=False))
print('Read-only accepted-probe gap6867115920ns, reply-sized prefix wait2210035668ns, owner sampling active; exact echo unavailable')
