#!/usr/bin/env python3
"""Known unread-buffer abort versus bounded drain, in fresh owned containers."""
import argparse,json,secrets,subprocess,time
from collections import Counter
from pathlib import Path
from m3_network import NetworkLab
from m3_neighbor_diagnostics import configure
from m3_capture import pcap_options,stop_captures,validate_tcpdump_footer
from m3_capture_drain import signal_recorder
from m3_monotonic_capture import start,records,feature_snapshot
from m3_tap_probe import pcap_records,probe_id
from m3_dds_result_timeline import common_clock

ROOT=Path(__file__).resolve().parents[1]


def run_case(run,image,mode):
    run.mkdir();inside='/workspace/'+str(run.relative_to(ROOT));lab=NetworkLab(ROOT,run,image,monotonic_capture=True);captures=[];server=None;server_log=None;paused={}
    key=run/'passphrase';key.touch(mode=0o600);key.write_text(secrets.token_urlsafe(32))
    result=dict(status='running',mode=mode,scope='deliberately paused recorder with16 finite known UDP sends; class reproduction only, not historical cause or capture acceptance waiver')
    try:
        lab.start(key);result['clocks']={role:lab.inside(role,role+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for role in lab.containers};common_clock(result['clocks'])
        configure(lab,'permanent');lab.apply('N0',1701);result['features_before']=feature_snapshot(lab,'features-before')
        for role,name in lab.containers.items():
            log=(run/(role+'-capture.log')).open('w');captures.append((subprocess.Popen(['docker','exec',name]+pcap_options()+['-w',inside+'/'+role+'.pcap','udp'],stdout=log,stderr=subprocess.STDOUT),log))
        start(run,inside,lab,captures)
        server_log=(run/'receiver.log').open('w');server=subprocess.Popen(['docker','exec',lab.containers['robot'],'python3','tools/m3_tap_probe.py','receive','--out',inside+'/received.json','--ready',inside+'/receive-ready','--stop',inside+'/receive-stop'],stdout=server_log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+5
        while not (run/'receive-ready').exists() or not all('listening on eth0' in (run/(role+'-capture.log')).read_text() for role in lab.containers):
            if server.poll() is not None or time.monotonic()>deadline:raise RuntimeError('drain probe readiness failed')
            time.sleep(.05)
        for role in lab.containers:paused[role]=signal_recorder(lab,role,'pause-'+role,'SIGSTOP')['identities']
        lab.inside('operator','send',['python3','tools/m3_tap_probe.py','send','--peer',lab.addresses['robot'],'--case','1','--count','16','--out',inside+'/sent.json'])
        time.sleep(.1);(run/'receive-stop').touch();assert server.wait(timeout=5)==0;server_log.close();server=None
        if mode=='drain':
            for role,identity in paused.items():signal_recorder(lab,role,'resume-'+role,'SIGCONT',identity)
            paused={};stop_captures(lab,drain_check=True)
        else:
            stop_captures(lab)
            for role,identity in paused.items():signal_recorder(lab,role,'resume-after-stop-'+role,'SIGCONT',identity)
            paused={}
        for p,log in captures:p.wait(timeout=5);log.close()
        result['features_after']=feature_snapshot(lab,'features-after');assert result['features_before']==result['features_after']
        result['captures']={};result['native']={}
        for role in lab.containers:
            pcaps=pcap_records(run/(role+'.pcap'));counts=validate_tcpdump_footer((run/(role+'-capture.log')).read_text(),len(pcaps),require_nonempty=False)
            ids=[r['identity'] for r in pcaps if r['identity']];result['captures'][role]=dict(counts,known_records=len(ids))
            status=json.loads((run/(role+'-monotonic-capture.log')).read_text().splitlines()[-1]);rows=list(records(run/(role+'.mono')))
            assert status['complete'] and status['records']==status['seen']==status['submitted']==len(rows) and not status['reserve_failed'] and not status['copy_failed']
            native=[probe_id(r['prefix']) for r in rows if probe_id(r['prefix'])];assert Counter(native)==Counter((1,n) for n in range(16));result['native'][role]=status
            if mode=='drain':assert len(ids)==16 and counts['tcpdump_population_reconciled']
            else:assert len(ids)<16 and counts['tcpdump_reported_filtered_packets']==16 and not counts['tcpdump_population_reconciled']
        received=json.loads((run/'received.json').read_text());assert sorted(r['sequence'] for r in received['rows'])==list(range(16))
        result.update(status='passed',application_received=16,interpretation='known abort produces incomplete file with zero kernel drops' if mode=='abort' else 'bounded drain plus final record/footer/known-ID checks complete')
    except Exception as error:result.update(status='failed',error=str(error));raise
    finally:
        if server is not None and server.poll() is None:
            (run/'receive-stop').touch()
            try:server.wait(timeout=5)
            except subprocess.TimeoutExpired:server.terminate();server.wait(timeout=5)
        if server_log is not None and not server_log.closed:server_log.close()
        for role,identity in paused.items():
            try:signal_recorder(lab,role,'cleanup-resume-'+role,'SIGCONT',identity)
            except Exception:pass
        for role in lab.containers:
            try:signal_recorder(lab,role,'cleanup-stop-'+role,'SIGINT')
            except Exception:pass
        for p,log in captures:
            if p.poll() is None:p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
            if not log.closed:log.close()
        lab.cleanup();key.unlink(missing_ok=True);(run/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);args=p.parse_args();run=args.out.resolve();run.mkdir(parents=True,exist_ok=False)
    image=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64','ros2-srt-m3:20261105'],text=True))[0]['RepoDigests'][0];report=dict(status='running',image=image,cases=[])
    try:
        for mode in ('abort','drain'):report['cases'].append(run_case(run/mode,image,mode))
        report['status']='passed'
    except Exception as error:report.update(status='failed',error=str(error));raise
    finally:(run/'result.json').write_text(json.dumps(report,indent=2)+'\n')
