#!/usr/bin/env python3
"""One frozen, sequential N5 development diagnostic set; no retries or default changes."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
from m3_source_preflight import ROOT,IMAGE,sha,write
from m3_command_trace import summarize_run
from m3_dds_result_timeline import read_journal,common_clock
sys.path.insert(0,str(ROOT/'ros2/robotweax_srt_bridge_demo/scripts'))
from command_workload import audit_commands


SLOTS=[dict(label='srt-N0-preflight',group='srt',profile='N0',seconds=15),
       dict(label='srt-N5-progress',group='srt',profile='N5',seconds=60),
       dict(label='dds-system-simultaneous',group='dds',profile='N5',seconds=15,dds='system',startup='simultaneous'),
       dict(label='dds-system-control-first',group='dds',profile='N5',seconds=15,dds='system',startup='control-first'),
       dict(label='dds-paced-simultaneous',group='dds',profile='N5',seconds=15,dds='paced-sensors',startup='simultaneous')]
RUNTIMES=['install/m3-ros/robotweax_srt_bridge/lib/robotweax_srt_bridge/'+p for p in ('bridge_node','ros_rate_worker','dds_command_node')]+['install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo/rate_simulator','install/bridge-m3/bin/robotweax-journal-worker','install/bridge-m3/lib/librobotweax_srt_bridge_endpoint.a','install/bridge-m3/lib/librobotweax_srt_bridge_transport.a','install/srt-m0/lib/librobotweax-srt.a']


def timeline(path):
    rows=[json.loads(s) for s in path.read_text().splitlines()]
    if not rows or rows[-1].get('kind')!='status':raise ValueError('missing timeline footer')
    status=rows.pop()
    if status.get('exhausted') is not False:raise ValueError('timeline budget exhausted or unspecified')
    if status['recorded']!=len(rows) or not 0<len(rows)<=status['limit']<=2048:raise ValueError('timeline population mismatch')
    stamps=[r['monotonic_ns'] for r in rows]
    if stamps!=sorted(stamps) or any(r.get('kind')!='snapshot' for r in rows):raise ValueError('invalid timeline ordering')
    states=[r for r in rows if r['command'] is not None]
    def first(predicate):
        return next((r['monotonic_ns'] for r in states if predicate(r['command'])),None)
    matched=first(lambda s:s['control_publishers']>0 and s['control_subscribers']>0 and s['hello_publishers']>0 and s['hello_subscribers']>0)
    hello=first(lambda s:s['hellos_received']>0);ready=first(lambda s:s['ready'])
    # Absence is limited to sampled local diagnostics; never a network-cause proof.
    classification=('ready_observed' if ready else 'no_command_diagnostics' if not states else 'no_complete_endpoint_match_observed' if not matched else 'no_received_hello_observed' if not hello else 'hello_received_but_not_ready')
    return dict(records=len(rows),first_ns=stamps[0],last_ns=stamps[-1],first_complete_match_ns=matched,first_received_hello_ns=hello,first_ready_ns=ready,classification=classification,last=rows[-1],phases=list(dict.fromkeys(r['phase'] for r in rows)),scope='sampled local diagnostic history; endpoint counts and HELLO callbacks, not RTPS packet parsing or unique discovery failure cause')


def command_progress(report,run):
    result=report['results'];rows=result['commands'];begin=result['checkpoints']['begin']['device']
    final=result.get('final_device',result.get('device'))
    # Legacy SRT rows omit the false flag for observations before cutoff. Keep
    # original rows intact; a missing true flag after cutoff still fails audit.
    normalized=[dict(r,observed_after_data_cutoff=r.get('observed_after_data_cutoff',False)) for r in rows]
    audit=audit_commands(normalized,begin,final,cutoff_ns=result['command_data_cutoff_monotonic_ns'])
    common_clock(report['clock_namespace_proof'])
    sender=read_journal(run/'operator.sqlite',1);receiver=read_journal(run/'robot.sqlite',2)
    dds='dds_transport_profile' in report
    traces={} if dds else summarize_run(run)
    proof=[]
    for row in rows:
        id=row['number'].to_bytes(16,'little').hex();a=sender['entries'].get(id);b=receiver['entries'].get(id)
        handoffs=None if dds else sum(e['point']==25 and e['request']==id for n,t in traces.items() if n.startswith('operator-') for e in t['events'])
        if handoffs is not None and handoffs>1:raise ValueError('accepted command replay observed')
        if row.get('terminal')==4:
            if not a or not b or any(a[k]!=b[k] for k in ('state','reason','revision','route','payload_hash','source_epoch','source_ns','session','result_valid','result_generation')):raise ValueError('confirmed result journal mismatch')
            if a['state']!=4 or not a['result_valid'] or a['result_generation']!=row['new_generation']:raise ValueError('invalid durable success')
            if a['deadline_ns']!=a['source_ns']+5_000_000_000 or b['deadline_ns']>a['deadline_ns'] or not b['source_ns']<b['dispatched_ns']<b['deadline_ns']:raise ValueError('original deadline or dispatch proof mismatch')
            if handoffs is not None and handoffs!=1:raise ValueError('missing unique SDK handoff')
        proof.append(dict(number=row['number'],terminal=row.get('terminal'),sdk_handoffs=handoffs,sender=a,receiver=b))
    stamps=[r['submitted_monotonic_ns'] for r in rows]
    if stamps!=sorted(stamps):raise ValueError('intent observation time regressed')
    return dict(audit=audit,skipped_slots=result['skipped_command_slots'],maximum_adjacent_intent_gap_ms=max((b-a for a,b in zip(stamps,stamps[1:])),default=0)/1e6,
        no_unresolved_attempts=audit['all_succeeded'],entries=proof,command_traces={n:dict(records=t['records'],complete=t['complete']) for n,t in traces.items()},
        scope='all attempts, skipped slots and matching closed journal proof; UNKNOWN/unresolved retained; no latency bound, full N5 or transport superiority claim')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    inventory={p:sha(ROOT/p) for p in RUNTIMES}
    if inventory['install/srt-m0/lib/librobotweax-srt.a']!=json.loads((ROOT/'baselines/dependencies.json').read_text())['srt']['installed_library_sha256']:raise ValueError('provider archive pin mismatch')
    report=dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,runtime_before=inventory,slots=SLOTS,rows=[],qualification=False)
    write(out/'execution.json',report);srt_blocked=False
    for slot in SLOTS:
        row=dict(slot=slot,status='not_executed');report['rows'].append(row)
        if slot['group']=='srt' and srt_blocked:
            row['why']='SRT preflight failure';write(out/'execution.json',report);continue
        script='tools/run_m3.py' if slot['group']=='srt' else 'tools/run_m3_dds.py'
        base=ROOT/('.local/m3' if slot['group']=='srt' else '.local/m3-dds-combined');before=set(base.glob('*'))
        argv=[sys.executable,script,'--profile',slot['profile'],'--seed','1701','--seconds',str(slot['seconds']),'--skip-build']
        if slot['group']=='srt':argv+=['--command-diagnostics','--provider-diagnostics','--capture-drain-check']
        else:argv+=['--commands','--dds-profile',slot['dds'],'--startup',slot['startup']]
        row.update(status='running',argv=argv,started_ns=time.monotonic_ns());write(out/'execution.json',report)
        try:
            with (out/(slot['label']+'.log')).open('x') as log:
                child=subprocess.Popen(argv,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
                try:row['exit_code']=child.wait(timeout=slot['seconds']+240)
                except subprocess.TimeoutExpired:
                    child.terminate()
                    try:child.wait(timeout=15)
                    except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
                    raise ValueError('outer run timeout; inspect owned namespace cleanup')
            created=set(base.glob('*'))-before
            if len(created)!=1:raise ValueError('ambiguous run identity')
            run=created.pop();row['run']=str(run.relative_to(ROOT));data=json.loads((run/'run.json').read_text());row['harness_status']=data['status']
            if data['image_reference']!=IMAGE:raise ValueError('unexpected runtime image')
            if slot['group']=='dds':
                row['startup']={}
                for role in ('operator','robot'):
                    try:row['startup'][role]=timeline(run/(role+'-startup-timeline.jsonl'))
                    except Exception as error:row['startup'][role]=dict(error=str(error))
                row['shutdown']={f.name:json.loads(f.read_text()) for f in run.glob('*-shutdown.json')}
                expected={'robot-simulator-shutdown.json','robot-command-shutdown.json','operator-command-shutdown.json'}
                if any('error' in item for item in row['startup'].values()):raise ValueError('DDS timeline incomplete')
                if set(row['shutdown'])!=expected or not all(s['passed'] for s in row['shutdown'].values()):raise ValueError('DDS child shutdown incomplete')
            if row['exit_code'] or data['status']!='passed':raise ValueError(data.get('error','harness failed'))
            row['progress']=command_progress(data,run)
            if not row['progress']['no_unresolved_attempts']:raise ValueError('command progress has unresolved or unsuccessful attempts')
            if inventory!={p:sha(ROOT/p) for p in inventory}:raise ValueError('runtime changed')
            row['status']='passed'
        except Exception as error:
            row.update(status='failed',error=str(error))
            if slot['label']=='srt-N0-preflight':srt_blocked=True
        row['finished_ns']=time.monotonic_ns();write(out/'execution.json',report);print(slot['label']+': '+row['status'],flush=True)
    report['runtime_after']={p:sha(ROOT/p) for p in inventory};report['runtime_unchanged']=report['runtime_after']==inventory;write(out/'execution.json',report)


if __name__=='__main__':main()
