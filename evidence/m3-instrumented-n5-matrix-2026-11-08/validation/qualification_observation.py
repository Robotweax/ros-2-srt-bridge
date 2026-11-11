"""Closed sampled qualification after rejection; no policy/outcome changes."""
from pathlib import Path
import hashlib,json
root=Path.cwd();out=root/'evidence/m3-instrumented-n5-matrix-2026-11-08';x=json.loads((out/'closed-failure-analysis.json').read_text());execution=json.loads((out/'execution.json').read_text());run=root/execution['rows'][1]['run'];d=json.loads((run/'run.json').read_text());r=x['matched_rejection']['receiver']
events=[dict(file=n,**e) for n,t in d['command_diagnostics'].items() if n.startswith('robot-') for e in t['events'] if e['point']==32 and e['session']==r['session'] and e['evaluated_ns']>r['evaluated_ns'] and e['clock_error']==0 and e['clock_deadline_ns']>e['evaluated_ns']]
first=min(events,key=lambda e:e['evaluated_ns']);deadline=x['unresolved_intent']['sender']['deadline_ns'];assert first['evaluated_ns']<deadline
result=dict(first_later_sampled_qualification=first,rejection_to_qualified_observation_ns=first['evaluated_ns']-r['evaluated_ns'],original_sender_budget_remaining_ns=deadline-first['evaluated_ns'],scope='sampled local clock state/deadline on later QUERY; not exact recovery latency, command age/dispatch proof, counterfactual success or general cross-host timing',candidate='evaluate bounded receiver clock-gap retention with original deadline/context; neither resend nor extend budget; separately test expiry/context loss/capacity',provenance=dict(script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),original_run_sha256=hashlib.sha256((run/'run.json').read_bytes()).hexdigest()))
(out/'later-qualification-observation.json').write_text(json.dumps(result,indent=2)+'\n')
print('Later QUERY samples qualified receiver192.869ms after rejection with~2s of original budget left; not a counterfactual success proof')
