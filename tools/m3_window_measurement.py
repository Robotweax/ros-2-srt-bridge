"""Conditional, bounded window accounting; never interpolates process CPU ticks."""
import json
from pathlib import Path


def read_samples(path):return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def select_window(samples,start,end):
    if end<=start:raise ValueError('invalid source window')
    before=[i for i,s in enumerate(samples) if s['end_ns']<=start]
    after=[i for i,s in enumerate(samples) if s['begin_ns']>=end]
    if not before or not after:raise ValueError('window not bracketed by samples')
    selected=samples[before[-1]:after[0]+1]
    if len(selected)<4:raise ValueError('insufficient window samples')
    for a,b in zip(selected,selected[1:]):
        if a['end_ns']>=b['begin_ns']:raise ValueError('overlapping/regressed sampling time')
        if b['begin_ns']-a['begin_ns']>1000000000:raise ValueError('sampling gap over one second')
    if any(s['begin_ns']>s['end_ns'] for s in selected):raise ValueError('invalid read bracket')
    return selected


def summarize_cpu(samples,start,end):
    result=dict(qualified=False,window_monotonic_ns=[start,end],
        scope='observed endpoint process trees including test observer/sampler; excludes capture/competitor; inner/outer tick deltas without interpolation; unobserved short-lived children not covered')
    try:
        selected=select_window(samples,start,end)
        if any(s['errors'] for s in selected):raise ValueError('process read failed in window bracket')
        maps=[{(p['label'],p['pid'],p['start_ticks']):p for p in s['processes']} for s in selected]
        if not maps[0] or any(set(m)!=set(maps[0]) for m in maps):raise ValueError('observed process identities changed')
        hz=selected[0]['hz']
        if hz<=0 or any(s['hz']!=hz for s in selected):raise ValueError('clock tick frequency changed')
        inner=[i for i,s in enumerate(selected) if s['begin_ns']>=start and s['end_ns']<=end]
        if len(inner)<2:raise ValueError('insufficient inner observations')
        processes=[]
        for identity in sorted(maps[0]):
            if any(m[identity]['cpu_ticks']<0 or m[identity]['rss_bytes']<0 for m in maps):raise ValueError('negative process counter')
            ticks=[m[identity]['cpu_ticks'] for m in maps]
            if len({m[identity]['waited_child_cpu_ticks'] for m in maps})!=1:raise ValueError('reaped-child CPU changed; transient/retired work not fully observed')
            if any(b<a for a,b in zip(ticks,ticks[1:])):raise ValueError('CPU ticks regressed')
            row=dict(label=identity[0],pid=identity[1],start_ticks=identity[2],
                inner_cpu_seconds=(ticks[inner[-1]]-ticks[inner[0]])/hz,
                outer_cpu_seconds=(ticks[-1]-ticks[0])/hz,
                maximum_observed_rss_bytes=max(maps[i][identity]['rss_bytes'] for i in inner))
            processes.append(row)
        span=(end-start)/1e9
        result.update(qualified=True,processes=processes,tick_resolution_seconds=1/hz,
            inner_observation_span_ns=[selected[inner[0]]['begin_ns'],selected[inner[-1]]['end_ns']],
            outer_observation_span_ns=[selected[0]['begin_ns'],selected[-1]['end_ns']],
            inner_cpu_seconds=sum(p['inner_cpu_seconds'] for p in processes),outer_cpu_seconds=sum(p['outer_cpu_seconds'] for p in processes),
            maximum_observed_sum_rss_bytes=max(sum(p['rss_bytes'] for p in selected[i]['processes']) for i in inner),
            rss_scope='sampled RSS sum, can double-count shared pages; not peak allocation/PSS')
        result['inner_cpu_core_percent']=100*result['inner_cpu_seconds']/span
        result['outer_cpu_core_percent']=100*result['outer_cpu_seconds']/span
    except ValueError as error:result['reason']=str(error)
    return result


def summarize_cgroup(samples,start,end):
    result=dict(qualified=False,window_monotonic_ns=[start,end],
        scope='namespace-root cgroup v2 counters including applications, test observers, capture and competitor processes; excludes work accounted outside cgroup; inner/outer observed deltas without interpolation; not isolated transport/observer cost')
    try:
        selected=select_window(samples,start,end)
        groups=[s.get('cgroup',{}) for s in selected]
        if any(g.get('available') is not True for g in groups):raise ValueError('cgroup sample unavailable')
        if any(g['identity']!=groups[0]['identity'] or g['limits']!=groups[0]['limits'] for g in groups):raise ValueError('cgroup identity or limits changed')
        if any(g['memory_current_bytes']<0 for g in groups):raise ValueError('negative cgroup memory')
        for field in ('cpu','memory_events'):
            if any(set(g[field])!=set(groups[0][field]) for g in groups):raise ValueError('cgroup counter set changed')
            for key in groups[0][field]:
                values=[g[field][key] for g in groups]
                if any(v<0 for v in values) or any(b<a for a,b in zip(values,values[1:])):raise ValueError('cgroup counter regressed')
        if not {'usage_usec','user_usec','system_usec'}<=groups[0]['cpu'].keys():raise ValueError('missing cgroup CPU counters')
        inner=[i for i,s in enumerate(selected) if s['begin_ns']>=start and s['end_ns']<=end]
        if len(inner)<2:raise ValueError('insufficient inner cgroup samples')
        def delta(field,first,last):return {k:groups[last][field][k]-groups[first][field][k] for k in groups[0][field]}
        result.update(qualified=True,identity=groups[0]['identity'],limits=groups[0]['limits'],
            inner_cpu_deltas=delta('cpu',inner[0],inner[-1]),outer_cpu_deltas=delta('cpu',0,-1),
            inner_memory_event_deltas=delta('memory_events',inner[0],inner[-1]),outer_memory_event_deltas=delta('memory_events',0,-1),
            maximum_observed_memory_current_bytes=max(groups[i]['memory_current_bytes'] for i in inner),
            memory_scope='sampled charged cgroup memory including cache/kernel allocations; not RSS/PSS or a hard peak',
            inner_observation_span_ns=[selected[inner[0]]['begin_ns'],selected[inner[-1]]['end_ns']],
            outer_observation_span_ns=[selected[0]['begin_ns'],selected[-1]['end_ns']],cpu_counter_unit_seconds=1e-6)
        for side in ('inner','outer'):
            seconds=result[side+'_cpu_deltas']['usage_usec']/1e6
            result[side+'_cpu_seconds']=seconds;result[side+'_cpu_core_percent']=100*seconds/((end-start)/1e9)
    except ValueError as error:result['reason']=str(error)
    return result


