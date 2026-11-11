#!/usr/bin/env python3
"""Frozen native DDS discovery continuation-fragment loss/recovery diagnostic."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import time
from m3_source_preflight import ROOT,IMAGE,sha,write
from m3_dds import DdsLab
from m3_dds_result_timeline import common_clock
from m3_control_fault import bracket
from m3_neighbor_diagnostics import configure
from m3_packet_capture import artifact_footer
from m3_capture import summarize
from m3_n5_progress import RUNTIMES

PREF='49146'


def counters(rules,expected=1):
    actions=[a for r in rules for a in r.get('options',{}).get('actions',[])]
    if len(actions)!=expected or any(r.get('kind')!='u32' or r.get('protocol')!='ip' or r.get('pref',int(PREF))!=int(PREF) for r in rules):raise ValueError('unexpected discovery drop rule')
    values=[]
    for a in actions:
        s=a.get('stats',{})
        if a.get('kind')!='gact' or a.get('control_action',{}).get('type')!='drop' or any(type(s.get(k)) is not int or s[k]<0 for k in ('packets','drops','bytes')) or s['packets']!=s['drops']:raise ValueError('invalid discovery drop counters')
        values.append({k:s[k] for k in ('packets','drops','bytes')})
    return values


def selector(source,destination):
    import ipaddress
    a,b=(ipaddress.ip_address(s) for s in (source,destination))
    if any(x.version!=4 or x.is_loopback or x.is_multicast or x.is_unspecified for x in (a,b)) or a==b:raise ValueError('owned distinct IPv4 endpoints required')
    return ['tc','filter','add','dev','eth0','egress','protocol','ip','pref',PREF,'u32','match','u8','0x45','0xff','at','0','match','ip','protocol','17','0xff','match','ip','src',str(a)+'/32','match','ip','dst',str(b)+'/32','match','u16','0x00b9','0x1fff','at','6','action','drop']


def state(out,role):
    p=out/(role+'-probe-state.json')
    return json.loads(p.read_text()) if p.exists() else None


def wait(predicate,peers,seconds=45):
    end=time.monotonic()+seconds
    while True:
        if any(p.poll() is not None for p,_ in peers):raise ValueError('probe owner exited unexpectedly')
        if predicate():return
        if time.monotonic()>end:raise ValueError('native DDS phase deadline exceeded')
        time.sleep(.05)


def qualified(s):return s and s['peer_discovered'] and s['writer_matches']==s['reader_matches']==1 and s['received']>=3 and s['invalid']==0


def hold(lab,seconds,label):
    return json.loads(lab.inside('operator',label,['python3','-c','import time,json;b=time.monotonic_ns();time.sleep('+str(seconds)+');print(json.dumps(dict(begin_ns=b,end_ns=time.monotonic_ns())))']))


def trace(path):
    rows=[];footer=[]
    for line in path.read_text().splitlines():
        if line.startswith('DDS_PROBE '):rows.append(json.loads(line[10:]))
        elif line.startswith('DDS_PROBE_STATUS '):footer.append(json.loads(line[17:]))
    if len(footer)!=1:raise ValueError('missing native DDS trace footer')
    f=footer[0]
    if f['attempted']!=f['recorded'] or f['recorded']!=len(rows) or f['exhausted'] or len(rows)>2048 or not f['dds_closed'] or not 0<f['shutdown_ns']<5_000_000_000:raise ValueError('native DDS trace/teardown incomplete')
    if [r['record'] for r in rows]!=list(range(1,len(rows)+1)):raise ValueError('native trace sequence incomplete')
    return dict(rows=rows,status=f)


def assess(result,traces):
    before=result['initial'];after=result['final']
    for role in ('operator','robot'):
        a=before[role];b=after[role]
        if not qualified(b):raise ValueError('final endpoint/callback qualification failed')
        if any(a[k]!=b[k] for k in ('pid','started_ns','participant','writer','reader')):raise ValueError('process or endpoint restarted')
        if not a['writer_metadata_bytes']==a['reader_metadata_bytes']==(4096 if role=='robot' else 0):raise ValueError('metadata size mismatch')
        if a['invalid'] or b['invalid']:raise ValueError('invalid HELLO callback')
        for row in traces[role]['rows']:
            if row['event']=='state' and any(row[k]!=a[k] for k in ('pid','started_ns','participant','writer','reader')):raise ValueError('observed endpoint identity changed')
    if result['case']=='fragment-cut':
        cut=result['blocked'];op=cut['operator'];robot=cut['robot']
        if not op['peer_discovered'] or not robot['peer_discovered']:raise ValueError('participant discovery was not preserved')
        if (op['writer_matches'],op['reader_matches'],op['received'])!=(0,0,0):raise ValueError('operator endpoints/callbacks not blocked')
        if (robot['writer_matches'],robot['reader_matches'])!=(1,1) or robot['sent']<30:raise ValueError('reverse endpoint discovery or HELLO source not live')
        if result['drops'][0]['drops']<1 or result['hold']['end_ns']-result['hold']['begin_ns']<8_000_000_000:raise ValueError('known fragment loss not established')
        if any(r['monotonic_ns']<result['remove']['begin_ns'] and r['event'] in ('writer_match','reader_match') and r['current']>0 for r in traces['operator']['rows']):raise ValueError('operator matched before discovery restore')
        origin=result['remove']['end_ns']
        if any(not origin<=s['monotonic_ns']<=origin+45_000_000_000 for s in result['qualified'].values()):raise ValueError('recovery outside declared bound')
    else:origin=max(v['monotonic_ns'] for v in result['qualified'].values())
    fence=result['steady']['end_ns']
    counts={role:sum(row['event']=='hello_received' and row['valid'] and row['sent_ns']>origin and row['monotonic_ns']<=fence for row in trace['rows']) for role,trace in traces.items()}
    steady_counts={role:sum(row['event']=='hello_received' and row['valid'] and row['sent_ns']>result['steady']['begin_ns'] and row['monotonic_ns']<=fence for row in trace['rows']) for role,trace in traces.items()}
    if any(n<20 for n in counts.values()) or any(n<20 for n in steady_counts.values()):raise ValueError('insufficient fresh bidirectional callback progress')
    return dict(fresh_callbacks=counts,steady_fresh_callbacks=steady_counts,callback_fence_ns=fence,original_endpoints_preserved=True,scope='real native DDS endpoints and callbacks with deliberately enlarged discovery metadata; controlled N0 fixture, not ROS bridge/N5/historical cause acceptance')


def run(out,case):
    out.mkdir(parents=True,exist_ok=False);inside='/workspace/'+str(out.relative_to(ROOT));lab=DdsLab(ROOT,out,IMAGE);peers=[];recorders=[];fault=False;result=dict(case=case,status='running',qualification=False)
    inventory={p:sha(ROOT/p) for p in RUNTIMES};probe=ROOT/'build/m3-dds-discovery-peer/m3_dds_discovery_peer';result['provenance']=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,probe_sha256=sha(probe),runtime_sha256=inventory)
    def readback(label):return json.loads(lab.inside('robot',label,['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF]))
    try:
        lab.start();configure(lab,'permanent');lab.apply('N0',1701)
        result['interfaces']={r:json.loads(lab.inside(r,r+'-mtu-proof',['ip','-j','link','show','dev','eth0'])) for r in lab.containers}
        if any(len(rows)!=1 or rows[0]['mtu']!=1500 for rows in result['interfaces'].values()):raise ValueError('requires owned eth0 MTU1500')
        result['clock_proof']={r:lab.inside(r,r+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for r in lab.containers};common_clock(result['clock_proof'])
        for role,name in lab.containers.items():
            log=(out/(role+'-capture.log')).open('x');argv=['docker','exec',name,'python3','tools/m3_packet_capture.py','--output',inside+'/'+role+'.pcap','--ready',inside+'/'+role+'-packet-ready.json','--stop',inside+'/'+role+'-packet-stop','--status',inside+'/'+role+'-packet-status.json','--filter','udp']
            recorders.append((subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT),log))
        wait(lambda:all((out/(r+'-packet-ready.json')).exists() for r in lab.containers),recorders,10)
        if case=='fragment-cut':
            q=json.loads(lab.inside('robot','fault-qdisc-before',['tc','-j','qdisc','show','dev','eth0']))
            if any(v['kind'] in ('clsact','ingress') for v in q):raise ValueError('refusing existing classifier')
            lab.inside('robot','fault-hook',['tc','qdisc','add','dev','eth0','clsact']);fault=True
            result['install']=bracket(lab,'robot','fault-install',selector(lab.addresses['robot'],lab.addresses['operator']))
            result['initial_counters']=counters(readback('fault-initial'),1)
            if result['initial_counters'][0]['packets']:raise ValueError('nonzero initial fault counters')
        for role,name in lab.containers.items():
            log=(out/(role+'-owner.log')).open('x');argv=['python3','tools/m3_dds_discovery_owner.py','--role',role,'--local',lab.addresses[role],'--peer',lab.addresses['robot' if role=='operator' else 'operator'],'--out',inside]
            command='source /opt/ros/jazzy/setup.bash && exec '+shlex.join(argv)
            peers.append((subprocess.Popen(['docker','exec',name,'bash','-c',command],stdout=log,stderr=subprocess.STDOUT),log))
        wait(lambda:all(state(out,r) for r in lab.containers),peers,15);result['initial']={r:state(out,r) for r in lab.containers}
        if case=='fragment-cut':
            wait(lambda:all(state(out,r)['peer_discovered'] for r in lab.containers),peers)
            result['hold']=hold(lab,8,'blocked-hold');result['blocked']={r:state(out,r) for r in lab.containers};result['drops']=counters(readback('fault-final'),1)
            # Preserve the blocked measurements; restore once even if the
            # post-run outcome gate later finds a contradicted hypothesis.
            result['remove']=bracket(lab,'robot','fault-remove',['tc','qdisc','del','dev','eth0','clsact']);fault=False
            if readback('fault-restored'):raise ValueError('selector remains after restore')
        wait(lambda:all(qualified(state(out,r)) for r in lab.containers),peers)
        result['qualified']={r:state(out,r) for r in lab.containers};result['steady']=hold(lab,3,'steady-hold');result['final']={r:state(out,r) for r in lab.containers}
        (out/'release').touch()
        for p,log in peers:
            if p.wait(timeout=12)!=0:raise ValueError('native owner failed')
            log.close()
        result['shutdown']={r:json.loads((out/(r+'-shutdown.json')).read_text()) for r in lab.containers}
        if not all(v['passed'] for v in result['shutdown'].values()):raise ValueError('unclean native child shutdown')
        traces={r:trace(out/(r+'-probe.log')) for r in lab.containers};result['assessment']=assess(result,traces);result['trace_status']={r:t['status'] for r,t in traces.items()}
        if inventory!={p:sha(ROOT/p) for p in inventory} or sha(probe)!=result['provenance']['probe_sha256']:raise ValueError('runtime changed during live test')
        result['status']='passed'
    except Exception as e:result.update(status='failed',error=str(e))
    finally:
        if fault:
            try:result['cleanup_remove']=bracket(lab,'robot','cleanup-fault-remove',['tc','qdisc','del','dev','eth0','clsact'])
            except Exception as e:result['cleanup_fault_error']=str(e)
        (out/'release').touch()
        for p,log in peers:
            try:p.wait(timeout=12)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
            if not log.closed:log.close()
        for r in lab.containers:(out/(r+'-packet-stop')).touch()
        for p,log in recorders:
            try:
                if p.wait(timeout=8)!=0:result.update(status='failed',capture_error='packet recorder failed')
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5);result.update(status='failed',capture_error='packet recorder timeout')
            log.close()
        if recorders:
            try:
                result['captures']={}
                for r,a in lab.addresses.items():
                    c=summarize([out/(r+'.pcap')],a,allow_udp_fragments=True);footer=artifact_footer(out,r,c['records'])
                    if c['unaccounted'] or not footer['population_reconciled']:raise ValueError('capture population incomplete')
                    result['captures'][r]=dict(c,footer=footer)
            except Exception as e:result.update(status='failed',capture_error=str(e))
        try:lab.cleanup()
        finally:write(out/'result.json',result)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);rows=[]
    for case in ('baseline','fragment-cut'):
        if rows and rows[-1]['status']!='passed':rows.append(dict(case=case,status='not_executed'));break
        r=run(out/case,case);rows.append(dict(case=case,status=r['status'],error=r.get('error')));write(out/'execution.json',dict(cases=rows,qualification=False));print(case,r['status'],flush=True)
    write(out/'execution.json',dict(cases=rows,qualification=False))
    return 0 if len(rows)==2 and all(r['status']=='passed' for r in rows) else 1


if __name__=='__main__':raise SystemExit(main())
