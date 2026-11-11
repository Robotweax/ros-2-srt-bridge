"""Closed, read-only proof of the newly observed pre-SDK clock deferral."""
import hashlib,json
from pathlib import Path
root=Path.cwd();out=root/'evidence/m3-admission-diagnostics-2026-11-08'
x=json.loads((out/'execution.json').read_text());row=x['rows'][1];run=root/row['run'];d=json.loads((run/'run.json').read_text())
events=[dict(file=n,**e) for n,t in d['command_diagnostics'].items() for e in t['events']]
proof=[]
for e in events:
 if e['point']!=29:continue
 identity=e['request'];number=int.from_bytes(bytes.fromhex(identity),'little')
 p=next(p for p in row['analysis']['progress']['entries'] if p['number']==number)
 sent=[v for v in events if v['point']==25 and v['request']==identity];assert len(sent)==1 and p['sdk_handoffs']==1 and p['terminal']==4
 admission=[v for v in events if v['point']==32 and v['detail']==6 and v['request']==identity];assert len(admission)==1 and admission[0]['value']==0 and admission[0]['age_error']==0
 assert p['sender']['deadline_ns']-p['sender']['source_ns']==5_000_000_000
 proof.append(dict(number=number,deferred=e,provider_sent=sent[0],receiver_admission=admission[0],closed_journal_proof=p,deferral_to_sdk_ns=sent[0]['monotonic_ns']-e['monotonic_ns']))
assert len(proof)==1 and proof[0]['number']==7
(out/'deferred-intent-audit.json').write_text(json.dumps(dict(proof=proof,scope='new cohort pre-SDK clock deferral; same original budget and one accepted handoff; not replay, historical stall recovery or latency guarantee',analysis_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),original_run_sha256=hashlib.sha256((run/'run.json').read_bytes()).hexdigest()),indent=2)+'\n')
print('New intent7:957.679ms deferral-to-SDK, one handoff, qualified admission and durable success')
