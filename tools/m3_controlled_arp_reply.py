#!/usr/bin/env python3
"""Two fresh owned ARP reply cases, once each; no tuning or synthetic retransmit."""
import argparse,json,secrets,subprocess,sys,time
from pathlib import Path
from m3_network import NetworkLab
from m3_source_preflight import ROOT,IMAGE,sha,write
from m3_n5_progress import RUNTIMES
from m3_session_sensor_diagnostics import OBSERVERS
from m3_neighbor_diagnostics import configure,start as neighbor_start,stop as neighbor_stop
from m3_monotonic_capture import start as native_start,feature_snapshot
from m3_capture import pcap_options,wait_ready,stop_captures
from m3_capture_drain import check as drain_check
from m3_control_fault import BRACKET
from m3_dds_result_timeline import common_clock
from m3_arp_reply_observer import selector,PREF
from m3_arp_reply_analysis import analyze_case


def wait_for(predicate,children,seconds,label):
    end=time.monotonic()+seconds
    while not predicate():
        if any(p.poll() is not None for p in children):raise ValueError(label+' child exited before readiness')
        if time.monotonic()>end:raise ValueError(label+' timeout')
        time.sleep(.01)


def root_config(raw):
    q=[r for r in raw if r.get('root')]
    if len(q)!=1:raise ValueError('ambiguous root')
    return {k:q[0].get(k) for k in ('kind','handle','options')}


