#!/usr/bin/env python3
"""Development-only loopback recorder pause/recovery control in network-none.

Fresh owned containers, synthetic UDP and unchanged bounded PCAP options. A
known SIGSTOP must be visible in /proc samples and rejected by the zero-drop
gate; SIGCONT must restore capture. Does not explain any historical failure.
"""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import socket
import struct
import subprocess
import threading
import time
from m3_capture import pcap_options, pcap_rotation_options, pcap_configuration, summarize, validate_tcpdump_footer
import m3_recorder_diagnostics as diagnostics

ROOT=Path(__file__).resolve().parents[1]
PORT=39782
RECOVERY=b'RECORDER-RECOVERED'


def contains_recovery(paths):
    for path in paths:
        with path.open('rb') as file:
            header=file.read(24)
            if header[:4]!=b'\xd4\xc3\xb2\xa1':raise ValueError('unexpected probe PCAP format')
            while record:=file.read(16):
                if len(record)!=16:raise ValueError('short record')
                length=struct.unpack('<IIII',record)[2]
                if length>262144:raise ValueError('oversized record')
                frame=file.read(length)
                if len(frame)!=length:raise ValueError('short frame')
                if frame.endswith(RECOVERY):return True
    return False


def child(run, pause):
    run.mkdir(parents=True,exist_ok=False)
    report=dict(status='failed',case='pause' if pause else 'baseline',capture_config=pcap_configuration())
    capture=None;observer=None;thread=None;done=threading.Event();received=[0]
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as receiver, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
        receiver.bind(('127.0.0.1',PORT));receiver.settimeout(.05)
        def receive():
            while not done.is_set():
                try:receiver.recvfrom(4096);received[0]+=1
                except socket.timeout:pass
        thread=threading.Thread(target=receive);thread.start()
        with (run/'capture.log').open('w') as capture_log, (run/'observer.log').open('w') as observer_log:
            try:
                capture=subprocess.Popen(pcap_options('lo')+pcap_rotation_options()+['-Z','root','-w',str(run/'probe.pcap'),'udp','port',str(PORT)],stdout=capture_log,stderr=subprocess.STDOUT)
                observer=subprocess.Popen(['python3','tools/m3_recorder_diagnostics.py','--out',str(run/'samples.jsonl'),'--ready',str(run/'ready.json'),'--stop',str(run/'stop')],stdout=observer_log,stderr=subprocess.STDOUT)
                deadline=time.monotonic()+10
                while not (run/'ready.json').exists():
                    if capture.poll() is not None or observer.poll() is not None or time.monotonic()>deadline:raise RuntimeError('probe readiness failed')
                    time.sleep(.05)
                # Process discovery does not prove socket readiness.
                while 'listening on' not in (run/'capture.log').read_text():
                    if capture.poll() is not None or time.monotonic()>deadline:raise RuntimeError('capture socket readiness failed')
                    time.sleep(.05)
                started=time.monotonic();paused=False;resumed=False;sent=0;events=[]
                while time.monotonic()-started<3:
                    elapsed=time.monotonic()-started
                    if pause and not paused and elapsed>=.5:
                        capture.send_signal(signal.SIGSTOP);paused=True;events.append(dict(signal='SIGSTOP',monotonic_ns=time.monotonic_ns()))
                    if paused and not resumed and elapsed>=2:
                        capture.send_signal(signal.SIGCONT);resumed=True;events.append(dict(signal='SIGCONT',monotonic_ns=time.monotonic_ns()))
                    sender.sendto(struct.pack('!I',sent)+bytes(1020),('127.0.0.1',PORT));sent+=1
                    time.sleep(.001)
                sender.sendto(RECOVERY,('127.0.0.1',PORT));sent+=1
                time.sleep(.5)
                report.update(sent_datagrams=sent,received_datagrams=received[0],events=events)
            finally:
                if capture and capture.poll() is None:
                    capture.send_signal(signal.SIGCONT);capture.send_signal(signal.SIGINT);capture.wait(timeout=5)
                (run/'stop').touch()
                if observer and observer.poll() is None:observer.wait(timeout=5)
                done.set();thread.join(timeout=2)
        rows=[json.loads(line) for line in (run/'samples.jsonl').read_text().splitlines()]
        report['diagnostics']=diagnostics.summarize(rows)
        paths=sorted(run.glob('probe.pcap*'));pcap=summarize(paths,'127.0.0.1');footer=(run/'capture.log').read_text()
        import re
        drops=int(re.findall(r'(\d+) packets dropped by kernel',footer)[-1])
        try:report['capture_gate']=validate_tcpdump_footer(footer,pcap['records']);rejected=False
        except ValueError as error:report['capture_gate_error']=str(error);rejected=True
        stopped=sum(p['state']=='T' for row in rows for p in row['processes'])
        recovery=contains_recovery(paths)
        report.update(kernel_drops=drops,captured_records=pcap['records'],stopped_state_observations=stopped,
                      recovery_marker_captured=recovery,capture_gate_rejected=rejected)
        report['status']='passed' if (not pcap['unaccounted'] and recovery and observer.returncode==0 and capture.returncode==0 and
            received[0]==report['sent_datagrams'] and ((pause and stopped>0 and drops>0 and rejected) or
            (not pause and stopped==0 and drops==0 and not rejected))) else 'failed'
        (run/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        if report['status']!='passed':raise RuntimeError('recorder control failed; see '+str(run/'result.json'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--container-child',action='store_true');parser.add_argument('--pause',action='store_true')
    args=parser.parse_args()
    if args.container_child:child(args.out,args.pause);return
    run=args.out.resolve();run.mkdir(parents=True,exist_ok=False)
    relative=run.relative_to(ROOT)
    image=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64','ros2-srt-m3:20261105'],text=True))[0]['RepoDigests'][0]
    report=dict(status='running',image=image,cases=[],source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (Path(__file__),ROOT/'tools/m3_recorder_diagnostics.py',ROOT/'tools/m3_capture.py')},
        scope='synthetic loopback diagnostic controls in network-none; not an N5 retry or historical root-cause proof')
    try:
        for case in ('baseline','pause'):
            argv=['docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none',
                  '-v',str(ROOT)+':/workspace','-w','/workspace',image,'python3','tools/check_m3_recorder.py',
                  '--container-child','--out','/workspace/'+str(relative/case)]
            if case=='pause':argv.append('--pause')
            with (run/(case+'.log')).open('w') as log:subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=45)
            report['cases'].append(json.loads((run/case/'result.json').read_text()))
            print(case+': passed',flush=True)
        report['status']='passed'
    except BaseException as error:report.update(status='failed',error=str(error));raise
    finally:(run/'run.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
