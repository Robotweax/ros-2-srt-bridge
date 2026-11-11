from pathlib import Path
import json,subprocess,sys
sys.path.insert(0,'tools')
from m3_source_preflight import ROOT,sha
out=ROOT/'evidence/m3-loaded-arp-eligibility-2026-11-09';dest=out/'analysis';dest.mkdir(exist_ok=False);x=json.loads((out/'execution.json').read_text());hashes=json.loads((out/'local-artifact-hashes.json').read_text());summary=[]
for row in x['rows']:
 if 'run' not in row:continue
 run=ROOT/row['run'];label=row['slot']['label'];results={}
 for tool,suffix in [('m3_loaded_arp_analysis.py','arp'),('m3_sensor_provider_analysis.py','sensor'),('m3_telemetry_diagnosis.py','telemetry')]:
  target=dest/(label+'-'+suffix+'.json');cmd=[sys.executable,'tools/'+tool,'--run',row['run'],'--out',str(target)]
  if suffix in ('arp','telemetry'):cmd+=['--hash-manifest',str(out/'local-artifact-hashes.json')]
  p=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True);results[suffix]=json.loads(target.read_text());print(label,suffix,p.returncode,p.stdout.strip(),p.stderr[-200:])
 d=json.loads((run/'run.json').read_text());a=row.get('analysis',{});joined=[]
 for w in results['arp'].get('analysis',{}).get('windows',[]):
  target=w['responder'];reply=w['reply_comparisons'][target];joined.append(dict(family=w['family'],requester=w['requester'],responder=target,window_ns=w['window_ns'],control_stage=w['control_stage'],control_primary_classification=w['control_primary_classification'],identity_stable=w['identity_stable'],neighbor_states={r:v['inside_states'] for r,v in w['neighbors'].items()},control_qdisc_totals=w['control_qdisc']['totals'],max_root_backlog=w['control_qdisc']['max_root_backlog_bytes'],max_root_qlen=w['control_qdisc']['max_root_qlen'],responder_reply_witness=reply['witness'],all_reply_role_witnesses={r:v['witness'] for r,v in w['reply_comparisons'].items()}))
 summary.append(dict(label=label,status=row['status'],harness_status=d['status'],command_audit=a.get('progress',{}).get('audit'),skipped=a.get('progress',{}).get('skipped_slots'),durable=a.get('durable_outcomes'),active_context_events=len(a.get('active_context_events',[])),application=d.get('measurement_window'),arp_lifetime_totals={r:{k:v['last']['counters'][k] for k in ('eligible','verdict')} for r,v in d.get('arp_reply_diagnostics',{}).items()},analysis_status={k:v['status'] for k,v in results.items()},windows=joined))
for name,v in hashes.items():assert sha(ROOT/name)==v['sha256'],name
(dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');(dest/'provenance.json').write_text(json.dumps(dict(frozen_live_source=x['source_commit'],analysis_source_sha256={n:sha(ROOT/'tools'/n) for n in ['m3_loaded_arp_analysis.py','m3_udp_path_analysis.py','m3_arp_reply_diagnostics.py','m3_sensor_provider_analysis.py','m3_telemetry_diagnosis.py']},raw_files_rehashed=len(hashes),runtime_unchanged=x['runtime_unchanged'],scope='Loaded observation only; all primary windows retained; no tuning/unique historical cause/nonexecution inference'),indent=2)+'\n');print('All original raw hashes and closed analyses verified')
