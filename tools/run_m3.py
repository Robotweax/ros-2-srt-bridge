#!/usr/bin/env python3
"""Run an isolated SRT M3 development workload with verified kernel impairment.

This is the SRT measurement harness, not complete M3 acceptance: the DDS command
baseline and deterministic N3 DATA/FEC fault selector remain separate gates.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import re
import shlex
import subprocess
import time
from m3_network import NetworkLab, SEEDS
from m3_dds import summarize_competitor
from m3_capture import summarize,validate_tcpdump_footer,stop_captures,pcap_options,pcap_configuration,pcap_rotation_options
from m3_window_measurement import summarize_endpoints
import m3_monotonic_capture as mono_capture
from m3_accounting import summarize_window
from m3_results import summarize_resources, summarize_commands, summarize_gaps

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['N0','N1','N2','N4','N5'],default='N0')
    parser.add_argument('--seed',type=int,choices=SEEDS,default=SEEDS[0])
    parser.add_argument('--smoke',action='store_true',help='15 s development run; never full-duration qualification')
    parser.add_argument('--seconds',type=int,help='explicit development duration, 10..7200 seconds')
    parser.add_argument('--skip-build',action='store_true',help='reuse M3 build during development')
    parser.add_argument('--build-image',action='store_true')
    parser.add_argument('--outage-direction',choices=['both','robot','operator'],default='both')
    parser.add_argument('--monotonic-capture',action='store_true',help='experimental passive kernel-monotonic observer; adds CAP_BPF to owned endpoints')
    args=parser.parse_args()
    if args.smoke and args.seconds:parser.error('choose --smoke or --seconds')
    duration=15 if args.smoke else args.seconds or (600 if args.profile in ('N1','N2') else 300)
    if not 10<=duration<=7200:parser.error('duration must be 10..7200 seconds')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run=ROOT/'.local/m3'/stamp;run.mkdir(parents=True)
    inside='/workspace/'+str(run.relative_to(ROOT))
    report=dict(status='running',pcap_dispatch_mode='immediate',pcap_capture_config=pcap_configuration(),milestone='M3 development',complete_m3_acceptance=False,
        profile=args.profile,seed=args.seed,seconds=duration,smoke=args.smoke,skip_build=args.skip_build,
        max_clock_interval_ms=200,clock_assumptions=dict(relative_drift_ppm=1000,timestamp_error_ns=1000000,max_probe_age_ns=5000000000),
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ['src','ros2','proto','cmake','containers','tools','tests']
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in str(p)},
        missing_gates=['DDS Best Effort/fully journaled Reliable command baseline','deterministic N3 DATA/FEC loss selector',
                       'N4 timing at admission/dispatch/result commit','full three-seed duration matrix'])
    processes=[];captures=[];lab=None;competitor=None;competitor_alive_checks=0
    credential=run/'passphrase';credential.touch(mode=0o600);credential.write_text(secrets.token_urlsafe(32)+'\n')
    def save():(run/'run.json').write_text(json.dumps(report,indent=2)+'\n')
    def execute(label,argv):
        print(label,flush=True)
        with (run/(label+'.log')).open('w') as log:
            p=subprocess.run(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        if p.returncode:raise RuntimeError(label+' failed; see '+str(run/(label+'.log')))
    try:
        if args.build_image:
            execute('image-build',['docker','build','--platform','linux/amd64','--pull=false','-f','containers/m3.Dockerfile','-t','ros2-srt-m3:20261105','.'])
        info=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64','ros2-srt-m3:20261105'],text=True))[0]
        assert info['Architecture']=='amd64' and info['Os']=='linux'
        image=info['RepoDigests'][0];report.update(image_reference=image,image_platform_id=info['Id'])
        save()
        def offline(command):return ['docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none',
            '-v',str(ROOT)+':/workspace','-w','/workspace',image,'bash','-c',command]
        archive=list((ROOT/'install/srt-m0').glob('lib*/**/librobotweax-srt.a'))
        qualified=json.loads((ROOT/'baselines/dependencies.json').read_text())['srt']['installed_library_sha256']
        assert len(archive)==1 and hashlib.sha256(archive[0].read_bytes()).hexdigest()==qualified
        report['srt_archive_sha256']=qualified
        if not args.skip_build:
            execute('build',offline('set -e; cmake -S . -B build/m3-sdk -G Ninja -DCMAKE_BUILD_TYPE=Release '
                '-DCMAKE_PREFIX_PATH=/workspace/install/srt-m0 -DBUILD_MANAGEMENT_CODEC=ON -DBUILD_SRT_TRANSPORT=ON '
                '-DBUILD_TESTING=ON -DBUILD_SHARED_LIBS=OFF; cmake --build build/m3-sdk --parallel 3; '
                'cmake --install build/m3-sdk --prefix /workspace/install/bridge-m3; source /opt/ros/jazzy/setup.bash; '
                'colcon --log-base '+inside+'/colcon-build build --cmake-clean-first --base-paths ros2 '
                '--build-base build/m3-ros --install-base install/m3-ros --cmake-args -DCMAKE_BUILD_TYPE=Release '
                '-DCMAKE_PREFIX_PATH="/workspace/install/bridge-m3;/workspace/install/srt-m0"'))
            execute('ros-tests',offline('set -e; source /opt/ros/jazzy/setup.bash; source install/m3-ros/setup.bash; '
                'colcon --log-base '+inside+'/colcon-test test --base-paths ros2 --build-base build/m3-ros '
                '--install-base install/m3-ros --return-code-on-test-failure; colcon test-result --test-result-base build/m3-ros --verbose'))
        execute('versions',offline('dpkg-query -W; tc -V'))
        if args.monotonic_capture:report['monotonic_capture_config']=mono_capture.prepare(ROOT,run,image,execute,args.skip_build)
        lab=NetworkLab(ROOT,run,image,monotonic_capture=args.monotonic_capture);lab.start(credential)
        clocks={role:lab.inside(role,role+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for role in lab.containers}
        if len(set(clocks.values()))!=1:raise RuntimeError('endpoint measurements require common VM clock namespaces')
        report['clock_namespace_proof']=clocks
        lab.apply('N0' if args.profile=='N4' else args.profile,args.seed)
        for role,name in lab.containers.items():
            log=(run/(role+'-capture.log')).open('w')
            argv=['docker','exec',name]+pcap_options()+pcap_rotation_options()+[
                  '-w',inside+'/'+role+'.pcap','udp']
            captures.append((subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT),log))
        if args.monotonic_capture:
            report['monotonic_capture_config']['features_before']=mono_capture.feature_snapshot(lab,'features-before')
            mono_capture.start(run,inside,lab,captures)
        if args.profile=='N5':
            lab.inside('operator','competitor-server',['iperf3','-s','-D'])
            log=(run/'competitor-process.log').open('w')
            competitor=subprocess.Popen(['docker','exec',lab.containers['robot'],'iperf3','-c',lab.addresses['operator'],
                '-u','-b','128K','-t',str(duration+60),'-l','1024','--logfile',inside+'/competing-traffic.json','-J'],stdout=log,stderr=subprocess.STDOUT)
            captures.append((competitor,log))
        lab.snapshot('before')
        for role,name in lab.containers.items():
            command='source /opt/ros/jazzy/setup.bash; source install/m3-ros/setup.bash; exec python3 '+shlex.join([
                'ros2/robotweax_srt_bridge_demo/scripts/m3_scenario.py','--role',role,'--run',inside,
                '--peer',lab.addresses['operator'],'--seconds',str(duration),'--clock-width-ms','200'])
            log=(run/(role+'-scenario.log')).open('w')
            processes.append((subprocess.Popen(['docker','exec',name,'bash','-c',command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT),log))
        deadline=time.monotonic()+duration+120;outage=False
        while time.monotonic()<deadline:
            if competitor is not None:
                if competitor.poll() is not None:raise RuntimeError('N5 competitor exited before scenario completion')
                competitor_alive_checks+=1
            if any(p.poll() not in (None,0) for p,_ in processes):raise RuntimeError('scenario failed; see '+str(run))
            if all(p.poll() is not None for p,_ in processes):break
            if args.profile=='N4' and not outage and (run/'measurement-start.json').exists():
                started=json.loads((run/'measurement-start.json').read_text())
                # Host/VM monotonic epochs differ. Wait a host interval after observing the phase marker.
                if 'outage_due' not in report:report['outage_due']=time.monotonic()+duration/2;save()
                if time.monotonic()>=report['outage_due']:
                    roles=('operator','robot') if args.outage_direction=='both' else (args.outage_direction,)
                    lab.apply('N4',args.seed,roles,label='outage')
                    start=time.monotonic_ns()
                    # Two-second isolated kernel outage; outer sampling resumes afterwards.
                    time.sleep(2)
                    lab.apply('N0',args.seed,roles,label='restore')
                    report['outage']=dict(direction=args.outage_direction,host_elapsed_ns=time.monotonic_ns()-start,
                        placement='mid-window; not a dispatch/commit barrier qualification')
                    outage=True;save()
            time.sleep(.25)
        else:raise RuntimeError('M3 scenario deadline exceeded')
        if args.profile=='N4' and not outage:raise RuntimeError('outage was not applied')
        lab.snapshot('after')
        if args.monotonic_capture:
            report['monotonic_capture_config']['features_after']=mono_capture.feature_snapshot(lab,'features-after')
            if report['monotonic_capture_config']['features_before']!=report['monotonic_capture_config']['features_after']:raise RuntimeError('interface feature state changed during run')
        result=json.loads((run/'operator-result.json').read_text());assert result['status']=='passed'
        report['results']=result;report['measurement_window']=summarize_window(result['checkpoints']['begin'],result['checkpoints']['end'],result['publication_interval']);report['gap_attribution']=summarize_gaps(run,result);report['command_summary']=summarize_commands(result['commands']);report['resources']={role:summarize_resources(run/(role+'-resources.jsonl')) for role in ('robot','operator')}
        interval=result['publication_interval']
        report['endpoint_measurements']=summarize_endpoints(run,dict(source_enabled=[interval['resume_monotonic_ns'],interval['pause_monotonic_ns']],fenced_observation=result['endpoint_fenced_interval_ns']),require_dedicated=True)
        report['status']='passed'
    except BaseException as error:
        report['status']='failed';report['error']=str(error);raise
    finally:
        if lab:
            try:stop_captures(lab)
            except Exception as error:report['status']='failed';report['capture_stop_error']=str(error)
            for p,log in captures:
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.terminate()
                log.close()
            try:
                report['captures']={role:summarize(sorted(run.glob(role+'.pcap*')),address) for role,address in lab.addresses.items()}
                for role,capture in report['captures'].items():
                    footer=(run/(role+'-capture.log')).read_text()
                    capture.update(validate_tcpdump_footer(footer,capture['records']))
                    if any(key.endswith('/dds_rtps') for key in capture['classes']):raise RuntimeError('DDS traffic leaked onto the SRT-only network')
                    if capture['unaccounted']:raise RuntimeError('capture contains unaccounted frames')
                if args.monotonic_capture:report['monotonic_captures']=mono_capture.summarize_run(run,lab.addresses,report['endpoint_measurements'],allow_udp_fragments=False,features=report['monotonic_capture_config']['features_before'])
                report['pcap_population_reconciled']=all(c['tcpdump_population_reconciled'] for c in report['captures'].values())
                report['window_captures']={}
                for window,measurement in report.get('endpoint_measurements',{}).get('windows',{}).items():
                    clock=measurement['wire_clock']
                    if clock['qualified'] and report['pcap_population_reconciled']:
                        report['window_captures'][window]={role:summarize(sorted(run.glob(role+'.pcap*')),address,
                            allow_udp_fragments=False,timestamp_window=clock['timestamp_bounds_ns'])['time_window'] for role,address in lab.addresses.items()}

            except Exception as error:
                report['status']='failed';report['capture_error']=str(error);report.pop('window_captures',None);report.pop('monotonic_captures',None)
            if competitor is not None:
                try:
                    report['competitor_check']=summarize_competitor(json.loads((run/'competing-traffic.json').read_text()))
                    report['competitor_check']['alive_poll_checks']=competitor_alive_checks
                    if not competitor_alive_checks:raise RuntimeError('competitor was never observed alive')
                except Exception as error:report['status']='failed';report['competitor_error']=str(error)
            lab.cleanup()
        for p,log in processes:
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.terminate()
            log.close()
        credential.unlink(missing_ok=True);save();print(run,flush=True)
    if report['status']!='passed':raise RuntimeError(report.get('competitor_error',report.get('capture_error',report.get('error','M3 failed'))))


if __name__=='__main__':main()
