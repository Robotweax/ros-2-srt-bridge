import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,'tools');sys.path.insert(0,'.local/v2-observer-study-dev')
from m3_window_measurement import read_samples,summarize_cgroup
from audit_journals import audit
root=Path.cwd();study_dir=Path('.local/m3-observer-study/20261106-v2-buffer32768');out=Path('evidence/m3-v2-observer-impairments-2026-11-06')
study=json.loads((study_dir/'study.json').read_text());definition=json.loads((study_dir/'plan.json').read_text());assert study['status']=='passed' and len(study['rows'])==12
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
for name in ('study.json','plan.json'):shutil.copyfile(study_dir/name,out/name)
for name in ('python-tests.log','audit_journals.py'):shutil.copyfile(Path('.local/v2-observer-study-dev')/name,out/name)
raw=[];verification={};journal_audits=[];isolation={};cpu_rows=[];sensor_rows=[];long_rows=[];replayed=0
for row in study['rows']:
 slot=row['slot'];label=slot['label'];run=Path(row['run']);d=json.loads((run/'run.json').read_text());dest=out/label;dest.mkdir(exist_ok=True)
 assert d['source_sha256']==definition['source_sha256']
 mismatches=[f for f,h in d['source_sha256'].items() if sha(Path(f))!=h];assert not mismatches
 verification[label]=dict(source_files=len(d['source_sha256']),mismatches=mismatches)
 for name in ('run.json','operator-result.json','robot-monotonic-capture.log','operator-monotonic-capture.log','robot-monotonic-ready.json','operator-monotonic-ready.json','robot-capture.log','operator-capture.log','profile-robot-readback.log','profile-operator-readback.log'):
  if (run/name).exists():shutil.copyfile(run/name,dest/name)
 for p in sorted(run.iterdir()):
  if p.suffix in ('.mono','.sqlite','.jsonl') or '.pcap' in p.name:raw.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
 isolation[label]={}
 for role in ('robot','operator'):
  inspect=json.loads((run/(role+'-inspect.log')).read_text())[0];host=inspect['HostConfig'];caps=host['CapAdd'];assert ('CAP_BPF' in caps or 'BPF' in caps)==slot['observer'];assert not host['Privileged'] and not host['PortBindings']
  isolation[label][role]=dict(cap_add=caps,privileged=False,published_ports=False,cgroup_namespace_mode=host.get('CgroupnsMode'),cpu_quota=host.get('CpuQuota'),cpuset_cpus=host.get('CpusetCpus'),clock_proof=d['clock_namespace_proof'][role])
  samples=read_samples(run/(role+'-endpoint-samples.jsonl'));projected=[dict(begin_ns=s['begin_ns'],end_ns=s['end_ns'],cgroup=s['cgroup']) for s in samples]
  (dest/(role+'-cgroup-samples.jsonl')).write_text(''.join(json.dumps(s)+'\n' for s in projected))
  for name,w in d['endpoint_measurements']['windows'].items():
   actual=summarize_cgroup(projected,*w['monotonic_ns']);assert actual==w['container_cgroup'][role];assert actual['qualified'];replayed+=1
  g=d['endpoint_measurements']['windows']['source_enabled']['container_cgroup'][role]
  cpu_rows.append(f"| {label} | {role} | {g['inner_cpu_core_percent']:.2f}–{g['outer_cpu_core_percent']:.2f} | {g['maximum_observed_memory_current_bytes']/1048576:.2f} |")
 audit_result=audit(run);journal_audits.append(audit_result)
 m=row['metrics'];sensor=m['sensors'];command=m['command_summary'];hz='/'.join(f'{v:.3f}' for v in sensor['actual_source_hz'].values())
 sensor_rows.append(f"| {label} | {command['attempts']} | {m['effects']} | {sensor['produced']} | {sensor['received']} | {hz} |")
 if slot['phase']=='long':
  statuses=m['monotonic_captures']['statuses'];assert all(s['complete'] and not s['reserve_failed'] and not s['copy_failed'] for s in statuses.values())
  assert m['competitor']['alive_poll_checks']>0
  total_frames='/'.join(str(statuses[r]['records']) for r in ('robot','operator'))
  long_rows.append(f"| {slot['seed']} | {command['attempts']} | {m['effects']} | {sensor['produced']} | {sensor['received']} | {total_frames} | 0 |")
