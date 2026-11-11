#!/usr/bin/env python3
"""Phase-controlled native N4 development fixtures; installed SDK, no ROS sensor claim."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import struct
import subprocess
import time
from m3_network import NetworkLab,PROFILES
from m3_source_preflight import ROOT,IMAGE,sha,write,source_inventory
from m3_control_fault import bracket
from m3_neighbor_diagnostics import configure
from m3_dds_result_timeline import common_clock,read_journal
from m3_ros_sensor import wait_files
from m3_runtime_layout import LAYOUTS
from m3_n4_fixture import native_layout

PHASES=('admission','started','committed')
DIRECTIONS={'both':('operator','robot'),'to-robot':('operator',),'to-operator':('robot',)}
ID='01'+'00'*15


def network(lab,role,drop,label):
    seed=1702 if role=='operator' else 1701
    commands=PROFILES['N4' if drop else 'N0'].commands(seed)
    event=bracket(lab,role,label,commands[0])
    state=json.loads(lab.inside(role,label+'-readback',['tc','-j','-s','qdisc','show','dev','eth0']))
    q=next(q for q in state if q['kind']=='netem')
    if q['options'].get('seed')!=seed or q['options'].get('loss-random',{}).get('loss',0)!=(1 if drop else 0):raise ValueError('N4 kernel loss/seed readback mismatch')
    return dict(bracket=event,qdisc=q)


def check_outcome(phase,sender,receiver,a,b,barrier,resumed,barrier_record,initial,submitted):
    if set(a['entries'])!={ID} or set(b['entries'])!={ID}:raise ValueError('unexpected/missing journal identity')
    s=a['entries'][ID];r=b['entries'][ID]
    for key in ('route','payload_hash','source_epoch','source_ns','session','state','reason','revision','result_valid','result_generation'):
        if s[key]!=r[key]:raise ValueError('sender/receiver durable proof mismatch: '+key)
    expected_hash=hashlib.sha256(struct.pack('!IIIIQQ',0x52574331,100,100,5000,0,1)).hexdigest()
    if s['owner_epoch']!=initial['operator']['owner'] or s['source_epoch']!=s['owner_epoch'] or r['owner_epoch']!=initial['robot']['owner'] or any(initial[role]['snapshot']['session']!=r['session'] for role in ('operator','robot')):raise ValueError('original command owner/session provenance mismatch')
    if r['source_ns']!=submitted['origin_ns'] or s['deadline_ns']!=submitted['deadline_ns'] or r['payload_hash']!=expected_hash:raise ValueError('original ingress/deadline/payload changed')
    if s['deadline_ns']!=s['source_ns']+5_000_000_000 or not r['source_ns']<r['deadline_ns']<=s['deadline_ns']:raise ValueError('sender deadline changed or conservative receiver deadline extended')
    if not all(endpoint['ready'] and endpoint['clock'] for endpoint in (sender,receiver)):raise ValueError('restored endpoints not qualified')
    if sender['commands_sent']!=1 or sender['fault'] or receiver['fault'] or sender['worker_fault'] or receiver['worker_fault']:raise ValueError('endpoint fault or replay')
    if not 0<barrier['ns']<resumed['begin_ns']:raise ValueError('phase barrier did not precede resumed worker')
    if phase!='committed' and r['finished_ns']<resumed['begin_ns']:raise ValueError('pre-effect phase result predates resume')
    if r['state']==4:
        if not r['result_valid'] or r['revision']!=3 or r['result_generation']!=1 or receiver['effects']!=1 or receiver['generation']!=1 or receiver['rate_hz']!=100:raise ValueError('unsupported success or duplicate effect')
        if phase!='committed' and resumed['begin_ns']>=r['deadline_ns']:raise ValueError('effect resumed after original deadline')
        if phase=='admission' and not resumed['begin_ns']<=r['dispatched_ns']<r['deadline_ns']:raise ValueError('dispatch outside restored fresh window')
    elif r['state'] in (6,7):
        if r['result_valid'] or receiver['effects'] or receiver['generation'] or receiver['rate_hz']!=200:raise ValueError('declined command caused effect or fabricated result')
        if phase=='committed':raise ValueError('committed success was lost')
        if r['reason'] not in ((1,3) if r['state']==6 else (3,)):raise ValueError('unexpected rejection/expiry reason')
    else:raise ValueError('pure packet-outage fixture did not reconcile to durable success/rejection/expiry')
    if phase=='committed':
        if not barrier_record or barrier_record['state']!=4 or not barrier_record['result_valid'] or barrier_record['finished_ns']>barrier['ns']:raise ValueError('result-commit barrier not backed by committed proof')
    elif phase=='admission':
        if barrier_record is not None:raise ValueError('receiver admission already visible before commit barrier')
    elif not barrier_record or barrier_record['state']!=3 or barrier['effects']!=0 or barrier['ns']>=r['deadline_ns']:
        raise ValueError('after-start barrier not before effect within original deadline')
    if phase=='dispatch' and not 0<r['dispatched_ns']<=barrier['ns']<resumed['begin_ns']:raise ValueError('durable dispatch barrier/order mismatch')
    return dict(state=r['state'],reason=r['reason'],effects=receiver['effects'],command_sends=sender['commands_sent'],sender_deadline_ns=s['deadline_ns'],receiver_deadline_ns=r['deadline_ns'],deadline_conservative_margin_ns=s['deadline_ns']-r['deadline_ns'],journal_proof_match=True,scope='controlled packet interruption, live same-owner endpoint/worker; temporary UNKNOWN allowed during outage, final durable evidence required; no replay, crash-recovery or ROS sensor-age qualification')


LIVE_READ='''import sqlite3,json,sys
with sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True,timeout=1) as db:
 rows=db.execute('SELECT id,state,record FROM entries').fetchall()
 out=[]
 for id,state,b in rows:
  assert len(b)==512 and b[:6]==b'RWJ1\\x00\\x01' and state==10+b[6]
  out.append(dict(id=id.hex(),state=b[6],result_valid=bool(b[164]),finished_ns=int.from_bytes(b[144:152],'big')))
 print(json.dumps(out))
'''


def run_case(out,phase,direction,hold_seconds=2,runtime_layout='baseline'):
    selected=native_layout(ROOT,runtime_layout)
    if hold_seconds not in (2,6):raise ValueError("only declared2/6-second holds")
    out.mkdir(parents=True,exist_ok=False);inside='/workspace/'+str(out.relative_to(ROOT));lab=NetworkLab(ROOT,out,IMAGE);peers=[];result=dict(status='running',phase=phase,direction=direction,hold_seconds=hold_seconds,qualification=False)
    key=out/'passphrase';key.touch(mode=0o600);key.write_text(secrets.token_urlsafe(32))
    inventory=dict(selected['runtime_sha256'])
    write(out/'provenance.json',dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,source_sha256=source_inventory(ROOT),runtime_sha256=inventory,runtime_layout=selected['layout'],fixture_binding=selected['binding'],simulated_handler=True,source_load=False,operation_watchdog_seconds=20,command_budget_seconds=5))
    try:
        lab.start(key);configure(lab,'permanent');lab.apply('N0',1701)
        result['clock_proof']={r:lab.inside(r,r+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for r in lab.containers};common_clock(result['clock_proof'])
        for role,name in lab.containers.items():
            log=(out/(role+'-peer.log')).open('w');peers.append((subprocess.Popen(['docker','exec',name,selected['peer'],role,inside,lab.addresses['operator'],phase,'/run/bridge/passphrase'],stdout=log,stderr=subprocess.STDOUT),log))
        wait_files(out,[r+'-ready.json' for r in lab.containers],peers);(out/'go').touch()
        wait_files(out,['robot-barrier.json','submitted.json'],peers)
        barrier=json.loads((out/'robot-barrier.json').read_text())['snapshot']
        visible=json.loads(lab.inside('robot','barrier-journal-read',['python3','-c',LIVE_READ,inside+'/robot.sqlite']))
        if len(visible)>1:raise ValueError('multiple receiver records at barrier')
        record=visible[0] if visible else None
        if record and record['id']!=ID:raise ValueError('wrong barrier journal ID')
        result['barrier']=dict(snapshot=barrier,visible_journal=record)
        if not barrier['paused'] or not barrier['ready'] or not barrier['clock']:raise ValueError('unqualified initial phase barrier')
        roles=DIRECTIONS[direction];result['outage_install']={r:network(lab,r,True,'outage-'+r) for r in roles}
        last=max(v['bracket']['end_ns'] for v in result['outage_install'].values())
        # The wait itself runs in the VM, sharing the clock proof with the peers.
        result['hold']=json.loads(lab.inside('robot','outage-hold',['python3','-c','import time,json;b=time.monotonic_ns();time.sleep('+str(hold_seconds)+');print(json.dumps(dict(begin_ns=b,end_ns=time.monotonic_ns())))']))
        result['outage_final']={r:json.loads(lab.inside(r,'outage-final-'+r,['tc','-j','-s','qdisc','show','dev','eth0'])) for r in roles}
        if any(next(q for q in qs if q['kind']=='netem').get('drops',0)<=0 for qs in result['outage_final'].values()):raise ValueError('outage matched no traffic')
        result['outage_restore']={r:network(lab,r,False,'restore-'+r) for r in roles}
        first=min(v['bracket']['begin_ns'] for v in result['outage_restore'].values())
        if first-last<hold_seconds*1_000_000_000:raise ValueError('guaranteed interruption shorter than declared hold')
        result['guaranteed_outage_ns']=[last,first]
        (out/'restored').touch();(out/'resume').touch()
        wait_files(out,['operator-outcome.json','resumed.json'],peers,timeout=35)
        (out/'settle').touch();wait_files(out,[r+'-result.json' for r in lab.containers],peers)
        (out/'release').touch()
        for p,log in peers:
            if p.wait(timeout=10)!=0:raise ValueError('native N4 peer failed')
            log.close()
        a=read_journal(out/'operator.sqlite',1);b=read_journal(out/'robot.sqlite',2)
        sender=json.loads((out/'operator-result.json').read_text());receiver=json.loads((out/'robot-result.json').read_text())
        result['outcome']=check_outcome('committed' if phase=='query' else phase,sender,receiver,a,b,barrier,json.loads((out/'resumed.json').read_text()),record,{role:json.loads((out/(role+'-ready.json')).read_text()) for role in lab.containers},json.loads((out/'submitted.json').read_text()))
        if hold_seconds==6 and (result['outcome']['state'] not in (6,7) or result['outcome']['effects']!=0 or json.loads((out/'resumed.json').read_text())['begin_ns']<=result['outcome']['sender_deadline_ns']):raise ValueError('deadline overrun was executed or not checked beyond expiry')
        if phase=='query' and sender['queries_sent']<=0:raise ValueError('withheld result did not recover by query')
        result['withheld_direct_result']=phase=='query'
        result['stopped']={r:json.loads((out/(r+'-stopped.json')).read_text()) for r in lab.containers}
        result['journals']=dict(sender=a,receiver=b)
        if selected!=native_layout(ROOT,runtime_layout):raise ValueError('runtime or fixture binding changed')
        result['status']='passed'
    except Exception as error:result.update(status='failed',error=str(error))
    finally:
        (out/'resume').touch();(out/'restored').touch();(out/'settle').touch();(out/'release').touch()
        for p,log in peers:
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
            if not log.closed:log.close()
        try:lab.cleanup()
        finally:key.unlink(missing_ok=True);write(out/'result.json',result)
    return result


def failure_suite(out):
    out.mkdir(parents=True,exist_ok=False);lab=NetworkLab(ROOT,out,IMAGE);key=out/'passphrase';key.touch(mode=0o600);key.write_text(secrets.token_urlsafe(32))
    result=dict(status='running');runtime={p:sha(ROOT/p) for p in ('install/m3-ros/robotweax_srt_bridge/lib/robotweax_srt_bridge/bridge_node','install/bridge-m3/bin/robotweax-journal-worker')}
    write(out/'provenance.json',dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,runtime_sha256=runtime))
    try:
        lab.start(key);configure(lab,'permanent');inside='/workspace/'+str(out.relative_to(ROOT))+'/controls'
        lab.inside('operator','failure-controls',['bash','-c','source /opt/ros/jazzy/setup.bash && source install/m3-ros/setup.bash && exec python3 tools/m3_failure_detection.py --output '+inside+' --peer '+lab.addresses['robot']])
        result['controls']=json.loads((out/'controls/result.json').read_text())
        if not result['controls']['passed']:raise ValueError('failure controls did not all classify correctly')
        if runtime!={p:sha(ROOT/p) for p in runtime}:raise ValueError('failure-test runtime changed')
        result['status']='passed'
    except Exception as error:result.update(status='failed',error=str(error))
    finally:
        try:lab.cleanup()
        finally:key.unlink(missing_ok=True);write(out/'result.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--failure-controls',action='store_true');p.add_argument('--dispatch-only',action='store_true');p.add_argument('--remaining-native',action='store_true');p.add_argument('--runtime-layout',choices=tuple(LAYOUTS),default='baseline');a=p.parse_args();root=a.output.resolve()
    if a.failure_controls and a.runtime_layout!='baseline':p.error('failure-controls retains its baseline-only fixture; select a separate matched case')
    if a.failure_controls:result=failure_suite(root)
    else:
        root.mkdir(parents=True,exist_ok=False);rows=[];result=dict(status='running',cases=rows,qualification=False)
        try:
            phases=(('admission','dispatch','started','query') if a.remaining_native else ('dispatch',) if a.dispatch_only else PHASES)
            for phase in phases:
                for direction in (('both',) if a.remaining_native else DIRECTIONS):
                    print('START '+phase+' '+direction,flush=True);case=run_case(root/(phase+'-'+direction),phase,direction,6 if a.remaining_native and phase!='query' else 2,a.runtime_layout);rows.append(dict(phase=phase,direction=direction,status=case['status'],error=case.get('error')));write(root/'cohort.json',result)
                    print(json.dumps(rows[-1]),flush=True)
                    if case['status']!='passed':raise RuntimeError('N4 phase case failed; remaining cases not executed')
            result['status']='passed'
        except Exception as error:result.update(status='failed',error=str(error))
        finally:write(root/'cohort.json',result)
    raise SystemExit(result['status']!='passed')
