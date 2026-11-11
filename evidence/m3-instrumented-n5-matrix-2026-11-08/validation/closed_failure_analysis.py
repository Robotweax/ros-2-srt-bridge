"""Read-only recurrence audit; original cohort/workload reports are unchanged."""
from pathlib import Path
import hashlib,json,sys
root=Path.cwd();sys.path.insert(0,str(root/'tools'))
from m3_command_trace import summarize_run
from m3_admission_diagnostics import correlate
base=root/'.local/m3-instrumented-n5-matrix-2026-11-08';out=root/'evidence/m3-instrumented-n5-matrix-2026-11-08'
x=json.loads((base/'execution.json').read_text());assert all(r['status']!='running' for r in x['rows'])
row=next(r for r in x['rows'] if r['slot']['label']=='srt-N5-4211');assert row['status']=='failed'
run=root/row['run'];d=json.loads((run/'run.json').read_text());assert d['status']=='passed' and d['pcap_population_reconciled']
a=row['analysis'];p=a['progress'];assert p['audit']['unresolved']==1
attempt=d['results']['commands'][-1];entry=p['entries'][-1];identity=attempt['number'].to_bytes(16,'little').hex()
traces=summarize_run(run);pairs=[pair for pair in correlate(traces) if pair['receiver']['request']==identity];assert len(pairs)==1
r=pairs[0]['receiver'];s=pairs[0]['sender'];assert r['clock_error']==2 and r['age_error']==2 and r['value']==13 and s['value']==5
assert r['origin_ns']==entry['sender']['source_ns'] and r['session']==entry['sender']['session'] and r['route']==entry['sender']['route']
assert entry['sdk_handoffs']==1 and entry['receiver'] is None and entry['sender']['state']==8 and entry['sender']['reason']==2
assert entry['sender']['deadline_ns']-entry['sender']['source_ns']==5_000_000_000
assert r['evaluated_ns']<entry['sender']['deadline_ns'] and not a['active_context_events']
assert attempt['last_status_observation']['state']==1 and 'terminal' not in attempt
commands=[dict(file=n,**e) for n,t in traces.items() for e in t['events'] if e['request']==identity and (e['point'] in (5,6,7,25,29) or (e['point'] in (32,33,34) and e['detail']==6))]
assert not any(e['point']==34 for e in commands)
assert [v['status'] for v in x['rows'][2:]]==['not_executed','not_executed']
result=dict(source=x['source_commit'],cohort_status=row['status'],original_harness_status=d['status'],audit=p['audit'],skipped_slots=p['skipped_slots'],
 unresolved_intent=entry,live_attempt=attempt,matched_rejection=pairs[0],command_events=commands,
 shared_vm_fixture_timing=dict(source_to_receiver_evaluation_ns=r['evaluated_ns']-r['origin_ns'],sender_budget_remaining_at_rejection_ns=entry['sender']['deadline_ns']-r['evaluated_ns'],scope='shared VM monotonic namespace verified by original report; not general cross-host clock/packet arrival measurement'),
 active_context_change_events=a['active_context_events'],later_slots_not_executed=[v['slot'] for v in x['rows'][2:]],
 findings=['This COMMAND was rejected at receiver transport clock admission with expired clock/age errors, before forwarding to receiver worker.',
 'Matching sender COMMAND peer error preserves original request kind/sequence/session/route; this is not an ambiguous QUERY error.',
 'The sender stays live LOCAL_QUEUED and later queries cannot recover an unrecorded receiver result; deadline expiry does not resolve uncertainty.',
 'Closed sender UNKNOWN may be cleanup invalidation; no live UNKNOWN transition is inferred from its closed state.',
 'Ephemeral traces, NOT_FOUND and closed journal absence do not authorize replay or a durable negative outcome.',
 'This identifies the observed rejection/stall boundary in this new run, not why clock qualification expired or the unique cause of an older run.'],
 provenance=dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),original_run_sha256=hashlib.sha256((run/'run.json').read_bytes()).hexdigest()))
(out/'closed-failure-analysis.json').write_text(json.dumps(result,indent=2)+'\n')
print('Closed recurrence: matched COMMAND clock expiry, one SDK handoff, retained unresolved intent; later seeds skipped')