# Preserve the full environment/counter scopes, not inferred hardware isolation.
verification['projected_cgroup_windows_replayed_exactly']=replayed
verification['installed_python']={}
for p in Path('ros2/robotweax_srt_bridge_demo/scripts').glob('*.py'):
 q=Path('install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo')/p.name
 if q.exists():assert p.read_bytes()==q.read_bytes();verification['installed_python'][p.name]=sha(p)
old=json.loads(Path('evidence/m3-monotonic-capture-2026-11-06/source-verification.json').read_text())['production_binaries'];verification['production_binaries']={}
for key,item in old.items():assert sha(Path(item['path']))==item['sha256'];verification['production_binaries'][key]=item
compiled=[p for p in subprocess.check_output(['git','ls-files'],text=True).splitlines() if p.startswith(('src/','ros2/','proto/')) and Path(p).suffix in ('.cpp','.hpp','.h','.proto')]
assert all(Path(p).read_bytes()==subprocess.check_output(['git','show','235cc73:'+p]) for p in compiled);verification['compiled_sources_unchanged_since_235cc73']=len(compiled)
from m3_observer_study import installed_inventory
assert installed_inventory()==definition['installed_sha256'];verification['installed_sha256']=installed_inventory()
# Every current child records the same boot as all others; distinct namespaces remain recorded per role.
boots={r['clock_proof'].splitlines()[0] for roles in isolation.values() for r in roles.values()};assert len(boots)==1;verification['single_VM_boot_id']=next(iter(boots))
dump(out/'source-verification.json',verification);dump(out/'raw-artifacts.json',raw);dump(out/'isolation.json',isolation);dump(out/'journal-audits.json',journal_audits)
pairs=[]
for group,data in study['comparisons'].items():
 for pair in data['pairs']:
  for role,v in pair['roles'].items():
   delta=v['observed_on_minus_off_core_percent'];pairs.append(f"| {group} | {pair['on']} / {pair['off']} | {role} | {delta[0]:+.2f}–{delta[1]:+.2f} | {v['sampled_charged_memory_max_difference_bytes']/1048576:+.2f} |")
(out/'RESULTS.md').write_text("# Results and limits\n\nAll twelve changed-configuration workloads passed without retries: eight 45-second N0 runs and four 60-second N1/N2 probes. The earlier smaller-buffer study failed and remains separate. The short impairment probes do not satisfy the full 600-second, three-seed matrix.\n\nEvery cgroup phase replays exactly from the archived projections. Opt-in native recorders report zero reserve/copy failures. PCAP kernel drops are zero. Raw captures, packet prefixes, clocks and journals remain local with hashes. No physical delivery, isolated CPU cost or full M3 acceptance is established.\n\n## Observer on/off observations\n\nThe observed CPU differences retain variation and negative values; inner/outer observations are neither physical bounds nor confidence intervals. Charged-memory maxima include cache/kernel allocations. Both modes use immediate PCAP with the larger buffer; historical smaller-buffer or v1 results cannot substitute. Source/callback populations differ.\n\n| Group | On / off pair | Endpoint | Observed CPU difference (core percentage points) | Sampled charged-memory max difference (MiB) |\n| --- | --- | --- | ---: | ---: |\n"+'\n'.join(pairs)+"\n\n## Workload populations\n\nRates list IMU/joints in Hz. Command attempts, receiver effects, terminal states and unresolved observations remain distinct; see study.json and journal-audits.json for status detail. Callback deficits are not isolated network loss.\n\n| Run | Command attempts | Effects | Produced | Received callbacks | Actual source Hz |\n| --- | ---: | ---: | ---: | ---: | --- |\n"+'\n'.join(sensor_rows)+"\n\n## Container source-enabled resources\n\nCPU includes all work charged to the container, excludes work elsewhere, and is affected by shared emulated VM scheduling. Memory is sampled cgroup charge, not RSS/PSS or a hard peak. These results do not establish a transport advantage.\n\n| Run | Endpoint | Observed cgroup CPU (core %) | Sampled charged memory (MiB) |\n| --- | --- | ---: | ---: |\n"+'\n'.join(cpu_rows)+'\n')
print('archived',len(study['rows']),'runs;',replayed,'exactly reproduced cgroup windows')
