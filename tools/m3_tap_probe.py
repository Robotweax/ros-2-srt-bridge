#!/usr/bin/env python3
"""Controlled synthetic UDP tap/offload experiment in fresh owned containers."""
import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import secrets
import signal
import socket
import struct
import subprocess
import time
from m3_network import NetworkLab
from m3_capture import validate_tcpdump_footer,stop_captures,pcap_options
import m3_monotonic_capture as mono

ROOT=Path(__file__).resolve().parents[1]
PORT=39781
MAGIC=b'RTPSTAP1'
CASES=('baseline','egress-drop','egress-delay','ingress-drop','gso-noqueue','gso-netem','shaped-only')


def write(path,data):Path(path).write_text(json.dumps(data,indent=2)+'\n')


def feature_snapshot(lab,label):
    return {role:json.loads(lab.inside(role,label+'-'+role,['build/m3-netdev-features/netdev_features','eth0'])) for role in lab.containers}


def probe_id(frame):
    if len(frame)<34 or frame[12:14]!=b'\x08\x00' or frame[23]!=17:return None
    offset=14+(frame[14]&15)*4
    if len(frame)<offset+24 or struct.unpack_from('!H',frame,offset+2)[0]!=PORT:return None
    payload=frame[offset+8:]
    if not payload.startswith(MAGIC):return None
    return struct.unpack_from('!II',payload,8)


def pcap_records(path):
    with Path(path).open('rb') as file:
        header=file.read(24)
        if len(header)!=24 or header[:4]!=b'\xd4\xc3\xb2\xa1' or struct.unpack_from('<I',header,20)[0]!=1:raise ValueError('unsupported probe pcap')
        rows=[]
        while True:
            record=file.read(16)
            if not record:break
            if len(record)!=16:raise ValueError('short pcap record')
            _,_,included,original=struct.unpack('<IIII',record);frame=file.read(included)
            if len(frame)!=included or included!=original:raise ValueError('truncated pcap')
            rows.append(dict(length=original,identity=probe_id(frame)))
        return rows


def flow_packets(filters):
    actions=[action for rule in filters for action in rule.get('options',{}).get('actions',[]) if action.get('kind')=='gact']
    if len(actions)!=1:raise ValueError('ambiguous probe flow action')
    return actions[0]['stats']['packets']


def classify_stage(case,sent,outgoing,incoming,received,drop_count,delays):
    if case=='egress-drop':
        if drop_count!=sent or incoming or received:raise ValueError('drop population not verified')
        if outgoing==0:return 'egress tap after tested qdisc drop'
        if outgoing==sent:return 'egress tap before tested qdisc drop'
        raise ValueError('partial egress population')
    if case=='ingress-drop':
        if outgoing!=sent or drop_count!=sent or received:raise ValueError('ingress drop population not verified')
        if incoming==sent:return 'ingress tap before tested ingress drop'
        if incoming==0:return 'ingress tap after tested ingress drop'
        raise ValueError('partial ingress population')
    if case=='egress-delay':
        if (outgoing,incoming,received)!=(sent,sent,sent) or len(delays)!=sent:raise ValueError('delay population incomplete')
        if min(delays)>=150000000:return 'egress tap includes tested 200ms queue delay'
        if max(delays)<50000000:return 'egress tap precedes tested 200ms queue delay'
        raise ValueError('ambiguous tap delay')
    if case.startswith('gso-'):
        if received!=sent or not outgoing or not incoming:raise ValueError('GSO delivery incomplete')
        return 'UDP segmentation representation characterized'
    if outgoing!=sent or incoming!=sent or received!=sent:raise ValueError('plain population incomplete')
    return 'plain UDP observation population matches delivery'


def receive(args):
    rows=[]
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as server:
        server.bind(('0.0.0.0',PORT));server.settimeout(.05);Path(args.ready).touch();deadline=time.monotonic()+20
        while not Path(args.stop).exists():
            if time.monotonic()>deadline:raise RuntimeError('receiver timeout')
            try:payload,_=server.recvfrom(65536)
            except socket.timeout:continue
            stamp=time.monotonic_ns()
            if not payload.startswith(MAGIC) or len(payload)<16:raise ValueError('unexpected probe payload')
            case,sequence=struct.unpack_from('!II',payload,8)
            rows.append(dict(case=case,sequence=sequence,bytes=len(payload),monotonic_ns=stamp,sha256=hashlib.sha256(payload).hexdigest()))
    write(args.out,dict(rows=rows,stop_ns=time.monotonic_ns()))


