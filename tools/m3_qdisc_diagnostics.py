#!/usr/bin/env python3
"""Opt-in owned-container CONTROL tc pass-action counters and root qdisc polling.

The classifier executes a PASS verdict; it is an observer intervention, not the
passive AF_PACKET hook. Its placement must be qualified by the synthetic probe.
Counters cover selected UDP ports/peer, not authenticated SRT socket identities.
"""
import argparse,json,subprocess,time
from pathlib import Path
from m3_control_fault import selector as fault_selector

PREF='49150'
PERIOD_NS=200000000
LIMIT=37500


def selector(role,peer):
    args=fault_selector(role,peer);args[args.index('pref')+1]=PREF;args[-1]='pass';return args


def counters(filters):
    if not isinstance(filters,list) or any(r.get('pref',int(PREF))!=int(PREF) or r.get('kind')!='u32' or r.get('protocol')!='ip' for r in filters):raise ValueError('unexpected pass classifier')
    rules=[r['options'] for r in filters if r.get('options',{}).get('actions')]
    if len(rules)!=1 or rules[0].get('not_in_hw') is not True:raise ValueError('ambiguous or offloaded pass rule')
    actions=rules[0]['actions']
    if len(actions)!=1 or actions[0].get('kind')!='gact' or actions[0].get('control_action',{}).get('type')!='pass':raise ValueError('not a pure pass action')
    if actions[0].get('prob',{}).get('random_type','none')!='none':raise ValueError('probabilistic pass action')
    stats=actions[0]['stats']
    if any(type(stats.get(k)) is not int or stats[k]<0 for k in ('packets','bytes','drops')) or stats['drops']:raise ValueError('invalid pass counters')
    return {k:stats[k] for k in ('packets','bytes','drops')}


def root(qdiscs):
    roots=[q for q in qdiscs if q.get('root')]
    if len(roots)!=1:raise ValueError('ambiguous root qdisc')
    q=roots[0]
    for k in ('packets','bytes','drops','overlimits','backlog','qlen'):
        if type(q.get(k)) is not int or q[k]<0:raise ValueError('invalid root counter/gauge')
    return {k:q[k] for k in ('kind','handle','packets','bytes','drops','overlimits','backlog','qlen')}


def query(args):
    before=time.monotonic_ns();p=subprocess.run(args,capture_output=True,text=True,timeout=1);after=time.monotonic_ns()
    if p.returncode or len(p.stdout)>32768:raise ValueError('tc query failed/exceeded bound')
    return json.loads(p.stdout),[before,after]


