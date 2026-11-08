#!/usr/bin/env python3
"""One planned ROS discovery confirmation and three-seed SRT N5 progress cohort."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from m3_source_preflight import ROOT,IMAGE,sha,write
from m3_n5_progress import RUNTIMES,command_progress,timeline
from m3_ros_discovery_cut import blocked,recovered

SLOTS=[dict(label='ros-N0-control',group='ros',seconds=15,profile='N0',seed=1701,cut=False),dict(label='ros-N0-fragment-cut',group='ros',seconds=15,profile='N0',seed=1701,cut=True),dict(label='srt-N0-control',group='srt',seconds=15,profile='N0',seed=1701)]+[dict(label='srt-N5-'+str(seed),group='srt',seconds=300,profile='N5',seed=seed) for seed in (1701,2903,4211)]


def check(report,run,slot):
    if report['status']!='passed' or report['image_reference']!=IMAGE:raise ValueError('harness failed or runtime image differs')
    if report.get('pcap_population_reconciled') is not True:raise ValueError('unreconciled capture population')
    proof=dict(progress=command_progress(report,run))
    if not proof['progress']['no_unresolved_attempts']:raise ValueError('unsuccessful or unresolved command attempt; uncertainty retained')
    if slot['group']=='ros':
        proof['timeline']={r:timeline(run/(r+'-startup-timeline.jsonl')) for r in ('operator','robot')}
        proof['shutdown']={p.name:json.loads(p.read_text()) for p in run.glob('*-shutdown.json')}
        if len(proof['shutdown'])!=3 or not all(x['passed'] for x in proof['shutdown'].values()):raise ValueError('ROS owned child shutdown incomplete')
        if slot['cut']:
            cut=report['controlled_discovery']
            if cut['status']!='recovered' or not cut['restored'] or cut['drops'][0]['drops']<1:raise ValueError('ROS controlled loss/recovery incomplete')
            blocked(cut['blocked']);recovered(cut['initial'],cut['recovered'])
            if cut['hold']['end_ns']-cut['hold']['begin_ns']<8_000_000_000:raise ValueError('discovery hold too short')
            for role,side in [('operator','sender'),('robot','receiver')]:
                if cut['initial'][role]['process_epoch']!=report['results']['final_command_'+side]['process_epoch']:raise ValueError('coordinator owner changed after recovery')
            ready=json.loads((run/'control-ready.json').read_text())
            if ready['device']['imu_published'] or ready['device']['joints_published']:raise ValueError('telemetry ran before controlled discovery recovery')
            proof['controlled_discovery']=cut
    return proof


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    inventory={p:sha(ROOT/p) for p in RUNTIMES}
    if inventory['install/srt-m0/lib/librobotweax-srt.a']!=json.loads((ROOT/'baselines/dependencies.json').read_text())['srt']['installed_library_sha256']:raise ValueError('SRT pin differs')
    report=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),slots=SLOTS,runtime_before=inventory,rows=[],qualification=False);blocked_groups=set()
    write(out/'execution.json',report)
    for slot in SLOTS:
        row=dict(slot=slot,status='not_executed');report['rows'].append(row)
        if slot['group'] in blocked_groups:
            row['why']='prior failure in independent group';write(out/'execution.json',report);continue
        dds=slot['group']=='ros';base=ROOT/('.local/m3-dds-combined' if dds else '.local/m3');before=set(base.glob('*'))
        argv=[sys.executable,'tools/run_m3_dds.py' if dds else 'tools/run_m3.py','--profile',slot['profile'],'--seconds',str(slot['seconds']),'--seed',str(slot['seed']),'--skip-build','--capture-drain-check']
        argv+=['--commands','--startup','control-first']+(['--discovery-fragment-cut'] if slot['cut'] else []) if dds else ['--command-diagnostics','--provider-diagnostics']
        row.update(status='running',argv=argv);write(out/'execution.json',report)
        try:
            with (out/(slot['label']+'.log')).open('x') as log:
                child=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                try:row['exit_code']=child.wait(timeout=slot['seconds']+240)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    try:child.wait(timeout=15)
                    except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
                    raise ValueError('outer fixture timeout; inspect owned cleanup')
            created=set(base.glob('*'))-before
            if len(created)!=1:raise ValueError('ambiguous original run directory')
            run=created.pop();row['run']=str(run.relative_to(ROOT));data=json.loads((run/'run.json').read_text());row['harness_status']=data['status']
            if row['exit_code']:raise ValueError(data.get('error','harness returned failure'))
            row['proof']=check(data,run,slot)
            if inventory!={p:sha(ROOT/p) for p in inventory}:raise ValueError('production binary changed')
            row['status']='passed'
        except Exception as e:row.update(status='failed',error=str(e));blocked_groups.add(slot['group'])
        write(out/'execution.json',report);print(slot['label'],row['status'],row.get('error',''),flush=True)
    report['runtime_after']={p:sha(ROOT/p) for p in inventory};report['runtime_unchanged']=report['runtime_after']==inventory;write(out/'execution.json',report)
    return 1 if blocked_groups or not report['runtime_unchanged'] else 0


if __name__=='__main__':raise SystemExit(main())
