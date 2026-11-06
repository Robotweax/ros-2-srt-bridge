import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,'tools');sys.path.insert(0,'.local/v2-observer-study-dev')
from m3_dds_result_timeline import analyze
from m3_observer_study import installed_inventory
from audit_journals import audit
base=Path('.local/dds-status-followup/20261106-history');dev=Path('.local/dds-status-diagnosis-dev');out=Path('evidence/m3-dds-status-timeline-2026-11-06')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
plan=json.loads((base/'plan.json').read_text());study=json.loads((base/'study.json').read_text());assert study['status']=='passed' and len(study['rows'])==3
for name in ('plan.json','study.json'):shutil.copyfile(base/name,out/name)
for name in ('python-tests.log','demo-install.log','run_followup.py','trace_controls.py','controls.json','timeline-at-run.py','timeline-tests-at-run.py','archive_followup.py'):shutil.copyfile(dev/name,out/name)
shutil.copyfile(Path('.local/v2-observer-study-dev/audit_journals.py'),out/'audit_journals.py')
historical=Path('.local/m3-dds-combined/20261106T124118032413Z');dump(out/'historical-timeline.json',analyze(historical))
raw=[];audits=[];isolation={};rows=[];deltas=[]
for item in study['rows']:
 label=item['slot']['label'];run=Path(item['run']);report=json.loads((run/'run.json').read_text());dest=out/label;dest.mkdir(exist_ok=True)
 assert report['source_sha256']==plan['source_sha256']
 for name in ('run.json','operator-result.json','robot-capture.log','operator-capture.log','robot-monotonic-capture.log','operator-monotonic-capture.log','robot-monotonic-ready.json','operator-monotonic-ready.json','profile-robot-readback.log','profile-operator-readback.log'):
  if (run/name).exists():shutil.copyfile(run/name,dest/name)
 timeline=analyze(run.resolve());assert timeline==json.loads((base/(label+'-timeline.json')).read_text());dump(dest/'timeline.json',timeline)
 audit_result=audit(run);audits.append(audit_result)
 assert not audit_result['sender_only'] and not audit_result['receiver_only'] and not audit_result['status_divergences']
 assert audit_result['receiver_expiries']==audit_result['receiver_expiries_without_dispatch']
 isolation[label]={}
 for role in ('robot','operator'):
  log=(run/(role+'-capture.log')).read_text();assert re.findall(r'(\d+) packets? dropped by kernel',log)==['0']
  status=report['monotonic_captures']['statuses'][role];assert status['complete'] and not status['reserve_failed'] and not status['copy_failed']
  info=json.loads((run/(role+'-inspect.log')).read_text())[0]['HostConfig'];assert not info['Privileged'] and not info['PortBindings']
  isolation[label][role]=dict(cap_add=info['CapAdd'],privileged=False,published_ports=False,cgroup_namespace=info.get('CgroupnsMode'),clock_proof=report['clock_namespace_proof'][role])
 for p in run.iterdir():
  if p.suffix in ('.sqlite','.mono','.jsonl') or '.pcap' in p.name:raw.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
 m=item['metrics'];c=m['command_summary'];results=report['results'];exp=audit_result['receiver_expiries']
 rows.append(f"| {item['slot']['seed']} | {c['attempts']} | {m['effects']} | {exp} | {c['unresolved']} | {results['skipped_command_slots']} | {c['terminal_observation_latency_ms']['maximum']:.3f} |")
 for entry in timeline['rows']:
  if entry['qualified']:deltas.append(entry)
verification=dict(frozen_sources_each=len(plan['source_sha256']),source_manifests_verified=3,installed_sha256=installed_inventory(),installed_scripts=plan['installed_scripts'],post_run_analysis_guard={})
assert installed_inventory()==plan['installed_sha256']
for path,expected in plan['installed_scripts'].items():assert sha(Path(path))==expected
changed={p:dict(at_run=h,final=sha(Path(p))) for p,h in plan['source_sha256'].items() if sha(Path(p))!=h}
expected={'tools/m3_dds_result_timeline.py':'timeline-at-run.py','tests/test_m3_dds_result_timeline.py':'timeline-tests-at-run.py'}
assert set(changed)==set(expected)
for p,copy in expected.items():assert sha(out/copy)==plan['source_sha256'][p]
verification['post_run_analysis_guard']=dict(changed_files=changed,scope='after all three workloads completed: additionally reject records whose stored owner differs from current coordinator process; frozen analyzer/test sources retained; final analyzer reproduces every archived timeline exactly; no measured script/binary changed')
compiled=[p for p in subprocess.check_output(['git','ls-files'],text=True).splitlines() if p.startswith(('src/','ros2/','proto/')) and Path(p).suffix in ('.cpp','.hpp','.h','.proto')]
assert all(Path(p).read_bytes()==subprocess.check_output(['git','show','bb44d5f:'+p]) for p in compiled);verification['unchanged_compiled_sources_since_bb44d5f']=len(compiled)
dump(out/'source-verification.json',verification);dump(out/'raw-artifacts.json',raw);dump(out/'journal-audits.json',audits);dump(out/'isolation.json',isolation)
(out/'RESULTS.md').write_text('''# Short N2 follow-up results

All three frozen runs passed without retries. 84 distinct admitted intents ended
with 82 confirmed successes/effects and two receiver-backed expiries (revision 1,
zero dispatch, invalid result). All six closed journals pass integrity checks and
agree on immutable commands and terminal states. No intent remains unresolved.
No NOT_FOUND or missing status is treated as nonexecution.

| Seed | Attempts | Successes/effects | Expired without dispatch | Unresolved | Skipped command slots | Maximum terminal-observation latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
'''+ '\n'.join(rows)+'''

Both expiry runs report one stale COMMAND at the receiver. The driver histories
retain 27 polls for seed 1701 intent 12 and 42 for seed 4211 intent 15, including
local queued observations after the five-second budget and a final authoritative
expiry. Neither history is truncated. Later distinct intents succeed without
advancing generation for the expired intent. These are original-session durable
absence seals, not evidence that context-changing failures can always resolve.

Seed 1701 confirms its expiry after 5.413 s; seed 4211 takes 8.459 s. Prompt effects
and eventual terminal agreement do not imply a terminal-status time guarantee.
The historical 10.871 s success remains a separate observation. No run is dropped
or replaced to improve latency, and no freshness/deadline policy is weakened.

All six PCAPs report zero kernel drops. Native v2 recorders have zero reserve/copy
failures and qualify both measured phases. These are socket-tap observations,
not physical wire or callback delivery. The same common VM/zero-offset clock proof
is recorded at both endpoints. Containers are private, nonprivileged, with NET_ADMIN
and opt-in BPF capabilities, no host networking or published ports.

The plan froze 161 source files, eight selected installed application/worker/
capture/SDK hashes and installed Python script bytes. All three run inventories
match that plan; selected binaries and measured scripts remain unchanged. After
the runs, the offline analyzer/test added a current-owner guard. Its two frozen
versions/hashes are retained, and final analysis reproduces all three timelines
exactly. The 56 compiled production sources remain unchanged from bb44d5f.
83 final host Python tests pass; the demo Python package was installed normally.
No new ROS GTest/full M2 execution is claimed.

Each workload is only 60 s. This step does not satisfy the full 600-second matrix,
physical tap/device coverage, isolated observer resource cost, transport semantic/
security parity or complete M3 acceptance. No SRT/DDS performance advantage is
claimed. Raw PCAPs/native prefixes/SQLite/clock samples stay local with hashes.
''')
print('archived 3 short N2 runs,',len(deltas),'qualified successful timelines; owner guard reanalysis identical')