def observe():
    begin=time.monotonic_ns();value={};error=None
    try:
        rules,span=query(['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF]);value.update(pass_counter=counters(rules),filter_read_ns=span)
        qdiscs,span=query(['tc','-j','-s','qdisc','show','dev','eth0']);value.update(root=root(qdiscs),root_read_ns=span)
    except (OSError,ValueError,subprocess.TimeoutExpired) as failure:error=type(failure).__name__
    return dict(begin_ns=begin,end_ns=time.monotonic_ns(),error=error,**value)


def install(lab):
    configured={}
    for role in lab.containers:
        peer='robot' if role=='operator' else 'operator'
        state=json.loads(lab.inside(role,'qdisc-observer-before-'+role,['tc','-j','-s','qdisc','show','dev','eth0']))
        if any(q['kind'] in ('clsact','ingress') for q in state):raise ValueError('refusing existing classifier hook')
        before=next(q for q in state if q.get('root'))
        lab.inside(role,'qdisc-observer-hook-'+role,['tc','qdisc','add','dev','eth0','clsact'])
        lab.inside(role,'qdisc-observer-install-'+role,selector(role,lab.addresses[peer]))
        rules=json.loads(lab.inside(role,'qdisc-observer-rule-'+role,['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF]))
        configured[role]=dict(initial=counters(rules),selector=selector(role,lab.addresses[peer]))
        after=json.loads(lab.inside(role,'qdisc-observer-after-'+role,['tc','-j','-s','qdisc','show','dev','eth0']))
        current=next(q for q in after if q.get('root'))
        if any(before.get(k)!=current.get(k) for k in ('kind','handle','options')):raise ValueError('observer changed root configuration')
    return dict(roles=configured,scope='dedicated software UDP CONTROL pass-action observer; root configuration retained; observer executes PASS and adds work, not default fixture')


def sample(out,ready,stop):
    status=out.with_suffix('.status.json')
    if status.exists() or ready.exists():raise FileExistsError('qdisc outputs exist')
    file=out.open('x');count=0;complete=False
    try:
        with file:
            for sequence in range(1,LIMIT+1):
                row=observe();row['sequence']=sequence;file.write(json.dumps(row)+'\n');file.flush();count=sequence
                if not row['error'] and not ready.exists():ready.write_text(json.dumps(dict(ready_ns=row['end_ns'])))
                if stop.exists():complete=True;break
                time.sleep(max(0,(row['begin_ns']+PERIOD_NS-time.monotonic_ns())/1e9))
    finally:
        with status.open('x') as f:f.write(json.dumps(dict(complete=complete,records=count,limit=LIMIT,finished_ns=time.monotonic_ns()))+'\n')
    if not complete:raise RuntimeError('qdisc observer budget exhausted')


def summarize(path):
    status=json.loads(path.with_suffix('.status.json').read_text());previous=None;count=span=gap=0;identity=None;first=None
    with path.open() as file:
        for line in file:
            if len(line)>8192:raise ValueError('qdisc sample bound exceeded')
            row=json.loads(line);count+=1
            if row['error'] or row['sequence']!=count or not 0<row['begin_ns']<=row['end_ns'] or previous and row['begin_ns']<previous['end_ns']:raise ValueError('invalid/error qdisc sample')
            f=row['filter_read_ns'];r=row['root_read_ns']
            if not row['begin_ns']<=f[0]<=f[1]<=r[0]<=r[1]<=row['end_ns']:raise ValueError('invalid tc read brackets')
            current=(row['root']['kind'],row['root']['handle'])
            if identity and current!=identity:raise ValueError('root qdisc identity changed')
            identity=current
            for group,keys in (('pass_counter',('packets','bytes','drops')),('root',('packets','bytes','drops','overlimits'))):
                if any(type(row[group].get(k)) is not int or row[group][k]<0 for k in keys):raise ValueError('invalid tc counters')
                if previous and any(row[group][k]<previous[group][k] for k in keys):raise ValueError('tc counter regression')
            if row['pass_counter']['drops']:raise ValueError('pass action dropped packets')
            for k in ('backlog','qlen'):
                if type(row['root'][k]) is not int or row['root'][k]<0:raise ValueError('invalid qdisc gauge')
            span=max(span,row['end_ns']-row['begin_ns'])
            if previous:gap=max(gap,row['begin_ns']-previous['begin_ns'])
            if first is None:first=row
            previous=row
    if status.get('complete') is not True or status.get('records')!=count or status.get('limit')!=LIMIT or not 0<count<=LIMIT:raise ValueError('incomplete qdisc diagnostics')
    return dict(complete=True,records=count,first=first,last=previous,max_read_span_ns=span,max_sample_start_gap_ns=gap,status=status,
                scope='non-atomic pass-action/root counter snapshots; root counters cover whole interface, backlog/qlen are gauges; no per-packet pairing, flow delivery or unique drop-cause proof')


def start(lab,run,inside,processes):
    for role,name in lab.containers.items():
        log=(run/(role+'-qdisc-diagnostics.log')).open('w');args=['docker','exec',name,'python3','tools/m3_qdisc_diagnostics.py','--out',inside+'/'+role+'-qdisc-samples.jsonl','--ready',inside+'/'+role+'-qdisc-ready.json','--stop',inside+'/qdisc-stop']
        processes.append((subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT),log))
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        if any(p.poll() is not None for p,_ in processes):raise RuntimeError('qdisc observer exited before ready')
        if all((run/(role+'-qdisc-ready.json')).exists() for role in lab.containers):return
        time.sleep(.1)
    raise RuntimeError('qdisc readiness timeout')


def stop(lab,run,processes):
    (run/'qdisc-stop').touch();errors=[]
    for p,log in processes:
        try:
            if p.wait(timeout=5):errors.append('qdisc observer failed')
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5);errors.append('qdisc observer stop timeout')
        finally:log.close()
    result={}
    for role in lab.containers:
        try:result[role]=summarize(run/(role+'-qdisc-samples.jsonl'))
        except Exception as error:errors.append(str(error))
        finally:
            lab.inside(role,'qdisc-observer-remove-'+role,['tc','filter','del','dev','eth0','egress','protocol','ip','pref',PREF])
            remaining=json.loads(lab.inside(role,'qdisc-observer-restored-'+role,['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF]))
            if remaining:errors.append('pass classifier remained installed')
    if errors:raise RuntimeError('; '.join(errors))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('out','ready','stop'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();sample(a.out,a.ready,a.stop)
