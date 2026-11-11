"""Read-only consolidated acceptance consistency; no live/rerun or waiver."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent

def verify(record=None):
    r=record if record is not None else json.loads((HERE/'acceptance.json').read_text());sources=json.loads((HERE/'evidence-sources.json').read_text())
    for name,item in sources.items():
        path=ROOT/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256'] or path.stat().st_size!=item['bytes']:raise ValueError('acceptance source drift: '+name)
    for original,item in json.loads((HERE/'archived-documents.json').read_text()).items():
        if hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest()!=item['sha256']:raise ValueError('archived root document drift: '+original)
    expected=json.loads((ROOT/'evidence/m3-closure-plan-2026-11-09/plan.json').read_text())['proposed_future_cases'];entries=r['matrix']['entries']
    if [e['slot']['id'] for e in entries]!=[s['id'] for s in expected] or len({e['slot']['id'] for e in entries})!=38:raise ValueError('acceptance slot population differs')
    for entry in entries:
        source=json.loads((ROOT/entry['source']).read_text());id=entry['slot']['id']
        if 'row_id' in entry:
            matches=[v for v in source['rows'] if v['id']==id]
            if len(matches)!=1:raise ValueError('acceptance row missing/duplicate')
            status=matches[0]['status']
        elif source.get('case_id')==id:status='passed' if source['passed_cases']==1 and source['failed_cases']==0 else 'failed'
        else:status=source['status']
        if status!=entry['status']:raise ValueError('acceptance verdict differs from retained evidence: '+id)
    counts={state:sum(e['status']==state for e in entries) for state in ('passed','failed','not_executed')}
    if counts!=dict(passed=37,failed=1,not_executed=0) or (r['matrix']['passing_slots'],r['matrix']['failed_slots'],r['matrix']['unexecuted_distinct_slots'])!=(37,1,0):raise ValueError('acceptance counts differ')
    failure=r['original_N1_2903'];row=next(e for e in entries if e['slot']['id']=='N1-combined-2903')
    if row['status']!='failed' or failure['status']!='failed' or row['source']!=failure['assessment_path'] or sources[row['source']]['sha256']!=failure['assessment_sha256']:raise ValueError('original failure not preserved')
    if r['status']!='not_accepted_as_complete' or r['merge_authorized'] or r['M4']!='not_started' or r['pending_fresh_attempt']['execution_authorized']:raise ValueError('unexpected acceptance/execution authority')
    return dict(status='passed_retained_only_acceptance_audit',passing_slots=37,failed_slots=1,original_failure_sha256=failure['assessment_sha256'],source_files=len(sources),live_runs=0,Docker_calls=0,acceptance_authorized=False)
if __name__=='__main__':print(json.dumps(verify(),indent=2))
