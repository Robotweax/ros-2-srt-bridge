"""Read-only original-intent localization; no negative-outcome authority."""
import json,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_command_trace import summarize_run
out=ROOT/'evidence/m3-start-broader-seeds-2026-11-09';e=json.loads((ROOT/'.local/m3-start-broader-seeds-2026-11-09/execution.json').read_text());row=e['rows'][1];run=ROOT/row['run'];d=json.loads((run/'run.json').read_text());hashes=json.loads((out/'local-artifact-hashes.json').read_text());assert all(sha(ROOT/n)==v['sha256'] for n,v in hashes.items())
failed=[c for c in d['results']['commands'] if c.get('terminal')!=4];assert len(failed)==1;c=failed[0];number=c['number'];identity=number.to_bytes(16,'little').hex();proof=next(p for p in row['analysis']['progress']['entries'] if p['number']==number);assert proof['receiver'] is None and proof['sdk_handoffs']==0;sender=proof['sender'];assert (sender['state'],sender['reason'])==(8,2)
traces=summarize_run(run);assert all(v['complete'] for v in traces.values());events=[dict(file=n,**v) for n,t in traces.items() for v in t['events'] if v['request']==identity];source=[v for v in events if v['file'].startswith('operator-') and v['point'] in (5,6,21,29)]
for v in source:assert v['session']==sender['session'] and v['owner_epoch']==sender['owner_epoch'] and v['route']==sender['route']
def one(point):
 rows=[v for v in source if v['point']==point];assert len(rows)==1;return rows[0]
a,queued,deferred,dropped=(one(p) for p in (5,6,29,21));assert a['value']==1 and queued['value']==0 and deferred['value']==13 and deferred['reason']==7 and dropped['reason']==5
assert sender['deadline_ns']==sender['source_ns']+5000000000 and sender['source_ns']<a['monotonic_ns']<queued['monotonic_ns']<deferred['monotonic_ns']<sender['deadline_ns']<=dropped['monotonic_ns']
assert not any(v['point']==25 for v in events);assert not any(v['file'].startswith('robot-') and v['point']==32 and v['detail']==6 for v in events);assert not any(v['point'] in range(40,45) for v in events)
relevant_names=['src/robotweax_srt_bridge_core/src/transport/transport.cpp','src/robotweax_srt_bridge_core/include/robotweax/srt_bridge/command_trace.hpp'];assert all(sha(ROOT/n)==d['source_sha256'][n] for n in relevant_names)
status=dict(c);status.pop('status_observation_history',None)
value=dict(run=row['run'],number=number,original_identity=identity,source_proof=proof,source_stage_events=source,all_original_request_events=events,event_populations={str(point):sum(v['point']==point for v in events) for point in sorted({v['point'] for v in events})},driver_status=status,driver_retained_history=c.get('status_observation_history'),raw_trace_complete=True,clock_defer_after_origin_ns=deferred['monotonic_ns']-sender['source_ns'],pending_input_drop_after_deadline_ns=dropped['monotonic_ns']-sender['deadline_ns'],source_sha256={n:sha(ROOT/n) for n in relevant_names},raw_sha256={n:v['sha256'] for n,v in hashes.items()},conclusion='Original source was admitted and queued, then held clock-unqualified and dropped at original deadline before recorded SDK handoff. No original receiver COMMAND/start observed. Closed sender remains UNKNOWN/reconcile_required; no authoritative expiry/nonexecution or replay follows. Source gate is upstream of worker tracing; transport trace does not identify exact ClockMapper invalidity or ARP cause.')
write(out/'analysis/unresolved-intent.json',value);assert all(sha(ROOT/n)==v['sha256'] for n,v in hashes.items());print('Read-only original intent',number,'source deferral/drop verified; UNKNOWN retained')
