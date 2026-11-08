#!/usr/bin/env python3
"""Closed SENSOR API snapshots; aggregate counters are not internal reason events."""
import argparse
import json
from pathlib import Path
from m3_source_preflight import ROOT,sha
from m3_provider_stats import summarize_run,SENSOR_COUNTERS,SENSOR_GAUGES,SENSOR_UNAVAILABLE_DIMENSIONS
from m3_control_fault_analysis import ARCHIVE,connection
from m3_dds_result_timeline import common_clock


def connection_windows(rows,start,end):
    if not 0<start<end:raise ValueError('invalid source interval')
    groups={}
    for row in rows:
        if not row['available']:continue
        identity=connection(row)
        g=groups.setdefault(identity,dict(identity=list(identity),sessions=[],available_records=0,first_read_ns=None,last_read_ns=None,last_cumulative={},gauges={},before_close_records=0,contained_pairs=0,contained_pair_totals={k:0 for k in SENSOR_COUNTERS},contained_first_read_ns=None,contained_last_read_ns=None))
        if row['session'] not in g['sessions']:g['sessions'].append(row['session'])
        g['available_records']+=1;g['before_close_records']+=row['before_close']
        if g['first_read_ns'] is None:g['first_read_ns']=[row['begin_ns'],row['end_ns']]
        g['last_read_ns']=[row['begin_ns'],row['end_ns']];g['last_cumulative']={k:row[k] for k in SENSOR_COUNTERS}
        for key in SENSOR_GAUGES:
            old=g['gauges'].get(key,[row[key],row[key]])
            g['gauges'][key]=[min(old[0],row[key]),max(old[1],row[key])]
    for previous,current in zip(rows,rows[1:]):
        if not all(r['available'] and start<=r['begin_ns']<=r['end_ns']<=end for r in (previous,current)):continue
        if connection(previous)!=connection(current):continue
        g=groups[connection(current)];g['contained_pairs']+=1
        if g['contained_first_read_ns'] is None:g['contained_first_read_ns']=[previous['begin_ns'],previous['end_ns']]
        g['contained_last_read_ns']=[current['begin_ns'],current['end_ns']]
        for key in SENSOR_COUNTERS:
            delta=current[key]-previous[key]
            if delta<0:raise ValueError('provider counter regression')
            g['contained_pair_totals'][key]+=delta
    return list(groups.values())


def analyze(run):
    run=run.resolve();paths=[run/'run.json',*sorted(run.glob('*-bridge-*.log'))]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in paths}
    report=json.loads(paths[0].read_text())
    if report['status']=='running' or not report.get('sensor_provider_diagnostics_enabled'):raise ValueError('requires closed SENSOR instrumented run')
    if report.get('srt_archive_sha256')!=ARCHIVE:raise ValueError('provider counter semantics pin mismatch')
    common_clock(report['clock_namespace_proof']);stats=summarize_run(run,sensor=True)
    window=report['results']['publication_interval'];start=window['resume_monotonic_ns'];end=window['pause_monotonic_ns']
    selected={name:dict(complete=s['complete'],connections=connection_windows(s['records'],start,end),potentially_saturated={key:v['potentially_saturated'] for key,v in s['connections'].items()},unavailable=s['unavailable'],status=s['status'],max_sample_start_gap_ns=s['max_sample_start_gap_ns'],max_read_duration_ns=s['max_read_duration_ns']) for name,s in stats.items()}
    if any(sha(ROOT/p)!=h for p,h in hashes.items()):raise ValueError('analysis input changed')
    return dict(run=str(run.relative_to(ROOT)),original_harness_status=report['status'],source_window_ns=[start,end],processes=selected,raw_sha256=hashes,unavailable_dimensions=SENSOR_UNAVAILABLE_DIMENSIONS,scope='Lifetime last counters and smoothed gauge min/max are separate from fully-contained adjacent-read deltas. Unavailable gaps/new identities are never bridged. These partial deltas omit boundary/gap increments; saturation can hide growth. DATA includes provider packet/filter semantics, unique includes accepted FEC recovery; none is typed SAMPLE emission/delivery or a reason-specific retirement/insert event.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():p.error('output already exists')
    try:d=dict(status='passed',analysis=analyze(a.run))
    except Exception as e:d=dict(status='failed',error=str(e))
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(d['status']);raise SystemExit(d['status']!='passed')
