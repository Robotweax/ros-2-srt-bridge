#!/usr/bin/env python3
"""Read-only N5 SENSOR assessment of the frozen probe cohort; never launches peers."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from m3_accounting import summarize_window
from m3_dds_result_timeline import common_clock
from m3_provider_stats import summarize_run,SENSOR_GAUGES
from m3_source_preflight import ROOT,sha,write

COHORT='evidence/m3-probe-loaded-cohort-2026-11-09'
SOURCE_FILES=('src/robotweax_srt_bridge_core/src/transport/transport.cpp',
    'src/robotweax_srt_bridge_core/src/queues.cpp',
    'src/robotweax_srt_bridge_core/include/robotweax/srt_bridge/queues.hpp',
    'ros2/robotweax_srt_bridge/src/bridge_node.cpp',
    'ros2/robotweax_srt_bridge/include/robotweax_srt_bridge/publication_metrics.hpp',
    'ros2/robotweax_srt_bridge_demo/scripts/m3_scenario.py')


def assess_publications(begin,end,interval):
    window=summarize_window(begin,end,interval)
    for phase in (begin,end):
        for role in ('sender','receiver'):
            s=phase[role]
            if not all(s[k] for k in ('ready','clock_qualified','sensor_qos_verified')) or s['fault'] or s['worker_fault']:raise ValueError('unqualified checkpoint')
        if phase['sender']['session_id']!=phase['receiver']['session_id']:raise ValueError('peer session mismatch')
    for role in ('sender','receiver'):
        for key in ('session_id','control_generation','sensor_generation'):
            if begin[role][key]!=end[role][key]:raise ValueError('checkpoint context changed')
    def delta(key):
        a,b=begin['receiver'][key],end['receiver'][key]
        if type(a) is not int or type(b) is not int or a<0 or b<a:raise ValueError('invalid rejection counter')
        return b-a
    unknown=delta('transport_samples_unknown_age');stale=delta('transport_samples_stale');rejected=delta('transport_samples_rejected')
    if unknown+stale>rejected:raise ValueError('age rejection subsets exceed all rejections')
    routes={}
    for route in ('imu','joint'):
        key=route+'_age_upper_max_ns';a,b=begin['receiver'][key],end['receiver'][key]
        if not 0<=a<=b<=250000000:raise ValueError('invalid or over-budget cumulative maximum')
        hist=window['age_upper_histograms'][route]
        if hist['count'] and hist['maximum_ms']>(b+999999)//1000000:raise ValueError('histogram exceeds cumulative maximum')
        if b>a and (not hist['count'] or hist['maximum_ms']!=(b+999999)//1000000):raise ValueError('new cumulative maximum not represented in window histogram')
        routes[route]=dict(histogram=hist,cumulative_begin_max_ns=a,cumulative_end_max_ns=b,
            exact_window_max_ns=b if b>a else None,
            exact_max_scope='new cumulative maximum belongs to checkpoint interval' if b>a else 'unchanged cumulative maximum cannot be assigned to window; use delta histogram',
            nonempty=hist['count']>0,freshness_gate='supported' if hist['count'] else 'unavailable_no_publications')
    return dict(window=window,publication_age=routes,
        populations=dict(source=window['source_produced'],sdk_accepted=end['sender']['sensor_sent']-begin['sender']['sensor_sent'],
            received=delta('transport_samples_received'),rejected=rejected,unknown_age_rejected=unknown,stale_rejected=stale,
            other_rejected_unclassified=rejected-unknown-stale,accepted_at_receive=delta('transport_samples_received')-rejected,
            published=window['published'],typed_observed=window['observer_received'],unobserved_source=window['missing']),
        checkpoint_occupancy={phase:{role:{key:data[role][key] for key in ('sensor_ingress_pending','sensor_outbound_pending','sensor_receive_pending')} for role in ('sender','receiver')} for phase,data in [('begin',begin),('end',end)]},
        observed_bridge_queue_high_water=None,
        scope='complete RPC checkpoint histogram deltas for all counted bridge publications, not per-packet ages, typed-observer arrival ages, physical source ages or continuous availability')


def provider_gauges(stats,start,end):
    result={}
    for name,s in stats.items():
        if not s['complete']:raise ValueError('incomplete provider observer')
        contained=[r for r in s['records'] if start<=r['begin_ns']<=r['end_ns']<=end]
        groups={}
        for row in contained:
            if not row['available']:continue
            key=':'.join(str(row[k]) for k in ('owner_epoch','generation','socket'))
            groups.setdefault(key,[]).append(row)
        result[name]=dict(status=s['status'],inside_reads=len(contained),unavailable_inside=sum(not r['available'] for r in contained),
            connections={key:dict(records=len(rows),first_read_ns=[rows[0]['begin_ns'],rows[0]['end_ns']],last_read_ns=[rows[-1]['begin_ns'],rows[-1]['end_ns']],
                gauges={k:dict(minimum=min(r[k] for r in rows),maximum=max(r[k] for r in rows)) for k in SENSOR_GAUGES}) for key,rows in groups.items()},
            hard_peak_qualified=False,scope='fully source-contained reads only; identities never merged; provider gauges are sampled/smoothed, not interval deltas or hard queue peaks; no connection means unavailable, not zero occupancy')
    return result


def analyze(out):
    cohort=ROOT/COHORT;gate=json.loads((cohort/'gate-report.json').read_text());manifest=json.loads((cohort/'local-artifact-hashes.json').read_text())
    for path,record in manifest.items():
        if sha(ROOT/path)!=record['sha256']:raise ValueError('retained raw artifact changed: '+path)
    outputs=[];source_proofs={}
    for selected in gate['rows']:
        run=ROOT/selected['run'];report=json.loads((run/'run.json').read_text());r=report['results']
        common_clock(report['clock_namespace_proof'])
        if report['status']!='passed' or report['runtime_layout']['name']!='probe-tracing' or not report['pcap_population_reconciled']:raise ValueError('original cohort/provenance mismatch')
        assessment=assess_publications(r['checkpoints']['begin'],r['checkpoints']['end'],r['publication_interval'])
        if assessment['window']!=report['measurement_window'] or assessment['window']!=selected['sensor']:raise ValueError('recomputed checkpoint deltas differ from original')
        if r['typed_errors'] or r['direct_dds_samples']:raise ValueError('typed/isolation error')
        if any('SAMPLE_TRACE_STATUS ' in p.read_text() for p in run.glob('*-bridge-*.log')):raise ValueError('unexpected sample trace; per-message scope requires separate analysis')
        stats=summarize_run(run,sensor=True);interval=r['publication_interval'];gauges=provider_gauges(stats,interval['resume_monotonic_ns'],interval['pause_monotonic_ns'])
        for path in SOURCE_FILES:
            blob=subprocess.check_output(['git','show',gate['source_commit']+':'+path],cwd=ROOT)
            h=hashlib.sha256(blob).hexdigest()
            if report['source_sha256'].get(path)!=h:raise ValueError('captured source differs from frozen Git blob: '+path)
            source_proofs[path]=dict(sha256=h,commit=gate['source_commit'])
        memory=report['endpoint_measurements']['windows']['source_enabled']
        sampled_memory={role:dict(qualified=m['qualified'],maximum_observed_sum_rss_bytes=m.get('maximum_observed_sum_rss_bytes'),scope=m['scope']) for role,m in memory['cpu'].items()}
        outputs.append(dict(label=selected['label'],run=selected['run'],profile=report['profile'],seed=report['seed'],source_commit=gate['source_commit'],runtime_layout=report['runtime_layout']['name'],
            source_window_ns=interval,assessment=assessment,provider_gauges=gauges,sampled_memory=sampled_memory,
            diagnostic_observation=r['diagnostic_observation'],diagnostic_scope='whole observed history with previous-state hold; not exact source-window clock availability',
            sample_trace_available=False,sample_trace_scope='no SAMPLE_TRACE_STATUS in these bridge logs; no per-SAMPLE rejection reason or receive-to-publication trace is available',
            checkpoints=r['checkpoints'],clock_assumptions=report['clock_assumptions'],clock_namespace_proof=report['clock_namespace_proof']))
    for path,record in manifest.items():
        if sha(ROOT/path)!=record['sha256']:raise ValueError('input changed during read-only assessment')
    result=dict(status='completed',read_only=True,original_raw_files_verified=len(manifest),source_cohort=COHORT,rows=outputs,captured_source_proofs=source_proofs,
        local_bridge_storage=dict(backing_slots_per_stage=8,active_sensor_routes=2,per_sensor_route_per_stage=1,stages=['ingress mailbox','outbound queue','receive mailbox'],
            qualification='structural fixed storage in frozen source, not measured continuous occupancy; transient stack copies/BIND/CONTROL/provider/RMW/kernel buffers outside this slot count'),
        sdk_configured_requests=dict(payload_bytes=1024,flow_control_packets=256,send_buffer_bytes=262144,receive_buffer_bytes=262144,udp_send_buffer_bytes=262144,udp_receive_buffer_bytes=262144,
            qualification='captured source requests with checked API return; no retained normalized option readbacks or hard internal allocator/FEC/kernel/RMW memory peak proof'),
        gate_scope='N5 publication-authorization age and balanced reductions on prior matched probe build; no newest-build promotion, lossless delivery, continuous availability or physical/hardware qualification')
    write(out/'assessment.json',result);write(out/'input-manifest.json',dict(original_manifest_sha256=sha(cohort/'local-artifact-hashes.json'),original_manifest=str((cohort/'local-artifact-hashes.json').relative_to(ROOT)),raw_files=manifest))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    result=analyze(out);print(json.dumps(dict(status=result['status'],runs=len(result['rows']),raw_files_verified=result['original_raw_files_verified'])))


if __name__=='__main__':main()
