"""Consolidate retained verdicts only; no Docker, procfs, builds or experiments."""
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
FRESH='evidence/m3-fresh-n1-2903-preparation-2026-11-11'
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(path):return json.loads((ROOT/path).read_text())
def build():
    if (HERE/'acceptance.json').exists():raise ValueError('acceptance snapshot already exists; no replacement')
    archive=HERE/'prior-root-documents';archive.mkdir()
    archived={}
    for name in ('README.md','DELIVERY_PLAN.md','M3_ACCEPTANCE_REVIEW.md','M3_CLOSURE_PLAN.md','M3_COMPARISON_AND_ACCEPTANCE.md','baselines/m3-plan.json'):
        target=archive/name.replace('/','__');shutil.copyfile(ROOT/name,target);archived[name]=dict(path=str(target.relative_to(ROOT)),sha256=sha(target))
    plan=read('evidence/m3-closure-plan-2026-11-09/plan.json')['proposed_future_cases'];evidence={}
    def source(path):
        evidence[path]=dict(sha256=sha(ROOT/path),bytes=(ROOT/path).stat().st_size);return read(path)
    paths={
        'N0':'evidence/m3-current-n0-stable-execution-2026-11-10/gate-report.json',
        'N3':'evidence/m3-strict-n3-execution-2026-11-10/gate-report.json',
        'N4':'evidence/m3-current-n4-corrected-execution-2026-11-10/gate-report.json',
        'seven':'evidence/m3-current-remaining-execution-2026-11-11/gate-report.json'}
    n0,n3,n4,seven=[source(paths[k]) for k in ('N0','N3','N4','seven')]
    assert n0['passed_cases']==1 and n0['failed_cases']==0 and n3['passed_cases']==9 and n3['failed_cases']==0 and n4['passed']==19 and n4['failed']==0 and seven['passed']==7 and seven['failed']==0
    slots={n0['case_id']:dict(status='passed',source=paths['N0'])}
    for stage,report in [('N3',n3),('N4',n4)]:
        for row in report['rows']:
            assert row['status']=='passed';slots[row['id']]=dict(status=row['status'],source=paths[stage],row_id=row['id'])
    original_path='evidence/m3-current-long-execution-2026-11-10/cohort.json';original=source(original_path);assert [r['status'] for r in original['rows']]==['passed','failed']+['not_executed']*7
    for row in original['rows'][:2]:
        id=row['slot']['id'];path='evidence/m3-current-long-execution-2026-11-10/cases/'+id+'/strict-assessment.json';proof=source(path);assert proof['status']==row['status'];slots[id]=dict(status=row['status'],source=path)
    for row in seven['cases']:
        id=row['id'];path='evidence/m3-current-remaining-execution-2026-11-11/cases/'+id+'/strict-assessment.json';proof=source(path);assert proof['status']=='passed';assert id not in slots;slots[id]=dict(status='passed',source=path)
    assert len(slots)==38 and sum(v['status']=='passed' for v in slots.values())==37 and slots['N1-combined-2903']['status']=='failed'
    entries=[dict(slot={k:s[k] for k in ('id','ordinal','stage','profile','seed','source_seconds') if k in s},**slots[s['id']]) for s in plan]
    for name in ('baselines/m1-acceptance.json','baselines/m2-acceptance.json'):
        assert source(name)['status']=='accepted'
    comparison=archived['M3_COMPARISON_AND_ACCEPTANCE.md'];evidence[comparison['path']]=dict(sha256=comparison['sha256'],bytes=(ROOT/comparison['path']).stat().st_size)
    fail=entries[30];assert fail['slot']['id']=='N1-combined-2903'
    record=dict(schema_version=1,date='2026-11-11',milestone='M3',status='not_accepted_as_complete',acceptance_decision='pending fresh scoped N1/2903 qualification and explicit milestone review',scope='retained local Linux amd64/ROS Jazzy simulator evidence under Docker emulation; native ARM64 observer, no physical robot or cross-host qualification',M0_M2='accepted only in recorded scope',matrix=dict(total_distinct_slots=38,passing_slots=37,failed_slots=1,unexecuted_distinct_slots=0,separate_frozen_series_not_one_statistical_trial=True,entries=entries),groups=dict(N0='1/1 passed,300s',N3='9/9 passed',N4='19/19 passed',N1='2 passing seeds;2903 historical strict failure',N2='3/3 passed,600s each',N5='3/3 passed,300s each'),original_N1_2903=dict(status='failed',error=read(fail['source']).get('error'),assessment_path=fail['source'],assessment_sha256=evidence[fail['source']]['sha256'],original_cohort_path=original_path,original_cohort_sha256=evidence[original_path]['sha256'],no_retroactive_requalification=True),latest_seven=dict(source=paths['seven'],attempts=seven['total_attempts'],confirmed_successes=seven['total_confirmed_successes'],effects=seven['total_effects'],UNKNOWN=seven['total_UNKNOWN'],unresolved=seven['total_unresolved'],N5_skipped_slots=seven['total_skipped_slots'],six_SENSOR_balances_zero_each=True,readable_stacks=seven['observed_stack_reads_ok'],unavailable_stacks=seven['observed_stack_reads_unavailable']),pending_fresh_attempt=dict(case_id='N1-combined-2903',profile='N1',seed=2903,source_seconds=600,preparation_path=FRESH,preparation_authorized=True,execution_authorized=False,original_run_resumed=False,original_failure_preserved=True,no_tuning=True,no_retries=True,other_cases_and_stages_disabled=True),limitations=['N5 skipped83 command slots and roughly6s adjacent intent gaps; no continuous2s service guarantee','zero SENSOR imbalance is not loss-free delivery; original age/admission bounds apply','observer-supported DDS ENOENT does not reconstruct original SRT-provider task metadata or prove no unseen reuse','DDS age/capture-population/security/resource comparison remains scoped; failed loaded cold startup supplies no steady-window denominator','no general transport superiority, observer-overhead equivalence, physical-robot, hard-real-time or cross-host-clock qualification'],comparison_statement=archived['M3_COMPARISON_AND_ACCEPTANCE.md'],PR2='draft_unmerged',M4='not_started',merge_authorized=False,live_runs=0,Docker_calls=0,tuning=False,retries=False)
    (HERE/'acceptance.json').write_text(json.dumps(record,indent=2)+'\n');(HERE/'evidence-sources.json').write_text(json.dumps(evidence,indent=2)+'\n');(HERE/'archived-documents.json').write_text(json.dumps(archived,indent=2)+'\n')
    return record
if __name__=='__main__':
    record=build();print(json.dumps(dict(status=record['status'],passing=record['matrix']['passing_slots'],failed=record['matrix']['failed_slots'])))
