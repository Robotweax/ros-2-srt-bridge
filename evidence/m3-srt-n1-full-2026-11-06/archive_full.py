import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,'tools');sys.path.insert(0,'.local/v2-observer-study-dev')
from m3_observer_study import source_inventory,installed_inventory
from m3_window_measurement import read_samples,summarize_cgroup
from m3_accounting import summarize_window
from m3_capture import pcap_configuration
from audit_journals import audit
base=Path('.local/srt-n1-full/20261106-v2-retention256');dev=Path('.local/srt-n1-full-dev');out=Path('evidence/m3-srt-n1-full-2026-11-06')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
plan=json.loads((base/'plan.json').read_text());study=json.loads((base/'study.json').read_text());assert study['status'] in ('passed','failed')
for name in ('plan.json','study.json'):shutil.copyfile(base/name,out/name)
for name in ('run_full.py','archive_full.py','write_results.py'):shutil.copyfile(dev/name,out/name)
shutil.copyfile(Path('.local/v2-observer-study-dev/audit_journals.py'),out/'audit_journals.py')
raw=[];audits=[];isolation={};commands=[];sensors=[];coverage=[];generation_proofs=[];replayed=0;totals=dict(attempts=0,successes=0,effects=0,expired=0,expired_without_dispatch=0,unknown=0,unresolved=0,not_admitted=0,rejected=0,failed=0,skipped_slots=0)
for item in study['rows']:
 label=item['slot']['label'];run=Path(item['run']);report=json.loads((run/'run.json').read_text());dest=out/label;dest.mkdir(exist_ok=True)
 assert report['source_sha256']==plan['source_sha256']
 for name in ('run.json','operator-result.json','robot-capture.log','operator-capture.log','robot-monotonic-capture.log','operator-monotonic-capture.log','robot-monotonic-ready.json','operator-monotonic-ready.json','profile-robot-readback.log','profile-operator-readback.log','before-robot.log','before-operator.log','after-robot.log','after-operator.log','operator-final-bridge-state.json','robot-final-bridge-state.json','robot-final-device-state.json'):
  if (run/name).exists():shutil.copyfile(run/name,dest/name)
 net=json.loads((run/'network.json').read_text());profile_commands=[dict(label=c['label'],argv=c['argv']) for c in net['commands'] if re.fullmatch(r'profile-(robot|operator)-0',c['label'])];assert len(profile_commands)==2
 dump(dest/'profile-commands.json',profile_commands)
 for role in ('robot','operator'):
  profile=next(q['options'] for q in json.loads((run/('profile-'+role+'-readback.log')).read_text()) if q['kind']=='netem')
  assert profile['limit']==256 and profile['seed']==item['slot']['seed']+(role=='operator') and profile['delay']['delay']==.02 and profile['delay']['jitter']==.005 and profile['loss-random']['loss']==.01
 for p in run.iterdir():
  if p.suffix in ('.sqlite','.mono','.jsonl') or '.pcap' in p.name:raw.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
 isolation[label]={}
 for role in ('robot','operator'):
  info=json.loads((run/(role+'-inspect.log')).read_text())[0]['HostConfig'];assert not info['Privileged'] and not info['PortBindings']
  isolation[label][role]=dict(cap_add=info['CapAdd'],privileged=False,published_ports=False,cgroup_namespace=info.get('CgroupnsMode'),clock_proof=report['clock_namespace_proof'][role])
 if item['status']!='passed':continue
 assert summarize_window(report['results']['checkpoints']['begin'],report['results']['checkpoints']['end'],report['results']['publication_interval'])==report['measurement_window']
 audit_result=audit(run);audits.append(audit_result)
 assert audit_result['receiver_successes']==report['results']['device']['effects']
 for role in ('robot','operator'):
  log=(run/(role+'-capture.log')).read_text();assert re.findall(r'(\d+) packets? dropped by kernel',log)==['0']
  status=report['monotonic_captures']['statuses'][role];assert status['complete'] and not status['reserve_failed'] and not status['copy_failed']
  samples=read_samples(run/(role+'-endpoint-samples.jsonl'));projected=[dict(begin_ns=s['begin_ns'],end_ns=s['end_ns'],cgroup=s['cgroup']) for s in samples]
  (dest/(role+'-cgroup-samples.jsonl')).write_text(''.join(json.dumps(s)+'\n' for s in projected))
  for phase,w in report['endpoint_measurements']['windows'].items():
   assert summarize_cgroup(projected,*w['monotonic_ns'])==w['container_cgroup'][role];assert w['container_cgroup'][role]['qualified'];replayed+=1
   native=report['monotonic_captures']['windows'][phase][role];assert native['qualified']
   coverage.append(dict(seed=item['slot']['seed'],role=role,phase=phase,records=native['inside_records'],frame_interpretation=native['frame_interpretation'],pcap_population_reconciled=report['captures'][role]['tcpdump_population_reconciled'],cgroup=w['container_cgroup'][role]))
 m=item['metrics'];c=m['command_summary'];r=report['results'];sensor=m['sensors']
 cursor=r['checkpoints']['begin']['device']['generation'];uncertain=False;expired_ids=[]
 for command in r['commands']:
  assert not uncertain,'later intent after unresolved/UNKNOWN'
  assert command['expected_generation']==cursor and command['new_generation']==cursor+1
  if command.get('terminal')==4:cursor=command['new_generation']
  elif command.get('terminal')==7:expired_ids.append(command['number'])
  elif command.get('terminal') in (8,None):uncertain=True
 if not uncertain:assert cursor==r['device']['generation']
 generation_proofs.append(dict(seed=item['slot']['seed'],known_chain_complete=not uncertain,observed_final_generation=r['device']['generation'],last_confirmed_generation=cursor,expired_ids=expired_ids,scope='driver expected-generation chain; expiries do not advance it; final device equality required only without uncertainty'))
 counts={k:v['count'] for k,v in c['by_state_reason'].items()}
 values=dict(attempts=c['attempts'],successes=counts.get('4/0',0),effects=m['effects'],expired=sum(v for k,v in counts.items() if k.startswith('7/')),expired_without_dispatch=audit_result['receiver_expiries_without_dispatch'],unknown=sum(v for k,v in counts.items() if k.startswith('8/')),unresolved=c['unresolved'],not_admitted=c['not_admitted'],rejected=sum(v for k,v in counts.items() if k.startswith('6/')),failed=sum(v for k,v in counts.items() if k.startswith('5/')),skipped_slots=r['skipped_command_slots'])
 for k,v in values.items():totals[k]+=v
 commands.append(dict(seed=item['slot']['seed'],**values,commands_paused_after_unknown=r['commands_paused_after_unknown'],maximum_terminal_observation_ms=c['terminal_observation_latency_ms']['maximum'],terminal_by_state_reason=c['by_state_reason'],closed_receiver_expiries=audit_result['receiver_expiries'],bridge_commands_sent=r['final_bridge_state']['commands_sent'],sender_only=audit_result['sender_only'],receiver_only=audit_result['receiver_only'],status_divergences=audit_result['status_divergences'],closed_state_counts={role:{str(state):sum(entry['state']==state for entry in data['entries'].values()) for state in range(1,9)} for role,data in audit_result['roles'].items()}))
 measurement=report['measurement_window'];assert not any(measurement['balances'].values())
 assert all(h['maximum_ms'] is None or h['maximum_ms']<=250 for h in measurement['age_upper_histograms'].values())
 sensors.append(dict(seed=item['slot']['seed'],measurement=measurement,publication_age_upper_snapshot=r['publication_age_upper'],diagnostic_observation=r['diagnostic_observation'],last_bridge_clock_qualified=r['final_bridge_state']['clock_qualified'],receiver_rejection_counters={key:r['checkpoints']['end']['receiver'][key]-r['checkpoints']['begin']['receiver'][key] for key in ('transport_samples_rejected','transport_samples_unknown_age','transport_samples_stale')},pcap_clock_qualified={phase:w['wire_clock']['qualified'] for phase,w in report['endpoint_measurements']['windows'].items()},pcap_clock_qualification={phase:{role:calibration.get('reason','qualified') for role,calibration in w['wire_clock']['calibrations'].items()} for phase,w in report['endpoint_measurements']['windows'].items()}))

