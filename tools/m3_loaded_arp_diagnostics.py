#!/usr/bin/env python3
"""Frozen loaded ARP reply eligibility diagnostic cohort, once per slot, no retry or mitigation."""
import argparse,json,subprocess,sys
from pathlib import Path
from m3_source_preflight import ROOT,IMAGE,sha,write
from m3_n5_progress import RUNTIMES
from m3_admission_diagnostics import analyze
from m3_control_fault_analysis import ARCHIVE
import m3_runtime_layout

SLOTS=[dict(label='srt-N0-2903',profile='N0',seconds=15,seed=2903),dict(label='srt-N5-2903',profile='N5',seconds=300,seed=2903)]
OBSERVERS=['build/m3-monotonic-capture/monotonic_capture','build/m3-netdev-features/netdev_features']
ADDITIONAL_SLOTS=[dict(label='srt-N0-1701',profile='N0',seconds=15,seed=1701),dict(label='srt-N5-1701',profile='N5',seconds=300,seed=1701),dict(label='srt-N5-4211',profile='N5',seconds=300,seed=4211)]


def selected_slots(coverage,start_trace):
    if coverage=='focused':return SLOTS
    if coverage!='additional-seeds' or not start_trace:raise ValueError('additional seed coverage requires matched start tracing')
    return ADDITIONAL_SLOTS


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--packet-trace',action='store_true');parser.add_argument('--start-trace',action='store_true');parser.add_argument('--coverage',choices=('focused','additional-seeds'),default='focused');args=parser.parse_args();
    if args.start_trace and not args.packet_trace:parser.error('start-trace cohort requires packet-trace')
    try:slots=selected_slots(args.coverage,args.start_trace)
    except ValueError as error:parser.error(str(error))
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    layout=m3_runtime_layout.matched(ROOT,'start-trace' if args.start_trace else 'baseline')
    runtime_paths=layout['runtime_paths'];runtime={p:sha(ROOT/p) for p in runtime_paths};observers={p:sha(ROOT/p) for p in OBSERVERS+(['build/arp-packet-trace/arp_packet_trace'] if args.packet_trace else [])}
    if runtime[runtime_paths[-1]]!=ARCHIVE:raise ValueError('provider pin mismatch')
    report=dict(runtime_layout=layout,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,coverage=args.coverage,slots=slots,progress_gate='durable-outcomes',strict_success_also_reported=True,runtime_before=runtime,observer_before=observers,rows=[],qualification=False)
    write(out/'execution.json',report);failed=False
    for slot in slots:
        row=dict(slot=slot,status='not_executed');report['rows'].append(row)
        if failed:row['why']='prior cohort failure; no retries';write(out/'execution.json',report);continue
        before=set((ROOT/'.local/m3').glob('*'))
        argv=[sys.executable,'tools/run_m3.py','--profile',slot['profile'],'--seconds',str(slot['seconds']),'--seed',str(slot['seed']),'--skip-build','--command-diagnostics','--provider-diagnostics','--sensor-provider-diagnostics','--monotonic-capture','--capture-drain-check','--neighbor-diagnostics','--neighbor-mode','dynamic','--control-qdisc-diagnostics','--arp-reply-diagnostics']
        if args.packet_trace:argv+=['--arp-packet-trace']
        if args.start_trace:argv+=['--start-diagnostics','--runtime-layout','start-trace']
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
            if data.get('neighbor_mode')!='dynamic' or not data.get('neighbor_diagnostics') or not data.get('qdisc_diagnostics'):raise ValueError('path observers missing')
            for name in ('neighbor_diagnostics','qdisc_diagnostics'):
                if not all(v['complete'] for v in data[name].values()):raise ValueError(name+' incomplete')
            if slot['profile']=='N0' and not all(v['last']['pass_counter']['packets']>v['first']['pass_counter']['packets'] for v in data['qdisc_diagnostics'].values()):raise ValueError('N0 selected PASS positive control absent')
            if not data.get('arp_reply_diagnostics') or not all(v['complete'] for v in data['arp_reply_diagnostics'].values()):raise ValueError('ARP reply diagnostics incomplete')
            if slot['profile']=='N0' and sum(v['last']['counters']['eligible']['packets']-v['first']['counters']['eligible']['packets'] for v in data['arp_reply_diagnostics'].values())<=0:raise ValueError('N0 ARP reply positive control absent')
            if args.packet_trace:
                values=data.get('arp_packet_diagnostics',{})
                if set(values)!={'operator','robot'} or not all(v['complete'] for v in values.values()):raise ValueError('packet trace incomplete')
                if slot['profile']=='N0' and sum(v['status']['created'] for v in values.values())<=0:raise ValueError('packet trace positive control absent')
            if args.start_trace:
                if data.get('runtime_layout')!=layout or not data.get('start_diagnostics_enabled') or not data.get('start_diagnostics',{}).get('complete') or not data['start_diagnostics']['starts']:raise ValueError('matched start diagnostics incomplete')
                m3_runtime_layout.matched(ROOT,'start-trace')
            row['analysis']=analyze(data,run)
            if runtime!={p:sha(ROOT/p) for p in runtime} or observers!={p:sha(ROOT/p) for p in observers}:raise ValueError('runtime/observer changed during cohort')
            if not row['analysis']['durable_outcomes']['complete']:raise ValueError('command progress failed; uncertainty retained')
            row['status']='passed'
        except Exception as error:row.update(status='failed',error=str(error));failed=True
        write(out/'execution.json',report);print(slot['label'],row['status'],row.get('error',''),flush=True)
    report['runtime_after']={p:sha(ROOT/p) for p in runtime};report['observer_after']={p:sha(ROOT/p) for p in observers}
    report['runtime_unchanged']=runtime==report['runtime_after'] and observers==report['observer_after'];
    if args.start_trace:report['matched_after']=m3_runtime_layout.matched(ROOT,'start-trace')
    write(out/'execution.json',report)
    return int(failed or not report['runtime_unchanged'])


if __name__=='__main__':raise SystemExit(main())
