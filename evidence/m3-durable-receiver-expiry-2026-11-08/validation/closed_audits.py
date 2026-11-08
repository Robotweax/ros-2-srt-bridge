"""Closed native/live qualified-expiry audits; never alters original verdicts."""
from pathlib import Path
import hashlib,json,sys
root=Path.cwd();sys.path.insert(0,str(root/'tools'))
from m3_dds_result_timeline import read_journal
from m3_command_trace import summarize_run
base=root/'.local/m3-durable-expiry-build';out=root/'evidence/m3-durable-receiver-expiry-2026-11-08'
text=(base/'SDK-LastTest.log').read_text()
def records(prefix):return [json.loads(l.split(' ',1)[1]) for l in text.splitlines() if l.startswith(prefix+' ')]
native=records('DURABLE_EXPIRY_NATIVE');assert len(native)==4 and sum(n['retained'] for n in native)==2
assert all(n['sdk_handoffs']==1 and n['expired_dispatches']==n['expired_effects']==0 and n['restart_query_duplicate'] and n['later_fresh_success'] for n in native)
threshold=(base/'runtime-before.json').stat().st_mtime
paths=[p.parent for p in (root/'build/m3-sdk/tests/native').glob('wire-errors-*/durable-*/sender.sqlite') if p.stat().st_mtime>=threshold];assert len(paths)==4
closed={};hashes={}
for directory in paths:
 a=read_journal(directory/'sender.sqlite',1);b=read_journal(directory/'receiver.sqlite',2);assert len(a['entries'])==len(b['entries'])==2
 for identity,e in a['entries'].items():
  f=b['entries'][identity];assert all(e[k]==f[k] for k in ('state','reason','revision','route','payload_hash','source_epoch','source_ns','session','result_valid','result_generation'))
  assert e['deadline_ns']-e['source_ns']==500_000_000
  if e['state']==7:assert e['reason']==3 and not e['result_valid'] and f['dispatched_ns']==0 and 0<f['deadline_ns']<f['admitted_ns']
  else:assert e['state']==4 and e['result_valid'] and f['dispatched_ns']<f['deadline_ns']
 assert sorted(e['state'] for e in a['entries'].values())==[4,7]
 closed[str(directory.relative_to(root))]=dict(sender=a,receiver=b,scope='expiry-only record plus later fresh success, original500ms fixture source budget')
 for p in directory.iterdir():
  if p.is_file():hashes[str(p.relative_to(root))]=dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(out/'native-audits.json').write_text(json.dumps(dict(native_cases=native,proof_contract=records('DURABLE_EXPIRY_PROOF'),retention_regressions=records('RECEIVER_RETENTION_NATIVE'),closed_journals=closed,raw_hashes=hashes),indent=2)+'\n')
x=json.loads((out/'execution.json').read_text());cases=[]
for row in x['rows']:
 if 'analysis' not in row:cases.append(dict(slot=row['slot'],status=row['status'],error=row.get('error')));continue
 run=root/row['run'];report=json.loads((run/'run.json').read_text());a=row['analysis'];traces=summarize_run(run);events=[dict(file=n,**e) for n,t in traces.items() for e in t['events']]
 expired=[]
 for entry in a['progress']['entries']:
  if entry['terminal']!=7:continue
  identity=entry['number'].to_bytes(16,'little').hex();proof=[e for e in events if e['request']==identity and e['point']==39];assert len(proof)==1
  e=proof[0];assert e['age_lower_ns']>5_000_000_000 and e['clock_error']==e['age_error']==0 and e['expiry_deadline_ns']==entry['receiver']['deadline_ns'] and entry['receiver']['dispatched_ns']==0
  later_successes=[p['number'] for p in a['progress']['entries'] if p['number']>entry['number'] and p['terminal']==4]
  expired.append(dict(closed_journal_pair=entry,qualified_proof=e,original_live_row=next(r for r in report['results']['commands'] if r['number']==entry['number']),later_successful_intents=later_successes))
 cases.append(dict(slot=row['slot'],status=row['status'],original_harness_status=report['status'],audit=a['progress']['audit'],durable_outcomes=a['durable_outcomes'],expired=expired,active_context_events=a['active_context_events']))
(out/'durable-outcome-audits.json').write_text(json.dumps(dict(cases=cases,scope='separate all-success versus confirmed success/verified-expiry completion; no past UNKNOWN resolution or full N5 acceptance',analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),indent=2)+'\n')
print('Closed native/query/restart/fresh-work and live dual-outcome proofs audited')
