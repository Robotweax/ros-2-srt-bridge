#!/usr/bin/env python3
"""N4 ROS freshness and deliberate restart fixtures on owned Docker peers."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import shlex
import subprocess
from m3_network import NetworkLab
from m3_neighbor_diagnostics import configure
from m3_source_preflight import ROOT,IMAGE,sha,write,source_inventory
from m3_ros_sensor import wait_files
from native_adapter import network,DIRECTIONS
from m3_dds_result_timeline import common_clock,read_journal
from m3_source_trace import summarize as source_trace
from m3_sample_trace import summarize as samples
from m3_command_trace import summarize as commands
from m3_n4_sensor_check import assess
from disposition_runtime import matched


def hold(lab,seconds,label):return json.loads(lab.inside('robot',label,['python3','-c','import time,json;b=time.monotonic_ns();time.sleep('+str(seconds)+');print(json.dumps(dict(begin_ns=b,end_ns=time.monotonic_ns())))']))


def run_case(out,mode,runtime_layout='baseline'):
    if runtime_layout!='socket-disposition' or mode not in (*DIRECTIONS,'before','effect','committed'):raise ValueError('only declared6 ROS N4 cases on frozen socket-disposition build')
    layout=matched(ROOT,runtime_layout)
    out.mkdir(parents=True,exist_ok=False);inside='/workspace/'+str(out.relative_to(ROOT));lab=NetworkLab(ROOT,out,IMAGE);peers=[];cut={};result=dict(status='running',mode=mode,qualification=False)
    key=out/'passphrase';key.touch(mode=0o600);key.write_text(secrets.token_urlsafe(32))
    paths=('install/m3-ros/robotweax_srt_bridge/lib/robotweax_srt_bridge/bridge_node','install/m3-ros/robotweax_srt_bridge/lib/robotweax_srt_bridge/ros_rate_worker','install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo/rate_simulator','install/srt-m0/lib/librobotweax-srt.a')
    paths=[p.replace('install/m3-ros/',layout['ros']+'/',1) for p in paths]
    if runtime_layout!='baseline':paths+=layout['runtime_paths'][:-1]
    inventory={p:sha(ROOT/p) for p in paths}
    write(out/'provenance.json',dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,source_sha256=source_inventory(ROOT),runtime_sha256=inventory,runtime_layout=layout))
    fresh=mode in DIRECTIONS
    try:
        lab.start(key)
        for role in lab.containers:
            prefix=lab.inside(role,role+'-selected-ros-prefix',['bash','-c','source /opt/ros/jazzy/setup.bash && source '+shlex.quote(layout['ros']+'/setup.bash')+' && ros2 pkg prefix robotweax_srt_bridge']).strip()
            if prefix!='/workspace/'+layout['ros']+'/robotweax_srt_bridge':raise ValueError('selected ROS prefix mismatch')
        configure(lab,'permanent');lab.apply('N0',1701)
        result['clock_proof']={r:lab.inside(r,r+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for r in lab.containers};common_clock(result['clock_proof'])
        for role,name in lab.containers.items():
            log=(out/(role+'-scenario.log')).open('w');script='ros_sensor.py' if fresh else 'ros_crash.py'
            cmd='source /opt/ros/jazzy/setup.bash && source '+shlex.quote(layout['ros']+'/setup.bash')+' && exec python3 evidence/m3-current-n4-preparation-2026-11-10/'+script+' --role '+role+' --run '+inside+' --peer '+lab.addresses['operator']+' --ros-install '+shlex.quote(layout['ros'])+('' if fresh else ' --case '+mode)
            peers.append((subprocess.Popen(['docker','exec',name,'bash','-c',cmd],stdout=log,stderr=subprocess.STDOUT),log))
        if fresh:
            wait_files(out,[r+'-fresh-ready.json' for r in lab.containers],peers)
            (out/'armed').touch();wait_files(out,['load-started.json'],peers)
            result['warmup']=hold(lab,2,'warmup')
            cut={r:network(lab,r,True,'outage-'+r) for r in DIRECTIONS[mode]};result['outage_install']=cut
            result['hold']=hold(lab,2,'hold')
            result['drop_readback']={r:json.loads(lab.inside(r,'drops-'+r,['tc','-j','-s','qdisc','show','dev','eth0'])) for r in cut}
            if any(next(q for q in qs if q['kind']=='netem')['drops']<=0 for qs in result['drop_readback'].values()):raise ValueError('N4 cut dropped no packets')
            restored={r:network(lab,r,False,'restore-'+r) for r in cut};result['outage_restore']=restored
            interval=[max(v['bracket']['end_ns'] for v in cut.values()),min(v['bracket']['begin_ns'] for v in restored.values())];end=max(v['bracket']['end_ns'] for v in restored.values());cut={}
            if interval[1]-interval[0]<2_000_000_000:raise ValueError('cut shorter than declared2s')
            result['outage_ns']=interval;result['restored_ns']=end
            wait_files(out,[r+'-fresh-result.json' for r in lab.containers],peers,timeout=40);(out/'release').touch()
        else:
            wait_files(out,['operator-ready.json','robot-ready.json'],peers)
            if mode=='before':
                cut={r:network(lab,r,True,'cut-'+r) for r in DIRECTIONS['both']};result['outage_install']=cut;(out/'cut-active').touch()
            wait_files(out,['restart-launched'],peers,timeout=35)
            if cut:
                result['outage_restore']={r:network(lab,r,False,'restore-'+r) for r in cut};cut={}
            (out/'restored').touch()
            wait_files(out,['operator-result.json','robot-final.json'],peers,timeout=45)
        for p,log in peers:
            if p.wait(timeout=25)!=0:raise ValueError('ROS scenario exited abnormally')
            log.close()
        result['shutdown']={r:json.loads((out/(r+('-child-shutdown.json' if fresh else '-shutdown.json'))).read_text()) for r in lab.containers}
        if not all(v['passed'] for v in result['shutdown'].values()):raise ValueError('unplanned shutdown failure')
        if fresh:
            sender=json.loads((out/'robot-fresh-result.json').read_text());receiver=json.loads((out/'operator-fresh-result.json').read_text())
            result['freshness']=assess(source_trace(out/'robot-source.log'),sender,receiver,samples(out/'robot-bridge-0.log',allow_inactive_admissions=True),samples(out/'operator-bridge-0.log'),result['outage_ns'],result['restored_ns'],mode)
        else:
            result['crash']=check_crash(out,mode)
        if inventory!={p:sha(ROOT/p) for p in inventory} or matched(ROOT,runtime_layout)!=layout:raise ValueError('runtime changed during case')
        result['status']='passed'
    except Exception as error:result.update(status='failed',error=str(error))
    finally:
        for r in cut:
            try:network(lab,r,False,'cleanup-restore-'+r)
            except Exception as error:result['restore_error']=str(error)
        (out/'release').touch();(out/'restored').touch()
        for p,log in peers:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
            if not log.closed:log.close()
        try:lab.cleanup()
        finally:key.unlink(missing_ok=True);write(out/'result.json',result)
    return result


def check_crash(out,mode):
    op=json.loads((out/'operator-result.json').read_text());robot=json.loads((out/'robot-final.json').read_text());initial=json.loads((out/'robot-ready.json').read_text());crash=json.loads((out/'crashed.json').read_text())
    a=read_journal(out/'operator.sqlite',1);b=read_journal(out/'robot.sqlite',2);id='01'+'00'*15;s=a['entries'][id]
    if s['deadline_ns']!=s['source_ns']+5_000_000_000 or op['end']['commands_sent']!=1:raise ValueError('deadline extended or accepted command replayed')
    trace=commands(out/'operator-bridge-0.log')
    if not trace['complete'] or sum(e['point']==25 and e['request']==id for e in trace['events'])!=1:raise ValueError('sender trace does not prove one SDK handoff')
    expected=4 if mode=='committed' else 8
    if s['state']!=expected or op['status']['state']!=expected or op['device']['effects']!=(0 if mode=='before' else 1):raise ValueError('wrong recovered outcome/effect count')
    if mode=='before':
        if b['entries'] or not op['not_found'] or s['reason']!=2 or s['result_valid'] or crash['journal']:raise ValueError('NOT_FOUND converted uncertainty or receiver admitted cut command')
        if op['observations'][-1]['ns']<=s['deadline_ns']:raise ValueError('unknown was not checked beyond original expiry')
    else:
        r=b['entries'][id]
        if r['state']!=expected or r['owner_epoch']!=initial['owner'] or r['payload_hash']!=s['payload_hash'] or s['result_valid']!=(mode=='committed') or r['result_valid']!=s['result_valid']:raise ValueError('recovered journal proof/old ownership mismatch')
        if mode=='effect' and (crash['device']['effects']!=1 or crash['journal'][0]['state']!=3 or not crash['fault']['worker_fault']):raise ValueError('crash did not occur after external effect before commit')
        if mode=='committed' and crash['journal'][0]['state']!=4:raise ValueError('crash not after durable success')
    controlled=[]
    for path in sorted(out.glob('*-bridge-*.log')):
        if path.name=='robot-bridge-1.log' and mode in ('before','committed'):continue
        item=commands(path)
        if not item['complete']:raise ValueError('controlled incarnation command trace incomplete')
        controlled.append(dict(name=path.name,attempted=item['attempted'],complete=True))
    new_owner=bytes(robot['metrics']['owner_epoch']).hex()
    if new_owner==initial['owner'] or bytes(robot['metrics']['session_id']).hex()==initial['session']:raise ValueError('restart did not change owner/session')
    return dict(sender_journal=a,receiver_journal=b,sender_trace=trace,status=op['status'],device=op['device'],initial_owner=initial['owner'],new_owner=new_owner,expected_crashes=robot['crashes'],controlled_traces=controlled,not_found_observed=op['not_found'],scope='real ROS worker/bridge restart, external simulator persists; no accepted-command replay, original deadline and unresolved UNKNOWN retained; no physical-device outcome proof')

