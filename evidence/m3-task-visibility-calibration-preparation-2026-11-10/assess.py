"""Calibration-only schema/present-task/controlled-absence gates, never campaign credit."""
import json
import hashlib
from pathlib import Path
from m3_observer_filtering import require_role
from shutdown_observer import task_identity,task_lifetime
from plan import CANDIDATE_SHA
def require(value,message):
    if not value:raise ValueError(message)
def snapshot(text):return [json.loads(line) for line in text.splitlines(keepends=True) if line.endswith('\n')]
def zero_offsets(text):return bool(text.splitlines()) and all(len(line.split())==3 and all(int(n)==0 for n in line.split()[1:]) for line in text.splitlines())
def key(value):return value['tid'],value['start_ticks']
def live_header(rows,context):
    require(bool(rows),'observer header unavailable')
    begin=rows[0]
    require(begin['kind']=='begin' and begin['clock']=='monotonic' and begin['mode']=='procfs' and begin['observer_independent'] and begin['task_visibility_schema_version']==1 and begin['task_history_capacity']==512,'observer task mode differs')
    require(begin['root']==dict(pid=context['target_pid'],start_ticks=context['target_start_ticks']) and begin['pid']!=context['target_pid'],'observer live identity differs')
    return begin
def context_matches(process,context):return process['identity']['pid']==context['target_pid'] and process['identity']['start_ticks']==context['target_start_ticks'] and process['identity_check']['status']=='matching' and process['identity_still_matches']
def checked_task(thread,process,sample):
    e=thread['task_evidence'];enum=process['task_enumeration'];tid=thread['tid']
    require(e['schema_version']==1 and e['confirmed_exit'] is False,'task schema/exit authority differs')
    require(e['parent_identity']==dict(pid=process['identity']['pid'],start_ticks=process['identity']['start_ticks']) and e['parent_identity_check']==process['identity_check'],'task parent binding differs')
    require(e['enumeration_begin_ns']==enum['begin_ns'] and e['enumeration_end_ns']==enum['end_ns'] and tid in enum['selected_tids'],'enumeration binding differs')
    end=enum['end_ns']
    for name in ('stat','wchan','syscall','stack','children'):
        read=e['reads'][name];require(end<=read['begin_ns']<=read['end_ns']<=sample['end_ns'],'task read bracket differs');end=read['end_ns']
        require(read['result'].get('errno') not in (1,13),'task read permission denied')
    for read in (e['final_stat'],e['directory_presence']):
        require(end<=read['begin_ns']<=read['end_ns']<=process['identity_check']['checked_ns']<=sample['end_ns'],'final task bracket differs');end=read['end_ns']
        require(read['result'].get('errno') not in (1,13),'final task access denied')
    for name,raw in (('stat','stat'),('wchan','wchan'),('syscall','syscall'),('kernel_stack','stack')):require(thread[name]==e['reads'][raw]['result'],'raw task evidence differs')
    before=task_identity(e['reads']['stat']['result'],tid);after=task_identity(e['final_stat']['result'],tid)
    require(before==e['identity_before'] and after==e['identity_after'],'recomputed task identity differs')
    require(e['lifetime_status']==task_lifetime(before,after,e['directory_presence']['result']),'task lifetime label differs')
    require(e['lifetime_status'] not in ('tid_reused','parent_identity_not_matching') and not e['changed_since_prior'],'identity changed within calibration')
    return e
