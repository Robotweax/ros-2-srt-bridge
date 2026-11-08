"""Read-only seed4211 analysis of original closed inputs; no outcome mutation."""
import hashlib,json,sys
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'tools'))
from m3_n5_progress import command_progress
from m3_command_trace import summarize_run
out=root/'evidence/m3-ros-confirmation-srt-n5-2026-11-08'
x=json.loads((out/'execution.json').read_text());row=next(r for r in x['rows'] if r['slot']['label']=='srt-N5-4211');run=root/row['run'];report=json.loads((run/'run.json').read_text())
p=command_progress(report,run);attempt=report['results']['commands'][-1];entry=p['entries'][-1]
assert attempt['number']==12 and p['audit']['unresolved']==1 and entry['sdk_handoffs']==1
assert entry['receiver'] is None and entry['sender']['state']==8 and entry['sender']['reason']==2
last=attempt['last_status_observation'];assert last['state']==1 and last['revision']==0 and last['peer_error']==3
assert entry['sender']['deadline_ns']-entry['sender']['source_ns']==5_000_000_000
traces=summarize_run(run);begin=report['results']['publication_interval']['resume_monotonic_ns'];end=report['results']['command_data_cutoff_monotonic_ns']
active=[dict(file=n,**e) for n,t in traces.items() for e in t['events'] if begin<=e['monotonic_ns']<=end and e['point'] in (2,3,4,30,31)]
assert not active
request=attempt['number'].to_bytes(16,'little').hex()
clock=[s for s in attempt['status_observation_history'] if s['peer_error']==5]
assert clock and all(s['state']==1 for s in attempt['status_observation_history'])
analysis=dict(original_harness_status=report['status'],cohort_status=row['status'],audit=p['audit'],skipped_slots=p['skipped_slots'],unresolved_intent=entry,
 observed_live=dict(attempt=attempt,retained_poll_history_only=True,retained_history_count=len(attempt['status_observation_history']),pending_observed_for_ns=last['observed_monotonic_ns']-attempt['submitted_monotonic_ns']),
 clock_error_observations=clock,clock_error_request_kind_exposed=False,
 request_trace_events={n:[e for e in t['events'] if e['request']==request] for n,t in traces.items()},
 trace_population={n:dict(complete=t['complete'],records=t['records'],counts=t['counts']) for n,t in traces.items()},
 active_context_change_window=dict(begin_ns=begin,end_ns=end,points=[2,3,4,30,31],events=active),
 limitations=['No receiver request-admission trace point exists here; lack of a receiver request trace is not proof of nonreceipt.',
 'Original status cache preserves prior LOCAL_QUEUED entry when an error event carries no entry; request_kind is not exposed in that ROS status.',
 'Closed sender UNKNOWN/reconcile_required may be cleanup/session invalidation; no live UNKNOWN transition was recorded for this intent.',
 'Receiver journal absence, elapsed budget and NOT_FOUND do not authorize an absence conclusion or replay.',
 'No unique admission, clock, provider or receiver rejection cause is established.'],
 provenance=dict(analysis_script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),original_run_sha256=hashlib.sha256((run/'run.json').read_bytes()).hexdigest(),frozen_source=x['source_commit']))
(out/'seed4211-closed-analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
print('Seed4211: 11/12 successes, 1 unresolved, 1 SDK handoff, no active context-change trace events; cause unproven')