assert source_inventory()==plan['source_sha256'] and installed_inventory()==plan['installed_sha256']
for path,expected in plan['installed_scripts'].items():assert sha(Path(path))==expected
compiled=[p for p in subprocess.check_output(['git','ls-files'],text=True).splitlines() if p.startswith(('src/','ros2/','proto/')) and Path(p).suffix in ('.cpp','.hpp','.h','.proto')]
assert all(Path(p).read_bytes()==subprocess.check_output(['git','show','d2912fc:'+p]) for p in compiled)
tool_changes={p:dict(frozen_sha256=h,base_sha256=hashlib.sha256(subprocess.check_output(['git','show','d2912fc:'+p])).hexdigest()) for p,h in plan['source_sha256'].items() if hashlib.sha256(subprocess.check_output(['git','show','d2912fc:'+p])).hexdigest()!=h}
assert set(tool_changes)=={'tools/m3_capture.py','tools/run_m3.py','tools/run_m3_dds.py','tests/test_m3_observer_study.py'}
verification=dict(capture_configuration=pcap_configuration(),source_changes_since_base=tool_changes,source_files_each=len(plan['source_sha256']),run_source_inventories=len(study['rows']),mismatches=[],selected_installed_sha256=installed_inventory(),installed_scripts=plan['installed_scripts'],unchanged_compiled_sources_since_d2912fc=len(compiled),cgroup_windows_replayed_exactly=replayed,source_fenced_windows_replayed_exactly=sum(item['status']=='passed' for item in study['rows']),VM_boot_ids=sorted({item['metrics']['measurement_scope']['boot_id'] for item in study['rows'] if 'metrics' in item}))
for name,value in [('source-verification.json',verification),('raw-artifacts.json',raw),('journal-audits.json',audits),('isolation.json',isolation),('coverage.json',coverage),('command-outcomes.json',commands),('sensor-populations.json',sensors),('totals.json',totals),('generation-proofs.json',generation_proofs)]:dump(out/name,value)
print('archived',len(study['rows']),'executed cases;',replayed,'exact cgroup windows; totals',totals)
