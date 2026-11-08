#!/usr/bin/env python3
"""One frozen admission diagnostic cohort; preserve failures and never retry."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from m3_source_preflight import ROOT,IMAGE,sha,write
from m3_n5_progress import RUNTIMES,command_progress
from m3_command_trace import summarize_run

SLOTS=[dict(label='srt-N0-control',profile='N0',seconds=15,seed=4211),
       dict(label='srt-N5-4211',profile='N5',seconds=300,seed=4211)]
MATRIX_SLOTS=[SLOTS[0]]+[dict(label='srt-N5-'+str(seed),profile='N5',seconds=300,seed=seed) for seed in (4211,1701,2903)]


def correlate(traces):
    """Match observations only, by original context/request/sequence/kind."""
    def key(e):return tuple(e[k] for k in ('session','route','request','request_sequence','detail'))
    rejections=[dict(file=n,**e) for n,t in traces.items() if n.startswith('robot-') for e in t['events']
                if e['point']==32 and e['detail']==6 and e['value']==13]
    errors=[dict(file=n,**e) for n,t in traces.items() if n.startswith('operator-') for e in t['events']
            if e['point']==33 and e['detail']==6 and e['value']==5]
    return [dict(receiver=r,sender=s) for r in rejections for s in errors if key(r)==key(s)]


def successful_receiver_pairs(entry,events):
    """Bind admission/worker observations to the original durable intent."""
    sender=entry['sender']
    matching=[e for e in events if e['detail']==6 and e['value']==0 and
              e['session']==sender['session'] and e['route']==sender['route'] and e['origin_ns']==sender['source_ns']]
    # Initial admission may pass while queued behind an earlier deferred frame.
    # A recorded resume is the later forwarding gate and supersedes that sample.
    gate=36 if any(e['point']==36 for e in matching) else 32
    return [dict(admission=a,worker=w) for a in matching if a['point']==gate for w in matching
            if w['point']==34 and a['request_sequence']==w['request_sequence']]


def verify_expired(entry,events):
    a=entry['sender'];b=entry['receiver']
    if not a or not b or any(a[k]!=b[k] for k in ('state','reason','revision','route','payload_hash','source_epoch','source_ns','session','result_valid','result_generation')):raise ValueError('durable expiry journal mismatch')
    if a['state']!=7 or a['reason']!=3 or a['result_valid'] or b['dispatched_ns'] or not 0<b['deadline_ns']<b['admitted_ns']:raise ValueError('invalid journal-only expiry')
    if a['deadline_ns']!=a['source_ns']+5_000_000_000 or entry['sdk_handoffs']!=1:raise ValueError('expiry source budget/replay mismatch')
    proofs=[e for e in events if e['point']==39 and e['session']==a['session'] and e['route']==a['route'] and e['origin_ns']==a['source_ns'] and e['expiry_deadline_ns']==b['deadline_ns']]
    if len(proofs)!=1 or proofs[0]['age_lower_ns']<=5_000_000_000:raise ValueError('missing unique lower-bound expiry proof')
    if not any(e['point']==34 and e['value']==0 and e['session']==a['session'] and e['route']==a['route'] and e['origin_ns']==a['source_ns'] and e['request_sequence']==proofs[0]['request_sequence'] for e in events):raise ValueError('expiry worker proof missing')


def analyze(report,run):
    progress=command_progress(report,run);traces=summarize_run(run)
    receivers=[dict(file=n,**e) for n,t in traces.items() if n.startswith('robot-') for e in t['events'] if e['point'] in (32,34,35,36,37,38,39)]
    attempts=[]
    for entry in progress['entries']:
        identity=entry['number'].to_bytes(16,'little').hex()
        # Original closed journal audits independently validate confirmed results.
        # These additional observations cannot authorize a command outcome.
        events=[e for e in receivers if e['request']==identity and e['detail']==6]
        if entry['terminal']==4 and len(successful_receiver_pairs(entry,events))!=1:
            raise ValueError('confirmed result lacks unique original-context admission/worker diagnostic coverage')
        if entry['terminal']==7:
            verify_expired(entry,events)
        attempts.append(dict(number=entry['number'],terminal=entry['terminal'],sdk_handoffs=entry['sdk_handoffs'],receiver_command_events=events))
    begin=report['results']['publication_interval']['resume_monotonic_ns'];end=report['results']['command_data_cutoff_monotonic_ns']
    context=[dict(file=n,**e) for n,t in traces.items() for e in t['events'] if begin<=e['monotonic_ns']<=end and e['point'] in (2,3,4,30,31)]
    expired=sum(e['terminal']==7 for e in progress['entries'])
    outcomes=bool(progress['entries']) and all(e['terminal'] in (4,7) for e in progress['entries']) and progress['audit']['effects']==progress['audit']['confirmed_successes']
    return dict(progress=progress,durable_outcomes=dict(complete=outcomes,verified_expired=expired,all_success=progress['audit']['all_succeeded'],scope='success or qualified durable expiry only; not all-success deadline qualification'),attempts=attempts,clock_rejection_correlations=correlate(traces),active_context_events=context,
                trace_population={n:dict(records=t['records'],complete=t['complete'],counts=t['counts']) for n,t in traces.items()},
                scope='local observed admission/error correlations, not durable absence, root-cause uniqueness, execution or replay authority')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--matrix',choices=('focused','three-seed'),default='focused');parser.add_argument('--progress-gate',choices=('all-success','durable-outcomes'),default='all-success');args=parser.parse_args()
    slots=SLOTS if args.matrix=='focused' else MATRIX_SLOTS
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    runtime={p:sha(ROOT/p) for p in RUNTIMES}
    if runtime['install/srt-m0/lib/librobotweax-srt.a']!=json.loads((ROOT/'baselines/dependencies.json').read_text())['srt']['installed_library_sha256']:raise ValueError('provider pin mismatch')
    report=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),matrix=args.matrix,progress_gate=args.progress_gate,slots=slots,
                runtime_before=runtime,rows=[],qualification=False);write(out/'execution.json',report);failed=False
    for slot in slots:
        row=dict(slot=slot,status='not_executed');report['rows'].append(row)
        if failed:row['why']='prior cohort failure; no retries';write(out/'execution.json',report);continue
        base=ROOT/'.local/m3';before=set(base.glob('*'))
        argv=[sys.executable,'tools/run_m3.py','--profile',slot['profile'],'--seconds',str(slot['seconds']),'--seed',str(slot['seed']),
              '--skip-build','--command-diagnostics','--provider-diagnostics','--capture-drain-check']
        row.update(status='running',argv=argv);write(out/'execution.json',report)
        try:
            with (out/(slot['label']+'.log')).open('x') as log:
                child=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                try:row['exit_code']=child.wait(timeout=slot['seconds']+240)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    try:child.wait(timeout=15)
                    except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
                    raise ValueError('outer timeout; inspect owned cleanup')
            created=set(base.glob('*'))-before
            if len(created)!=1:raise ValueError('ambiguous original run identity')
            run=created.pop();row['run']=str(run.relative_to(ROOT));data=json.loads((run/'run.json').read_text());row['harness_status']=data['status']
            if row['exit_code'] or data['status']!='passed':raise ValueError(data.get('error','original harness failed'))
            if data['image_reference']!=IMAGE or data.get('pcap_population_reconciled') is not True:raise ValueError('image/capture gate failed')
            if not data.get('provider_diagnostics') or not all(v['complete'] for v in data['provider_diagnostics'].values()):raise ValueError('provider diagnostics incomplete')
            if not all(sha(ROOT/p)==h for p,h in data['source_sha256'].items()):raise ValueError('run source changed')
            row['analysis']=analyze(data,run)
            if runtime!={p:sha(ROOT/p) for p in runtime}:raise ValueError('runtime changed during cohort')
            gate=row['analysis']['progress']['no_unresolved_attempts'] if args.progress_gate=='all-success' else row['analysis']['durable_outcomes']['complete']
            if not gate:raise ValueError('command progress failed; uncertainty retained')
            row['status']='passed'
        except Exception as error:row.update(status='failed',error=str(error));failed=True
        write(out/'execution.json',report);print(slot['label'],row['status'],row.get('error',''),flush=True)
    report['runtime_after']={p:sha(ROOT/p) for p in runtime};report['runtime_unchanged']=runtime==report['runtime_after'];write(out/'execution.json',report)
    return 1 if failed or not report['runtime_unchanged'] else 0


if __name__=='__main__':raise SystemExit(main())