def samples(rows,context):
    previous_end=None
    for sample in (r for r in rows if r['kind']=='sample'):
        require(sample['begin_ns']<sample['end_ns'] and (previous_end is None or previous_end<=sample['begin_ns']),'sample order differs');previous_end=sample['end_ns']
        require(sample['task_visibility_schema_version']==1,'sample schema differs')
        require(not sample['process_limit_hit'],'process budget hit')
        for process in sample['processes']:
            require(process['identity']['pid']==context['target_pid'],'unexpected descendant')
            if process['status']!='sampled':continue
            if not context_matches(process,context):continue
            enum=process['task_enumeration']
            require(enum['complete'] and not process['threads_truncated'] and len(enum['selected_tids'])<=64,'task scan incomplete')
            require(enum['entries_seen']==len(enum['selected_tids']) and enum['selected_tids']==[t['tid'] for t in process['threads']] and enum['selected_tids']==sorted(set(enum['selected_tids'])),'task list differs')
            require(sample['begin_ns']<=enum['begin_ns']<=enum['end_ns']<=sample['end_ns'],'enumeration time differs')
            require(process['identity_before']['status']=='matching' and sample['begin_ns']<=process['identity_before']['checked_ns']<=enum['begin_ns'],'parent initial identity bracket differs')
            require(len(process['prior_tasks_not_listed'])<=64 and all(h['confirmed_exit'] is False for h in process['prior_tasks_not_listed']),'prior hint exit authority differs')
            for thread in process['threads']:checked_task(thread,process,sample)
            yield sample,process
def presence(rows,context):
    matches=[]
    for sample,process in samples(rows,context):
        for thread in process['threads']:
            e=thread['task_evidence'];identity=e['identity_before']
            if thread['tid']!=context['worker_tid']:continue
            stack=thread['kernel_stack']
            if identity['status']=='known' and key(identity['identity'])==(context['worker_tid'],context['worker_start_ticks']) and e['lifetime_status']=='matching' and stack['status']=='ok' and not stack['truncated'] and stack['text'].strip():matches.append(sample)
    require(len(matches)>=2,'two live worker observations required')
    return dict(samples=len(matches),first_begin_ns=matches[0]['begin_ns'],last_end_ns=matches[-1]['end_ns'])
def absence(rows,context,joined):
    require(joined['joined'] is True and all(joined[k]==context[k] for k in context),'controlled join context differs')
    for sample,process in samples(rows,context):
        if sample['end_ns']<joined['release_ns']:continue
        for hint in process['prior_tasks_not_listed']:
            if key(hint['identity'])==(context['worker_tid'],context['worker_start_ticks']) and hint['status']=='not_in_complete_enumeration' and hint['confirmed_exit'] is False and context['worker_tid'] not in process['task_enumeration']['selected_tids'] and process['task_enumeration']['begin_ns']>=joined['release_ns']:
                return dict(kind='not_in_complete_enumeration',sample_begin_ns=sample['begin_ns'],sample_end_ns=sample['end_ns'],candidate_confirmed_exit=False)
        for thread in process['threads']:
            e=thread['task_evidence']
            if thread['tid']!=context['worker_tid'] or e['directory_presence']['begin_ns']<joined['release_ns']:continue
            identity=e['identity_before'].get('identity') or e['prior_sample_identity_hint']
            if identity and key(identity)==(context['worker_tid'],context['worker_start_ticks']) and e['lifetime_status'] in ('absent_after_identified_read','absent_without_current_identity') and e['directory_presence']['result']==dict(status='absent',errno=2):
                return dict(kind=e['lifetime_status'],sample_begin_ns=sample['begin_ns'],sample_end_ns=sample['end_ns'],candidate_confirmed_exit=False)
    raise ValueError('controlled absence evidence unavailable')