def send(args):
    rows=[]
    def payload(n):return MAGIC+struct.pack('!II',args.case,n)+bytes(1200-16)
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as client:
        if getattr(args,'bind_port',0):client.bind(('0.0.0.0',args.bind_port))
        if args.gso:
            data=b''.join(payload(i) for i in range(args.count));before=time.monotonic_ns();n=client.sendmsg([data],[(socket.IPPROTO_UDP,103,struct.pack('H',1200))],0,(args.peer,PORT));after=time.monotonic_ns();assert n==len(data)
            rows=[dict(sequence=i,before_ns=before,after_ns=after) for i in range(args.count)]
        else:
            for i in range(args.count):
                data=payload(i);before=time.monotonic_ns();n=client.sendto(data,(args.peer,PORT));after=time.monotonic_ns();assert n==len(data);rows.append(dict(sequence=i,before_ns=before,after_ns=after));time.sleep(.005)
    write(args.out,dict(case=args.case,count=args.count,segmented=args.gso,payload_bytes=1200,rows=rows))


def run_case(run,image,case,number):
    run.mkdir();inside='/workspace/'+str(run.relative_to(ROOT));lab=NetworkLab(ROOT,run,image,monotonic_capture=True);captures=[];server=None
    credential=run/'passphrase';credential.touch(mode=0o600);credential.write_text(secrets.token_urlsafe(32))
    result=dict(status='running',case=case,number=number,scope='synthetic UDP only, no ROS/SRT application peers; fresh internal containers; no competitor; offload settings read-only')
    try:
        lab.start(credential)
        clocks={role:lab.inside(role,role+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for role in lab.containers}
        if len(set(clocks.values()))!=1:raise ValueError('different endpoint clocks')
        result['clock_proof']=clocks;result['features_before']=feature_snapshot(lab,'features-before')
        lab.inside('robot','neighbor-warmup',['ping','-c','1','-W','1',lab.addresses['operator']])
        if case!='gso-noqueue':lab.apply('N4' if case=='egress-drop' else 'N5' if case=='shaped-only' else 'N0',1701,roles=('robot',))
        if case=='egress-delay':lab.inside('robot','delay',['tc','qdisc','replace','dev','eth0','root','netem','delay','200ms','limit','256','seed','1701'])
        filter_role='robot' if case=='egress-drop' else 'operator'
        direction='egress' if case=='egress-drop' else 'ingress'
        if case in ('egress-drop','ingress-drop'):
            lab.inside(filter_role,'filter-hook',['tc','qdisc','add','dev','eth0','clsact'])
            lab.inside(filter_role,'flow-filter',['tc','filter','add','dev','eth0',direction,'protocol','ip','pref','1','u32','match','ip','protocol','17','0xff','match','ip','dport',str(PORT),'0xffff','action','pass' if case=='egress-drop' else 'drop'])
        lab.snapshot('before');before_filters=lab.inside(filter_role,'filters-before',['tc','-j','-s','filter','show','dev','eth0',direction])
        for role,name in lab.containers.items():
            log=(run/(role+'-capture.log')).open('w');p=subprocess.Popen(['docker','exec',name]+pcap_options()+['-w',inside+'/'+role+'.pcap','udp'],stdout=log,stderr=subprocess.STDOUT);captures.append((p,log))
        mono.start(run,inside,lab,captures)
        log=(run/'receiver.log').open('w');server=subprocess.Popen(['docker','exec',lab.containers['operator'],'python3','tools/m3_tap_probe.py','receive','--out',inside+'/received.json','--ready',inside+'/receive-ready','--stop',inside+'/receive-stop'],stdout=log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+5
        while not (run/'receive-ready').exists() or not all('listening on eth0' in (run/(r+'-capture.log')).read_text() for r in lab.containers):
            if server.poll() is not None or time.monotonic()>deadline:raise RuntimeError('probe readiness failed')
            time.sleep(.01)
        count=8 if case.startswith('gso-') else 16
        cmd=['python3','tools/m3_tap_probe.py','send','--peer',lab.addresses['operator'],'--case',str(number),'--count',str(count),'--out',inside+'/sent.json']+(['--gso'] if case.startswith('gso-') else [])
        lab.inside('robot','send',cmd);time.sleep(1)
        lab.snapshot('after-probe');after_filters=lab.inside(filter_role,'filters-after',['tc','-j','-s','filter','show','dev','eth0',direction])
        result['filters']=dict(before=json.loads(before_filters),after=json.loads(after_filters))
        if case in ('egress-drop','ingress-drop'):lab.inside(filter_role,'filter-remove',['tc','qdisc','del','dev','eth0','clsact'])
        if case=='shaped-only':lab.inside('robot','shaper-remove',['tc','qdisc','del','dev','eth0','root'])
        if case!='gso-noqueue':lab.apply('N0',1701,roles=('robot',),label='restore')
        # Same open observers must see a known control datagram after restoration.
        lab.inside('robot','control',['python3','tools/m3_tap_probe.py','send','--peer',lab.addresses['operator'],'--case',str(number+1000),'--count','1','--out',inside+'/control-sent.json'])
        time.sleep(.1);(run/'receive-stop').touch();assert server.wait(timeout=5)==0;log.close();server=None
        result['features_after']=feature_snapshot(lab,'features-after')
        if result['features_before']!=result['features_after']:raise ValueError('feature settings changed')
        result['status']='captured'
    finally:
        if server and server.poll() is None:server.terminate();server.wait(timeout=5)
        try:
            stop_captures(lab)
            for p,log in captures:p.wait(timeout=5);log.close()
        finally:
            lab.cleanup();credential.unlink(missing_ok=True);write(run/'result.json',result)
    statuses={};observations={};pcaps={};dispatch={}
    for role in ('robot','operator'):
        status=json.loads((run/(role+'-monotonic-capture.log')).read_text().splitlines()[-1]);all_rows=list(mono.records(run/(role+'.mono')))
        assert status['complete'] and status['records']==status['seen']==status['submitted']==len(all_rows) and not status['reserve_failed'] and not status['copy_failed'];statuses[role]=status
        observations[role]=[{k:v for k,v in r.items() if k!='prefix'}|dict(case=probe_id(r['prefix'])[0],sequence=probe_id(r['prefix'])[1]) for r in all_rows if probe_id(r['prefix'])]
        pcaps[role]=pcap_records(run/(role+'.pcap'));footer=(run/(role+'-capture.log')).read_text()
        counter=validate_tcpdump_footer(footer,len(pcaps[role]));dispatch[role]=dict(qualified=counter['tcpdump_population_reconciled'],**counter,scope='filter population reconciliation separate from file integrity; exact known-probe equality checked independently')
        assert Counter((r['case'],r['sequence'],r['length']) for r in observations[role])==Counter((*r['identity'],r['length']) for r in pcaps[role] if r['identity'])
    received=json.loads((run/'received.json').read_text());sent=json.loads((run/'sent.json').read_text());main={r:[x for x in rows if x['case']==number] for r,rows in observations.items()};deliveries=[r for r in received['rows'] if r['case']==number]
    assert all(len([r for r in observations[role] if r['case']==number+1000])==1 for role in observations) and len([r for r in received['rows'] if r['case']==number+1000])==1
    if case=='egress-drop':
        before=json.loads((run/'before-robot.log').read_text());after=json.loads((run/'after-probe-robot.log').read_text());qdisc_drops=sum(q['drops'] for q in after)-sum(q['drops'] for q in before)
        drop_count=flow_packets(result['filters']['after'])
        assert qdisc_drops>=drop_count and next(q for q in before if q['kind']=='netem')['options']['loss-random']['loss']==1
        result['qdisc_drops_including_background']=qdisc_drops
    elif case=='ingress-drop':drop_count=flow_packets(result['filters']['after'])
    else:drop_count=0
    times={r['sequence']:r['before_ns'] for r in sent['rows']};delays=[r['monotonic_ns']-times[r['sequence']] for r in main['robot']]
    stage=classify_stage(case,sent['count'],len(main['robot']),len(main['operator']),len(deliveries),drop_count,delays)
    assert sorted(r['sequence'] for r in deliveries)==([] if 'drop' in case else list(range(sent['count'])))
    result.update(status='passed',stage=stage,sent_datagrams=sent['count'],sender_observations=len(main['robot']),receiver_observations=len(main['operator']),application_deliveries=len(deliveries),drop_count=drop_count,sender_delay_ns=delays,capture_status=statuses,pcap_dispatch=dispatch,observations=observations,positive_restoration_control_passed=True)
    if case.startswith('gso-'):
        result['gso_metadata']={role:[dict(length=r['length'],gso_segs=r['gso_segs'],gso_size=r['gso_size']) for r in rows] for role,rows in main.items()}
        result['window_accounting']={role:mono.summarize(run/(role+'.mono'),statuses[role],lab.addresses[role],[min(times.values()),received['stop_ns']]) for role in lab.addresses}
    write(run/'result.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('receive');p.add_argument('--out',required=True);p.add_argument('--ready',required=True);p.add_argument('--stop',required=True)
    p=sub.add_parser('send');p.add_argument('--peer',required=True);p.add_argument('--case',type=int,required=True);p.add_argument('--count',type=int,required=True);p.add_argument('--out',required=True);p.add_argument('--gso',action='store_true');p.add_argument('--bind-port',type=int,default=0)
    p=sub.add_parser('run');p.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='receive':receive(args);return
    if args.command=='send':send(args);return
    run=args.out.resolve();run.mkdir(parents=True,exist_ok=False)
    image=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64','ros2-srt-m3:20261105'],text=True))[0]['RepoDigests'][0]
    from m3_observer_study import source_inventory
    report=dict(status='running',image=image,source_sha256=source_inventory(),binary_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'build/m3-monotonic-capture/monotonic_capture',ROOT/'build/m3-netdev-features/netdev_features')},cases=[]);write(run/'run.json',report)
    try:
        for n,case in enumerate(CASES,1):
            result=run_case(run/case,image,case,n);report['cases'].append(result);write(run/'run.json',report);print(case+': '+result['stage'],flush=True)
        report['status']='passed'
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:write(run/'run.json',report)


if __name__=='__main__':main()
