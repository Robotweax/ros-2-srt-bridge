from pathlib import Path
import hashlib,json,shutil,subprocess,sys
sys.path.insert(0,'tools')
from m3_observer_study import source_inventory,installed_inventory
from m3_dds_result_timeline import read_journal
from m3_accounting import summarize_window
from m3_window_measurement import read_samples,summarize_cgroup
ROOT=Path.cwd();DEV=Path('.local/n5-cause-repro-dev');OUT=Path('evidence/m3-n5-close-cause-2026-11-06')
plan=json.loads((DEV/'plan.json').read_text());paths=[Path(l) for l in (DEV/'run.log').read_text().splitlines() if l.startswith(str(ROOT/'.local/')) and (Path(l)/'run.json').exists()];assert len(paths)==1
run=paths[0];r=json.loads((run/'run.json').read_text());assert r['status']!='running'
assert source_inventory()==plan['source_sha256']==r['source_sha256'] and installed_inventory()==plan['installed_sha256']
for p,h in plan['source_sha256'].items():assert hashlib.sha256(subprocess.check_output(['git','show',plan['source_commit']+':'+p])).hexdigest()==h
OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
shutil.copy2(DEV/'plan.json',OUT/'plan.json');shutil.copy2(DEV/'archive.py',OUT/'archive.py')
for name in ['run.json','operator-result.json','measurement-start.json','robot-final-device-state.json']+[p.name for p in run.glob('*-bridge-*.log')]:
 if (run/name).exists():shutil.copy2(run/name,OUT/name)
for role in ('robot','operator'):
 for suffix in ('-capture.log','-monotonic-capture.log','-recorder-samples.jsonl','-recorder-ready.json','-recorder-diagnostics.log','-final-bridge-state.json','-scenario.log'):
  p=run/(role+suffix)
  if p.exists():shutil.copy2(p,OUT/p.name)
 for name in ('profile-'+role+'-readback.log','before-'+role+'.log','after-'+role+'.log'):
  if (run/name).exists():shutil.copy2(run/name,OUT/name)
write(OUT/'raw-sha256.json',{p.name:dict(bytes=p.stat().st_size,sha256=sha(p)) for p in run.iterdir() if p.is_file() and ('.pcap' in p.name or p.suffix in ('.mono','.sqlite','.jsonl'))})
result=r.get('results');summary=dict(harness_status=r['status'],errors={k:v for k,v in r.items() if k.endswith('error')},qualification=False,complete_m3_acceptance=False)
if result:
 start=json.loads((run/'measurement-start.json').read_text())['monotonic_ns'];cutoff=result['command_data_cutoff_monotonic_ns']
 events=[dict(log=name,**e) for name,t in r['command_diagnostics'].items() for e in t['events']]
 active=sorted([e for e in events if start<=e['monotonic_ns']<cutoff and e['point'] in (28,30,31)],key=lambda e:e['monotonic_ns'])
 summary.update(command_window_ns=[start,cutoff],active_window_close_events=active,reset_observed=bool(active),command_summary=r['command_summary'],effects=result['device']['effects'],skipped=result['skipped_command_slots'],trace_counts={name:dict(records=t['records'],attempted=t['attempted'],dropped=t['dropped'],complete=t['complete'],counts=t['counts']) for name,t in r['command_diagnostics'].items()},pcap_drops={role:c['tcpdump_kernel_drops'] for role,c in r['captures'].items()})
 journals={role:read_journal(run/(role+'.sqlite'),side) for role,side in (('operator',1),('robot',2))};write(OUT/'journals.json',journals)
 a=journals['operator']['entries'];b=journals['robot']['entries'];summary['sender_only']=sorted(a.keys()-b.keys());summary['sender_unknown']=[id for id,e in a.items() if e['state']==8]
 common=a.keys()&b.keys();summary['status_divergences']=[id for id in common if any(a[id][k]!=b[id][k] for k in ('state','reason','revision','result_valid','result_generation'))]
 assert summarize_window(result['checkpoints']['begin'],result['checkpoints']['end'],result['publication_interval'])==r['measurement_window'];summary['measurement']=r['measurement_window']
 replayed=0
 for role in ('robot','operator'):
  rows=[dict(begin_ns=s['begin_ns'],end_ns=s['end_ns'],cgroup=s['cgroup']) for s in read_samples(run/(role+'-endpoint-samples.jsonl'))]
  (OUT/(role+'-cgroup-samples.jsonl')).write_text(''.join(json.dumps(s)+'\n' for s in rows))
  for phase,w in r['endpoint_measurements']['windows'].items():assert summarize_cgroup(rows,*w['monotonic_ns'])==w['container_cgroup'][role];replayed+=1
 summary['cgroup_windows_replayed']=replayed
write(OUT/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k not in ('trace_counts','measurement')},indent=2))
