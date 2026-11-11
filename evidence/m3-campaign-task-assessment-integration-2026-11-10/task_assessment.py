"""Offline schema1 task observations; absence is never a readable stack or exit."""
import hashlib
from pathlib import Path
import types
ROOT=Path(__file__).resolve().parents[2]
COLLECTOR=ROOT/'evidence/m3-task-identity-visibility-2026-11-10/shutdown_observer.py'
COLLECTOR_SHA='6deab3c5e83e48b7c33dbbb4613c361469d9b62aa1bea86db0c1a8012cfae72e'
source=COLLECTOR.read_bytes()
if hashlib.sha256(source).hexdigest()!=COLLECTOR_SHA:raise ValueError('task parser source binding differs')
_collector=types.ModuleType('_robotweax_task_assessment_schema1');_collector.__file__=str(COLLECTOR)
exec(compile(source,str(COLLECTOR),'exec'),_collector.__dict__)

def require(value,message):
    if not value:raise ValueError(message)
def integer(value,maximum=2**64-1):return type(value) is int and 0<=value<=maximum
def process_key(value):
    require(integer(value['pid'],2**31-1) and value['pid']>0 and integer(value['start_ticks']) and value['start_ticks']>0,'invalid process identity')
    return value['pid'],value['start_ticks']
def task_key(value):
    require(integer(value['tid'],2**31-1) and value['tid']>0 and integer(value['start_ticks']) and value['start_ticks']>0,'invalid task identity')
    return value['tid'],value['start_ticks']
def bracket(value,low,high,label):
    require(integer(value['begin_ns']) and integer(value['end_ns']) and low<=value['begin_ns']<=value['end_ns']<=high,label+' bracket invalid')
def raw(value):
    if value['status']=='ok':
        require(value['truncated'] is False and isinstance(value['text'],str) and len(value['text'].encode('utf-8'))<=16384,'truncated or invalid task read')
        return 'ok'
    require(value['status']=='unavailable' and value.get('error')=='FileNotFoundError' and type(value.get('errno')) is int and value['errno']==2,'task read error is not supported absence')
    return 'missing'
def identity_check(check,expected,low,high):
    require(check['status']=='matching' and process_key(check['observed'])==expected and integer(check['checked_ns']) and low<=check['checked_ns']<=high,'process identity/read bracket mismatch')
def offsets(value):
    require(value['status']=='ok' and value['truncated'] is False,'clock origin unavailable')
    lines=value['text'].splitlines()
    require(len(lines)==2 and {r.split()[0] for r in lines}=={'monotonic','boottime'} and all(len(r.split())==3 and all(int(n)==0 for n in r.split()[1:]) for r in lines),'time namespace differs')

