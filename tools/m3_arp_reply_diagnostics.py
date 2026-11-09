#!/usr/bin/env python3
"""Bounded loaded ARP reply PIPE/PASS observer; no fault mode or counter clearing."""
import argparse,json,subprocess,time
from pathlib import Path
from m3_arp_reply_observer import selector,counters,parse_tc_json,PREF,query

PERIOD_NS=200000000
LIMIT=37500


def install(lab,peer_macs):
    roles={}
    for role in lab.containers:
        peer='robot' if role=='operator' else 'operator'
        before=json.loads(lab.inside(role,'arp-reply-root-before-'+role,['tc','-j','qdisc','show','dev','eth0']))
        if sum(q['kind']=='clsact' for q in before)!=1:raise ValueError('requires existing owned clsact observer hook')
        if parse_tc_json(lab.inside(role,'arp-reply-rule-before-'+role,['tc','-j','filter','show','dev','eth0','egress','pref',PREF])):raise ValueError('ARP preference already occupied')
        args=(lab.addresses[role],lab.addresses[peer],peer_macs[role],peer_macs[peer],'pass')
        lab.inside(role,'arp-reply-install-'+role,selector(*args))
        c=counters(parse_tc_json(lab.inside(role,'arp-reply-readback-'+role,['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF])),*args)
        after=json.loads(lab.inside(role,'arp-reply-root-after-'+role,['tc','-j','qdisc','show','dev','eth0']))
        def root(qs):
            roots=[q for q in qs if q.get('root')]
            if len(roots)!=1:raise ValueError('ambiguous root')
            return {k:roots[0].get(k) for k in ('kind','handle','options')}
        if root(before)!=root(after):raise ValueError('ARP observer altered root')
        roles[role]=dict(args=list(args),selector=selector(*args),initial=c)
    return dict(roles=roles,scope='software owned ARP reply PIPE/PASS, not passive or authenticated per-packet identity; root options unchanged')


def observe(args):
    begin=time.monotonic_ns();value={};error=None
    try:
        r=query(['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF])
        value=dict(read_ns=[r['begin_ns'],r['end_ns']],counters=counters(parse_tc_json(r['stdout']),args.source,args.target,args.source_mac,args.target_mac,'pass'))
    except (OSError,ValueError,subprocess.TimeoutExpired) as e:error=type(e).__name__
    return dict(begin_ns=begin,end_ns=time.monotonic_ns(),error=error,**value)


def sample(args):
    status=args.out.with_suffix('.status.json')
    if status.exists() or args.ready.exists():raise FileExistsError('ARP outputs exist')
    complete=False;count=0;file=args.out.open('x')
    try:
        with file:
            for sequence in range(1,LIMIT+1):
                r=observe(args);r['sequence']=sequence;file.write(json.dumps(r)+'\n');file.flush();count=sequence
                if not r['error'] and not args.ready.exists():args.ready.write_text(json.dumps(dict(ready_ns=r['end_ns']))+'\n')
                if args.stop.exists():complete=True;break
                time.sleep(max(0,(r['begin_ns']+PERIOD_NS-time.monotonic_ns())/1e9))
    finally:
        with status.open('x') as f:f.write(json.dumps(dict(complete=complete,records=count,limit=LIMIT,finished_ns=time.monotonic_ns()))+'\n')
    if not complete:raise ValueError('ARP sample budget exhausted')


def summarize(path):
    status=json.loads(path.with_suffix('.status.json').read_text());first=previous=None;count=gap=span=0
    for line in path.read_text().splitlines():
        if len(line)>4096:raise ValueError('ARP row exceeds bound')
        r=json.loads(line);count+=1
        if r.get('error') or r['sequence']!=count or not 0<r['begin_ns']<=r['read_ns'][0]<=r['read_ns'][1]<=r['end_ns'] or previous and r['begin_ns']<previous['end_ns']:raise ValueError('invalid ARP sequence/bracket/error')
        c=r['counters']
        if c['verdict_type']!='pass':raise ValueError('loaded ARP observer must PASS')
        for kind in ('eligible','verdict'):
            v=c[kind]
            if any(type(v.get(k)) is not int or v[k]<0 for k in ('index','packets','bytes','drops')) or not v['index'] or v['drops']:raise ValueError('invalid/dropping ARP observation')
            if previous:
                old=previous['counters'][kind]
                if v['index']!=old['index'] or any(v[k]<old[k] for k in ('packets','bytes')):raise ValueError('ARP action identity/counters changed')
        if c['eligible']['index']==c['verdict']['index']:raise ValueError('aliased ARP actions')
        if first is None:first=r
        if previous:gap=max(gap,r['begin_ns']-previous['begin_ns'])
        span=max(span,r['end_ns']-r['begin_ns']);previous=r
    if status.get('complete') is not True or status.get('records')!=count or status.get('limit')!=LIMIT or not 0<count<=LIMIT:raise ValueError('incomplete ARP observer')
    return dict(complete=True,records=count,first=first,last=previous,max_read_span_ns=span,max_sample_start_gap_ns=gap,status=status,scope='non-atomic PIPE/PASS cumulative reads; distinct action indexes; validated selector each query; no equality/drop subtraction or exact packet attribution')


def start(lab,run,inside,configuration,processes):
    for role,name in lab.containers.items():
        a=configuration['roles'][role]['args'];log=(run/(role+'-arp-reply-diagnostics.log')).open('w')
        argv=['docker','exec',name,'python3','tools/m3_arp_reply_diagnostics.py','--source',a[0],'--target',a[1],'--source-mac',a[2],'--target-mac',a[3],'--out',inside+'/'+role+'-arp-reply-samples.jsonl','--ready',inside+'/'+role+'-arp-reply-ready.json','--stop',inside+'/arp-reply-stop']
        processes.append((subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT),log))
    deadline=time.monotonic()+10
    while not all((run/(r+'-arp-reply-ready.json')).exists() for r in lab.containers):
        if any(p.poll() is not None for p,_ in processes) or time.monotonic()>deadline:raise ValueError('ARP observer readiness failed')
        time.sleep(.02)


def stop(lab,run,processes):
    (run/'arp-reply-stop').touch();errors=[];result={}
    for p,log in processes:
        try:
            if p.wait(timeout=5):errors.append('ARP observer exit failure')
        except subprocess.TimeoutExpired:
            p.terminate();p.wait(timeout=5);errors.append('ARP observer timeout')
        finally:log.close()
    for role in lab.containers:
        try:result[role]=summarize(run/(role+'-arp-reply-samples.jsonl'))
        except Exception as e:errors.append(str(e))
        finally:
            lab.inside(role,'arp-reply-final-'+role,['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF])
            lab.inside(role,'arp-reply-remove-'+role,['tc','filter','del','dev','eth0','egress','protocol','arp','pref',PREF])
            if parse_tc_json(lab.inside(role,'arp-reply-restored-'+role,['tc','-j','filter','show','dev','eth0','egress','pref',PREF])):errors.append('ARP reply rule remained')
    if errors:raise ValueError('; '.join(errors))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('source','target','source-mac','target-mac'):p.add_argument('--'+k,required=True)
    for k in ('out','ready','stop'):p.add_argument('--'+k,type=Path,required=True)
    sample(p.parse_args())
