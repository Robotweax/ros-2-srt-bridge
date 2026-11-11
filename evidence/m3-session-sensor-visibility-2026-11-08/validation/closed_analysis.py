from pathlib import Path
import json,subprocess,sys,shutil,hashlib
sys.path.insert(0,'tools')
from m3_control_provider_liveness import analyze as control
from m3_source_preflight import ROOT,sha
out=ROOT/'evidence/m3-session-sensor-visibility-2026-11-08';dest=out/'analysis';dest.mkdir(exist_ok=False)
execution=json.loads((out/'execution.json').read_text());hashes=json.loads((out/'local-artifact-hashes.json').read_text());summary=[]
for row in execution['rows']:
 if 'run' not in row:continue
 run=ROOT/row['run'];label=row['slot']['label'];d=json.loads((run/'run.json').read_text());results={}
 for tool,suffix in [('m3_sensor_provider_analysis.py','sensor'),('m3_telemetry_diagnosis.py','telemetry')]:
  target=dest/(label+'-'+suffix+'.json');argv=[sys.executable,'tools/'+tool,'--run',row['run'],'--out',str(target)]
  if suffix=='telemetry':argv+=['--hash-manifest',str(out/'local-artifact-hashes.json')]
  p=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True);results[suffix]=json.loads(target.read_text());print(label,suffix,p.returncode,p.stdout.strip(),p.stderr[-200:])
 target=dest/(label+'-control.json')
 try:value=dict(status='passed',analysis=control(run))
 except Exception as e:value=dict(status='failed',error=str(e))
 target.write_text(json.dumps(value,indent=2)+'\n');results['control']=value
 print(label,'control',value['status'])
 sensor=results['sensor'];compact={}
 for process,v in sensor.get('analysis',{}).get('processes',{}).items():
  compact[process]=[dict(identity=g['identity'],sessions=g['sessions'],contained_pairs=g['contained_pairs'],contained_first_read_ns=g['contained_first_read_ns'],contained_last_read_ns=g['contained_last_read_ns'],partial_window_totals=g['contained_pair_totals'],lifetime_last_cumulative=g['last_cumulative'],gauges_minmax=g['gauges'],before_close_records=g['before_close_records']) for g in v['connections']]
 c=value.get('analysis',{});summary.append(dict(label=label,status=row['status'],harness_status=d['status'],command_audit=row.get('analysis',{}).get('progress',{}).get('audit'),skipped=row.get('analysis',{}).get('progress',{}).get('skipped_slots'),durable=row.get('analysis',{}).get('durable_outcomes'),application=d.get('measurement_window'),sensor_processes=compact,control_summary=dict(gaps=len(c.get('gaps',[])),active_control_events=len(c.get('active_control_events',[])),loss_windows=c.get('loss_windows',[])),analysis_status={k:v['status'] for k,v in results.items()}))
# Guard every original input after all closed analyses, not only selected pcap.
for name,v in hashes.items():assert sha(ROOT/name)==v['sha256'],name
(dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for name in ['original-2903-analysis.json','original_2903.py']:
 shutil.copy2(ROOT/'.local/m3-session-sensor-build'/name,dest/name)
metadata=dict(frozen_live_source=execution['source_commit'],original_raw_files_reverified=len(hashes),provider_unchanged=True,analysis_source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'tools/m3_sensor_provider_analysis.py',ROOT/'tools/m3_control_provider_liveness.py',ROOT/'tools/m3_telemetry_diagnosis.py']},limits='No unique old/new cause or full M3 acceptance. Partial provider deltas and whole captures remain separate populations; no historic replay/expiry/nonexecution.')
(dest/'provenance.json').write_text(json.dumps(metadata,indent=2)+'\n');print('Closed original hashes and analysis lineage verified')