def task(thread,process,sample,previous):
    tid=thread['tid'];e=thread['task_evidence'];enum=process['task_enumeration'];pk=process_key(process['identity'])
    require(type(e['schema_version']) is int and e['schema_version']==1 and e['confirmed_exit'] is False,'task schema/exit authority differs')
    require(process_key(e['parent_identity'])==pk and e['parent_identity_check']==process['identity_check'],'task parent binding differs')
    require(e['enumeration_begin_ns']==enum['begin_ns'] and e['enumeration_end_ns']==enum['end_ns'] and tid in enum['selected_tids'],'task enumeration binding differs')
    require(e['prior_sample_identity_hint']==previous,'task prior hint not supported by previous sample')
    end=enum['end_ns'];states=[];first_missing=None
    for name in ('stat','wchan','syscall','stack','children'):
        read=e['reads'][name];bracket(read,end,sample['end_ns'],name);end=read['end_ns'];state=raw(read['result']);states.append(state)
        if state=='missing' and first_missing is None:first_missing=read['begin_ns']
    final=e['final_stat'];presence=e['directory_presence'];bracket(final,end,sample['end_ns'],'final stat');states.append(raw(final['result']))
    if states[-1]=='missing' and first_missing is None:first_missing=final['begin_ns']
    bracket(presence,final['end_ns'],process['identity_check']['checked_ns'],'directory presence')
    for old,new in (('stat','stat'),('wchan','wchan'),('syscall','syscall'),('kernel_stack','stack')):require(thread[old]==e['reads'][new]['result'],'raw task result disagrees with metadata')
    before=_collector.task_identity(e['reads']['stat']['result'],tid);after=_collector.task_identity(final['result'],tid)
    require(before==e['identity_before'] and after==e['identity_after'],'recomputed task identity differs')
    require(before['status'] in ('known','missing') and after['status'] in ('known','missing'),'task identity invalid or unavailable')
    for identity in (before,after):
        if tid==pk[0] and identity['status']=='known':require(identity['identity']['start_ticks']==pk[1],'root task incarnation differs from process')
    observed=before if before['status']=='known' else after
    changed=bool(previous and observed['status']=='known' and previous['start_ticks']!=observed['identity']['start_ticks'])
    require(type(e['changed_since_prior']) is bool and e['changed_since_prior']==changed and not changed,'task incarnation changed since previous sample')
    if before['status']=='known' and after['status']=='known':require(task_key(before['identity'])==task_key(after['identity']),'task incarnation changed within read bracket')
    d=presence['result'];label=_collector.task_lifetime(before,after,d)
    require(e['lifetime_status']==label,'task lifetime label differs')
    result=dict(tid=tid,classification=None,task_identity=None,raw_stack_status=thread['kernel_stack']['status'],nonempty_readable_stack=False,confirmed_exit=False,observed_begin_ns=None,observed_end_ns=None)
    if label=='matching':
        require(all(s=='ok' for s in states) and d['status']=='present' and integer(d['inode']) and integer(d['device']),'live task read/presence unavailable')
        result.update(classification='readable_task',task_identity=before['identity'],nonempty_readable_stack=bool(thread['kernel_stack']['text'].strip()))
        return result,after['identity']
    require(label in ('absent_after_identified_read','absent_without_current_identity') and d['status']=='absent' and type(d.get('errno')) is int and d['errno']==2,'task absence not supported by final stat/directory evidence')
    # Once an ENOENT appears, a later readable file is ambiguous, not teardown proof.
    require('missing' in states and states[states.index('missing'):]==['missing']*(len(states)-states.index('missing')),'task reappeared or partial read error during absence bracket')
    if before['status']=='known':identity=before['identity'];classification='observed_disappearance_after_identity'
    else:
        require(previous is not None and all(s=='missing' for s in states),'missing task lacks current or previous identity evidence')
        identity=previous;classification='observed_absence_after_prior_identity'
    result.update(classification=classification,task_identity=identity,observed_begin_ns=first_missing,observed_end_ns=presence['end_ns'])
    return result,None

