#!/usr/bin/env python3
"""Frozen session2903 diagnostic cohort, once per slot, no retry or mitigation."""
import argparse,json,subprocess,sys
from pathlib import Path
from m3_source_preflight import ROOT,IMAGE,sha,write
from m3_n5_progress import RUNTIMES
from m3_admission_diagnostics import analyze
from m3_control_fault_analysis import ARCHIVE

SLOTS=[dict(label='srt-N0-2903',profile='N0',seconds=15,seed=2903),dict(label='srt-N5-2903',profile='N5',seconds=300,seed=2903)]
OBSERVERS=['build/m3-monotonic-capture/monotonic_capture','build/m3-netdev-features/netdev_features']


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    runtime={p:sha(ROOT/p) for p in RUNTIMES};observers={p:sha(ROOT/p) for p in OBSERVERS}
    if runtime[RUNTIMES[-1]]!=ARCHIVE:raise ValueError('provider pin mismatch')
    report=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,slots=SLOTS,progress_gate='durable-outcomes',strict_success_also_reported=True,runtime_before=runtime,observer_before=observers,rows=[],qualification=False)
    write(out/'execution.json',report);failed=False
    for slot in SLOTS:
        row=dict(slot=slot,status='not_executed');report['rows'].append(row)
        if failed:row['why']='prior cohort failure; no retries';write(out/'execution.json',report);continue
        before=set((ROOT/'.local/m3').glob('*'))
        argv=[sys.executable,'tools/run_m3.py','--profile',slot['profile'],'--seconds',str(slot['seconds']),'--seed',str(slot['seed']),'--skip-build','--command-diagnostics','--provider-diagnostics','--sensor-provider-diagnostics','--monotonic-capture','--capture-drain-check']
        row.update(status='running',argv=argv);write(out/'execution.json',report)
        try:
            with (out/(slot['label']+'.log')).open('x') as log:
                child=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                try:row['exit_code']=child.wait(timeout=slot['seconds']+240)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    try:child.wait(timeout=15)
                    except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
                    raise ValueError('outer timeout; owned cleanup requires inspection')
            created=set((ROOT/'.local/m3').glob('*'))-before
            if len(created)!=1:raise ValueError('ambiguous original run')
            run=created.pop();row['run']=str(run.relative_to(ROOT));data=json.loads((run/'run.json').read_text());row['harness_status']=data['status']
            if row['exit_code'] or data['status']!='passed':raise ValueError('original harness failed; preserve all raw artifacts')
            if data['image_reference']!=IMAGE or data.get('pcap_population_reconciled') is not True:raise ValueError('image/capture gate failed')
            for name in ('provider_diagnostics','sensor_provider_diagnostics'):
                if not data.get(name) or not all(v['complete'] for v in data[name].values()):raise ValueError(name+' incomplete')
            statuses=data['monotonic_captures']['statuses']
            if set(statuses)!={'robot','operator'} or not all(v['complete'] and v['artifact_version']==2 and v['clock']=='kernel_monotonic' and v['time_namespace_zero'] for v in statuses.values()):raise ValueError('native v2 coverage gate failed')
            if not all(sha(ROOT/p)==h for p,h in data['source_sha256'].items()):raise ValueError('source changed during cohort')
            row['analysis']=analyze(data,run)
            if runtime!={p:sha(ROOT/p) for p in runtime} or observers!={p:sha(ROOT/p) for p in observers}:raise ValueError('runtime/observer changed during cohort')
            if not row['analysis']['durable_outcomes']['complete']:raise ValueError('command progress failed; uncertainty retained')
            row['status']='passed'
        except Exception as error:row.update(status='failed',error=str(error));failed=True
        write(out/'execution.json',report);print(slot['label'],row['status'],row.get('error',''),flush=True)
    report['runtime_after']={p:sha(ROOT/p) for p in runtime};report['observer_after']={p:sha(ROOT/p) for p in observers}
    report['runtime_unchanged']=runtime==report['runtime_after'] and observers==report['observer_after'];write(out/'execution.json',report)
    return int(failed or not report['runtime_unchanged'])


if __name__=='__main__':raise SystemExit(main())
