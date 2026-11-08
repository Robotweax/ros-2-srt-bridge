#!/usr/bin/env python3
"""Owned synthetic ARP reply counter/verdict chain and timed removal controller."""
import argparse,ipaddress,json,subprocess,time
from pathlib import Path
from m3_neighbor_diagnostics import valid_mac

PREF='49140'


def selector(source,target,source_mac,target_mac,verdict):
    for address in (source,target):
        a=ipaddress.ip_address(address)
        if a.version!=4 or a.is_loopback or a.is_unspecified:raise ValueError('requires owned nonloopback IPv4')
    if source==target or not all(valid_mac(v) for v in (source_mac,target_mac)) or source_mac==target_mac or verdict not in ('pass','drop'):raise ValueError('invalid owned ARP selector')
    args=['tc','filter','add','dev','eth0','egress','protocol','arp','pref',PREF,'u32','skip_hw']
    for offset,value in reply_words(source,target,source_mac,target_mac).items():
        args+=['match','u32',hex(value),'0xffffffff','at',str(offset)]
    return args+['action','gact','pipe','action','gact',verdict]


def reply_words(source,target,source_mac,target_mac):
    # Exact Ethernet/IPv4 ARP payload: network-header aligned seven words.
    # Native validation separately requires the owned Ethernet MAC identities.
    payload=bytes.fromhex('0001080006040002')+bytes.fromhex(source_mac.replace(':',''))+ipaddress.ip_address(source).packed+bytes.fromhex(target_mac.replace(':',''))+ipaddress.ip_address(target).packed
    return {offset:int.from_bytes(payload[offset:offset+4],'big') for offset in range(0,28,4)}


def parse_tc_json(text):
    # Pinned iproute2 emits repeated "match" and "success" object keys for
    # u32. Preserve every selector word; never silently accept just the last.
    def object_hook(pairs):
        result={}
        for key,value in pairs:
            if key in ('match','success'):result.setdefault('_repeated_'+key,[]).append(value)
            elif key in result:raise ValueError('unexpected duplicate tc JSON key')
            else:result[key]=value
        return result
    return json.loads(text,object_pairs_hook=object_hook)


def counters(raw,source,target,source_mac,target_mac,verdict):
    if not isinstance(raw,list) or not raw or any(r.get('kind')!='u32' or r.get('protocol')!='arp' or r.get('pref',int(PREF))!=int(PREF) for r in raw):raise ValueError('not owned ARP u32 rules')
    rules=[r['options'] for r in raw if r.get('options',{}).get('actions')]
    if len(rules)!=1 or rules[0].get('not_in_hw') is not True:raise ValueError('ambiguous or offloaded ARP rule')
    o=rules[0];expected=reply_words(source,target,source_mac,target_mac);actual={}
    for k in o.get('_repeated_match',[]):
        offset=k['off']
        if offset in actual or k.get('offmask','') not in ('',0):raise ValueError('ambiguous ARP payload offsets')
        if int(k['mask'],16)!=0xffffffff:raise ValueError('inexact ARP selector mask')
        actual[offset]=int(k['value'],16)
    if actual!=expected:raise ValueError('wrong exact ARP reply payload selector')
    actions=o.get('actions',[])
    if len(actions)!=2:raise ValueError('requires exactly PIPE then verdict')
    result=[]
    for order,(a,kind) in enumerate(zip(actions,('pipe',verdict)),1):
        if a.get('kind')!='gact' or a.get('order')!=order or a.get('control_action',{}).get('type')!=kind or a.get('prob',{}).get('random_type','none')!='none':raise ValueError('wrong action chain')
        stats=a.get('stats',{})
        if any(type(stats.get(v)) is not int or stats[v]<0 for v in ('packets','bytes','drops')):raise ValueError('invalid ARP counters')
        if type(a.get('index')) is not int or a['index']<1:raise ValueError('invalid action index')
        result.append(dict(index=a['index'],**{v:stats[v] for v in ('packets','bytes','drops')}))
    if result[0]['index']==result[1]['index'] or result[0]['drops'] or verdict=='pass' and result[1]['drops']:raise ValueError('unexpected observation/pass drops or aliased actions')
    return dict(eligible=result[0],verdict=result[1],verdict_type=verdict)


def query(argv):
    begin=time.monotonic_ns();p=subprocess.run(argv,capture_output=True,text=True,timeout=1);end=time.monotonic_ns()
    if p.returncode or len(p.stdout)>32768:raise ValueError('bounded observer query failed')
    return dict(begin_ns=begin,end_ns=end,argv=argv,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)


def snapshot(args):
    f=query(['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF]);q=query(['tc','-j','-s','qdisc','show','dev','eth0']);n=query(['ip','-j','-s','neigh','show','to',args.target])
    return dict(filter_read=f,root_read=q,neighbor_read=n,counters=counters(parse_tc_json(f['stdout']),args.source,args.target,args.source_mac,args.target_mac,args.verdict))


def control(args):
    result=dict(status='running',nominal_offsets_ns=[1150000000,1250000000,1350000000],snapshots=[])
    try:
        result['initial']=snapshot(args)
        for v in result['initial']['counters'].values():
            if isinstance(v,dict) and any(v[k] for k in ('packets','bytes','drops')):raise ValueError('initial reply counters not zero')
        args.ready.write_text(json.dumps(dict(ready_ns=time.monotonic_ns()))+'\n')
        deadline=time.monotonic()+8
        while not args.sent.exists():
            if time.monotonic()>deadline:raise ValueError('source bracket not supplied')
            time.sleep(.005)
        sent=json.loads(args.sent.read_text());origin=sent['rows'][0]['before_ns'];result['origin_ns']=origin
        for offset in result['nominal_offsets_ns'][:2]:
            while time.monotonic_ns()<origin+offset:time.sleep(.002)
            result['snapshots'].append(snapshot(args))
        while time.monotonic_ns()<origin+result['nominal_offsets_ns'][2]:time.sleep(.002)
        begin=time.monotonic_ns();p=subprocess.run(['tc','filter','del','dev','eth0','egress','protocol','arp','pref',PREF],capture_output=True,text=True,timeout=1);end=time.monotonic_ns()
        result['removal']=dict(begin_ns=begin,end_ns=end,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)
        if p.returncode:raise ValueError('reply rule removal failed')
        result['after']=query(['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF])
        if json.loads(result['after']['stdout']):raise ValueError('reply rule remained')
        if not origin+1250000000<=begin<=end<origin+2000000000:raise ValueError('restoration outside fixed timing gate')
        a,b=[r['counters'] for r in result['snapshots']]
        if a!=b or not b['eligible']['packets'] or any(b['eligible'][k]!=b['verdict'][k] for k in ('packets','bytes')):raise ValueError('unstable or unequal positive reply action populations')
        if args.verdict=='drop' and b['verdict']['drops']!=b['verdict']['packets']:raise ValueError('drop verdict not counted')
        result['status']='passed'
    except Exception as e:result.update(status='failed',error=str(e))
    finally:
        with args.out.open('x') as f:f.write(json.dumps(result,indent=2)+'\n')
    return result['status']=='passed'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source','target','source-mac','target-mac','verdict'):p.add_argument('--'+key,required=True)
    for key in ('sent','ready','out'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();raise SystemExit(not control(a))
