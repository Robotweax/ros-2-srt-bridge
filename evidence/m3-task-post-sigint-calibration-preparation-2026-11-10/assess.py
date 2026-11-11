"""One prospective native post-SIGINT fixture; no campaign acceptance authority."""
import hashlib
import json
from pathlib import Path
from assessment_binding import metadata,lifecycle
from m3_observer_filtering import require_role
from plan import CANDIDATE_SHA
require=metadata.require

def snapshot(text):return [json.loads(line) for line in text.splitlines(keepends=True) if line.endswith('\n')]
def live_header(rows,context):
    require(bool(rows),'observer header unavailable');b=rows[0]
    require(b['kind']=='begin' and b['root']==dict(pid=context['target_pid'],start_ticks=context['target_start_ticks']) and b['task_visibility_schema_version']==1,'observer live identity/schema differs')
    return b
def prefix_metadata(rows,context):
    live_header(rows,context);require(all(r['kind']=='sample' for r in rows[1:]),'observer stopped before phase proof')
    require(len(rows)>1,'observer samples unavailable')
    # Derived prefix footer is only for incremental validation, never native proof.
    tasks=[t for r in rows[1:] for p in r['processes'] for t in p.get('threads',[])]
    footer=dict(kind='status',completed=True,budget_exhausted=False,userspace_stacks_requested=False,samples=len(rows)-1,sample_limit=48,kernel_stack_reads_ok=sum(t['kernel_stack']['status']=='ok' for t in tasks),kernel_stack_reads_unavailable=sum(t['kernel_stack']['status']!='ok' for t in tasks))
    proof=metadata.assess_metadata([*rows,footer],dict(pid=context['target_pid'],start_ticks=context['target_start_ticks']))
    require(all(len(r['processes'])==1 and r['processes'][0]['identity']['pid']==context['target_pid'] and r['processes'][0]['status']=='sampled' for r in proof['rows']),'unexpected descendant or missing target')
    return proof
def task_key(t):return t['tid'],t['start_ticks']
def presence(rows,context,after_ns=None):
    proof=prefix_metadata(rows,context);matched=[]
    for r in proof['rows']:
        if after_ns is not None and r['begin_ns']<after_ns:continue
        for p in r['processes']:
            for t in p['tasks']:
                if t['classification']=='readable_task' and t['nonempty_readable_stack'] and task_key(t['task_identity'])==(context['worker_tid'],context['worker_start_ticks']):matched.append(r)
    require(len(matched)>=2,'two live worker observations required')
    return dict(samples=len(matched),first_begin_ns=matched[0]['begin_ns'],last_end_ns=matched[-1]['end_ns'])
def absence(rows,context,joined,waiting):
    require(joined['joined'] is True and all(joined[k]==context[k] for k in context),'controlled join context differs')
    require(all(waiting[k]==context[k] for k in context) and waiting['wait_enter_ns']<joined['release_ns']<=joined['monotonic_ns'],'post-signal join/wait order differs')
    proof=prefix_metadata(rows,context)
    for r in proof['rows']:
        for p in r['processes']:
            for t in p['disappearances']:
                if task_key(t['task_identity'])==(context['worker_tid'],context['worker_start_ticks']) and t['observed_begin_ns']>=joined['monotonic_ns']:
                    return dict(kind=t['classification'],observed_begin_ns=t['observed_begin_ns'],observed_end_ns=t['observed_end_ns'],sample_begin_ns=r['begin_ns'],sample_end_ns=r['end_ns'],confirmed_exit=False)
    raise ValueError('controlled absence evidence unavailable')
