from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys
sys.path.insert(0,'tools')
from m3_observer_study import source_inventory,installed_inventory,extract
from m3_dds_result_timeline import read_journal
root=Path.cwd();out=root/'.local/srt-n5-fixed/20261106-traced';out.mkdir(parents=True,exist_ok=False)
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def scripts():
 result={}
 for p in Path('ros2/robotweax_srt_bridge_demo/scripts').glob('*.py'):
  q=Path('install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo')/p.name
  if q.exists():
   assert p.read_bytes()==q.read_bytes(),str(p);result[str(q)]=hashlib.sha256(q.read_bytes()).hexdigest()
 return result
slots=[dict(label='srt-N5-'+str(seed),group='srt',phase='long',profile='N5',seed=seed,seconds=300,observer=True,command_diagnostics=True,recorder_diagnostics=True) for seed in (1701,2903,4211)]
plan=dict(created_utc=datetime.now(timezone.utc).isoformat(),base_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),runtime_fix_commit='899a6eb',source_sha256=source_inventory(),installed_sha256=installed_inventory(),installed_scripts=scripts(),slots=slots,criteria=dict(harness_pass=True,source_and_binary_inventory_constant=True,competitor_liveness_and_offer=True,source_enabled_seconds_at_least=300,native_v2_and_cgroup_windows_qualified=True,pcap_kernel_drops=0,command_trace_complete=True,unresolved_unknown_nonadmitted=0,allowed_terminal_states=['SUCCEEDED with matching device effect/generation','receiver-backed EXPIRED/start_deadline without dispatch'],closed_journal_agreement=True),scope='new fixed-runtime three-repetition SRT N5 cohort with explicit command/recorder observers; labels are not random-loss samples; zero stochastic impairment; sequential fresh owned labs; fail-fast, no retries/replacement/tuning; does not close realtime/physical/complete M3 or establish transport cost/superiority',complete_m3_acceptance=False)
for p,h in plan['source_sha256'].items():assert hashlib.sha256(subprocess.check_output(['git','show',plan['base_commit']+':'+p])).hexdigest()==h,p
dump(out/'plan.json',plan);result=dict(status='running',rows=[]);dump(out/'study.json',result)
try:
 for slot in slots:
  assert source_inventory()==plan['source_sha256'] and installed_inventory()==plan['installed_sha256'] and scripts()==plan['installed_scripts']
  with (out/(slot['label']+'.log')).open('w') as log:code=subprocess.call([sys.executable,'tools/run_m3.py','--profile','N5','--seed',str(slot['seed']),'--seconds','300','--skip-build','--monotonic-capture','--command-diagnostics','--recorder-diagnostics'],stdout=log,stderr=subprocess.STDOUT)
  paths=[Path(line) for line in (out/(slot['label']+'.log')).read_text().splitlines() if line.startswith(str(root/'.local/')) and (Path(line)/'run.json').exists()]
  assert paths,'missing child manifest';run=paths[-1];r=json.loads((run/'run.json').read_text());row=dict(slot=slot,run=str(run.relative_to(root)),exit_code=code,harness_status=r['status'],status='checking');result['rows'].append(row);dump(out/'study.json',result)
  assert not code and r['status']=='passed',r.get('capture_error',r.get('error',r.get('command_diagnostics_error','harness failed')))
  assert r['source_sha256']==plan['source_sha256'] and source_inventory()==plan['source_sha256'] and installed_inventory()==plan['installed_sha256'] and scripts()==plan['installed_scripts']
  assert r['command_diagnostics_enabled'] and r['recorder_diagnostics_enabled'] and all(t['complete'] for t in r['command_diagnostics'].values())
  assert r['results']['measured_seconds']>=300 and (r['results']['publication_interval']['pause_monotonic_ns']-r['results']['publication_interval']['resume_monotonic_ns'])>=300000000000
  assert r['competitor_check']['alive_poll_checks']>0 and r['competitor_check']['target_bitrate']==128000
  c=r['command_summary'];assert c['attempts']>0 and c['not_admitted']==c['unresolved']==0,'unresolved/nonadmitted command gate'
  sender=read_journal(run/'operator.sqlite',1);receiver=read_journal(run/'robot.sqlite',2);assert sender['entries'].keys()==receiver['entries'].keys(),'journal IDs differ'
  successes=0;expired=0
  for id,a in sender['entries'].items():
   b=receiver['entries'][id];assert all(a[k]==b[k] for k in ('route','payload_hash','state','reason','revision','result_valid','result_generation')),'journal status mismatch'
   if a['state']==4:assert a['revision']==3 and a['result_valid'];successes+=1
   else:assert a['state']==7 and a['reason']==3 and not a['result_valid'] and b['dispatched_ns']==0,'unexpected/uncertain terminal';expired+=1
  assert successes==r['results']['device']['effects']==r['results']['device']['generation'] and successes+expired==c['attempts']
  row.update(status='passed',confirmed_successes=successes,receiver_expiries_without_dispatch=expired,metrics=extract(r,slot));dump(out/'study.json',result);print(slot['label'],'passed',successes,'successes',expired,'expiries',run,flush=True)
 result['status']='passed'
except BaseException as error:
 if result['rows'] and result['rows'][-1]['status']=='checking':result['rows'][-1]['status']='failed'
 result.update(status='failed',error=str(error));dump(out/'study.json',result);raise
finally:dump(out/'study.json',result)
