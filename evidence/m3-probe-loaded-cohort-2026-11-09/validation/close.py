"""Compact acceptance-focused closure; raw streams stay intact and hashed."""
import json,sys,subprocess
from collections import Counter
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_runtime_layout import matched
from m3_dds_result_timeline import common_clock

out=ROOT/'evidence/m3-probe-loaded-cohort-2026-11-09';base=ROOT/'.local/m3-probe-loaded-cohort-2026-11-09';e=json.loads((base/'execution.json').read_text());manifest=json.loads((out/'local-artifact-hashes.json').read_text());preflight=json.loads((out/'preflight.json').read_text())
assert e['runtime_unchanged'] and e['matched_after']==e['runtime_layout']==preflight['layout']==matched(ROOT,'probe-tracing')
assert all(sha(ROOT/n)==h for n,h in preflight['observer_sha256'].items())
assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest.items());rows=[];owned=[];proofs={};lifecycle_rows={};examples=[]
for item in e['rows']:
    assert item['status']=='passed' and item['exit_code']==0
    run=ROOT/item['run'];d=json.loads((run/'run.json').read_text());assert all(sha(ROOT/n)==h for n,h in d['source_sha256'].items());common_clock(d['clock_namespace_proof'])
    assert not (run/'passphrase').exists();network=json.loads((run/'network.json').read_text());owned.append(network['network'])
    for role in ('operator','robot'):
        def config(path):return [{k:r.get(k) for k in ('kind','handle','parent','root','options')} for r in json.loads(path.read_text())]
        assert config(run/('before-'+role+'.log'))==config(run/('after-'+role+'.log'))
        assert json.loads((run/('features-before-'+role+'.log')).read_text())==json.loads((run/('features-after-'+role+'.log')).read_text())
    p=d['probe_diagnostics'];events=p['events'];interval=d['results']['publication_interval'];start,end=interval['resume_monotonic_ns'],interval['pause_monotonic_ns']
    rejected=[x for x in events if x['point']==53 and x['detail']==10 and x['value']==15]
    def why(x):return 'no_pending' if not x['probe_pending_before'] else 'different_pending_echo' if x['probe_pending_before']!=x['probe_t1'] else 'reply_age_timeout' if x['evaluated_ns']-x['probe_t1']>=2000000000 else 'unclassified'
    assert all(why(x)!='unclassified' for x in rejected)
    compact=[];waits=[];downstream=[];accepted_rtt=[];rejected_rtt=[]
    for l in p['lifecycles']:
        a=l['attempt'];sdk=[x for x in l['sdk'] if x['value']==0];reply_sdk=[x for x in l['reply_sdk'] if x['value']==0]
        assert len(sdk)==len(reply_sdk)==len(l['peer_admission'])==len(l['reply_admission'])==len(l['reply_queue'])==1
        local_wait=sdk[0]['evaluated_ns']-l['queue']['evaluated_ns'];peer_wait=reply_sdk[0]['evaluated_ns']-l['reply_queue'][0]['evaluated_ns'];waits.extend((local_wait,peer_wait))
        arrival=l['peer_admission'][0]['evaluated_ns'];delay=arrival-sdk[0]['probe_end_ns'];downstream.append(delay)
        r=l['reply_admission'][0];rtt=r['evaluated_ns']-r['probe_t1'];(accepted_rtt if r['probe_mapper_submitted'] and r['clock_error']==0 else rejected_rtt).append(rtt)
        compact.append(dict(owner_epoch=a['owner_epoch'],session=a['session'],control_generation=a['control_generation'],management_sequence=a['request_sequence'],t1=a['probe_t1'],attempt_inside_source_window=start<=a['evaluated_ns']<=end,local_queue_to_sdk_ns=local_wait,reply_queue_to_sdk_ns=peer_wait,sdk_call_end_to_peer_admission_ns=delay,round_trip_ns=rtt,reply_error=r['value'],mapper_submitted=r['probe_mapper_submitted'],clock_error=r['clock_error'],pending_before_reply=r['probe_pending_before'],pending_after_reply=r['probe_pending_after'],rejection_reason=why(r) if r['value']==15 else None))
    if rejected:
        for chosen in (min((l for l in p['lifecycles'] if l['reply_admission'][0]['value']==15),key=lambda l:l['reply_admission'][0]['evaluated_ns']-l['attempt']['probe_t1']),max((l for l in p['lifecycles'] if l['qualified_mapper_admissions']),key=lambda l:l['reply_admission'][0]['evaluated_ns']-l['attempt']['probe_t1'])):examples.append(dict(label=item['slot']['label'],lifecycle=chosen))
    trace_counts={str(point):sum(x['point']==point for x in events) for point in range(50,55)}
    row=dict(label=item['slot']['label'],run=item['run'],harness_status=d['status'],exit_code=item['exit_code'],strict_success=item['analysis']['progress']['audit']['all_succeeded'],durable_complete=item['analysis']['durable_outcomes']['complete'],commands=item['analysis']['progress']['audit'],skipped_offers=item['analysis']['progress']['skipped_slots'],probe_counts=trace_counts,probe_attempt_results=dict(Counter(x['value'] for x in events if x['point']==50)),reply_results=dict(Counter(x['value'] for x in events if x['point']==53 and x['detail']==10)),reply_rejection_reasons=dict(Counter(why(x) for x in rejected)),sdk_results=dict(Counter(x['value'] for x in events if x['point']==52)),qualified_mapper_admissions=sum(l['qualified_mapper_admissions'] for l in p['lifecycles']),emitted_probe_lifecycles=len(compact),emitted_inside_source_window=sum(x['attempt_inside_source_window'] for x in compact),maximum_queue_to_sdk_ns=max(waits),maximum_sdk_call_end_to_peer_admission_ns=max(downstream),maximum_qualified_round_trip_ns=max(accepted_rtt),minimum_rejected_round_trip_ns=min(rejected_rtt,default=None),maximum_round_trip_ns=max(accepted_rtt+rejected_rtt),sender_clock_events=[x for x in d['sender_diagnostics']['events'] if x['point']==45],sensor=d['measurement_window'],packet_capture_gate=d['pcap_population_reconciled'],active_context_events=len(item['analysis']['active_context_events']),scope='Probe totals cover all recorded incarnations/setup/drain; source-window membership is separate. Delay subtraction uses recorded common VM clock. SDK acceptance is not UDP delivery; downstream interval includes SRT/ordered delivery/owner admission, not unique network causality.')
    assert row['strict_success'] and row['durable_complete'] and row['packet_capture_gate'];rows.append(row);proofs[row['label']]=item['analysis']['progress']['entries'];lifecycle_rows[row['label']]=compact
