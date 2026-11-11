#!/usr/bin/env python3
"""Opt-in neighbor-table polling and separate owned-lab permanent-neighbor candidate.

Read-only polling adds subprocess/netlink work. Samples are not a complete state
transition log and cannot prove kernel queue/drop causes. No probes are sent.
"""
import argparse,ipaddress,json,re,subprocess,time
from collections import Counter
from pathlib import Path

LIMIT=75000
PERIOD_NS=100000000
# Keep dev in the JSON row: interface-scoped ip queries may elide it.
# Query only the peer and validate its returned dev==eth0 instead.
MAC=re.compile(r'^(?:[0-9a-f]{2}:){5}[0-9a-f]{2}$')


def valid_mac(value):
    return isinstance(value,str) and MAC.fullmatch(value) and value!='00:00:00:00:00:00' and not int(value[:2],16)&1


def normalize(raw,peer):
    if not isinstance(raw,list) or len(raw)>1:raise ValueError('ambiguous neighbor rows')
    for row in raw:
        if row.get('dst')!=peer or row.get('dev')!='eth0' or not isinstance(row.get('state'),list) or not row['state'] or not all(isinstance(s,str) for s in row['state']):raise ValueError('unexpected neighbor identity/state')
        if 'lladdr' in row and not valid_mac(row['lladdr']):raise ValueError('invalid neighbor MAC')
    return raw


def observe(peer):
    begin=time.monotonic_ns();entries=[];error=None
    try:
        p=subprocess.run(['ip','-j','-s','neigh','show','to',peer],capture_output=True,text=True,timeout=1)
        if p.returncode or len(p.stdout)>4096:raise ValueError('neighbor query failed or exceeded bound')
        entries=normalize(json.loads(p.stdout),peer)
    except (OSError,ValueError,subprocess.TimeoutExpired) as failure:error=type(failure).__name__
    return dict(begin_ns=begin,end_ns=time.monotonic_ns(),entries=entries,error=error)


def sample(out,ready,stop,peer):
    address=ipaddress.ip_address(peer)
    if address.version!=4 or address.is_loopback or address.is_unspecified:raise ValueError('requires peer IPv4')
    status=out.with_suffix('.status.json')
    if status.exists() or ready.exists():raise FileExistsError('neighbor observation output already exists')
    complete=False;count=0
    file=out.open('x')  # Failed exclusive creation must not rewrite an old status.
    try:
        with file:
            for sequence in range(1,LIMIT+1):
                row=observe(peer);row['sequence']=sequence;file.write(json.dumps(row)+'\n');file.flush();count=sequence
                if not row['error'] and not ready.exists():ready.write_text(json.dumps(dict(ready_ns=row['end_ns'])))
                if stop.exists():complete=True;break
                time.sleep(max(0,(row['begin_ns']+PERIOD_NS-time.monotonic_ns())/1e9))
    finally:
        with status.open('x') as final:final.write(json.dumps(dict(complete=complete,records=count,limit=LIMIT,finished_ns=time.monotonic_ns()))+'\n')
    if not complete:raise RuntimeError('neighbor observation budget exhausted')


def summarize(path,peer):
    status=json.loads(path.with_suffix('.status.json').read_text());states=Counter();lladdrs=Counter();errors=0;previous=None;span=gap=count=0
    with path.open() as file:
        for line in file:
            if len(line)>8192:raise ValueError('neighbor sample exceeds bound')
            row=json.loads(line);count+=1
            if row['sequence']!=count or not 0<row['begin_ns']<=row['end_ns'] or previous and row['begin_ns']<previous['end_ns']:raise ValueError('invalid neighbor sequence/read bracket')
            entries=normalize(row['entries'],peer)
            if row['error']:errors+=1
            elif not entries:states['ABSENT']+=1
            else:
                states['+'.join(sorted(entries[0]['state']))]+=1
                if 'lladdr' in entries[0]:lladdrs[entries[0]['lladdr']]+=1
            span=max(span,row['end_ns']-row['begin_ns'])
            if previous:gap=max(gap,row['begin_ns']-previous['begin_ns'])
            previous=row
    if status.get('complete') is not True or status.get('records')!=count or not 0<count<=LIMIT or status.get('limit')!=LIMIT or errors:raise ValueError('incomplete/error neighbor diagnostics')
    return dict(complete=True,records=count,states=dict(states),lladdrs=dict(lladdrs),max_read_span_ns=span,max_sample_start_gap_ns=gap,status=status,
                scope='read-only sampled netlink state, no active probe or full transition/queue/drop proof; observer adds subprocess work')


