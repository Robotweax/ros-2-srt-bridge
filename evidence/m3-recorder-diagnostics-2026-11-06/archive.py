from pathlib import Path
import hashlib,json,shutil,subprocess,sys
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'.local/v2-observer-study-dev'))
from audit_journals import audit
OUT=ROOT/'evidence/m3-recorder-diagnostics-2026-11-06'
OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
plan=json.loads((ROOT/'.local/srt-n5-v2/20261106-retention256/plan.json').read_text())
installed={k:sha(ROOT/k) for k in plan['installed_sha256']}
assert installed==plan['installed_sha256']
write(OUT/'selected-installed-sha256.json',dict(sha256=installed,scope='eight selected installed files unchanged from original frozen N5 plan; checked after development runs, not a new preregistered qualification cohort'))
controls=ROOT/'.local/recorder-diagnostics-dev/control-final'
shutil.copy2(controls/'run.json',OUT/'recorder-controls.json')
for case in ('baseline','pause'):
 target=OUT/('control-'+case);target.mkdir(exist_ok=True)
 for name in ('result.json','capture.log','samples.jsonl','observer.log'):
  shutil.copy2(controls/case/name,target/name)
 write(target/'raw-sha256.json',{str(p.relative_to(controls/case)):sha(p) for p in (controls/case).glob('probe.pcap*')})
cohorts=[]
for label,stamp,commit in [('n5-60-no-history','20261106T164322627870Z','013927f'),('n5-30-with-history','20261106T164650591243Z','56b7b8a')]:
 run=ROOT/'.local/m3'/stamp;r=json.loads((run/'run.json').read_text());assert r['status']!='running'
 for name,digest in r['source_sha256'].items():
  original=subprocess.check_output(['git','show',commit+':'+name])
  assert hashlib.sha256(original).hexdigest()==digest,(label,name)
 target=OUT/label;target.mkdir(exist_ok=True)
 names=['run.json','operator-result.json','robot-final-device-state.json','measurement-start.json']
 for role in ('robot','operator'):
  names += [role+s for s in ('-capture.log','-monotonic-capture.log','-recorder-samples.jsonl','-recorder-ready.json','-recorder-diagnostics.log','-final-bridge-state.json','-scenario.log')]
 for name in names:
  if (run/name).exists():shutil.copy2(run/name,target/name)
 journals=audit(run);write(target/'closed-journal-audit.json',journals)
 write(target/'raw-sha256.json',{p.name:sha(p) for p in run.iterdir() if p.is_file() and ('.pcap' in p.name or p.suffix in ('.mono','.sqlite') or p.name.endswith(('-endpoint-samples.jsonl','-clock-samples.jsonl','-resources.jsonl')))})
 commands=r['results']['commands'];unknown=[id for id,e in journals['roles']['operator']['entries'].items() if e['state']==8]
 poll_summaries=[dict(number=c['number'],status_observations=c.get('status_observations'),omitted=c.get('status_observations_omitted',0),first=c.get('status_observation_history',[None])[0],last=c.get('last_status_observation'),terminal=c.get('terminal')) for c in commands]
 cohorts.append(dict(label=label,source_commit=commit,harness_status=r['status'],command_summary=r['command_summary'],sender_unknown_ids=unknown,sender_only=journals['sender_only'],receiver_successes=journals['receiver_successes'],poll_summaries=poll_summaries,pcap={role:dict(records=c['records'],kernel_drops=c['tcpdump_kernel_drops']) for role,c in r.get('captures',{}).items()},recorder_diagnostics=r.get('recorder_diagnostics'),scope='development observations, not a replacement N5 qualification; unresolved intents retain uncertainty'))
write(OUT/'development-outcomes.json',cohorts)
shutil.copy2(ROOT/'.local/recorder-diagnostics-dev/python-tests-final.log',OUT/'python-tests.log')
print(json.dumps([{k:c[k] for k in ('label','harness_status','receiver_successes','sender_unknown_ids','pcap')} for c in cohorts],indent=2))
