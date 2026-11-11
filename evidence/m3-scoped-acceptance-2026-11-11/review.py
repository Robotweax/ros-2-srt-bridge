"""Read-only acceptance audit of retained files; no subprocess, runtime, SQLite or traffic."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
SERIES=[('m3-strict-n3-execution-2026-11-10','45036de78761'),('m3-current-n0-stable-execution-2026-11-10','98a357e418c2'),('m3-current-n4-corrected-execution-2026-11-10','ecb0d1346932'),('m3-current-long-execution-2026-11-10','868a21578a61'),('m3-current-remaining-execution-2026-11-11','df3cfbabfe3b'),('m3-fresh-n1-2903-execution-2026-11-11','b3609d03e5ac')]
HISTORY=['m3-n3-thirty-second-matrix-2026-11-09/execution-matrix.json','m3-n3-frozen-cohort-2026-11-09/gate-report.json','m3-n3-shutdown-diagnosis-2026-11-09/assessment.json','m3-current-n0-execution-2026-11-10/gate-report.json','m3-current-n0-corrected-execution-2026-11-10/gate-report.json','m3-current-n0-bound-execution-2026-11-10/gate-report.json','m3-current-n4-execution-2026-11-10/gate-report.json','m3-current-long-execution-2026-11-10/gate-report.json','m3-current-long-execution-2026-11-10/cohort.json','m3-current-long-execution-2026-11-10/cases/N1-combined-2903/strict-assessment.json','m3-sender-pending-diagnosis-2026-11-09/analysis.json','m3-sender-pending-diagnosis-2026-11-09/README.md','m3-sender-reconciliation-2026-11-09/README.md']
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def read(path):return json.loads((ROOT/path).read_text())
def write(name,value):(HERE/name).write_text(json.dumps(value,indent=2)+'\n')
def main():
    expected={};indexes={};sources={};series=[];current_build=None;native=None
    def expect(name,digest,size=None):
        prior=expected.get(name)
        if prior and prior['sha256']!=digest:raise ValueError('conflicting retained hashes: '+name)
        expected[name]=dict(sha256=digest,bytes=size if size is not None else prior.get('bytes') if prior else None)
    def source(name):
        p=ROOT/name;sources[name]=dict(sha256=sha(p),bytes=p.stat().st_size);expect(name,sha(p),p.stat().st_size)
    def index(name,digest=None):
        p=ROOT/name;actual=sha(p)
        if digest and actual!=digest:raise ValueError('index digest differs: '+name)
        indexes[name]=actual;source(name)
        for artifact,item in read(name).items():expect(artifact,item['sha256'],item['bytes'])
    freezes={sha(p):p for p in (ROOT/'evidence').glob('*/freeze.json')}
    for folder,prefix in SERIES:
        base='evidence/'+folder;gate=read(base+'/gate-report.json');digest=gate['freeze_sha256'];assert digest.startswith(prefix)
        path=freezes[digest];f=json.loads(path.read_text());source(str(path.relative_to(ROOT)));source(base+'/gate-report.json');source(base+'/README.md')
        build=f['runtime_layout']['matched_build_sha256'];current_build=current_build or build;assert build==current_build and len(build)==14
        native=native or f['reused_native_inputs_sha256'];assert f['reused_native_inputs_sha256']==native and len(native)==87
        for name,d in {**f['inputs_sha256'],**f['source_sha256'],**native,**build}.items():expect(name,d)
        for name,d in f['retained_indexes'].items():index(name,d)
        for p in (ROOT/base).glob('*artifact-hashes.json'):index(str(p.relative_to(ROOT)))
        series.append(dict(path=base,freeze_sha256=digest,matched_build_entries=14,native_inputs=87,scope='separate historical series; original failed LONG cohort retains failure'))
    comparison='evidence/m3-comparison-acceptance-2026-11-09';source(comparison+'/statement.json');source(comparison+'/evidence-index.json')
    for name,item in read(comparison+'/evidence-index.json')['source_reports'].items():expect(name,item['sha256'],item['bytes']);sources[name]=item
    for suffix in HISTORY:source('evidence/'+suffix)
    for name in ['ARCHITECTURE.md','baselines/dependencies.json','baselines/m2-acceptance.json','evidence/m3-closure-plan-2026-11-09/plan.json','evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-update.json','evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-sources.json']:source(name)
    update=read('evidence/m3-fresh-n1-2903-execution-2026-11-11/acceptance-update.json');entries=update['entries'];plan=read('evidence/m3-closure-plan-2026-11-09/plan.json')['proposed_future_cases']
    assert [e['slot']['id'] for e in entries]==[s['id'] for s in plan];assert len({e['slot']['id'] for e in entries})==38
    for entry in entries:
        d=read(entry['source']);id=entry['slot']['id'];source(entry['source'])
        if 'row_id' in entry:verdict=next(v['status'] for v in d['rows'] if v['id']==id)
        elif d.get('case_id')==id:verdict='passed' if d['passed_cases']==1 and d['failed_cases']==0 else 'failed'
        else:verdict=d['status']
        assert entry['status']==verdict=='passed',id
    ref=update['original_failure_reference'];expect(ref['path'],ref['sha256']);expect(ref['cohort_path'],ref['cohort_sha256']);assert read(ref['path'])['status']=='failed'
    assert [v['status'] for v in read(ref['cohort_path'])['rows']]==['passed','failed']+['not_executed']*7
    groups={g:sum(e['slot']['stage']==g for e in entries) for g in ['N0','N3','N4','LONG']};assert groups==dict(N0=1,N3=9,N4=19,LONG=9)
    total=0
    for name,item in sorted(expected.items()):
        p=ROOT/name
        if sha(p)!=item['sha256'] or item['bytes'] is not None and p.stat().st_size!=item['bytes']:raise ValueError('retained artifact differs: '+name)
        total+=p.stat().st_size
    write('source-reports.json',sources);write('reviewed-indexes.json',indexes);write('matched-build.json',dict(matched_build_sha256=current_build,native_inputs_sha256=native,series=series))
    write('verification.json',dict(status='passed_readonly_complete_record_audit',passing_distinct_ids=38,groups=groups,series=series,unique_artifacts_verified=len(expected),bytes_verified=total,retained_indexes_verified=len(indexes),same_14_matched_build_entries=True,same_87_native_inputs=True,original_N1_2903_failure_preserved=True,original_cohort_unchanged=True,source_reports=len(sources),live_runs=0,Docker_calls=0,builds=0,tuning=False,tests_run=0,formal_acceptance_granted=False,PR2_keep_draft=True,M4_enabled=False))
    print(json.dumps(dict(status='passed',artifacts=len(expected),bytes=total,indexes=len(indexes),groups=groups)))
if __name__=='__main__':main()
