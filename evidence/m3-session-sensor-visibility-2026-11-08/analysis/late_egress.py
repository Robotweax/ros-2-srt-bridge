from pathlib import Path
import json,sys,hashlib
sys.path.insert(0,'tools')
from m3_monotonic_capture import records
from m3_control_liveness import parse_control
from m3_control_provider_liveness import same_flow
from m3_command_trace import summarize_run
root=Path.cwd();out=root/'evidence/m3-session-sensor-visibility-2026-11-08';analysis=out/'analysis';run=root/'.local/m3/20261108T195455144739Z'
manifest=json.loads((out/'local-artifact-hashes.json').read_text());paths=[run/'run.json',run/'network.json',run/'operator.mono',run/'robot.mono',*run.glob('*-bridge-*.log')]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p in paths:assert sha(p)==manifest[str(p.relative_to(root))]['sha256']
d=json.loads((run/'run.json').read_text());c=json.loads((analysis/'srt-N5-2903-control.json').read_text())['analysis'];loss=next(v for v in c['loss_windows'] if v['process'].startswith('robot-'));assert loss['classification']=='selected_send_counters_increased_without_old_flow_egress_observation'
flow=loss['flow'];rows=d['provider_diagnostics'][loss['sender_process']]['records'];identity=loss['sender_identity']
def matching(r):return [r['owner_epoch'],r['generation'],r['socket']]==identity
closes=[r for r in rows if r['before_close'] and matching(r)];assert len(closes)==1;close=closes[0]
unavailable=next((r for r in rows if r['begin_ns']>close['end_ns'] and r['socket']==-1),None)
addresses=json.loads((run/'network.json').read_text())['addresses'];parsed={}
for role in ('operator','robot'):
 mtu=d['monotonic_captures']['statuses'][role]['mtu'];items=[]
 for r in records(run/(role+'.mono')):
  p=parse_control(r,addresses[role],mtu)
  if p and same_flow(p,flow):items.append(p)
 parsed[role]=items
source_after=[r for r in parsed['operator'] if r['monotonic_ns']>close['end_ns']];peer_after=[r for r in parsed['robot'] if r['monotonic_ns']>close['end_ns']]
first_native_after_unavailable=next((r for r in source_after if unavailable and r['monotonic_ns']>unavailable['end_ns']),None)
traces=summarize_run(run);request=(12).to_bytes(16,'little').hex();events={n:[e for e in t['events'] if e['request']==request and (e['point']==25 or e['detail']==6)] for n,t in traces.items()};assert sum(e['point']==25 for n,v in events.items() if n.startswith('operator-') for e in v)==1
value=dict(run=str(run.relative_to(root)),flow=flow,loss_window_ns=loss['window_ns'],quiet_ns=loss['quiet_ns'],provider_totals_inside_quiet=loss['provider']['totals'],fully_contained_provider_pairs=len(loss['provider']['adjacent_pairs']),source_and_peer_observations_inside_quiet=[loss['source_old_flow_observations'],loss['peer_old_flow_observations']],sender_before_close=close,first_sender_no_socket_sample_after_close=unavailable,first_old_flow_source_observations_after_close=source_after[:12],old_flow_source_observations_after_close=len(source_after),old_flow_peer_observations_after_close=len(peer_after),first_source_observation_after_no_socket_sample=first_native_after_unavailable,unresolved_original_command_events=events,raw_sha256={str(p.relative_to(root)):sha(p) for p in paths},scope='Before-close end is not exact srt_close return. A later no-socket sample is a transport observation; emitted old-tuple datagrams after it are not new SDK command handoffs. Captures prove local observation order only, no unique qdisc/neighbor/socket cause or typed encrypted COMMAND mapping. Original and new unresolved intents stay unresolved; no replay or negative outcome inferred.')
for p in paths:assert sha(p)==manifest[str(p.relative_to(root))]['sha256']
p=analysis/'late-egress.json';assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n')
print('close bracket',close['begin_ns'],close['end_ns'],'state',close['state_before'],close['state_after']);print('no_socket bracket',None if unavailable is None else [unavailable['begin_ns'],unavailable['end_ns']]);print('old flow after close',len(source_after),len(peer_after));print('first after no_socket',first_native_after_unavailable)
