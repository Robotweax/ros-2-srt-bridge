"""Read-only retained-evidence diagnosis; no collector, Docker, tests or live runs."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PREP=ROOT/'evidence/m3-current-long-preparation-2026-11-10'
EXEC=ROOT/'evidence/m3-current-long-execution-2026-11-10'
sys.path[:0]=[str(PREP),str(ROOT/'tools')]
from m3_source_preflight import sha,source_inventory
from disposition_runtime import matched

def load(path):return json.loads(path.read_text())
def integrity(freeze):
    if source_inventory()!=freeze['source_sha256']:raise ValueError('source drift')
    if matched(ROOT,'socket-disposition')!=freeze['runtime_layout']:raise ValueError('matched build drift')
    for path,digest in {**freeze['inputs_sha256'],**freeze['reused_native_inputs_sha256']}.items():
        if sha(ROOT/path)!=digest:raise ValueError('frozen input drift: '+path)
    indexes=dict(freeze['retained_indexes'])
    for path in (PREP/'public-artifact-hashes.json',EXEC/'public-artifact-hashes.json',EXEC/'local-artifact-hashes.json'):indexes[str(path.relative_to(ROOT))]=sha(path)
    for path,digest in indexes.items():
        if sha(ROOT/path)!=digest:raise ValueError('index drift')
        for name,item in load(ROOT/path).items():
            if sha(ROOT/name)!=item['sha256']:raise ValueError('retained file drift: '+name)
    return indexes

def stat_identity(text):
    fields=text[text.rfind(')')+2:].split()
    return dict(tid=int(text.split(' ',1)[0]),name=text[text.find('(')+1:text.rfind(')')],state=fields[0],start_ticks=int(fields[19]))

def source_reference(path,first,last):
    lines=path.read_text().splitlines()
    return dict(path=str(path.relative_to(ROOT)),sha256=sha(path),first_line=first,last_line=last,text='\n'.join(lines[first-1:last]))

def case(root,name):
    path=root/name
    strict=load(path/'strict-assessment.json');final=strict['launches']['operator']['measurement']
    child=final['child'];signal=child['signal_end_ns'];stages=final['stages']['rows']
    raw_stages=[json.loads(x) for x in (path/final['entry']['trace_path']).read_text().splitlines()]
    if stages!=raw_stages:raise ValueError('stored/raw stage mismatch')
    rows=[json.loads(x) for x in (path/'native-observer/blocked-target-shutdown-stacks.jsonl').read_text().splitlines()]
    samples=[];errors=[];history={};stage_by_name={r['point']:r for r in stages}
    for i,row in enumerate(rows):
        if row['kind']!='sample':continue
        root_process=next(p for p in row['processes'] if p['identity']['pid']==child['pid'])
        summary=dict(row=i,begin_ns=row['begin_ns'],end_ns=row['end_ns'],begin_ms_after_signal=(row['begin_ns']-signal)/1e6,end_ms_after_signal=(row['end_ns']-signal)/1e6,root_status=root_process['status'],root_identity_check=root_process.get('identity_check'),listed_tids=[t['tid'] for t in root_process.get('threads',[])])
        summary['tasks']=[]
        for thread in root_process.get('threads',[]):
            stat=thread['stat'];identity=stat_identity(stat['text']) if stat['status']=='ok' else None
            if identity is not None and identity['name'].startswith('rwx-'):
                history.setdefault(thread['tid'],[]).append(dict(row=i,sample_end_ns=row['end_ns'],task_identity=identity,stack_status=thread['kernel_stack']['status']))
                summary['tasks'].append(dict(tid=thread['tid'],identity=identity,stack_status=thread['kernel_stack']['status']))
            stack=thread['kernel_stack']
            if stack['status']!='ok' or stack['truncated']:
                errors.append(dict(sample_row=i,sample_begin_ns=row['begin_ns'],sample_end_ns=row['end_ns'],root_identity=root_process['identity'],root_check=root_process['identity_check'],tid=thread['tid'],reads={key:thread[key] for key in ('stat','wchan','syscall','kernel_stack')},prior_successful_task_identity=history.get(thread['tid'],[]),sample_within_provider_cleanup=stage_by_name['provider_cleanup_begin']['monotonic_ns']<=row['begin_ns']<=row['end_ns']<=stage_by_name['provider_cleanup_end']['monotonic_ns'],sample_after_worker_join=stage_by_name['worker_join_end']['monotonic_ns']<=row['begin_ns'],sample_before_supervisor_reap=row['end_ns']<child['end_ns']))
        samples.append(summary)
    points=('ros_context_shutdown_callback','main_spin_end','worker_join_end','provider_cleanup_begin','provider_cleanup_end','transport_thread_body_end','endpoint_transport_join_end','node_endpoint_join_end','main_node_reset_end','main_context_shutdown_end')
    timeline=[dict(point=p,monotonic_ns=stage_by_name[p]['monotonic_ns'],ms_after_signal=(stage_by_name[p]['monotonic_ns']-signal)/1e6,tid=stage_by_name[p]['tid']) for p in points]
    timeline.append(dict(point='supervisor_reap',monotonic_ns=child['end_ns'],ms_after_signal=(child['end_ns']-signal)/1e6,tid=None))
    return dict(case=name,namespace=load(path/'network.json')['network'],strict_status=strict['status'],strict_error=strict.get('error'),child=child,observer_begin=rows[0],observer_footer=rows[-1],samples=samples,stage_timeline=timeline,missing_stack_reads=errors,task_history=history,retained_shutdown_and_cleanup_passed=load(path/'operator-child-shutdown.json')['passed'] and all(load(path/'postflight.json').values()))

def main():
    freeze=load(PREP/'freeze.json');before=integrity(freeze);root=ROOT/freeze['output_relative']
    cohort=load(root/'cohort.json')
    if [r['status'] for r in cohort['rows']]!=['passed','failed']+['not_executed']*7:raise ValueError('original cohort changed')
    decisions={str(p.relative_to(ROOT)):sha(p) for p in [root/'cohort.json',*root.glob('*/strict-assessment.json')]}
    passed=case(root,'N1-combined-1701');failed=case(root,'N1-combined-2903')
    errors=failed['missing_stack_reads']
    if [e['tid'] for e in errors]!=[128,129,130] or passed['missing_stack_reads']:raise ValueError('unexpected failure population')
    for e in errors:
        if not all(v['status']=='unavailable' and v['errno']==2 and v['error']=='FileNotFoundError' for v in e['reads'].values()):raise ValueError('not uniform task ENOENT')
        if not all(e[k] for k in ('sample_within_provider_cleanup','sample_after_worker_join','sample_before_supervisor_reap')):raise ValueError('timeline assumption wrong')
        prior=e['prior_successful_task_identity']
        if len(prior)!=3 or len({x['task_identity']['start_ticks'] for x in prior})!=1 or any(x['stack_status']!='ok' for x in prior):raise ValueError('prior task identity/stack evidence differs')
    spec=importlib.util.spec_from_file_location('retained_thread_lifecycle',PREP/'lifecycle.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    fpath=root/'N1-combined-2903';s=load(fpath/'strict-assessment.json');final=s['launches']['operator']['measurement']
    rows=[json.loads(x) for x in (fpath/'native-observer/blocked-target-shutdown-stacks.jsonl').read_text().splitlines()]
    try:gate.coverage(rows,final['child'],final['stages']['rows'])
    except ValueError as error:
        if str(error)!='live target kernel stack unavailable':raise
        reproduced=str(error)
    else:raise ValueError('recorded failure not reproduced')
    provider=ROOT/'.deps/srt';revision='52be7c86ee1f303cbb0c8718c364217e4dd97a36'
    if subprocess.check_output(['git','-C',str(provider),'rev-parse','HEAD'],text=True).strip()!=revision:raise ValueError('provider source revision differs')
    if subprocess.check_output(['git','-C',str(provider),'status','--porcelain'],text=True).strip():raise ValueError('provider source dirty')
    refs=[source_reference(PREP/'shutdown_observer.py',19,24),source_reference(PREP/'shutdown_observer.py',46,72),source_reference(PREP/'lifecycle.py',18,53),source_reference(ROOT/'src/robotweax_srt_bridge_core/src/transport/transport.cpp',20,28),source_reference(provider/'src/compat/srt_api.cpp',155,169),source_reference(provider/'src/compat/socket_registry.cpp',902,959),source_reference(provider/'src/compat/runtime_scheduler.cpp',226,231),source_reference(provider/'src/compat/runtime_scheduler.cpp',522,570),source_reference(provider/'src/compat/socket_readiness.cpp',493,521),source_reference(provider/'src/compat/socket_readiness.cpp',604,611)]
    if integrity(freeze)!=before or any(sha(ROOT/p)!=digest for p,digest in decisions.items()):raise ValueError('evidence changed during diagnosis')
    for row in cohort['rows'][2:]:
        if (root/row['slot']['id']).exists():raise ValueError('later case created')
    report=dict(status='retained_only_diagnosis_complete_no_requalification',finding='process-versus-task lifetime mismatch: enumerated provider task paths disappear before per-task reads during srt_cleanup',classification='enumeration/read race observed; normal cleanup thread exit strongly supported but exact per-task exit/reuse proof unavailable',original_gate_failure_reproduced=reproduced,original_results=dict(passed=1,failed=1,not_executed=7),failed_case=failed,passing_case_control=passed,provider_source_revision=revision,provider_installed_archive_sha256=sha(ROOT/'install/srt-m0/lib/librobotweax-srt.a'),source_references=refs,missing_evidence=['no per-task read timestamps or explicit enumeration bracket','no task start_ticks in the missing-read sample','no post-failure task identity/absence check','no task-specific provider exit/join identity records','provider cleanup stage brackets return but does not record srt_cleanup return value'],unsupported_conclusions=['confirmed task exit or no TID reuse','SRT protocol/loss handling defect','global permission denial or hung provider threads','passing N1/2903 or any later strict combined gate'],original_decision_hashes_unchanged=decisions,verified_indexes=before,live_cases_run=0,Docker_calls=0,tests_run=0,builds=0,collector_or_policy_changes=False,assessor_changes=False,new_freeze=False,new_authorization=False,no_tuning=True,no_automatic_retries=True,remaining_cases_disabled=[r['slot']['id'] for r in cohort['rows'][2:]],completed_campaign_cases_excluded=29,M3_complete=False)
    (HERE/'diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],original_failure_reproduced=reproduced,missing_provider_tids=[e['tid'] for e in errors],all_four_task_reads_ENOENT=True,sample_within_srt_cleanup=True,original_results=report['original_results'],live_cases_run=0)))

if __name__=='__main__':main()
