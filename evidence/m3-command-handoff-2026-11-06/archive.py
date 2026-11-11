from pathlib import Path
import hashlib,json,shutil,subprocess,sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_dds_result_timeline import read_journal
from m3_command_trace import summarize_run
OUT=ROOT/'evidence/m3-command-handoff-2026-11-06';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
for name in ('development-plan.json','post-fix-plan.json','historical-owners.json','post-fix-execution.json','pre-fix-regression.log','fixed-build-tests.log','final-build-tests.log','python-tests-fixed.log','check_regression.py'):
 shutil.copy2(ROOT/'.local/command-trace-dev'/name,OUT/name)
rows=[]
post=json.loads((ROOT/'.local/command-trace-dev/post-fix-plan.json').read_text())
binding=json.loads((ROOT/'.local/command-trace-dev/post-fix-execution.json').read_text())
assert sha(ROOT/'.local/command-trace-dev/post-fix-plan.json')==binding['plan_sha256']
for label,stamp,commit in [('pre-fix','20261106T171724529229Z','381dfa8'),('post-fix',binding['run_stamp'],post['source_commit'])]:
 run=ROOT/'.local/m3'/stamp;r=json.loads((run/'run.json').read_text());assert r['status']!='running'
 target=OUT/label;target.mkdir(exist_ok=True)
 for path,digest in r['source_sha256'].items():assert hashlib.sha256(subprocess.check_output(['git','show',commit+':'+path])).hexdigest()==digest,path
 names=['run.json','operator-result.json','robot-final-device-state.json','measurement-start.json']
 for role in ('robot','operator'):
  names += [role+s for s in ('-capture.log','-monotonic-capture.log','-recorder-samples.jsonl','-recorder-ready.json','-recorder-diagnostics.log','-final-bridge-state.json','-scenario.log')]
 names += [p.name for p in run.glob('*-bridge-*.log')]
 for name in names:
  if (run/name).exists():shutil.copy2(run/name,target/name)
 traces=summarize_run(run);write(target/'trace-reanalysis.json',traces)
 sender=read_journal(run/'operator.sqlite',1);receiver=read_journal(run/'robot.sqlite',2)
 common=sender['entries'].keys()&receiver['entries'].keys()
 divergent=[]
 for id in common:
  a=sender['entries'][id];b=receiver['entries'][id]
  assert a['payload_hash']==b['payload_hash'] and a['route']==b['route']
  if any(a[k]!=b[k] for k in ('state','reason','revision','result_valid','result_generation')):divergent.append(id)
 journal=dict(sender=sender,receiver=receiver,common=len(common),divergent=divergent,sender_only=sorted(sender['entries'].keys()-receiver['entries'].keys()),scope='closed immutable SQLite reads; raw hashes stable; absence/UNKNOWN do not prove nonexecution')
 write(target/'journal-audit.json',journal)
 write(target/'raw-sha256.json',{p.name:sha(p) for p in run.iterdir() if p.is_file() and ('.pcap' in p.name or p.suffix in ('.mono','.sqlite') or p.name.endswith(('-endpoint-samples.jsonl','-clock-samples.jsonl','-resources.jsonl')))})
 cutoff=r['results']['command_data_cutoff_monotonic_ns']
 rows.append(dict(label=label,source_commit=commit,harness_status=r['status'],original_diagnostic_error=r.get('command_diagnostics_error'),command_summary=r['command_summary'],skipped=r['results']['skipped_command_slots'],cutoff_ns=cutoff,trace_incarnations=len(traces),all_traces_complete=all(v['complete'] for v in traces.values()),points={name:sum(v['counts'].get(name,0) for v in traces.values()) for name in ('clock_deferred','make_rejected','provider_sent','worker_unknown','invalidate_requested')},clock_events=[e for v in traces.values() for e in v['events'] if e['point'] in (22,29)],sender_only=journal['sender_only'],sender_unknown=[id for id,e in sender['entries'].items() if e['state']==8],receiver_successes=sum(e['state']==4 for e in receiver['entries'].values()),pcap_drops={role:c['tcpdump_kernel_drops'] for role,c in r['captures'].items()},scope='separate development cases; pre-fix manifest remains failed, not replaced or reclassified; no full N5/M3 acceptance'))
write(OUT/'outcomes.json',rows)
shutil.copy2(ROOT/'.local/command-trace-dev/archive.py',OUT/'archive.py')
print(json.dumps([{k:r[k] for k in ('label','harness_status','receiver_successes','sender_unknown','points','pcap_drops')} for r in rows],indent=2))
