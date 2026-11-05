"""Summaries retain unknown/censored populations instead of treating them as successes."""
import json
import math
from pathlib import Path


def percentiles(values):
    values=sorted(values)
    return dict(count=len(values),**{label:(values[max(0,math.ceil(len(values)*fraction)-1)] if values else None)
        for label,fraction in [('p50',.50),('p95',.95),('p99',.99),('maximum',1)]})


def summarize_resources(path):
    rows=[json.loads(line) for line in Path(path).read_text().splitlines() if line]
    history={};cpu_seconds=0;peak_rss=0
    for row in rows:
        peak_rss=max(peak_rss,sum(p['rss_bytes'] for p in row['processes']))
        for p in row['processes']:
            identity=(p['pid'],p['start_ticks'])
            previous=history.get(identity)
            if previous is not None:
                if p['cpu_ticks']<previous:raise ValueError('CPU ticks regressed')
                cpu_seconds+=(p['cpu_ticks']-previous)/row['clock_ticks_per_second']
            history[identity]=p['cpu_ticks']
    span=(rows[-1]['monotonic_ns']-rows[0]['monotonic_ns'])/1e9 if len(rows)>1 else 0
    return dict(samples=len(rows),observed_seconds=span,cpu_seconds=cpu_seconds,
        average_cpu_core_percent=cpu_seconds/span*100 if span else None,maximum_sum_rss_bytes=peak_rss,
        scope='process CPU deltas between observations; startup/exit tails unobserved; RSS sum can double-count shared pages')


def summarize_commands(commands):
    finalized=[c for c in commands if 'result_observed_monotonic_ns' in c]
    groups={}
    for c in finalized:
        key=str(c['terminal'])+'/'+str(c['reason'])
        groups.setdefault(key,[]).append((c['result_observed_monotonic_ns']-c['submitted_monotonic_ns'])/1e6)
    return dict(attempts=len(commands),not_admitted=sum(c.get('terminal')=='not_admitted' for c in commands),
        unresolved=sum('terminal' not in c for c in commands),
        terminal_observation_latency_ms=percentiles([(c['result_observed_monotonic_ns']-c['submitted_monotonic_ns'])/1e6 for c in finalized]),
        by_state_reason={key:percentiles(values) for key,values in groups.items()},
        scope='local Execute invocation to terminal status observation; includes up to 200ms status polling; unresolved attempts excluded and counted separately')
