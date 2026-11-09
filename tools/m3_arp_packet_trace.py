#!/usr/bin/env python3
"""One N0 then one unchanged N5 packet-trace calibration; never retry a case."""
import argparse,json,secrets,subprocess,time
from pathlib import Path
from m3_network import NetworkLab
from m3_source_preflight import ROOT,IMAGE,write,sha
from m3_n5_progress import RUNTIMES
from m3_session_sensor_diagnostics import OBSERVERS
from m3_controlled_arp_reply import wait_for
from m3_neighbor_diagnostics import configure
from m3_monotonic_capture import start as native_start,feature_snapshot
from m3_capture import pcap_options,wait_ready,stop_captures
from m3_dds_result_timeline import common_clock
from m3_arp_packet_analysis import analyze

BINARY='build/arp-packet-trace/arp_packet_trace'


def config(rows):
    return [{k:r.get(k) for k in ('kind','handle','parent','root','options')} for r in rows]


def stop_trace(lab):
    lab.inside('robot','trace-stop',['python3','-c','import pathlib,os,signal\nfor p in pathlib.Path("/proc").glob("[0-9]*/comm"):\n try:\n  if p.read_text().strip()=="m3_arp_trace":os.kill(int(p.parent.name),signal.SIGTERM)\n except (FileNotFoundError,ProcessLookupError):pass\n'])


