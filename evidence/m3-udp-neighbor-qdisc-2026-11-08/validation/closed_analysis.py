from pathlib import Path
import json,sys,subprocess,shutil
sys.path.insert(0,'tools')
from m3_source_preflight import ROOT,sha
from m3_udp_path_witness import common_witness
from m3_provider_stats import summarize_run
out=ROOT/'evidence/m3-udp-neighbor-qdisc-2026-11-08';dest=out/'analysis';dest.mkdir(exist_ok=False)
x=json.loads((out/'execution.json').read_text());hashes=json.loads((out/'local-artifact-hashes.json').read_text());summary=[]
for row in x['rows']:
 if 'run' not in row:continue
 label=row['slot']['label'];run=ROOT/row['run'];results={}
 for tool,suffix in [('m3_udp_path_analysis.py','path'),('m3_sensor_provider_analysis.py','sensor'),('m3_telemetry_diagnosis.py','telemetry')]:
  target=dest/(label+'-'+suffix+'.json');argv=[sys.executable,'tools/'+tool,'--run',row['run'],'--out',str(target)]
  if suffix in ('path','telemetry'):argv+=['--hash-manifest',str(out/'local-artifact-hashes.json')]
  p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True);results[suffix]=json.loads(target.read_text());print(label,suffix,p.returncode,p.stdout.strip(),p.stderr[-300:])
 path=results['path'];stats=summarize_run(run);joined=[];witnesses=[]
 for window in path.get('analysis',{}).get('windows',[]):
  control=path['analysis']['primary_control'];family='gaps' if window['family']=='adjacent_gap' else 'loss_windows'
  g=next(g for g in control[family] if g['window_ns']==window['window_ns'] and g['flow']==window['flow'])
  witness=dict(qualified=False,why='primary provider mapping withheld')
  if g.get('sender_identity') and g.get('sender_process'):
   witness=common_witness(window,stats[g['sender_process']]['records'],g['sender_identity'])
  witnesses.append(dict(family=window['family'],sender=window['sender'],window_ns=window['window_ns'],witness=witness))
  joined.append(dict(family=window['family'],sender=window['sender'],window_ns=window['window_ns'],flow=window['flow'],primary_classification=window['primary_classification'],stage_classification=window['stage_classification'],identity_stable=window['identity_stable'],provider_totals=None if window['provider'] is None else window['provider']['totals'],qdisc_totals=window['qdisc']['totals'],tc_pairs=len(window['qdisc']['pairs']),max_root_backlog=window['qdisc']['max_root_backlog_bytes'],max_root_qlen=window['qdisc']['max_root_qlen'],all_selected_source_control_observations=window['all_selected_source_control_observations'],neighbor_states={r:v['inside_states'] for r,v in window['neighbors'].items()},arp_counts=window['arp_counts'],common_interval_witness=witness))
 (dest/(label+'-common-interval.json')).write_text(json.dumps(witnesses,indent=2)+'\n')
 d=json.loads((run/'run.json').read_text());a=row.get('analysis',{})
 summary.append(dict(label=label,status=row['status'],harness_status=d['status'],audit=a.get('progress',{}).get('audit'),skipped=a.get('progress',{}).get('skipped_slots'),durable=a.get('durable_outcomes'),application=d.get('measurement_window'),analysis_status={k:v['status'] for k,v in results.items()},windows=joined))
for name,v in hashes.items():assert sha(ROOT/name)==v['sha256'],name
(dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
shutil.copy2(ROOT/'.local/m3-udp-path-build/common_interval.py',dest/'posthoc-witness-preparation.py')
(dest/'provenance.json').write_text(json.dumps(dict(frozen_live_source=x['source_commit'],posthoc_witness_source_sha256=sha(ROOT/'tools/m3_udp_path_witness.py'),posthoc_witness_added_after_closed_source_archive=True,original_raw_files_rehashed=len(hashes),source_runtime_tuning=False,scope='Common read-bracket witness strengthens comparison of positive provider increments with reported flat software-PASS counters; sampled neighbor/ARP remains association, no unique root cause or historic outcome authority'),indent=2)+'\n')
print('Closed analyses and original raw hashes verified')
