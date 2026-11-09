"""Closed all-attempt joins for calibrated start tracing; no outcome authority."""
import json
from m3_source_preflight import ROOT,sha
from m3_n5_progress import command_progress
from m3_command_trace import summarize_run as command_traces
from m3_start_trace_analysis import summarize_run as start_traces


def join_attempt(entry,starts,admissions):
    a,b=entry['sender'],entry['receiver'];identity=entry['number'].to_bytes(16,'little').hex()
    if a and b and any(a[k]!=b[k] for k in ('route','payload_hash','session','source_epoch','source_ns')):raise ValueError('journal original context mismatch')
    if a and any(e['session']!=a['session'] or e['route']!=a['route'] or e['origin_ns']!=a['source_ns'] for e in admissions):raise ValueError('admission/journal original context mismatch')
    selected=[s for s in starts if s['identity']['request']==identity]
    if len(selected)>1:raise ValueError('multiple start groups for one intent')
    result=dict(number=entry['number'],terminal=entry['terminal'],sdk_handoffs=entry['sdk_handoffs'],sender=a,receiver=b,start=None,admission_clock_context=admissions,scope='Trace is diagnostic; closed journals and original audits retain outcome authority')
    if not selected:
        result['unavailable_reason']='no dispatched start observation; not nonexecution proof'
        if b and b['dispatched_ns']:raise ValueError('dispatched record lacks start observation')
        return result
    if not a or not b:raise ValueError('start group without both original journal records')
    start=selected[0];c=start['identity']
    if c['session']!=a['session'] or c['route']!=a['route'] or c['origin_ns']!=a['source_ns'] or c['owner_epoch']!=b['owner_epoch']:raise ValueError('start/journal original context mismatch')
    if not b['dispatched_ns']:raise ValueError('start without durable dispatch record')
    for e in start['events']:
        if e['command_deadline_ns']!=b['deadline_ns'] or e['entry_owner_epoch']!=b['owner_epoch']:raise ValueError('start/journal deadline or owner mismatch')
    worker=[e for e in start['events'] if e['point']==43];owner=[e for e in start['events'] if e['point']==41]
    if worker:
        w=worker[0]
        if w['terminal_state']!=b['state'] or w['terminal_reason']!=b['reason']:raise ValueError('worker observation disagrees with closed journal')
        result['actual_slack_ns']=dict(consume=w['consume_deadline_ns']-w['consume_ns'],second_gate=w['second_gate_deadline_ns']-w['second_gate_ns'] if w['second_gate_checked'] else None,command_budget_at_consume=b['deadline_ns']-w['consume_ns'],command_minus_grant=b['deadline_ns']-w['grant_deadline_ns'])
    result['start']=start
    result['owner_grant']=owner[0] if owner else None
    result['last_admission_clock_margin_ns']=admissions[-1]['clock_deadline_ns']-admissions[-1]['evaluated_ns'] if admissions else None
    result['dispatch_minus_last_admission_clock_deadline_ns']=b['dispatched_ns']-admissions[-1]['clock_deadline_ns'] if admissions else None
    return result


def analyze(run,manifest):
    report=json.loads((run/'run.json').read_text());inputs=[p for p in run.rglob('*') if p.is_file()];hashes={}
    for p in inputs:
        name=str(p.relative_to(ROOT));h=sha(p)
        if manifest.get(name,{}).get('sha256')!=h:raise ValueError('original loaded start input changed')
        hashes[name]=h
    if not report.get('start_diagnostics_enabled') or report.get('runtime_layout',{}).get('name') not in ('start-trace','sender-visibility'):raise ValueError('matched start layout not recorded')
    progress=command_progress(report,run);traces=command_traces(run);starts=start_traces(run)
    if starts!=report.get('start_diagnostics'):raise ValueError('closed start reanalysis differs from original')
    events=[e for n,t in traces.items() if n.startswith('robot-') for e in t['events']];rows=[]
    for entry in progress['entries']:
        identity=entry['number'].to_bytes(16,'little').hex();admissions=sorted([e for e in events if e['point'] in (32,36) and e['detail']==6 and e['value']==0 and e['request']==identity],key=lambda e:e['monotonic_ns'])
        rows.append(join_attempt(entry,starts['starts'],admissions))
    known={r['number'].to_bytes(16,'little').hex() for r in rows}
    if any(s['identity']['request'] not in known for s in starts['starts']):raise ValueError('unmapped start group')
    if any(sha(ROOT/n)!=h for n,h in hashes.items()):raise ValueError('raw inputs changed during start analysis')
    branches={name:sum(s['branch']==name for s in starts['starts']) for name in sorted({s['branch'] for s in starts['starts']})}
    return dict(run=str(run.relative_to(ROOT)),all_attempts=rows,audit=progress['audit'],skipped=progress['skipped_slots'],branch_counts=branches,unavailable_starts=[r['number'] for r in rows if r['start'] is None],raw_sha256=hashes,scope='Every attempt and start group, matched immutable context; no replay/nonexecution or historical branch inference; original failed gate retained')
