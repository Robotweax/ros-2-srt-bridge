"""Closed live sender+receiver retention proof; no counterfactual claims."""
from pathlib import Path
import hashlib,json
root=Path.cwd();out=root/'evidence/m3-durable-receiver-expiry-2026-11-08';x=json.loads((out/'execution.json').read_text());row=x['rows'][1];run=root/row['run'];d=json.loads((run/'run.json').read_text());events=[dict(file=n,**e) for n,t in d['command_diagnostics'].items() for e in t['events']];proof=[]
for held in events:
 if held['point']!=35:continue
 identity=held['request'];number=int.from_bytes(bytes.fromhex(identity),'little');entry=next(e for e in row['analysis']['progress']['entries'] if e['number']==number)
 sent=[e for e in events if e['point']==25 and e['request']==identity];resumed=[e for e in events if e['point']==36 and e['request']==identity];deferred=[e for e in events if e['point']==29 and e['request']==identity]
 assert len(sent)==len(resumed)==len(deferred)==1 and entry['terminal']==4 and entry['sdk_handoffs']==1
 assert resumed[0]['age_upper_ns']<5_000_000_000 and entry['receiver']['deadline_ns']==resumed[0]['evaluated_ns']+5_000_000_000-resumed[0]['age_upper_ns'] and entry['receiver']['dispatched_ns']<entry['receiver']['deadline_ns']
 proof.append(dict(number=number,source_pre_sdk_defer=deferred[0],sdk_handoff=sent[0],receiver_defer=held,receiver_resume=resumed[0],closed_journal_pair=entry,trace_gaps=dict(source_defer_to_sdk_ns=sent[0]['monotonic_ns']-deferred[0]['monotonic_ns'],receiver_defer_to_resume_ns=resumed[0]['monotonic_ns']-held['monotonic_ns'],original_origin_to_receiver_revalidation_ns=resumed[0]['evaluated_ns']-entry['sender']['source_ns'])))
assert len(proof)==1 and proof[0]['number']==5
(out/'retained-success-audit.json').write_text(json.dumps(dict(proof=proof,scope='one new live successful intent with both unsent sender and received-frame receiver retention; observed trace gaps, not exact clock recovery or physical packet latency; no prior failure resolved',script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),original_run_sha256=hashlib.sha256((run/'run.json').read_bytes()).hexdigest()),indent=2)+'\n')