def run_case(run,number,fault):
    run.mkdir(exist_ok=False);inside='/workspace/'+str(run.relative_to(ROOT));credential=run/'passphrase';credential.touch(mode=0o600);credential.write_text(secrets.token_urlsafe(32));lab=NetworkLab(ROOT,run,IMAGE,monotonic_capture=True)
    captures=[];neighbors=[];children=[];logs=[];receiver=None;controller=None;result=dict(status='running',number=number,fault=fault,child_outcomes={},scope='synthetic UDP and kernel ARP only, fresh owned namespaces, no SRT/ROS peer or tuning')
    try:
        lab.start(credential);lab.apply('N0',2903);result['addresses']=dict(lab.addresses)
        result['clock_proof']={r:lab.inside(r,r+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for r in lab.containers};common_clock(result['clock_proof'])
        n=configure(lab,'dynamic');result['neighbor_configuration']=n
        if any(n['before'].values()):raise ValueError('fresh peers not initially ABSENT; no flush allowed')
        result['features_before']=feature_snapshot(lab,'features-before');lab.snapshot('before')
        result['roots_before']={r:json.loads((run/('before-'+r+'.log')).read_text()) for r in lab.containers}
        for role,name in lab.containers.items():
            log=(run/(role+'-capture.log')).open('w');captures.append((subprocess.Popen(['docker','exec',name]+pcap_options()+['-w',inside+'/'+role+'.pcap','arp or (ip and udp)'],stdout=log,stderr=subprocess.STDOUT),log))
        wait_ready(run,captures);native_start(run,inside,lab,captures);neighbor_start(lab,run,inside,neighbors)
        log=(run/'receiver.log').open('w');logs.append(log)
        receiver=subprocess.Popen(['docker','exec',lab.containers['robot'],'python3','tools/m3_arp_reply_receiver.py','--ready',inside+'/receiver-ready.json','--out',inside+'/received.json','--stop',inside+'/receiver-stop','--progress',inside+'/receive-progress.json'],stdout=log,stderr=subprocess.STDOUT);children.append(receiver)
        wait_for(lambda:(run/'receiver-ready.json').exists(),[receiver],5,'receiver')
        lab.inside('robot','reply-hook',['tc','qdisc','add','dev','eth0','clsact'])
        verdict='drop' if fault else 'pass';args=(lab.addresses['robot'],lab.addresses['operator'],n['peer_macs']['robot'],n['peer_macs']['operator'],verdict)
        result['installation']=json.loads(lab.inside('robot','reply-install',['python3','-c',BRACKET,json.dumps(selector(*args))]))
        log=(run/'controller.log').open('w');logs.append(log)
        controller=subprocess.Popen(['docker','exec',lab.containers['robot'],'python3','tools/m3_arp_reply_observer.py','--source',args[0],'--target',args[1],'--source-mac',args[2],'--target-mac',args[3],'--verdict',verdict,'--sent',inside+'/sent.json','--ready',inside+'/controller-ready.json','--out',inside+'/controller.json'],stdout=log,stderr=subprocess.STDOUT);children.append(controller)
        wait_for(lambda:(run/'controller-ready.json').exists(),[controller,receiver],5,'controller')
        lab.inside('operator','original-send',['python3','tools/m3_arp_reply_sender.py','--peer',lab.addresses['robot'],'--case',str(number),'--count','3','--out',inside+'/sent.json'])
        code=controller.wait(timeout=8);result['child_outcomes']['controller']=dict(exit_code=code,forced=False)
        if code:raise ValueError('bounded reply controller failed')
        result['controller']=json.loads((run/'controller.json').read_text())
        def population(case,count):
            p=run/'receive-progress.json'
            return p.exists() and sum(r['case']==case for r in json.loads(p.read_text())['rows'])>=count
        wait_for(lambda:population(number,3),[receiver],6,'original queued UDP delivery')
        lab.inside('operator','fresh-send',['python3','tools/m3_arp_reply_sender.py','--peer',lab.addresses['robot'],'--case',str(number+1000),'--count','1','--out',inside+'/fresh-sent.json'])
        wait_for(lambda:population(number+1000,1),[receiver],3,'fresh UDP delivery')
        (run/'receiver-stop').touch();code=receiver.wait(timeout=3);result['child_outcomes']['receiver']=dict(exit_code=code,forced=False)
        if code:raise ValueError('receiver incomplete')
        result['neighbor_diagnostics']=neighbor_stop(lab,run,neighbors,'dynamic',n['peer_macs']);neighbors=[]
        result['features_after']=feature_snapshot(lab,'features-after')
        if result['features_before']!=result['features_after']:raise ValueError('feature state changed')
        lab.snapshot('after');result['roots_after']={r:json.loads((run/('after-'+r+'.log')).read_text()) for r in lab.containers}
        for role in lab.containers:
            if root_config(result['roots_before'][role])!=root_config(result['roots_after'][role]):raise ValueError('root settings changed')
            a=next(r for r in result['roots_before'][role] if r.get('root'));b=next(r for r in result['roots_after'][role] if r.get('root'))
            if b['drops']!=a['drops']:raise ValueError('unexpected root drops in unshaped synthetic fixture')
        result['drain']=drain_check(lab,run);result['status']='captured'
    except Exception as e:result.update(status='failed',error=str(e))
    finally:
        for label,p in [('controller',controller),('receiver',receiver)]:
            if p is not None and p.poll() is None:
                if label=='receiver':(run/'receiver-stop').touch()
                try:code=p.wait(timeout=2);result['child_outcomes'][label]=dict(exit_code=code,forced=False,cleanup=True)
                except subprocess.TimeoutExpired:
                    p.terminate()
                    try:p.wait(timeout=2)
                    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
                    result['child_outcomes'][label]=dict(exit_code=p.returncode,forced=True,cleanup=True)
            elif p is not None and label not in result['child_outcomes']:result['child_outcomes'][label]=dict(exit_code=p.returncode,forced=False,cleanup=True)
        for log in logs:log.close()
        if neighbors:
            try:result['neighbor_cleanup']=neighbor_stop(lab,run,neighbors,'dynamic',result['neighbor_configuration']['peer_macs'])
            except Exception as e:result.setdefault('cleanup_errors',[]).append(str(e))
        try:
            if 'robot' in lab.containers:
                remaining=json.loads(lab.inside('robot','reply-rule-final',['tc','-j','filter','show','dev','eth0','egress','pref',PREF]))
                if remaining:lab.inside('robot','reply-emergency-remove',['tc','filter','del','dev','eth0','egress','protocol','arp','pref',PREF])
                result['remaining_rule']=json.loads(lab.inside('robot','reply-rule-restored',['tc','-j','filter','show','dev','eth0','egress','pref',PREF]))
                if result['remaining_rule']:raise ValueError('ARP reply rule not removed')
            if captures:stop_captures(lab)
            for p,log in captures:
                if p.wait(timeout=5):raise ValueError('capture child failed')
                log.close()
        except Exception as e:result.setdefault('cleanup_errors',[]).append(str(e));result['status']='failed'
        finally:
            lab.cleanup();credential.unlink(missing_ok=True);write(run/'result.json',result)
    if result['status']=='captured':
        try:result=analyze_case(run,result);result['status']='passed'
        except Exception as e:result.update(status='failed',error=str(e))
        write(run/'result.json',result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    before={n:sha(ROOT/n) for n in RUNTIMES+OBSERVERS};sources={str(p.relative_to(ROOT)):sha(p) for folder in ('src','ros2','tools','tests','proto','cmake','containers') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    report=dict(status='running',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),runtime_observers_before=before,source_sha256=sources,rows=[],qualification=False,no_tuning=True)
    write(out/'execution.json',report);failed=False
    for number,(label,fault) in enumerate([('clean-pass',False),('reply-drop-restore',True)],1):
        row=dict(label=label,number=number,fault=fault,status='not_executed');report['rows'].append(row)
        if failed:row['why']='prior case failed; no case retry';write(out/'execution.json',report);continue
        row['status']='running';write(out/'execution.json',report)
        try:
            r=run_case(out/label,number,fault);row.update(status=r['status'],run=str((out/label).relative_to(ROOT)),error=r.get('error'))
            if r['status']!='passed' or r.get('cleanup_errors'):failed=True
            if any(sha(ROOT/n)!=h for n,h in before.items()) or any(sha(ROOT/n)!=h for n,h in sources.items()):raise ValueError('runtime/observer/frozen source changed')
        except Exception as e:row.update(status='failed',error=str(e));failed=True
        write(out/'execution.json',report);print(label,row['status'],row.get('error'),flush=True)
    report['runtime_observers_after']={n:sha(ROOT/n) for n in before};report['runtime_unchanged']=before==report['runtime_observers_after'];report['status']='failed' if failed or not report['runtime_unchanged'] else 'passed';write(out/'execution.json',report)
    return int(report['status']!='passed')


if __name__=='__main__':raise SystemExit(main())