def _assess(rows,expected_root):
    require(len(rows)>=3,'observer capture incomplete');begin,footer=rows[0],rows[-1];root=process_key(begin['root'])
    require(begin['kind']=='begin' and begin['clock']=='monotonic' and begin['mode']=='procfs' and begin['observer_independent'] is True and begin['kernel_stacks_only'] is True and integer(begin['pid'],2**31-1) and begin['pid']>0 and begin['pid']!=root[0],'observer mode/identity differs')
    require(type(begin.get('task_visibility_schema_version')) is int and begin['task_visibility_schema_version']==1 and begin.get('task_history_capacity')==512,'task visibility schema1 required')
    if expected_root is not None:require(root==process_key(expected_root),'registered root differs')
    require(begin['boot_id']['status']=='ok' and begin['boot_id']['truncated'] is False and bool(begin['boot_id']['text'].strip()),'boot identity unavailable');offsets(begin['time_namespace_offsets'])
    require(footer['kind']=='status' and footer['completed'] is True and footer['budget_exhausted'] is False and footer['userspace_stacks_requested'] is False and type(footer['sample_limit']) is int and footer['sample_limit']==48,'observer finalization/budget differs')
    samples=rows[1:-1];require(all(r['kind']=='sample' for r in samples) and integer(footer['samples'],48) and footer['samples']==len(samples),'sample population differs')
    cache={};pid_epochs={};known_pids={root[0]};proofs=[];previous_end=0;raw_ok=raw_missing=readable=nonempty=absent=0
    for index,sample in enumerate(samples,1):
        require(type(sample['task_visibility_schema_version']) is int and sample['task_visibility_schema_version']==1 and sample['process_limit_hit'] is False and 0<len(sample['processes'])<=8,'sample schema/process budget differs')
        bracket(sample,previous_end,2**64-1,'sample');require(sample['begin_ns']<sample['end_ns'],'empty sample interval');previous_end=sample['end_ns'];seen=set();processes=[]
        for process in sample['processes']:
            pk=process_key(process['identity']);require(pk[0] not in seen,'duplicate process record');seen.add(pk[0])
            require(pk[0] not in pid_epochs or pid_epochs[pk[0]]==pk[1],'observed process PID reuse');pid_epochs[pk[0]]=pk[1]
            if pk[0]==root[0]:require(pk==root,'root incarnation differs')
            check=process['identity_check'];require(integer(check['checked_ns']) and sample['begin_ns']<=check['checked_ns']<=sample['end_ns'],'process check outside sample')
            if process['status']=='process_missing':
                require(check['status']=='process_missing' and check.get('errno')==2 and not process.get('threads'),'missing process evidence differs');cache.pop(pk,None)
                processes.append(dict(identity=process['identity'],status='process_missing',tasks=[],disappearances=[]));continue
            require(process['status']=='sampled' and process['identity_still_matches'] is True and process['threads_truncated'] is False,'process observation unavailable or truncated')
            enum=process['task_enumeration'];bracket(enum,sample['begin_ns'],sample['end_ns'],'enumeration')
            identity_check(process['identity_before'],pk,sample['begin_ns'],enum['begin_ns']);identity_check(check,pk,enum['end_ns'],sample['end_ns'])
            tids=[t['tid'] for t in process['threads']]
            require(len(tids)<=64 and all(integer(t,2**31-1) and t>0 for t in tids) and tids==sorted(set(tids)) and enum['selected_tids']==tids and enum['complete'] is True and integer(enum['entries_seen'],64) and enum['entries_seen']==len(tids),'task enumeration incomplete or inconsistent')
            previous=cache.get(pk,{});current={};tasks=[];gone=[];last_read=enum['end_ns']
            for thread in process['threads']:
                require(thread['task_evidence']['reads']['stat']['begin_ns']>=last_read,'task reads overlap or run backwards');item,identity=task(thread,process,sample,previous.get(thread['tid']));tasks.append(item);last_read=thread['task_evidence']['directory_presence']['end_ns']
                raw_ok+=thread['kernel_stack']['status']=='ok';raw_missing+=thread['kernel_stack']['status']!='ok'
                if item['classification']=='readable_task':readable+=1;nonempty+=item['nonempty_readable_stack']
                else:gone.append(item);absent+=1
                if identity is not None:current[thread['tid']]=identity
            expected_hints=[dict(identity=identity,status='not_in_complete_enumeration',confirmed_exit=False) for tid,identity in sorted(previous.items()) if tid not in tids]
            require(process['prior_tasks_not_listed']==expected_hints,'missing/forged/stale prior enumeration hint')
            for hint in expected_hints:
                gone.append(dict(tid=hint['identity']['tid'],classification='not_enumerated_after_prior_identity',task_identity=hint['identity'],raw_stack_status='not_attempted',nonempty_readable_stack=False,confirmed_exit=False,observed_begin_ns=enum['begin_ns'],observed_end_ns=enum['end_ns']));absent+=1
            cache[pk]=current;require(len(cache)<=8 and sum(len(v) for v in cache.values())<=512,'task history budget exceeded')
            processes.append(dict(identity=process['identity'],status='sampled',tasks=tasks,disappearances=gone))
        require(known_pids<=seen,'known process omitted from sample');known_pids.update(seen)
        proofs.append(dict(row=index,begin_ns=sample['begin_ns'],end_ns=sample['end_ns'],processes=processes))
    require(integer(footer['kernel_stack_reads_ok']) and integer(footer['kernel_stack_reads_unavailable']) and footer['kernel_stack_reads_ok']==raw_ok and footer['kernel_stack_reads_unavailable']==raw_missing,'raw stack footer population differs')
    return dict(status='consistent_metadata_only',scope='task observations only; no capture-origin attestation, exit/no-reuse guarantee or campaign acceptance',parser_collector_sha256=COLLECTOR_SHA,root=begin['root'],samples=len(samples),readable_task_records=readable,nonempty_readable_stacks=nonempty,observed_disappearances=absent,raw_stack_reads_ok=raw_ok,raw_stack_reads_unavailable=raw_missing,confirmed_task_exits=0,rows=proofs)

def assess_metadata(rows,expected_root=None):
    try:return _assess(rows,expected_root)
    except (KeyError,TypeError,IndexError,AttributeError) as error:raise ValueError('incomplete or invalid task metadata: '+str(error)) from error
