#!/usr/bin/env python3
"""Isolated DDS sensor or combined journaled-command development workload."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import time
from m3_dds import DdsLab,summarize_sensor_window,DDS_PROFILES,verify_profile,summarize_competitor
from m3_network import SEEDS
from m3_capture import summarize,validate_tcpdump_footer,stop_captures,pcap_options,pcap_configuration,pcap_rotation_options
from m3_window_measurement import summarize_endpoints
import m3_monotonic_capture as mono_capture
from m3_results import summarize_commands

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=['N0','N1','N2','N4','N5'],default='N0')
    parser.add_argument('--seed',type=int,choices=SEEDS,default=SEEDS[0])
    parser.add_argument('--dds-profile',choices=list(DDS_PROFILES),default='system',help='explicit DDS transport variant; system remains default')
    parser.add_argument('--startup',choices=['simultaneous','control-first'],default='simultaneous',help='explicit combined startup ordering; impairment stays active')
    parser.add_argument('--commands',action='store_true',help='combine steady sensors and journaled commands every 2s')
    parser.add_argument('--outage-direction',choices=['both','robot','operator'],default='both')
    parser.add_argument('--smoke',action='store_true')
    parser.add_argument('--seconds',type=int)
    parser.add_argument('--skip-build',action='store_true',help='reuse M3 binaries; recorded as development reuse')
    parser.add_argument('--monotonic-capture',action='store_true',help='experimental passive kernel-monotonic observer; adds CAP_BPF to owned endpoints')
    args=parser.parse_args()
    if args.smoke and args.seconds:parser.error('choose --smoke or --seconds')
    seconds=15 if args.smoke else args.seconds or (600 if args.profile in ('N1','N2') else 300)
    if not 10<=seconds<=7200:parser.error('duration must be 10..7200 seconds')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run=ROOT/('.local/m3-dds-combined' if args.commands else '.local/m3-dds')/stamp;run.mkdir(parents=True)
    inside='/workspace/'+str(run.relative_to(ROOT))
    report=dict(status='running',pcap_dispatch_mode='immediate',pcap_capture_config=pcap_configuration(),milestone='M3 DDS combined development' if args.commands else 'M3 DDS sensor development',sensor_only=not args.commands,commands_qualified=False,
        configured_workload=dict(imu_hz=200,joint_hz=50,command_period_s=2 if args.commands else None),
        complete_m3_acceptance=False,startup_mode=args.startup if args.commands else 'sensor-only',dds_transport_profile=args.dds_profile,profile=args.profile,seed=args.seed,seconds=seconds,smoke=args.smoke,skip_build=args.skip_build,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ['src','ros2','proto','cmake','containers','tools','tests']
            for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in str(p)},
        missing_gates=['full-duration combined impairment/seed qualification','matched-window CPU/wire accounting',
            'age-clock equivalence with conservative SRT bounds','encryption/security cost equivalence','expiry-seal semantic/cost equivalence with SRT','full seed/duration matrix'],
        topology='direct typed DDS sensor publisher/subscriber; no SRT bridge hops; simulator services/diagnostics also discoverable',
        clock_scope='same Linux VM boot ID and time namespace, realtime header estimate; no cross-host clock qualification',
        dds_command_protocol=2,expiry_seal_scope='non-executing durable absence seal; original sender/process/session only, strictly past saved 5s deadline; existing records unchanged',
        dds_command_channels=dict(control='Reliable/Volatile/KeepLast(64)',liveness='BestEffort/Volatile/KeepLast(1)',hello_period_ms=100,lease_ns=1500000000,sequence_scope='independent per channel'))
    lab=None;processes=[];captures=[];competitor=None;competitor_alive_checks=0
    def save():(run/'run.json').write_text(json.dumps(report,indent=2)+'\n')
    def execute(label,argv):
        print(label,flush=True)
        with (run/(label+'.log')).open('w') as log:
            subprocess.run(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    try:
        info=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64','ros2-srt-m3:20261105'],text=True))[0]
        assert info['Architecture']=='amd64' and info['Os']=='linux'
        image=info['RepoDigests'][0];report.update(image_reference=image,image_platform_id=info['Id']);save()
        if not args.skip_build:
            execute('build',['docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none',
                '-v',str(ROOT)+':/workspace','-w','/workspace',image,'bash','-c',
                'set -e; source /opt/ros/jazzy/setup.bash; colcon --log-base '+inside+'/colcon-build build '
                '--cmake-clean-first --base-paths ros2 --build-base build/m3-ros --install-base install/m3-ros '
                '--cmake-args -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="/workspace/install/bridge-m3;/workspace/install/srt-m0"'])
            execute('ros-tests',['docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none',
                '-v',str(ROOT)+':/workspace','-w','/workspace',image,'bash','-c',
                'set -e; source /opt/ros/jazzy/setup.bash; source install/m3-ros/setup.bash; '
                'colcon --log-base '+inside+'/colcon-test test --base-paths ros2 --build-base build/m3-ros '
                '--install-base install/m3-ros --return-code-on-test-failure; colcon test-result --test-result-base build/m3-ros --verbose'])
        binary=ROOT/'install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo/rate_simulator'
        report['simulator_binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
        if args.commands:
            binary=ROOT/'install/m3-ros/robotweax_srt_bridge/lib/robotweax_srt_bridge/dds_command_node'
            report['command_node_binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
        report.update(verify_profile(ROOT,run,image,args.dds_profile,execute,build_probe=not args.skip_build))
        if args.monotonic_capture:report['monotonic_capture_config']=mono_capture.prepare(ROOT,run,image,execute,args.skip_build)
        lab=DdsLab(ROOT,run,image,args.dds_profile,monotonic_capture=args.monotonic_capture);lab.start()
        report['discovery']=dict(ros_domain_id=60,range='SUBNET',static_peers={role:lab.addresses['operator' if role=='robot' else 'robot'] for role in lab.containers},rmw='rmw_fastrtps_cpp')
        # Cross-container realtime age estimates require the same kernel and
        # time namespaces. Capture the raw proof rather than assuming host time.
        clocks={role:lab.inside(role,role+'-clock-proof',['sh','-c',
            'cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for role in lab.containers}
        if len(set(clocks.values()))!=1:raise RuntimeError('DDS age estimate requires common VM clock namespaces')
        report['clock_namespace_proof']=clocks
        lab.apply('N0' if args.profile=='N4' else args.profile,args.seed)
        for role,name in lab.containers.items():
            log=(run/(role+'-capture.log')).open('w')
            p=subprocess.Popen(['docker','exec',name]+pcap_options()+pcap_rotation_options()+[
                '-w',inside+'/'+role+'.pcap','udp'],stdout=log,stderr=subprocess.STDOUT)
            captures.append((p,log))
        if args.monotonic_capture:
            report['monotonic_capture_config']['features_before']=mono_capture.feature_snapshot(lab,'features-before')
            mono_capture.start(run,inside,lab,captures)
        if args.profile=='N5':
            lab.inside('operator','competitor-server',['iperf3','-s','-D'])
            log=(run/'competitor-process.log').open('w')
            p=subprocess.Popen(['docker','exec',lab.containers['robot'],'iperf3','-c',lab.addresses['operator'],
                '-u','-b','128K','-t',str(seconds+90),'-l','1024','--logfile',inside+'/competing-traffic.json','-J'],stdout=log,stderr=subprocess.STDOUT)
            captures.append((p,log));competitor=p
        lab.snapshot('before')
        for role,name in lab.containers.items():
            command='source /opt/ros/jazzy/setup.bash; source install/m3-ros/setup.bash; exec python3 '+shlex.join([
                'ros2/robotweax_srt_bridge_demo/scripts/m3_dds_scenario.py','--role',role,'--run',inside,'--seconds',str(seconds),'--startup',args.startup]+(['--commands'] if args.commands else []))
            log=(run/(role+'-scenario.log')).open('w')
            peer=lab.addresses['operator' if role=='robot' else 'robot']
            p=subprocess.Popen(['docker','exec','-e','ROS_STATIC_PEERS='+peer,name,'bash','-c',command],stdout=log,stderr=subprocess.STDOUT)
            processes.append((p,log))
        deadline=time.monotonic()+seconds+150;outage=False
        while time.monotonic()<deadline:
            if competitor is not None:
                if competitor.poll() is not None:raise RuntimeError('N5 competitor exited before scenario completion')
                competitor_alive_checks+=1
            if any(p.poll() not in (None,0) for p,_ in processes):raise RuntimeError('DDS scenario failed')
            if all(p.poll() is not None for p,_ in processes):break
            if args.profile=='N4' and not outage and (run/'measurement-start.json').exists():
                if 'outage_due' not in report:report['outage_due']=time.monotonic()+seconds/2;save()
                if time.monotonic()>=report['outage_due']:
                    roles=('operator','robot') if args.outage_direction=='both' else (args.outage_direction,)
                    lab.apply('N4',args.seed,roles,label='outage');started=time.monotonic_ns()
                    time.sleep(2);lab.apply('N0',args.seed,roles,label='restore')
                    report['outage']=dict(direction=args.outage_direction,host_elapsed_ns=time.monotonic_ns()-started,
                        placement='mid-window kernel outage; not command-phase barriers')
                    outage=True;save()
            time.sleep(.25)
        else:raise RuntimeError('DDS scenario deadline exceeded')
        if args.profile=='N4' and not outage:raise RuntimeError('outage was not applied')
        lab.snapshot('after')
        if args.monotonic_capture:
            report['monotonic_capture_config']['features_after']=mono_capture.feature_snapshot(lab,'features-after')
            if report['monotonic_capture_config']['features_before']!=report['monotonic_capture_config']['features_after']:raise RuntimeError('interface feature state changed during run')
        result=json.loads((run/'operator-result.json').read_text())
        report['results']=result
        report['sensor_count_checks_passed']=result['sensor_count_checks_passed']
        report['age_estimates_qualified']=result['age_estimates_qualified']
        report['measurement_window']=summarize_sensor_window(result['checkpoints']['begin'],result['checkpoints']['end'],result['publication_interval'])
        if args.commands:
            report['command_summary']=summarize_commands(result['commands'])
            report['command_audit']=result['command_audit']
            report['command_latency_scope']='includes terminal observations during the <=8s post-cutoff drain; rows flag observation phase'
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
                except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
                log.close()
            try:
                report['captures']={role:summarize(sorted(run.glob(role+'.pcap*')),address,allow_udp_fragments=True) for role,address in lab.addresses.items()}
                for role,capture in report['captures'].items():
                    footer=(run/(role+'-capture.log')).read_text()
                    capture.update(validate_tcpdump_footer(footer,capture['records']))
                    if capture['unaccounted']:raise RuntimeError('unaccounted DDS capture frames')
                    if not any(key.endswith('/dds_rtps') for key in capture['classes']):raise RuntimeError('no RTPS observed on eth0')
                    if any('_srt_' in key or '_source_data' in key or '_fec_parity' in key for key in capture['classes']):raise RuntimeError('SRT traffic on DDS baseline')
                if args.monotonic_capture:report['monotonic_captures']=mono_capture.summarize_run(run,lab.addresses,report['endpoint_measurements'],allow_udp_fragments=True,features=report['monotonic_capture_config']['features_before'])
                report['pcap_population_reconciled']=all(c['tcpdump_population_reconciled'] for c in report['captures'].values())
                report['window_captures']={}
                for window,measurement in report.get('endpoint_measurements',{}).get('windows',{}).items():
                    clock=measurement['wire_clock']
                    if clock['qualified'] and report['pcap_population_reconciled']:
                        report['window_captures'][window]={role:summarize(sorted(run.glob(role+'.pcap*')),address,
                            allow_udp_fragments=True,timestamp_window=clock['timestamp_bounds_ns'])['time_window'] for role,address in lab.addresses.items()}

                report['capture_scope']='whole-run Ethernet frames including discovery, simulator diagnostics/services and N5 competitor; multicast ingress may be direction other; IP fragment frames counted separately without RTPS/payload attribution; not matched-window sensor bytes'
            except Exception as error:report['status']='failed';report['capture_error']=str(error);report.pop('window_captures',None);report.pop('monotonic_captures',None)
            if competitor is not None:
                try:
                    report['competitor_check']=summarize_competitor(json.loads((run/'competing-traffic.json').read_text()))
                    report['competitor_check']['alive_poll_checks']=competitor_alive_checks
                    if not competitor_alive_checks:raise RuntimeError('competitor was never observed alive')
                except Exception as error:report['status']='failed';report['competitor_error']=str(error)
            lab.cleanup()
        for p,log in processes:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
            log.close()
        save();print(run,flush=True)
    if report['status']!='passed':raise RuntimeError(report.get('competitor_error',report.get('capture_error',report.get('error','DDS baseline failed'))))


if __name__=='__main__':main()