def assess(data):
    load=lambda n:json.loads((data/n).read_text())
    result=load('result.json');require(result['status']=='passed' and result['shutdown']['passed'] and len(result['shutdown']['children'])==1,'fixture supervisor failed');child=result['shutdown']['children'][0]
    require(child['passed'] and child['signal_sent'] and not child['forced_kill'] and child['returncode']==0 and child['signal_begin_ns']<=child['signal_end_ns']<=child['end_ns']<=child['signal_begin_ns']+5_000_000_000,'child shutdown failed')
    info=load('target-info.json');context=load('fixture-ready.json');joined=load('worker-joined.json');waiting=load('signal-wait.json');seen=load('signal-seen.json')
    require(context['target_pid']==child['pid']==info['pid'] and context['target_start_ticks']==info['start_ticks'] and context['calibration_id']==info['calibration_id']==result['calibration_id'],'fixture identity differs')
    for control in (waiting,seen):require(all(control[k]==context[k] for k in context),'signal witness context differs')
    require(child['signal_end_ns']<=waiting['wait_enter_ns']<joined['release_ns'] and child['signal_begin_ns']<=seen['monotonic_ns']<joined['release_ns'],'signal/wait/release order differs')
    for role in (info['permissions'],info['supervisor_permissions'],load('target-before-signal.json')['target'],load('target-before-signal.json')['supervisor'],load('target-supervisor-final.json')):require_role(role,0)
    events=[json.loads(x) for x in (data/'observer-exec.jsonl').read_text().splitlines()]
    require([x['kind'] for x in events]==['entry','preexec_verified','exec_begin'],'observer bootstrap differs');require_role(events[1]['permissions'],1<<21)
    require(all(e.get('collector_sha256')==CANDIDATE_SHA and e.get('task_visibility') is True for e in events[1:]),'collector activation binding differs')
    require(events[2]['target']==dict(pid=info['pid'],start_ticks=info['start_ticks']) and events[1]['profile_sha256']==hashlib.sha256((Path(__file__).parent/'observer-seccomp.json').read_bytes()).hexdigest(),'exec target/profile differs')
    text=(data/'blocked-target-shutdown-stacks.jsonl').read_text();require(text.endswith('\n'),'incomplete final observer record');rows=snapshot(text);begin=live_header(rows,context);ready=load('blocked-target-shutdown-stacks.ready.json')
    require(begin['pid']==events[0]['pid']==ready['pid'] and ready['ready_ns']<=child['signal_begin_ns'],'observer identity/readiness differs')
    require(begin['boot_id']['text'].strip()==info['boot_id']==events[1]['boot_id'],'observer boot differs')
    metadata.offsets(dict(status='ok',truncated=False,text=info['time_namespace_offsets']));metadata.offsets(dict(status='ok',truncated=False,text=events[1]['time_namespace_offsets']))
    proof=metadata.assess_metadata(rows,dict(pid=info['pid'],start_ticks=info['start_ticks']))
    require(all(len(r['processes'])==1 and r['processes'][0]['identity']['pid']==context['target_pid'] for r in proof['rows']),'unexpected descendant or missing target')
    stages=[json.loads(x) for x in (data/'task-stages.jsonl').read_text().splitlines()]
    points=['worker_started','fixture_ready','fixture_sigint','worker_release','worker_return','worker_joined','absence_acknowledged','fixture_exit']
    require([r['point'] for r in stages]==points and [r['sequence'] for r in stages]==list(range(1,9)) and all(r['pid']==child['pid'] and r['calibration_id']==context['calibration_id'] and r['dropped_before']==0 for r in stages),'controlled stage sequence differs')
    require(all(a['monotonic_ns']<=b['monotonic_ns'] for a,b in zip(stages,stages[1:])) and stages[2]['monotonic_ns']==seen['monotonic_ns'] and stages[3]['monotonic_ns']==joined['release_ns'] and stages[5]['monotonic_ns']==joined['monotonic_ns'] and stages[-1]['monotonic_ns']<=child['end_ns'],'controlled stage times differ')
    require(task_key(stages[0]['task_identity'])==(context['worker_tid'],context['worker_start_ticks']) and stages[0]['tid']==stages[4]['tid']==context['worker_tid'] and all(stages[i]['tid']==child['pid'] for i in (1,2,3,5,6,7)),'worker registration/join differs')
    prefix=rows[:-1];pre=presence([r for r in prefix if r['kind']!='sample' or r['end_ns']<child['signal_begin_ns']],context)
    post=presence([r for r in prefix if r['kind']!='sample' or r['end_ns']<joined['release_ns']],context,after_ns=max(waiting['wait_enter_ns'],seen['monotonic_ns']))
    gone=absence(prefix,context,joined,waiting)
    require(gone['observed_end_ns']<=stages[6]['absence_end_ns']<=stages[6]['monotonic_ns']<=stages[-1]['monotonic_ns']<=child['end_ns'],'absence acknowledgement/reap order differs')
    # Synthetic fixture stages remain distinct from SDK join stages. Candidate
    # join_end validates sequence/identity; no worker-process exit credit is needed.
    adapted=dict(child,start_ticks=info['start_ticks']);coverage=lifecycle.coverage(rows,adapted,stages)
    require(len(coverage['observed_task_disappearances'])==1 and coverage['confirmed_task_exits']==0 and not coverage['confirmed_worker_exits'],'unexpected lifecycle disappearance/exit population')
    return dict(status='passed',scope='one controlled native post-SIGINT metadata/lifecycle fixture only; no N1 rerun or campaign qualification',pre_signal_live=pre,post_signal_live=post,controlled_absence=gone,candidate_metadata=proof,candidate_lifecycle=coverage,confirmed_task_exits=0,limitations=['no exact mid-read race guarantee','no no-reuse guarantee','no SDK/ROS/SRT workload or overhead equivalence'])
