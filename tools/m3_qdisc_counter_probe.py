#!/usr/bin/env python3
"""Qualify the owned CONTROL PASS counter versus root qdisc and AF_PACKET taps."""
import argparse,json,secrets,subprocess,time
from pathlib import Path
from collections import Counter
from m3_network import NetworkLab
from m3_neighbor_diagnostics import configure
from m3_qdisc_diagnostics import install,counters,root,PREF
from m3_capture import pcap_options,stop_captures,validate_tcpdump_footer
from m3_monotonic_capture import start,records,feature_snapshot
from m3_tap_probe import probe_id,pcap_records
from m3_dds_result_timeline import common_clock

ROOT=Path(__file__).resolve().parents[1]


def apply_profile(lab,profile,label):
    # tc replace cannot reuse handle1: for a different qdisc kind. Only this
    # synthetic fixture transitions root kinds; its generator is idle here.
    state=json.loads(lab.inside('operator',label+'-transition-before',['tc','-j','qdisc','show','dev','eth0']))
    current=next(q for q in state if q.get('root'))
    target='tbf' if profile=='N5' else 'netem'
    if current['kind']!=target:lab.inside('operator',label+'-transition-remove',['tc','qdisc','del','dev','eth0','root'])
    lab.apply(profile,1701,roles=('operator',),label=label)


def run_probe(run):
    run=run.resolve();run.mkdir(parents=True,exist_ok=False);inside='/workspace/'+str(run.relative_to(ROOT))
    image=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64','ros2-srt-m3:20261105'],text=True))[0]['RepoDigests'][0]
    lab=NetworkLab(ROOT,run,image,monotonic_capture=True);capture=[];server=None;server_log=None
    credential=run/'passphrase';credential.touch(mode=0o600);credential.write_text(secrets.token_urlsafe(32))
    result=dict(status='running',image=image,phases=[],qualification=False,scope='synthetic UDP only; source port10080, destination39781; known counts, no ROS/SRT authentication or physical-frame claim')
    try:
        lab.start(credential);result['clock_proof']={role:lab.inside(role,role+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for role in lab.containers};common_clock(result['clock_proof'])
        result['neighbor_configuration']=configure(lab,'permanent');lab.apply('N0',1701);result['observer_configuration']=install(lab)
        result['features_before']=feature_snapshot(lab,'features-before')
        for role,name in lab.containers.items():
            log=(run/(role+'-capture.log')).open('w');capture.append((subprocess.Popen(['docker','exec',name]+pcap_options()+['-w',inside+'/'+role+'.pcap','udp'],stdout=log,stderr=subprocess.STDOUT),log))
        start(run,inside,lab,capture)
        server_log=(run/'receiver.log').open('w');server=subprocess.Popen(['docker','exec',lab.containers['robot'],'python3','tools/m3_tap_probe.py','receive','--out',inside+'/received.json','--ready',inside+'/receive-ready','--stop',inside+'/receive-stop'],stdout=server_log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+5
        while not (run/'receive-ready').exists() or not all('listening on eth0' in (run/(role+'-capture.log')).read_text() for role in lab.containers):
            if server.poll() is not None or time.monotonic()>deadline:raise ValueError('probe readiness failed')
            time.sleep(.05)
        for case,(label,profile,count,port) in enumerate([('baseline','N0',16,10080),('sensor-negative','N0',4,10081),('root-drop','N4',16,10080),('shaped','N5',16,10080),('restored','N0',1,10080)],1):
            apply_profile(lab,profile,label)
            def snapshot(suffix):
                rules=json.loads(lab.inside('operator',label+'-filter-'+suffix,['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF]))
                qs=json.loads(lab.inside('operator',label+'-root-'+suffix,['tc','-j','-s','qdisc','show','dev','eth0']))
                return dict(pass_counter=counters(rules),root=root(qs))
            before=snapshot('before')
            lab.inside('operator',label+'-send',['python3','tools/m3_tap_probe.py','send','--bind-port',str(port),'--peer',lab.addresses['robot'],'--case',str(case),'--count',str(count),'--out',inside+'/'+label+'-sent.json'])
            time.sleep(1);after=snapshot('after')
            if after['pass_counter']['packets']-before['pass_counter']['packets']!=(0 if label=='sensor-negative' else count):raise ValueError('selected counter population mismatch')
            if label=='root-drop' and after['root']['drops']-before['root']['drops']<count:raise ValueError('known root loss not counted')
            result['phases'].append(dict(case=case,label=label,sent=count,source_port=port,before=before,after=after))
        (run/'receive-stop').touch();assert server.wait(timeout=5)==0;server_log.close();server=None
        for role in lab.containers:
            lab.inside(role,'observer-remove-'+role,['tc','filter','del','dev','eth0','egress','protocol','ip','pref',PREF])
            remaining=json.loads(lab.inside(role,'observer-restored-'+role,['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF]));assert not remaining
        result['features_after']=feature_snapshot(lab,'features-after');assert result['features_after']==result['features_before'];result['status']='captured'
    except Exception as error:result.update(status='failed',error=str(error));raise
    finally:
        if server is not None and server.poll() is None:
            (run/'receive-stop').touch()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.terminate();server.wait(timeout=5)
        if server_log is not None and not server_log.closed:server_log.close()
        try:
            stop_captures(lab)
            for p,log in capture:p.wait(timeout=5);log.close()
        finally:lab.cleanup();credential.unlink(missing_ok=True);(run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    try:
        captured={};statuses={};pcap={}
        for role in lab.containers:
            status=json.loads((run/(role+'-monotonic-capture.log')).read_text().splitlines()[-1]);rows=list(records(run/(role+'.mono')))
            if not status['complete'] or status['records']!=len(rows) or status['seen']!=len(rows) or status['submitted']!=len(rows) or status['reserve_failed'] or status['copy_failed']:raise ValueError('incomplete probe capture')
            statuses[role]=status;selected=[probe_id(r['prefix']) for r in rows if probe_id(r['prefix'])]
            captured[role]=Counter(case for case,_ in selected)
            frames=pcap_records(run/(role+'.pcap'));pcap[role]=validate_tcpdump_footer((run/(role+'-capture.log')).read_text(),len(frames))
            if not pcap[role]['tcpdump_population_reconciled'] or Counter(selected)!=Counter(r['identity'] for r in frames if r['identity']):raise ValueError('probe native/PCAP identity population mismatch')
        received=Counter(r['case'] for r in json.loads((run/'received.json').read_text())['rows'])
        for phase in result['phases']:
            case=phase['case'];expected=0 if phase['label']=='root-drop' else phase['sent']
            if any(captured[role][case]!=expected for role in captured) or received[case]!=expected:raise ValueError('probe forwarding/loss population mismatch')
            phase.update(sender_tap=captured['operator'][case],receiver_tap=captured['robot'][case],received=received[case])
        result.update(status='passed',stage='selected tc pass action observes sends before tested root loss; AF_PACKET tap after tested root loss',capture_status=statuses,pcap_status=pcap)
        (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result
    except Exception as error:
        result.update(status='failed',error=str(error));(run/'result.json').write_text(json.dumps(result,indent=2)+'\n');raise



if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args();r=run_probe(args.out);print(r['stage'])
