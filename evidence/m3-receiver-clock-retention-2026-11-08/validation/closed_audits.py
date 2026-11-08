"""Read-only native and live candidate audits; no original verdict changes."""
from pathlib import Path
import hashlib,json,sys
root=Path.cwd();sys.path.insert(0,str(root/'tools'))
from m3_dds_result_timeline import read_journal
from m3_command_trace import summarize_run
base=root/'.local/m3-receiver-retention-build';out=root/'evidence/m3-receiver-clock-retention-2026-11-08'
last=(base/'SDK-LastTest.log').read_text()
def records(prefix):return [json.loads(l.split(' ',1)[1]) for l in last.splitlines() if l.startswith(prefix+' ')]
native=records('RECEIVER_RETENTION_NATIVE');assert len(native)==8
assert all(n['sdk_handoffs']==1 and n['resumes']==(1 if n['mode']=='recover' else 0) and n['effects']==(1 if n['mode']=='recover' else 0) for n in native)
threshold=(base/'runtime-before.json').stat().st_mtime
pairs=[p.parent for p in (root/'build/m3-sdk/tests/native').glob('wire-errors-*/retention-*/sender.sqlite') if p.stat().st_mtime>=threshold];assert len(pairs)==8
audits={};raw={}
for directory in pairs:
 mode=directory.name.removeprefix('retention-');a=read_journal(directory/'sender.sqlite',1);b=read_journal(directory/'receiver.sqlite',2);assert len(a['entries'])==1
 e=next(iter(a['entries'].values()));assert e['deadline_ns']-e['source_ns']==(500_000_000 if mode=='expiry' else 5_000_000_000)
 if mode=='recover':
  target=next(iter(b['entries'].values()));assert len(b['entries'])==1 and e['state']==target['state']==4 and e['result_valid'] and target['dispatched_ns']<target['deadline_ns']
 else:assert e['state']==8 and e['reason']==2 and not e['result_valid'] and not b['entries']
 audits[str(directory.relative_to(root))]=dict(mode=mode,sender=a,receiver=b,scope='controlled closed fixture records; absence is not general nonexecution/replay authority')
 for p in directory.iterdir():
  if p.is_file():raw[str(p.relative_to(root))]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(out/'native-audits.json').write_text(json.dumps(dict(cases=native,queue=records('RECEIVER_RETENTION_CONTRACT'),late_stale=records('RECEIVER_RETENTION_PROTOCOL'),original_session_negatives=records('CLOCK_REJECTION_CONTRACT'),closed_journals=audits,raw_hashes=raw),indent=2)+'\n')
x=json.loads((out/'execution.json').read_text());row=x['rows'][1];run=root/row['run'];d=json.loads((run/'run.json').read_text());assert d['status']=='passed' and d['pcap_population_reconciled']
a=row['analysis'];p=a['progress'];traces=summarize_run(run);events=[dict(file=n,**e) for n,t in traces.items() for e in t['events']]
attempt=d['results']['commands'][-1];entry=p['entries'][-1];identity=attempt['number'].to_bytes(16,'little').hex()
selected=[e for e in events if e['request']==identity and (e['point'] in (5,6,25,29) or (e['point'] in (32,33,34,35,36,37,38) and e['detail']==6))]
initial=[e for e in selected if e['point']==32];held=[e for e in selected if e['point']==35];dropped=[e for e in selected if e['point']==37];errors=[e for e in selected if e['point']==33]
assert len(initial)==len(held)==len(dropped)==len(errors)==1
r=initial[0];q=dropped[0];s=errors[0]
assert r['value']==13 and r['age_error']==2 and q['value']==25 and q['clock_error']==q['age_error']==0 and s['value']==6
assert all(e['request_sequence']==r['request_sequence'] and e['session']==r['session'] and e['route']==r['route'] for e in [held[0],q,s])
assert entry['sdk_handoffs']==1 and entry['receiver'] is None and entry['sender']['state']==8 and attempt['last_status_observation']['state']==1
assert entry['sender']['source_ns']==r['origin_ns'] and entry['sender']['deadline_ns']<r['evaluated_ns'] and p['audit']['unresolved']==1
assert not any(e['point'] in (34,36) for e in selected)
result=dict(cohort_status=row['status'],original_harness_status=d['status'],audit=p['audit'],skipped_slots=p['skipped_slots'],unresolved=entry,live_attempt=attempt,events=selected,
 shared_vm_fixture_timing=dict(source_to_initial_evaluation_ns=r['evaluated_ns']-r['origin_ns'],already_past_sender_deadline_at_initial_evaluation_ns=r['evaluated_ns']-entry['sender']['deadline_ns'],defer_to_drop_trace_gap_ns=q['monotonic_ns']-held[0]['monotonic_ns'],scope='shared VM monotonic comparisons and event record gap; not physical-wire delay/exact clock recovery'),
 active_context_events=a['active_context_events'],scope='retained COMMAND revalidated as stale and safely dropped; START_EXPIRED is diagnostic, not durable terminal result; no replay or historical uncertainty resolution',
 provenance=dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),original_run_sha256=hashlib.sha256((run/'run.json').read_bytes()).hexdigest()))
(out/'live-late-expiry-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('Audited8 native cases and live retained command: already expired at initial receiver evaluation, fresh recheck stale, no forwarding/replay')
