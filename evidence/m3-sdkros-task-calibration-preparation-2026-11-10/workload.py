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
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from m3_source_preflight import source_inventory
from m3_network import NetworkLab, SEEDS
from m3_dds import summarize_competitor
from m3_capture import summarize,validate_tcpdump_footer,stop_captures,pcap_options,pcap_configuration,pcap_rotation_options,wait_ready
from m3_window_measurement import summarize_endpoints
import m3_monotonic_capture as mono_capture
import m3_recorder_diagnostics as recorder_diagnostics
import m3_command_trace
import m3_start_trace_analysis
import m3_runtime_layout
import m3_provider_stats
import m3_control_fault
import m3_neighbor_diagnostics as neighbor_diagnostics
import m3_qdisc_diagnostics as qdisc_diagnostics
import m3_arp_reply_diagnostics as arp_reply_diagnostics
import m3_arp_packet_diagnostics as arp_packet_diagnostics
import m3_root_loss_burst
from m3_source_preflight import source_inventory
from m3_accounting import summarize_window
from m3_results import summarize_resources, summarize_commands, summarize_gaps

ROOT=Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT/'evidence/m3-current-n0-preparation-2026-11-10'))
from disposition_runtime import matched
from sidecar import Sidecar
from cases import allowed


def main(argv=None,*,bundle=None,prefix=None):
    from calibration_scope import guard
    # Guard again after parsing, before any workload output or runtime action.
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,help='fresh campaign-owned output directory inside the repository')
    parser.add_argument('--image-reference',help='explicit immutable image reference; never pulls')
    parser.add_argument('--profile',choices=['N0','N1','N2','N4','N5'],default='N0')
    parser.add_argument('--seed',type=int,choices=SEEDS,default=SEEDS[0])
    parser.add_argument('--smoke',action='store_true',help='15 s development run; never full-duration qualification')
    parser.add_argument('--seconds',type=int,help='explicit development duration, 10..7200 seconds')
    parser.add_argument('--runtime-layout',choices=('socket-disposition',),default='baseline',help='explicit calibrated install paths; nonbaseline requires --skip-build')
    parser.add_argument('--skip-build',action='store_true',help='reuse M3 build during development')
    parser.add_argument('--build-image',action='store_true')
    parser.add_argument('--outage-direction',choices=['both','robot','operator'],default='both')
    parser.add_argument('--monotonic-capture',action='store_true',help='experimental passive kernel-monotonic observer; adds CAP_BPF to owned endpoints')
    parser.add_argument('--recorder-diagnostics',action='store_true',help='development-only 100ms /proc recorder observations; changes observer workload')
    parser.add_argument('--root-loss-burst',choices=['operator','robot'],help='known two-second N5 child loss; requires permanent neighbors and all diagnostics, >=60s')
    parser.add_argument('--capture-drain-check',action='store_true',help='experimental bounded stable-equal tcpdump snapshots before stop; final capture gate unchanged')
    parser.add_argument('--arp-packet-trace',action='store_true',help='passive scoped ARP lifecycle tracing, requires all loaded ARP diagnostics, <=480s')
    parser.add_argument('--arp-reply-diagnostics',action='store_true',help='bounded software owned ARP reply PIPE/PASS observer; adds work')
    parser.add_argument('--control-qdisc-diagnostics',action='store_true',help='experimental CONTROL tc PASS counters plus root polling; N0/N5 only, observer intervention')
    parser.add_argument('--neighbor-diagnostics',action='store_true',help='bounded read-only neighbor-table polling; observer workload')
    parser.add_argument('--neighbor-mode',choices=['dynamic','permanent'],default='dynamic',help='permanent is a separate owned-lab L2 diagnostic candidate, not default baseline')
    parser.add_argument('--control-egress-fault',choices=['operator','robot'],help='development-only six-second CONTROL drop, N0 >=45s with all diagnostics; not qualification')
    parser.add_argument('--sensor-provider-diagnostics',action='store_true',help='separate bounded SENSOR SDK statistics; adds observer work')
    parser.add_argument('--provider-diagnostics',action='store_true',help='development-only CONTROL non-clearing provider statistics; adds observer workload')
    parser.add_argument('--start-diagnostics',action='store_true',help='bounded start-check/grant/worker observations, requires command diagnostics and matched rebuilt worker')
    parser.add_argument('--sender-diagnostics',action='store_true',help='bounded sender clock/release/journal/event observations; requires command diagnostics')
    parser.add_argument('--probe-diagnostics',action='store_true',help='default-off per-probe lifecycle observations; requires command diagnostics and calibrated probe layout')
    parser.add_argument('--command-diagnostics',action='store_true',help='development-only bounded command handoff trace; adds observer workload')
    args=parser.parse_args(argv)
    if args.smoke and args.seconds:parser.error('choose --smoke or --seconds')
    duration=15 if args.smoke else args.seconds or (600 if args.profile in ('N1','N2') else 300)
    if not 10<=duration<=7200:parser.error('duration must be 10..7200 seconds')
    if args.control_egress_fault and (args.profile!='N0' or duration<45 or not all((args.monotonic_capture,args.command_diagnostics,args.provider_diagnostics))):
        parser.error('CONTROL fault requires N0 >=45s plus monotonic, command and provider diagnostics')
    if args.neighbor_mode=='permanent' and (not args.neighbor_diagnostics or args.profile not in ('N0','N5') or args.control_egress_fault):
        parser.error('permanent neighbor candidate requires neighbor diagnostics, N0/N5 and no injected CONTROL fault')
    if args.control_qdisc_diagnostics and (args.profile not in ('N0','N5') or args.control_egress_fault):
        parser.error('CONTROL qdisc diagnostics require N0/N5 and no injected classifier fault')
    if args.root_loss_burst and (args.profile!='N5' or duration<60 or args.neighbor_mode!='permanent' or not all((args.neighbor_diagnostics,args.monotonic_capture,args.command_diagnostics,args.provider_diagnostics,args.control_qdisc_diagnostics,args.capture_drain_check)) or args.control_egress_fault):
        parser.error('root loss burst requires N5 >=60s, permanent neighbors, drain check and all diagnostics')
    if args.arp_reply_diagnostics and (args.profile not in ('N0','N5') or args.neighbor_mode!='dynamic' or args.control_egress_fault or args.root_loss_burst or not all((args.neighbor_diagnostics,args.control_qdisc_diagnostics,args.monotonic_capture,args.capture_drain_check,args.command_diagnostics,args.provider_diagnostics,args.sensor_provider_diagnostics))):
        parser.error('loaded ARP observer requires N0/N5, dynamic neighbors, all diagnostics/drain, no faults')
    if args.arp_packet_trace and (not args.arp_reply_diagnostics or duration>480):parser.error('ARP packet trace requires loaded ARP diagnostics and <=480s')
    if args.start_diagnostics and not args.command_diagnostics:parser.error('start diagnostics require command diagnostics')
    if args.sender_diagnostics and not args.command_diagnostics:parser.error('sender diagnostics require command diagnostics')
    if args.sender_diagnostics and args.runtime_layout not in ('socket-disposition',):parser.error('sender diagnostics require sender-visibility runtime layout or probe-tracing')
    if args.probe_diagnostics and not args.command_diagnostics:parser.error('probe diagnostics require command diagnostics')
    if args.probe_diagnostics and args.runtime_layout not in ('probe-tracing','sender-reconcile'):parser.error('probe diagnostics require probe-tracing runtime layout')
    if args.runtime_layout!='baseline' and not args.skip_build:parser.error('explicit matched runtime layout requires --skip-build')
    if not allowed(args.profile,args.seed,duration) or not all((args.skip_build,args.monotonic_capture,args.command_diagnostics,args.provider_diagnostics,args.sensor_provider_diagnostics,args.start_diagnostics,args.sender_diagnostics)) or any((args.smoke,args.build_image,args.probe_diagnostics,args.recorder_diagnostics,args.root_loss_burst,args.capture_drain_check,args.arp_packet_trace,args.arp_reply_diagnostics,args.control_qdisc_diagnostics,args.neighbor_diagnostics,args.control_egress_fault)) or args.neighbor_mode!='dynamic' or args.outage_direction!='both':parser.error('only SDKROS N0/1701/10s calibration allowed')
    if bundle is None or prefix is None or args.output is None:parser.error('owned observer bundle/prefix and fresh output required')
    guard(args.output,bundle,prefix)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run=args.output.resolve() if args.output else ROOT/'.local/m3'/stamp
    run.relative_to(ROOT)
    run.mkdir(parents=True,exist_ok=False)
    inside='/workspace/'+str(run.relative_to(ROOT))
    report=dict(status='running',pcap_dispatch_mode='immediate',pcap_capture_config=pcap_configuration(),milestone='M3 development',complete_m3_acceptance=False,
        profile=args.profile,seed=args.seed,seconds=duration,smoke=args.smoke,skip_build=args.skip_build,
        max_clock_interval_ms=200,clock_assumptions=dict(relative_drift_ppm=1000,timestamp_error_ns=1000000,max_probe_age_ns=5000000000),
        source_sha256=source_inventory(ROOT),
        missing_gates=['DDS Best Effort/fully journaled Reliable command baseline','deterministic N3 DATA/FEC loss selector',
                       'N4 timing at admission/dispatch/result commit','full three-seed duration matrix'])
    observer=None
    processes=[];captures=[];recorder_processes=[];neighbor_processes=[];qdisc_processes=[];arp_reply_processes=[];arp_packet_processes=[];lab=None;competitor=None;competitor_alive_checks=0
    report['root_loss_burst_requested']=args.root_loss_burst
    report['capture_drain_check_enabled']=args.capture_drain_check
    report['arp_packet_trace_enabled']=args.arp_packet_trace
    report['arp_reply_diagnostics_enabled']=args.arp_reply_diagnostics
    report['control_qdisc_diagnostics_enabled']=args.control_qdisc_diagnostics
    report['neighbor_mode']=args.neighbor_mode
    report['neighbor_diagnostics_enabled']=args.neighbor_diagnostics
    report['control_egress_fault_requested']=args.control_egress_fault
    report['recorder_diagnostics_enabled']=args.recorder_diagnostics
    report['provider_diagnostics_enabled']=args.provider_diagnostics
    report['sensor_provider_diagnostics_enabled']=args.sensor_provider_diagnostics
    report['start_diagnostics_enabled']=args.start_diagnostics
    report['sender_diagnostics_enabled']=args.sender_diagnostics
    report['probe_diagnostics_enabled']=args.probe_diagnostics
    report['command_diagnostics_enabled']=args.command_diagnostics
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
        info=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64',args.image_reference or 'ros2-srt-m3:20261105'],text=True))[0]
        assert info['Architecture']=='amd64' and info['Os']=='linux'
        image=args.image_reference or info['RepoDigests'][0]
        if args.image_reference and args.image_reference not in info['RepoDigests']:raise ValueError('requested immutable image reference not present')
        report.update(image_reference=image,image_platform_id=info['Id'])
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
        report['runtime_layout']=matched(ROOT,args.runtime_layout)
        ros_install=report['runtime_layout']['ros']
        execute('versions',offline('dpkg-query -W; tc -V'))
        if args.monotonic_capture:report['monotonic_capture_config']=mono_capture.prepare(ROOT,run,image,execute,args.skip_build)
        if args.arp_packet_trace:report['arp_packet_configuration']=arp_packet_diagnostics.prepare()
        lab=NetworkLab(ROOT,run,image,monotonic_capture=args.monotonic_capture,packet_trace=args.arp_packet_trace);lab.start(credential)
        clocks={role:lab.inside(role,role+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for role in lab.containers}
        if len(set(clocks.values()))!=1:raise RuntimeError('endpoint measurements require common VM clock namespaces')
        report['clock_namespace_proof']=clocks
        if args.neighbor_diagnostics:report['neighbor_configuration']=neighbor_diagnostics.configure(lab,args.neighbor_mode)
        lab.apply('N0' if args.profile=='N4' else args.profile,args.seed)
        if args.control_qdisc_diagnostics:report['qdisc_observer_configuration']=qdisc_diagnostics.install(lab)
        if args.arp_reply_diagnostics:report['arp_reply_configuration']=arp_reply_diagnostics.install(lab,report['neighbor_configuration']['peer_macs'])
        for role,name in lab.containers.items():
            log=(run/(role+'-capture.log')).open('w')
            argv=['docker','exec',name]+pcap_options()+pcap_rotation_options()+[
                  '-w',inside+'/'+role+'.pcap','udp']
            captures.append((subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT),log))
        wait_ready(run,captures)
        if args.control_qdisc_diagnostics:qdisc_diagnostics.start(lab,run,inside,qdisc_processes)
        if args.neighbor_diagnostics:neighbor_diagnostics.start(lab,run,inside,neighbor_processes)
        if args.recorder_diagnostics:recorder_diagnostics.start(lab,run,inside,recorder_processes)
        if args.monotonic_capture:
            report['monotonic_capture_config']['features_before']=mono_capture.feature_snapshot(lab,'features-before')
            mono_capture.start(run,inside,lab,captures)
        if args.arp_reply_diagnostics:arp_reply_diagnostics.start(lab,run,inside,report['arp_reply_configuration'],arp_reply_processes)
        if args.arp_packet_trace:arp_packet_diagnostics.start(lab,run,inside,report['neighbor_configuration']['peer_macs'],arp_packet_processes)
        if args.profile=='N5':
            lab.inside('operator','competitor-server',['iperf3','-s','-D'])
            log=(run/'competitor-process.log').open('w')
            competitor=subprocess.Popen(['docker','exec',lab.containers['robot'],'iperf3','-c',lab.addresses['operator'],
                '-u','-b','128K','-t',str(duration+60),'-l','1024','--logfile',inside+'/competing-traffic.json','-J'],stdout=log,stderr=subprocess.STDOUT)
            captures.append((competitor,log))
        if bundle is None or prefix is None:raise ValueError('owned observer bundle/prefix required')
        observer=Sidecar(run,bundle,prefix)
        lab.snapshot('before')
        for role,name in lab.containers.items():
            command=('set -e; ' if args.runtime_layout!='baseline' else '')+'source /opt/ros/jazzy/setup.bash; source '+shlex.quote(ros_install+'/setup.bash')+'; exec python3 '+shlex.join([
                'evidence/m3-sdkros-task-calibration-preparation-2026-11-10/scenario.py','--role',role,'--run',inside,
                '--peer',lab.addresses['operator'],'--seconds',str(duration),'--clock-width-ms','200','--ros-install',ros_install,'--shutdown-diagnostics']+(['--probe-diagnostics'] if args.probe_diagnostics else [])+(['--sender-diagnostics'] if args.sender_diagnostics else [])+(['--start-diagnostics'] if args.start_diagnostics else [])+(['--command-diagnostics'] if args.command_diagnostics else [])+(['--provider-diagnostics'] if args.provider_diagnostics else [])+(['--sensor-provider-diagnostics'] if args.sensor_provider_diagnostics else []))
            log=(run/(role+'-scenario.log')).open('w')
            processes.append((subprocess.Popen(['docker','exec',name,'bash','-c',command],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT),log))
        deadline=time.monotonic()+duration+120;outage=False
        while time.monotonic()<deadline:
            if competitor is not None:
                if competitor.poll() is not None:raise RuntimeError('N5 competitor exited before scenario completion')
                competitor_alive_checks+=1
            if any(p.poll() not in (None,0) for p,_ in processes):raise RuntimeError('scenario failed; see '+str(run))
            if (run/'n0-shutdown-ready').exists() and not (run/'n0-shutdown-release').exists():
                observer.arm(lab)
                (run/'n0-shutdown-release').touch()
            if all(p.poll() is not None for p,_ in processes):break
            if args.root_loss_burst and (run/'measurement-start.json').exists():
                if 'root_burst_due' not in report:report['root_burst_due']=time.monotonic()+duration/3;save()
                if 'root_loss_burst' not in report and time.monotonic()>=report['root_burst_due']:
                    report['root_loss_burst']=m3_root_loss_burst.start(lab,args.root_loss_burst,args.seed)
                    report['root_burst_restore_due']=time.monotonic()+2;save()
                if 'root_loss_burst' in report and not report['root_loss_burst']['restored'] and time.monotonic()>=report['root_burst_restore_due']:
                    m3_root_loss_burst.stop(lab,report['root_loss_burst']);save()
            if args.control_egress_fault and (run/'measurement-start.json').exists():
                if 'control_fault_due' not in report:report['control_fault_due']=time.monotonic()+duration/3;save()
                if 'controlled_control_fault' not in report and time.monotonic()>=report['control_fault_due']:
                    report['controlled_control_fault']=m3_control_fault.start(lab,args.control_egress_fault)
                    report['control_fault_restore_due']=time.monotonic()+6;save()
                if 'controlled_control_fault' in report and not report['controlled_control_fault']['restored'] and time.monotonic()>=report['control_fault_restore_due']:
                    m3_control_fault.stop(lab,report['controlled_control_fault']);save()
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
        if args.root_loss_burst and not report.get('root_loss_burst',{}).get('restored'):raise RuntimeError('root loss burst not applied/restored')
        if args.profile=='N4' and not outage:raise RuntimeError('outage was not applied')
        if args.control_egress_fault and not report.get('controlled_control_fault',{}).get('restored'):raise RuntimeError('CONTROL fault not applied/restored')
        observer.close()
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
        if observer is not None:
            try:observer.close()
            except Exception as error:report['status']='failed';report['observer_cleanup_error']=str(error)
        if lab:
            try:stop_captures(lab,drain_check=args.capture_drain_check,before_close=(lambda:arp_packet_diagnostics.stop(lab,arp_packet_processes)) if arp_packet_processes else None)
            except Exception as error:report['status']='failed';report['capture_stop_error']=str(error)
            for p,log in captures:
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.terminate()
                log.close()
            if arp_packet_processes:
                try:report['arp_packet_diagnostics']=arp_packet_diagnostics.summarize(run,lab.addresses,report['neighbor_configuration']['peer_macs'])
                except Exception as error:report['status']='failed';report['arp_packet_diagnostics_error']=str(error)
            if arp_reply_processes:
                try:report['arp_reply_diagnostics']=arp_reply_diagnostics.stop(lab,run,arp_reply_processes)
                except Exception as error:report['status']='failed';report['arp_reply_diagnostics_error']=str(error)
            if qdisc_processes:
                try:report['qdisc_diagnostics']=qdisc_diagnostics.stop(lab,run,qdisc_processes)
                except Exception as error:report['status']='failed';report['qdisc_diagnostics_error']=str(error)
            if neighbor_processes:
                try:report['neighbor_diagnostics']=neighbor_diagnostics.stop(lab,run,neighbor_processes,args.neighbor_mode,report['neighbor_configuration']['peer_macs'])
                except Exception as error:report['status']='failed';report['neighbor_diagnostics_error']=str(error)
            if recorder_processes:
                try:report['recorder_diagnostics']=recorder_diagnostics.stop(run,recorder_processes)
                except Exception as error:report['status']='failed';report['recorder_diagnostics_error']=str(error)
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
        if args.command_diagnostics:
            try:
                report['command_diagnostics']=m3_command_trace.summarize_run(run)
                if args.start_diagnostics:report['start_diagnostics']=m3_start_trace_analysis.summarize_run(run)
                if args.sender_diagnostics:
                    from m3_sender_trace_analysis import summarize as summarize_sender
                    report['sender_diagnostics']=summarize_sender(report['command_diagnostics'])
                if args.probe_diagnostics:
                    from m3_probe_trace_analysis import summarize as summarize_probes
                    report['probe_diagnostics']=summarize_probes(report['command_diagnostics'])
            except Exception as error:report['status']='failed';report['command_diagnostics_error']=str(error)
        if args.sensor_provider_diagnostics:
            try:report['sensor_provider_diagnostics']=m3_provider_stats.summarize_run(run,sensor=True)
            except Exception as error:report['status']='failed';report['sensor_provider_diagnostics_error']=str(error)
        if args.provider_diagnostics:
            try:report['provider_diagnostics']=m3_provider_stats.summarize_run(run)
            except Exception as error:report['status']='failed';report['provider_diagnostics_error']=str(error)
        credential.unlink(missing_ok=True);save();print(run,flush=True)
    if report['status']!='passed':raise RuntimeError(report.get('competitor_error',report.get('command_diagnostics_error',report.get('provider_diagnostics_error',report.get('qdisc_diagnostics_error',report.get('neighbor_diagnostics_error',report.get('capture_error',report.get('error','M3 failed'))))))))


if __name__=='__main__':main()