def assess(data):
    load=lambda name:json.loads((data/name).read_text())
    result=load('result.json');require(result['status']=='passed','fixture supervisor failed');child=result['shutdown']['children'][0]
    require(result['shutdown']['passed'] and child['passed'] and not child['forced_kill'] and child['returncode']==0 and 0<=child['end_ns']-child['signal_begin_ns']<=5_000_000_000,'child shutdown failed')
    info=load('target-info.json');context=load('fixture-ready.json');joined=load('worker-joined.json')
    require(context['target_pid']==child['pid']==info['pid'] and context['target_start_ticks']==info['start_ticks'] and context['calibration_id']==info['calibration_id']==result['calibration_id'],'fixture identity differs')
    for role in (info['permissions'],info['supervisor_permissions'],load('target-before-signal.json')['target'],load('target-before-signal.json')['supervisor'],load('target-supervisor-final.json')):require_role(role,0)
    events=[json.loads(x) for x in (data/'observer-exec.jsonl').read_text().splitlines()]
    require([x['kind'] for x in events]==['entry','preexec_verified','exec_begin'],'observer bootstrap differs');require_role(events[1]['permissions'],1<<21)
    require(all(e.get('collector_sha256')==CANDIDATE_SHA and e.get('task_visibility') is True for e in events[1:]),'collector activation binding differs')
    require(events[2]['target']==dict(pid=info['pid'],start_ticks=info['start_ticks']) and events[1]['profile_sha256']==hashlib.sha256((Path(__file__).parent/'observer-seccomp.json').read_bytes()).hexdigest(),'exec target/profile differs')
    text=(data/'blocked-target-shutdown-stacks.jsonl').read_text();require(text.endswith('\n'),'incomplete final observer record');rows=snapshot(text);begin=rows[0];footer=rows[-1];ready=load('blocked-target-shutdown-stacks.ready.json')
    live_header(rows,context)
    require(begin['kind']=='begin' and begin['mode']=='procfs' and begin['observer_independent'] and begin['task_visibility_schema_version']==1 and begin['task_history_capacity']==512,'observer task mode differs')
    require(begin['root']==dict(pid=info['pid'],start_ticks=info['start_ticks']) and begin['pid']!=info['pid'] and begin['pid']==events[0]['pid']==ready['pid'] and ready['ready_ns']<=child['signal_begin_ns'],'observer identity/readiness differs')
    require(begin['boot_id']['text'].strip()==info['boot_id']==events[1]['boot_id'] and all(zero_offsets(s) for s in (begin['time_namespace_offsets']['text'],info['time_namespace_offsets'],events[1]['time_namespace_offsets'])),'observer clock origin differs')
    require(footer['kind']=='status' and footer['completed'] and not footer['budget_exhausted'] and not footer['userspace_stacks_requested'] and footer['samples']<=48,'observer budget/finalization differs')
    require(footer['samples']==sum(r['kind']=='sample' for r in rows) and footer['sample_limit']==48 and all(r['kind']=='sample' for r in rows[1:-1]),'observer record population differs')
    counts={True:0,False:0}
    for r in rows:
        if r['kind']=='sample':
            for p in r['processes']:
                for t in p.get('threads',[]):counts[t['kernel_stack']['status']=='ok']+=1
    require(counts[True]==footer['kernel_stack_reads_ok'] and counts[False]==footer['kernel_stack_reads_unavailable'],'observer footer counts differ')
    stages=[json.loads(x) for x in (data/'task-stages.jsonl').read_text().splitlines()]
    expected=['worker_started','fixture_ready','worker_release','worker_return','worker_joined','fixture_sigint','fixture_exit']
    require([r['point'] for r in stages]==expected and [r['sequence'] for r in stages]==list(range(1,8)) and all(r['pid']==child['pid'] and r['calibration_id']==context['calibration_id'] for r in stages),'controlled stage sequence differs')
    require(all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(stages,stages[1:])) and stages[2]['release_ns']==joined['release_ns']<=joined['monotonic_ns']<=child['signal_begin_ns']<=stages[5]['monotonic_ns']<=stages[6]['monotonic_ns']<=child['end_ns'],'controlled stage times differ')
    require(key(stages[0]['task_identity'])==(context['worker_tid'],context['worker_start_ticks']) and stages[0]['tid']==stages[3]['tid']==context['worker_tid'] and all(stages[i]['tid']==child['pid'] for i in (1,2,4,5,6)) and stages[4]['monotonic_ns']<=joined['monotonic_ns'],'worker registration/join differs')
    pre=[r for r in rows if r['kind']!='sample' or r['end_ns']<child['signal_begin_ns']]
    live=presence([r for r in pre if r['kind']!='sample' or r['end_ns']<joined['release_ns']],context);gone=absence(pre,context,joined)
    require(live['last_end_ns']<joined['release_ns'] and gone['sample_end_ns']<child['signal_begin_ns'],'phase ordering differs')
    return dict(status='passed',scope='one controlled task and schema/access only; no N1 rerun, race guarantee or campaign qualification',live_task=live,controlled_absence=gone,candidate_confirmed_exit=False,post_signal_task_read_availability_not_qualified=True)