def run_case(run,profile):
    run.mkdir();inside='/workspace/'+str(run.relative_to(ROOT));credential=run/'passphrase';credential.touch(mode=0o600);credential.write_text(secrets.token_urlsafe(32));lab=NetworkLab(ROOT,run,IMAGE,monotonic_capture=True,packet_trace=True)
    captures=[];children=[];logs=[];trace=None;receiver=None;result=dict(status='running',profile=profile,seed=2903,child_outcomes={})
    def child(label,role,argv):
        log=(run/(label+'.log')).open('w');logs.append(log);p=subprocess.Popen(['docker','exec',lab.containers[role]]+argv,stdout=log,stderr=subprocess.STDOUT);children.append((label,p));return p
    def stimulus(role,mode,label,extra=()):
        peer='operator' if role=='robot' else 'robot';return ['python3','tools/m3_arp_trace_stimulus.py','--mode',mode,'--source',lab.addresses[role],'--target',lab.addresses[peer],'--out',inside+'/'+label+'.json']+list(extra)
    try:
        lab.start(credential);lab.apply(profile,2903);result['addresses']=dict(lab.addresses);n=configure(lab,'dynamic');result['neighbors']=n;result['macs']=n['peer_macs']
        if any(n['before'].values()):raise ValueError('fresh peers must be ABSENT')
        result['clock_proof']={r:lab.inside(r,r+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for r in lab.containers};common_clock(result['clock_proof'])
        lab.inside('robot','btf',[BINARY,'--inspect']);(run/'btf.json').write_text((run/'btf.log').read_text())
        result['features_before']=feature_snapshot(lab,'features-before');lab.snapshot('before');result['configs_before']={r:config(json.loads((run/('before-'+r+'.log')).read_text())) for r in lab.containers}
        for role,name in lab.containers.items():
            log=(run/(role+'-capture.log')).open('w');captures.append((subprocess.Popen(['docker','exec',name]+pcap_options()+['-w',inside+'/'+role+'.pcap','arp'],stdout=log,stderr=subprocess.STDOUT),log))
        wait_ready(run,captures);native_start(run,inside,lab,captures)
        trace=child('trace','robot',[BINARY,'eth0',lab.addresses['robot'],lab.addresses['operator'],n['peer_macs']['robot'],n['peer_macs']['operator'],inside+'/trace.jsonl',inside+'/trace-ready.json','45'])
        wait_for(lambda:(run/'trace-ready.json').exists(),[trace],10,'trace')
        receiver=child('receiver','operator',stimulus('operator','receive','receiver',['--ready',inside+'/receiver-ready.json','--stop',inside+'/receiver-stop']))
        wait_for(lambda:(run/'receiver-ready.json').exists(),[receiver,trace],5,'receiver')
        request_extra=['--source-mac',n['peer_macs']['operator'],'--target-mac',n['peer_macs']['robot']]
        lab.inside('operator','pre-requests',stimulus('operator','requests','pre-requests',request_extra+['--count','5']));time.sleep(.3)
        flood=None
        if profile=='N5':
            flood=child('flood','robot',stimulus('robot','flood','flood',['--ready',inside+'/flood-ready.json']))
            wait_for(lambda:(run/'flood-ready.json').exists(),[flood,receiver,trace],5,'flood')
        lab.inside('operator','middle-requests',stimulus('operator','requests','middle-requests',request_extra+['--count','20']))
        if flood is not None and flood.wait(timeout=5):raise ValueError('flood failed')
        time.sleep(3)
        lab.inside('operator','post-requests',stimulus('operator','requests','post-requests',request_extra+['--count','5']));time.sleep(1)
        (run/'receiver-stop').touch()
        if receiver.wait(timeout=3):raise ValueError('receiver failed')
        stop_trace(lab)
        if trace.wait(timeout=5):raise ValueError('trace failed')
        lab.snapshot('after');result['configs_after']={r:config(json.loads((run/('after-'+r+'.log')).read_text())) for r in lab.containers}
        if result['configs_before']!=result['configs_after']:raise ValueError('qdisc settings changed')
        result['features_after']=feature_snapshot(lab,'features-after')
        if result['features_before']!=result['features_after']:raise ValueError('feature settings changed')
        result['status']='captured'
    except Exception as e:result.update(status='failed',error=str(e))
    finally:
        if receiver is not None and receiver.poll() is None:(run/'receiver-stop').touch()
        if trace is not None and trace.poll() is None:
            try:stop_trace(lab)
            except Exception as e:result.setdefault('cleanup_errors',[]).append(str(e))
        for label,p in children:
            forced=False
            try:code=p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.terminate();forced=True;code=p.wait(timeout=3)
            result['child_outcomes'][label]=dict(exit_code=code,forced=forced)
            if code or forced:result['status']='failed'
        try:
            if captures:stop_captures(lab)
            for p,log in captures:
                if p.wait(timeout=5):raise ValueError('capture exit')
                log.close()
        except Exception as e:result.setdefault('cleanup_errors',[]).append(str(e));result['status']='failed'
        for log in logs:log.close()
        lab.cleanup();credential.unlink(missing_ok=True);write(run/'result.json',result)
    if result['status']=='captured':
        try:result['analysis']=analyze(run,result);result['status']='passed'
        except Exception as e:result.update(status='failed',error=str(e))
    write(run/'result.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.relative_to(ROOT);out.mkdir(parents=True,exist_ok=False)
    before={n:sha(ROOT/n) for n in RUNTIMES+OBSERVERS+[BINARY]};sources={str(p.relative_to(ROOT)):sha(p) for f in ('src','ros2','tools','tests','proto','cmake','containers') for p in (ROOT/f).rglob('*') if p.is_file() and '__pycache__' not in str(p)}
    report=dict(status='running',source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,binaries_before=before,source_sha256=sources,rows=[],no_tuning=True,qualification=False);write(out/'execution.json',report);failed=False
    for profile in ('N0','N5'):
        row=dict(profile=profile,status='not_executed');report['rows'].append(row)
        if failed:row['why']='prior failure; no retry';write(out/'execution.json',report);continue
        try:
            result=run_case(out/profile,profile);row.update(status=result['status'],error=result.get('error'));failed=result['status']!='passed' or bool(result.get('cleanup_errors'))
            if any(sha(ROOT/n)!=h for n,h in before.items()) or any(sha(ROOT/n)!=h for n,h in sources.items()):raise ValueError('frozen source/binary changed')
        except Exception as e:row.update(status='failed',error=str(e));failed=True
        write(out/'execution.json',report);print(json.dumps(row),flush=True)
    report['binaries_after']={n:sha(ROOT/n) for n in before};report['binaries_unchanged']=before==report['binaries_after'];report['status']='failed' if failed or not report['binaries_unchanged'] else 'passed';write(out/'execution.json',report);return int(report['status']!='passed')


if __name__=='__main__':raise SystemExit(main())