def configure(lab,mode):
    if mode not in ('dynamic','permanent'):raise ValueError('invalid neighbor mode')
    if set(lab.containers)!= {'operator','robot'}:raise ValueError('requires two owned endpoints')
    macs={}
    for role in lab.containers:
        links=json.loads(lab.inside(role,'neighbor-link-'+role,['ip','-j','link','show','dev','eth0']))
        if len(links)!=1 or links[0].get('ifname')!='eth0' or not valid_mac(links[0].get('address')):raise ValueError('invalid owned link')
        macs[role]=links[0]['address']
    rows={}
    for role in lab.containers:
        peer='robot' if role=='operator' else 'operator';address=lab.addresses[peer]
        if ipaddress.ip_address(address).version!=4 or ipaddress.ip_address(address).is_loopback:raise ValueError('invalid owned peer')
        if mode=='permanent':lab.inside(role,'neighbor-install-'+role,['ip','neigh','replace',address,'lladdr',macs[peer],'nud','permanent','dev','eth0'])
        entries=normalize(json.loads(lab.inside(role,'neighbor-before-'+role,['ip','-j','-s','neigh','show','to',address])),address)
        if mode=='permanent' and (len(entries)!=1 or entries[0].get('lladdr')!=macs[peer] or entries[0]['state']!=['PERMANENT']):raise ValueError('permanent neighbor readback failed')
        rows[role]=entries
    return dict(mode=mode,peer_macs=macs,before=rows,scope='permanent mode is a separate L2 diagnostic candidate; dynamic mode does not write neighbor entries')


def start(lab,run,inside,processes):
    for role,name in lab.containers.items():
        peer='robot' if role=='operator' else 'operator';log=(run/(role+'-neighbor-diagnostics.log')).open('w')
        args=['docker','exec',name,'python3','tools/m3_neighbor_diagnostics.py','--out',inside+'/'+role+'-neighbor-samples.jsonl','--ready',inside+'/'+role+'-neighbor-ready.json','--stop',inside+'/neighbor-stop','--peer',lab.addresses[peer]]
        processes.append((subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT),log))
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        if any(p.poll() is not None for p,_ in processes):raise RuntimeError('neighbor observer exited before ready')
        if all((run/(role+'-neighbor-ready.json')).exists() for role in lab.containers):return
        time.sleep(.1)
    raise RuntimeError('neighbor readiness timeout')


def stop(lab,run,processes,mode,peer_macs):
    (run/'neighbor-stop').touch();errors=[]
    for p,log in processes:
        try:
            if p.wait(timeout=5):errors.append('neighbor observer failed')
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5);errors.append('neighbor stop timeout')
        finally:log.close()
    if errors:raise RuntimeError('; '.join(errors))
    result={}
    for role in lab.containers:
        peer='robot' if role=='operator' else 'operator';address=lab.addresses[peer]
        result[role]=summarize(run/(role+'-neighbor-samples.jsonl'),address)
        final=normalize(json.loads(lab.inside(role,'neighbor-after-'+role,['ip','-j','-s','neigh','show','to',address])),address)
        result[role]['after']=final
        if mode=='permanent' and (result[role]['states']!={'PERMANENT':result[role]['records']} or len(final)!=1 or final[0]['state']!=['PERMANENT'] or final[0].get('lladdr')!=peer_macs[peer] or result[role]['lladdrs']!={peer_macs[peer]:result[role]['records']}):raise ValueError('permanent neighbor changed or unavailable')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('out','ready','stop'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--peer',required=True);args=p.parse_args();sample(args.out,args.ready,args.stop,args.peer)
