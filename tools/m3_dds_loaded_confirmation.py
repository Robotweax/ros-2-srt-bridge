#!/usr/bin/env python3
"""Two fixed default-DDS cases on the matched build; stop on first failed gate."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from m3_source_preflight import ROOT,IMAGE,write
from m3_runtime_layout import matched
from m3_n5_progress import command_progress,timeline

SLOTS=[dict(label='dds-N0-control',profile='N0',seconds=15,seed=1701),
       dict(label='dds-N5-cold',profile='N5',seconds=60,seed=1701)]


def check(report,slot,progress,timelines,shutdown):
    if report['status']!='passed' or report['image_reference']!=IMAGE:raise ValueError('harness failed or image differs')
    if report.get('dds_transport_profile')!='system' or report.get('startup_mode')!='simultaneous':raise ValueError('default cold-start configuration differs')
    if report.get('profile')!=slot['profile'] or report.get('seconds')!=slot['seconds'] or report.get('seed')!=slot['seed']:raise ValueError('predeclared case differs')
    if report.get('runtime_layout',{}).get('name')!='sender-reconcile':raise ValueError('matched runtime missing')
    if report.get('pcap_population_reconciled') is not True or report.get('age_estimates_qualified') is not True:raise ValueError('capture/clock qualification failed')
    if not progress['no_unresolved_attempts'] or len(progress['entries'])<(8 if slot['profile']=='N0' else 1):raise ValueError('insufficient confirmed command progress')
    if slot['profile']=='N0' and progress['skipped_slots']:raise ValueError('N0 command slots skipped')
    if set(timelines)!={'operator','robot'} or any(t['classification']!='ready_observed' for t in timelines.values()):raise ValueError('cold discovery not ready')
    if len(shutdown)!=3 or not all(s['passed'] for s in shutdown.values()):raise ValueError('owned child shutdown incomplete')
    if slot['profile']=='N5' and (report.get('competitor_check',{}).get('target_bitrate')!=128000 or not report['competitor_check'].get('alive_poll_checks')):raise ValueError('loaded competitor not established')
    for route,target in (('imu',200),('joints',50)):
        row=report['measurement_window']['routes'][route]
        if abs(row['actual_source_hz']/target-1)>.01 or row['accepted']<1 or row['invalid'] or row['clock_rejected']:raise ValueError('source cadence or typed/clock progress failed')
    return dict(progress=progress,timelines=timelines,shutdown=shutdown)


def execute(slots,invoke,record):
    rows=[];failed=False
    for slot in slots:
        row=dict(slot=slot,status='not_executed')
        if failed:row['reason']='previous case failed; no retry'
        else:
            try:row.update(invoke(slot));failed=row['status']!='passed'
            except Exception as error:row.update(status='failed',error=str(error));failed=True
        rows.append(row);record(dict(status='failed' if failed else 'running',rows=rows,full_M3_accepted=False))
    result=dict(status='failed' if failed else 'passed',rows=rows,full_M3_accepted=False);record(result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    fixed=matched(ROOT,'sender-reconcile');write(out/'runtime-before.json',fixed)
    def invoke(slot):
        base=ROOT/'.local/m3-dds-combined';before=set(base.glob('*'))
        argv=[sys.executable,'tools/run_m3_dds.py','--profile',slot['profile'],'--seconds',str(slot['seconds']),'--seed',str(slot['seed']),'--commands','--dds-profile','system','--startup','simultaneous','--runtime-layout','sender-reconcile','--skip-build','--capture-drain-check']
        row=dict(status='failed',argv=argv)
        with (out/(slot['label']+'.log')).open('x') as log:
            child=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            try:row['exit_code']=child.wait(timeout=slot['seconds']+240)
            except subprocess.TimeoutExpired:
                child.terminate()
                try:child.wait(timeout=20)
                except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
                raise ValueError('outer fixture timeout; audit owned cleanup')
        created=set(base.glob('*'))-before
        if len(created)!=1:raise ValueError('ambiguous original run directory')
        run=created.pop();row['run']=str(run.relative_to(ROOT));report=json.loads((run/'run.json').read_text());row['harness_status']=report['status']
        try:
            row['timelines']={role:timeline(run/(role+'-startup-timeline.jsonl')) for role in ('operator','robot') if (run/(role+'-startup-timeline.jsonl')).exists()}
            if row['exit_code']:raise ValueError(report.get('capture_error',report.get('error','harness returned failure')))
            progress=command_progress(report,run);shutdown={p.name:json.loads(p.read_text()) for p in run.glob('*-shutdown.json')}
            row['proof']=check(report,slot,progress,row['timelines'],shutdown)
            if matched(ROOT,'sender-reconcile')!=fixed:raise ValueError('matched/preserved runtime chain changed')
            row['status']='passed'
        except Exception as error:row['error']=str(error)
        return row
    def record(result):
        write(out/'execution.json',result)
        print(json.dumps(dict(status=result['status'],case=result['rows'][-1]['slot']['label'],case_status=result['rows'][-1]['status'])),flush=True)
    result=execute(SLOTS,invoke,record);return result['status']!='passed'


if __name__=='__main__':raise SystemExit(main())
