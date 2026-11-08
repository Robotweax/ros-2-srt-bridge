from pathlib import Path
import json,sys,hashlib
sys.path.insert(0,'tools')
from m3_command_trace import summarize_run
from m3_provider_stats import summarize_run as providers
from m3_dds_result_timeline import common_clock
from m3_control_fault_analysis import inside_deltas,connection
root=Path.cwd();run=root/'.local/m3/20261108T192149714504Z';evidence=root/'evidence/m3-broader-seeds-telemetry-2026-11-08';manifest=json.loads((evidence/'local-artifact-hashes.json').read_text())
inputs=[run/'run.json',*run.glob('*-bridge-*.log')]
for p in inputs:assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest[str(p.relative_to(root))]['sha256']
report=json.loads((run/'run.json').read_text());common_clock(report['clock_namespace_proof']);t=summarize_run(run);stats=providers(run)
session='94fc4d3a15073966520f294726d45599';request=(98).to_bytes(16,'little').hex()
hand=[dict(file=n,**e) for n,v in t.items() if n.startswith('operator-') for e in v['events'] if e['point']==25 and e['request']==request];assert len(hand)==1
begin=hand[0]['monotonic_ns']
loss={}
for role in ('operator','robot'):
 events=[dict(file=n,**e) for n,v in t.items() if n.startswith(role+'-') for e in v['events'] if e['point']==31 and e['detail']==0 and e['session']==session and e['monotonic_ns']>begin]
 loss[role]=min(events,key=lambda e:e['monotonic_ns'])
selected={}
for role in ('operator','robot'):
 name=loss[role]['file'];records=stats[name]['records'];available=[r for r in records if r['available'] and r['session']==session and r['end_ns']<=begin];baseline=available[-1];ident=connection(baseline)
 selected[role]=dict(process=name,identity=list(ident),baseline=baseline,until_robot_loss=inside_deltas(records,ident,begin,loss['robot']['monotonic_ns']),robot_to_operator_loss=inside_deltas(records,ident,loss['robot']['monotonic_ns'],loss['operator']['monotonic_ns']),last_available_old_identity=next(r for r in reversed(records) if r['available'] and connection(r)==ident),all_before_close=[r for r in records if r['before_close'] and connection(r)==ident])
d=dict(run=str(run.relative_to(root)),original_progress=json.loads((evidence/'summary.json').read_text())[-1]['command_audit'],handoff=hand[0],control_loss=loss,provider=selected,original_monotonic_capture_available='monotonic_captures' in report,scope='Same proven VM clock, original SDK handoff and CONTROL identity snapshots. Counters exclude some UDP types; partial read deltas are not exact packet emission. No original kernel-monotonic capture, exact terminal break reason or unique causal mapping. Original intent98 stays unresolved; no replay/expiry/nonexecution inferred.')
p=root/'.local/m3-session-sensor-build/original-2903-analysis.json';p.write_text(json.dumps(d,indent=2)+'\n')
for role,v in selected.items():
 print(role, {k:dict(pairs=len(v[k]['adjacent_pairs']),totals=v[k]['totals']) for k in ['until_robot_loss','robot_to_operator_loss']})