def capture_window(samples,start,end,*,max_gap_ns=1000000000):
    """Realtime bounds conditional on no hidden step and <=1000ppm relative drift."""
    result=dict(qualified=False,window_monotonic_ns=[start,end],
        assumptions=f'no undetected realtime step between <={max_gap_ns/1000000:g}ms calibration observations; <=1000ppm relative drift; 1ms maximum observed step/read width; pcap timestamp quantization retained as boundary uncertainty')
    try:
        selected=select_window(samples,start,end)
        result['maximum_allowed_calibration_gap_ns']=max_gap_ns
        for s in selected:
            if s['wall_ns']-s['offset_max_ns']!=s['begin_ns'] or s['wall_ns']-s['offset_min_ns']>s['end_ns']:raise ValueError('inconsistent clock bracket')
            if not 0<=s['offset_max_ns']-s['offset_min_ns']<=1000000:raise ValueError('clock read bracket too wide')
        for a,b in zip(selected,selected[1:]):
            distance=max(0,a['offset_min_ns']-b['offset_max_ns'],b['offset_min_ns']-a['offset_max_ns'])
            if distance>1000000:raise ValueError('observed realtime offset step')
            elapsed=b['wall_ns']-b['offset_min_ns']-a['begin_ns']
            if elapsed>max_gap_ns:raise ValueError('clock calibration gap exceeds configured limit')
            if distance>(elapsed+999)//1000:raise ValueError('observed offset drift exceeds 1000ppm model')
        gap=max(b['wall_ns']-b['offset_min_ns']-a['begin_ns'] for a,b in zip(selected,selected[1:]))
        pad=(gap+999)//1000 # 1000ppm, rounded up
        lower=min(s['offset_min_ns'] for s in selected)-pad
        upper=max(s['offset_max_ns'] for s in selected)+pad
        bounds=[start+lower,start+upper,end+lower,end+upper]
        if bounds[1]>=bounds[2]:raise ValueError('clock envelope wider than measurement window')
        result.update(qualified=True,timestamp_bounds_ns=bounds,offset_envelope_ns=[lower,upper],
            max_sample_gap_ns=gap,drift_padding_ns=pad,samples=len(selected))
    except ValueError as error:result['reason']=str(error)
    return result


def summarize_endpoints(run,windows,*,require_dedicated=False):
    run=Path(run);samples={role:read_samples(run/(role+'-endpoint-samples.jsonl')) for role in ('robot','operator')}
    result={}
    for name,window in windows.items():
        start,end=window
        cpu={role:summarize_cpu(rows,start,end) for role,rows in samples.items()}
        clock_paths={role:run/(role+'-clock-samples.jsonl') for role in samples}
        clocks={role:capture_window(read_samples(path) if path.exists() else samples[role],start,end,
            max_gap_ns=100000000 if path.exists() else 1000000000) for role,path in clock_paths.items()}
        for role,path in clock_paths.items():
            clocks[role]['sample_source']='dedicated-clock' if path.exists() else 'legacy-process-clock'
            if require_dedicated and not path.exists():clocks[role]=dict(qualified=False,reason='dedicated clock samples missing',sample_source='missing')
        wire=dict(qualified=all(c['qualified'] for c in clocks.values()),calibrations=clocks)
        if wire['qualified']:
            low=min(c['offset_envelope_ns'][0] for c in clocks.values());high=max(c['offset_envelope_ns'][1] for c in clocks.values())
            wire['timestamp_bounds_ns']=[start+low,start+high,end+low,end+high]
        result[name]=dict(monotonic_ns=[start,end],seconds=(end-start)/1e9,cpu=cpu,container_cgroup={role:summarize_cgroup(rows,start,end) for role,rows in samples.items()},wire_clock=wire)
    return dict(windows=result,scope='same phase definitions for SRT/DDS; includes observers/coordination overhead, excludes capture/competitor; conditional clock mapping; not isolated transport cost')
