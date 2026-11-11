"""Read-only lifecycle assessment: missing PID is not reused PID or a read error."""
WORKER_NAMES={'robotweax-journ','robotweax-journal-worker'}


def join_end(stages,root_pid):
    if not stages or any(r['pid']!=root_pid or r['dropped_before'] for r in stages) or [r['sequence'] for r in stages]!=list(range(1,len(stages)+1)):raise ValueError('stage identity/sequence/drop failure')
    pairs={name:[r for r in stages if r['point']==name] for name in ('worker_join_begin','worker_join_end')}
    if any(len(pairs[n])!=1 for n in pairs):return None
    begin,end=pairs['worker_join_begin'][0],pairs['worker_join_end'][0]
    if begin['tid']!=end['tid'] or begin['monotonic_ns']>end['monotonic_ns'] or begin['sequence']>=end['sequence']:raise ValueError('worker join stage order/thread failure')
    return end['monotonic_ns']


def coverage(rows,child,stages):
    first,footer=rows[0],rows[-1];root=first['root'];root_key=(root['pid'],root['start_ticks'])
    if first['kind']!='begin' or first['mode']!='procfs' or not first['observer_independent'] or root['pid']!=child['pid'] or first['pid']==child['pid']:raise ValueError('observer identity/mode failure')
    if footer.get('kind')!='status' or not footer['completed'] or footer['budget_exhausted']:raise ValueError('observer finalization/budget failure')
    joined=join_end(stages,root['pid']);registered=set();confirmed=set();available=0;post=[];samples=[]
    for sample in (r for r in rows if r['kind']=='sample'):
        if sample['process_limit_hit']:raise ValueError('observer process budget exceeded')
        in_wait=sample['end_ns']<=child['end_ns']
        if in_wait:
            samples.append(sample)
            if child['signal_end_ns']<=sample['begin_ns']:post.append(sample)
        for process in sample['processes']:
            expected=process['identity'];key=(expected['pid'],expected['start_ticks']);check=process.get('identity_check')
            if not check or not sample['begin_ns']<=check['checked_ns']<=sample['end_ns']:raise ValueError('explicit identity evidence unavailable')
            state=check['status']
            if state in ('pid_reused','identity_unavailable'):raise ValueError('PID reuse or identity read failure: '+state)
            if state=='process_missing':
                if check.get('errno')!=2:raise ValueError('missing PID lacks explicit ENOENT')
                if process['status']!='process_missing':raise ValueError('identity changed during a thread sample')
                if key==root_key:
                    if sample['begin_ns']<child['end_ns']:raise ValueError('root disappearance before supervisor reap')
                    continue
                if key not in registered or joined is None or not child['signal_end_ns']<=joined<=check['checked_ns']:raise ValueError('worker disappearance not confirmed by registered identity and join')
                confirmed.add(key);continue
            if state!='matching' or process['status']!='sampled' or not process['identity_still_matches'] or process['threads_truncated']:raise ValueError('live target observation incomplete')
            if check['observed']['pid']!=expected['pid'] or check['observed']['start_ticks']!=expected['start_ticks']:raise ValueError('matching identity evidence inconsistent')
            if sample['end_ns']<=child['signal_begin_ns'] and expected.get('ppid')==root['pid'] and expected.get('name') in WORKER_NAMES:registered.add(key)
            if len(registered)>1:raise ValueError('ambiguous worker registration')
            if in_wait:
                for thread in process['threads']:
                    stack=thread['kernel_stack']
                    if stack['status']!='ok' or stack['truncated']:raise ValueError('live target kernel stack unavailable')
                    if stack['text'].strip():available+=1
    if not available:raise ValueError('no real bridge kernel-stack sample')
    if child['forced_kill'] and (len(post)<2 or not any(t['kernel_stack'].get('text','').strip() for s in post for p in s['processes'] for t in p.get('threads',[]))):raise ValueError('shutdown failure lacks bounded post-signal stack coverage')
    return dict(samples=len(samples),post_signal_samples=len(post),nonempty_kernel_stacks=available,confirmed_worker_exits=[dict(pid=p,start_ticks=t) for p,t in sorted(confirmed)],worker_join_end_ns=joined,scope='registered worker absent after join completion; no worker exit-code/cause claim',clean_fast_exit_may_have_no_post_signal_sample=True)