assert all(sha(ROOT/n)==v['sha256'] for n,v in manifest.items())
prior=0
for folder,value in preflight['prior_raw'].items():
    p=ROOT/'evidence'/folder/'local-artifact-hashes.json';assert sha(p)==value['manifest_sha256'];entries=json.loads(p.read_text());assert all(sha(ROOT/n)==v['sha256'] for n,v in entries.items());prior+=len(entries)
containers=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines();nets=subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines();assert not any(c.startswith(n) for c in containers for n in owned) and not set(owned)&set(nets)
write(out/'gate-report.json',dict(source_commit=e['source_commit'],rows=rows,instrumentation_loop_closed=True,scope='One bounded diagnostic cohort; not full M3 qualification. Next implementation: authoritative per-command drop receipt and conservative journal reconciliation, not more probe/ARP instrumentation.'))
write(out/'command-proofs.json',proofs);write(out/'probe-lifecycles.json',lifecycle_rows);write(out/'probe-examples.json',examples)
write(out/'cleanup.json',dict(owned_networks=owned,containers_and_networks_removed=True,credentials_removed=True,roots_and_features_restored=True))
write(out/'binary-verification.json',dict(matched_before=preflight['layout'],matched_after=matched(ROOT,'probe-tracing'),observers=preflight['observer_sha256']))
write(out/'public-disposition.json',{n:dict(raw_sha256=v['sha256'],kind='local_only_raw',public_derivation=['gate-report.json','command-proofs.json','probe-lifecycles.json','probe-examples.json'],omission='Full raw streams/reports retained locally; no selected raw copy is claimed complete. All attempts and probe lifecycle summaries retained; two representative full probe joins public.') for n,v in manifest.items()})
write(out/'validation/results.json',dict(host_tests=398,exact_sdk79_ros41_qualification_reused=True,new_raw_verified=len(manifest),prior_raw_verified=prior,no_runtime_rebuild=True,no_heavy_work_during_capture=True,no_tuning=True,no_forced_expiry=True,no_historical118_replay=True,no_retry=True,instrumentation_loop_closed=True,m3_complete=False))
print('Closed bounded cohort:',[(r['label'],r['commands']['confirmed_successes'],r['reply_rejection_reasons']) for r in rows],len(manifest),'newraw,',prior,'priorraw; next=reconciliation implementation')
