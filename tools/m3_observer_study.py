#!/usr/bin/env python3
"""Sequential, preregistered observer on/off study and three-seed paced N5 runs.

Reuses the installed development build. Does not claim isolated observer cost,
controlled hardware performance, transport parity, or complete M3 acceptance.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
from m3_capture import pcap_configuration

ROOT=Path(__file__).resolve().parents[1]


def plan(short_seconds=45,long_seconds=300,*,skip_long_n5=False,impairment_seconds=None):
    rows=[]
    for transport,modes in [('srt',(False,True,True,False)),('dds',(True,False,False,True))]:
        for index,observer in enumerate(modes):rows.append(dict(label=f'{transport}-N0-{index+1}-'+('on' if observer else 'off'),group=transport,phase='on_off',observer=observer,profile='N0',seed=1701,seconds=short_seconds))
    if not skip_long_n5:rows.extend(dict(label=f'dds-paced-N5-{seed}',group='dds',phase='long',observer=True,profile='N5',seed=seed,seconds=long_seconds) for seed in (1701,2903,4211))
    if impairment_seconds is not None:
        rows.extend(dict(label=f'{group}-{profile}-probe',group=group,phase='impairment',observer=True,profile=profile,seed=1701,seconds=impairment_seconds) for profile in ('N1','N2') for group in ('srt','dds'))
    return rows


def source_inventory():
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ('src','ros2','proto','cmake','containers','tools','tests')
        for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in str(p)}


def installed_inventory():
    paths=[ROOT/'install/m3-ros/robotweax_srt_bridge/lib/robotweax_srt_bridge'/name for name in ('bridge_node','ros_rate_worker','dds_command_node')]
    paths += [ROOT/'install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo/rate_simulator',ROOT/'install/bridge-m3/bin/robotweax-journal-worker',ROOT/'build/m3-monotonic-capture/monotonic_capture',ROOT/'build/m3-netdev-features/netdev_features']
    paths += list((ROOT/'install/srt-m0').glob('lib*/**/librobotweax-srt.a'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def extract(report,slot):
    if report['status']!='passed':raise ValueError('workload did not pass')
    if (report['profile'],report['seed'],report['seconds'])!=(slot['profile'],slot['seed'],slot['seconds']):raise ValueError('study configuration mismatch')
    if bool(report.get('monotonic_capture_config',{}).get('enabled'))!=slot['observer']:raise ValueError('observer configuration mismatch')
    if slot['group']=='dds' and report['dds_transport_profile']!=('paced-sensors' if slot['profile']=='N5' else 'system'):raise ValueError('DDS profile mismatch')
    if report.get('pcap_dispatch_mode')!='immediate':raise ValueError('study requires immediate PCAP mode')
    if report.get('pcap_capture_config')!=pcap_configuration():raise ValueError('study capture buffer/snapshot configuration mismatch')
    proofs=list(report['clock_namespace_proof'].values())
    if len(set(proofs))!=1:raise ValueError('endpoint clock proofs differ')
    boot=proofs[0].splitlines()[0]
    if slot['observer'] and any(s.get('artifact_version')!=2 or s.get('record_bytes')!=168 for s in report['monotonic_captures']['statuses'].values()):raise ValueError('study requires capture artifact v2')
    windows=report['endpoint_measurements']['windows']
    for name,w in windows.items():
        if not all(g['qualified'] for g in w['container_cgroup'].values()):raise ValueError('unqualified cgroup window: '+name)
        if slot['observer'] and not all(g['qualified'] for g in report['monotonic_captures']['windows'][name].values()):raise ValueError('unqualified monotonic capture')
    measurement=report['measurement_window'];result=report['results'];commands=report['command_summary']
    if slot['group']=='srt':
        sensor=dict(produced=measurement['source_produced'],received=measurement['observer_received'],actual_source_hz=measurement['source_actual_hz'])
        effects=result['device']['effects']
    else:
        routes=measurement['routes'];sensor=dict(produced=sum(r['produced'] for r in routes.values()),received=sum(r['received'] for r in routes.values()),actual_source_hz={k:r['actual_source_hz'] for k,r in routes.items()})
        effects=result['final_device']['effects']
    return dict(measurement_scope=dict(pcap_mode='immediate',pcap_config=report['pcap_capture_config'],boot_id=boot,native_artifact_version=2 if slot['observer'] else None),image=report['image_platform_id'],configured_seconds=slot['seconds'],profile=slot['profile'],seed=slot['seed'],
        observer=slot['observer'],windows={name:dict(seconds=w['seconds'],cgroups=w['container_cgroup'],endpoint_cpu=w['cpu']) for name,w in windows.items()},
        command_summary=commands,effects=effects,sensors=sensor,monotonic_captures=report.get('monotonic_captures'),competitor=report.get('competitor_check'))


def compare_pairs(rows):
    comparisons={}
    for group in ('srt','dds'):
        block=[r for r in rows if r['slot']['group']==group and r['slot']['phase']=='on_off']
        if len(block)!=4:raise ValueError('incomplete on/off block')
        if any(r.get('status')!='passed' for r in block):raise ValueError('failed on/off block')
        if len({(r['metrics']['image'],r['metrics']['configured_seconds'],r['metrics']['profile'],r['metrics']['seed'],r['metrics']['measurement_scope']['pcap_mode'],r['metrics']['measurement_scope']['boot_id'],json.dumps(r['metrics']['measurement_scope']['pcap_config'],sort_keys=True)) for r in block})!=1:raise ValueError('incomparable on/off configurations')
        if any(r['metrics']['measurement_scope']['pcap_mode']!='immediate' or (r['slot']['observer'] and r['metrics']['measurement_scope']['native_artifact_version']!=2) for r in block):raise ValueError('incompatible capture version/mode')
        pairs=[]
        for first,second in (block[:2],block[2:]):
            if first['slot']['observer']==second['slot']['observer']:raise ValueError('pair lacks on/off contrast')
            on,off=(first,second) if first['slot']['observer'] else (second,first)
            deltas={}
            for role in ('robot','operator'):
                a=on['metrics']['windows']['source_enabled']['cgroups'][role];b=off['metrics']['windows']['source_enabled']['cgroups'][role]
                if not a['qualified'] or not b['qualified']:raise ValueError('unqualified comparison counters')
                if a['limits']!=b['limits']:raise ValueError('cgroup limits differ across pair')
                deltas[role]=dict(on_core_percent=[a['inner_cpu_core_percent'],a['outer_cpu_core_percent']],off_core_percent=[b['inner_cpu_core_percent'],b['outer_cpu_core_percent']],
                    observed_on_minus_off_core_percent=[a['inner_cpu_core_percent']-b['outer_cpu_core_percent'],a['outer_cpu_core_percent']-b['inner_cpu_core_percent']],
                    sampled_charged_memory_max_difference_bytes=a['maximum_observed_memory_current_bytes']-b['maximum_observed_memory_current_bytes'])
            state_counts=lambda row:{k:v['count'] for k,v in row['metrics']['command_summary']['by_state_reason'].items()}
            same_work=all(on['metrics']['command_summary'][key]==off['metrics']['command_summary'][key] for key in ('attempts','not_admitted','unresolved')) and state_counts(on)==state_counts(off) and on['metrics']['effects']==off['metrics']['effects']
            pairs.append(dict(on=on['slot']['label'],off=off['slot']['label'],same_command_counts_and_effects=same_work,roles=deltas))
        comparisons[group]=dict(pairs=pairs,scope='source-enabled phase; observed inner/outer differences, not physical CPU bounds/confidence intervals or isolated observer cost; shared emulated VM; memory includes charged cache; workload populations retained separately')
    return comparisons


def write(path,data):path.write_text(json.dumps(data,indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--seconds',type=int,default=45);parser.add_argument('--long-seconds',type=int,default=300);parser.add_argument('--plan-only',action='store_true');parser.add_argument('--skip-long-n5',action='store_true',help='explicitly omit the three long N5 repetitions');parser.add_argument('--impairment-seconds',type=int,help='append SRT/DDS N1/N2 seed-1701 development probes');args=parser.parse_args()
    if not 15<=args.seconds<=120 or not 300<=args.long_seconds<=7200:parser.error('on/off duration 15..120 s; long duration 300..7200 s')
    if args.impairment_seconds is not None and not 15<=args.impairment_seconds<=600:parser.error('impairment probes must be 15..600 seconds')
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    definition=dict(created_utc=datetime.now(timezone.utc).isoformat(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),source_sha256=source_inventory(),
        build_scope='development reuse of installed M3 SDK/ROS/native binaries; no rebuild during study',installed_sha256=installed_inventory(),slots=plan(args.seconds,args.long_seconds,skip_long_n5=args.skip_long_n5,impairment_seconds=args.impairment_seconds),
        expected_measurement=dict(pcap_mode='immediate',pcap_config=pcap_configuration(),capture_artifact_version=2),skip_long_n5=args.skip_long_n5,impairment_seconds=args.impairment_seconds,
        design='SRT N0 off/on/on/off; DDS N0 on/off/off/on; optional long N5 and N1/N2 probes explicitly listed; sequential fresh containers; no retries or host tuning',complete_m3_acceptance=False)
    write(out/'plan.json',definition)
    if args.plan_only:return 0
    report=dict(status='running',rows=[],complete_m3_acceptance=False)
    write(out/'study.json',report)
    try:
        for slot in definition['slots']:
            if source_inventory()!=definition['source_sha256']:raise ValueError('study sources changed after preregistration')
            if installed_inventory()!=definition['installed_sha256']:raise ValueError('installed binaries changed after preregistration')
            script='tools/run_m3.py' if slot['group']=='srt' else 'tools/run_m3_dds.py'
            argv=[sys.executable,script,'--profile',slot['profile'],'--seed',str(slot['seed']),'--seconds',str(slot['seconds']),'--skip-build']
            if slot['group']=='dds':argv+=['--commands']+(['--dds-profile','paced-sensors'] if slot['profile']=='N5' else [])
            if slot['observer']:argv+=['--monotonic-capture']
            log_path=out/(slot['label']+'.log')
            with log_path.open('w') as log:
                child=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                try:code=child.wait()
                except BaseException:
                    child.send_signal(signal.SIGINT)
                    try:child.wait(timeout=30)
                    except subprocess.TimeoutExpired:child.terminate();child.wait(timeout=10)
                    raise
            candidates=[Path(line) for line in log_path.read_text().splitlines() if line.startswith(str(ROOT/'.local/')) and (Path(line)/'run.json').is_file()]
            if not candidates:raise ValueError('missing child run manifest: '+slot['label'])
            run=candidates[-1];data=json.loads((run/'run.json').read_text());row=dict(slot=slot,run=str(run.relative_to(ROOT)),exit_code=code,status=data['status']);report['rows'].append(row);write(out/'study.json',report)
            if code or data['status']!='passed':raise ValueError('child workload failed: '+slot['label'])
            if data['source_sha256']!=definition['source_sha256']:raise ValueError('child source inventory differs')
            if installed_inventory()!=definition['installed_sha256']:raise ValueError('installed binaries changed during workload')
            row['metrics']=extract(data,slot);write(out/'study.json',report)
            print(slot['label']+' passed: '+str(run),flush=True)
        report['comparisons']=compare_pairs(report['rows']);report['status']='passed'
    except BaseException as error:
        report.update(status='failed',error=str(error));write(out/'study.json',report);raise
    write(out/'study.json',report);print(out,flush=True);return 0


if __name__=='__main__':raise SystemExit(main())
