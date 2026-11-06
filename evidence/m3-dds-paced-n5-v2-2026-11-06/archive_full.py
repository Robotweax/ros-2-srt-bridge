import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
sys.path.insert(0,'tools');sys.path.insert(0,'.local/v2-observer-study-dev')
from m3_dds_result_timeline import analyze
from m3_observer_study import source_inventory,installed_inventory
from m3_window_measurement import read_samples,summarize_cgroup
from m3_capture import pcap_configuration
from m3_dds import summarize_competitor
from audit_journals import audit
base=Path('.local/dds-n5-v2/20261106-retention256');dev=Path('.local/dds-n5-v2-dev');out=Path('evidence/m3-dds-paced-n5-v2-2026-11-06')
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
 for name in ('run.json','operator-result.json','robot-capture.log','operator-capture.log','robot-monotonic-capture.log','operator-monotonic-capture.log','robot-monotonic-ready.json','operator-monotonic-ready.json','profile-robot-readback.log','profile-operator-readback.log','before-robot.log','before-operator.log','after-robot.log','after-operator.log','dds-profile-probe.log'):
  if (run/name).exists():shutil.copyfile(run/name,dest/name)
 net=json.loads((run/'network.json').read_text());profile_commands=[dict(label=c['label'],argv=c['argv']) for c in net['commands'] if re.fullmatch(r'profile-(robot|operator)-[01]',c['label'])];assert len(profile_commands)==4
 dump(dest/'profile-commands.json',profile_commands)
 for role in ('robot','operator'):
  state=json.loads((run/('profile-'+role+'-readback.log')).read_text());netem=next(q['options'] for q in state if q['kind']=='netem');tbf=next(q['options'] for q in state if q['kind']=='tbf')
  assert netem['limit']==16 and netem['seed']==item['slot']['seed']+(role=='operator')
  assert netem.get('delay',{}).get('delay',0)==0 and netem.get('loss-random',{}).get('loss',0)==0
  assert tbf['rate']==64000 and tbf['burst']==4096
  if 'limit' in tbf:assert tbf['limit']==32768
  else:assert tbf['lat']==448000 # pinned iproute JSON exposes normalized latency, not a limit field
 for p in run.iterdir():
  if p.suffix in ('.sqlite','.mono','.jsonl') or '.pcap' in p.name or p.name=='competing-traffic.json':raw.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
 isolation[label]={}
 for role in ('robot','operator'):
  info=json.loads((run/(role+'-inspect.log')).read_text())[0]['HostConfig'];assert not info['Privileged'] and not info['PortBindings']
  isolation[label][role]=dict(cap_add=info['CapAdd'],privileged=False,published_ports=False,cgroup_namespace=info.get('CgroupnsMode'),clock_proof=report['clock_namespace_proof'][role])
 if item['status']!='passed':continue
 timeline=analyze(run.resolve());assert timeline==json.loads((base/(label+'-timeline.json')).read_text());dump(dest/'timeline.json',timeline)
 audit_result=audit(run);audits.append(audit_result)
 full=json.loads((run/'competing-traffic.json').read_text());computed=summarize_competitor(full)
 assert all(report['competitor_check'][k]==v for k,v in computed.items()) and report['competitor_check']['alive_poll_checks']>0
 assert report['profile_probe']['verified'] and report['profile_probe_binary_sha256']==plan['installed_sha256']['build/m3-dds-profile-probe/dds_profile_probe']
 assert report['dds_transport_xml_sha256']==plan['profile_xml_sha256']
 dump(dest/'competitor-offered.json',dict(setup=full['start']['test_start'],total=full['end']['sum'],intervals=[i['sum'] for i in full['intervals']],raw_sha256=sha(run/'competing-traffic.json'),scope='whole-run UDP offered load and process liveness; not matched-window delivery/loss'))
 assert audit_result['receiver_successes']==report['results']['final_device']['effects']
 for role in ('robot','operator'):
  log=(run/(role+'-capture.log')).read_text();assert re.findall(r'(\d+) packets? dropped by kernel',log)==['0']
  status=report['monotonic_captures']['statuses'][role];assert status['complete'] and not status['reserve_failed'] and not status['copy_failed']
  samples=read_samples(run/(role+'-endpoint-samples.jsonl'));projected=[dict(begin_ns=s['begin_ns'],end_ns=s['end_ns'],cgroup=s['cgroup']) for s in samples]
  (dest/(role+'-cgroup-samples.jsonl')).write_text(''.join(json.dumps(s)+'\n' for s in projected))
  for phase,w in report['endpoint_measurements']['windows'].items():
   assert summarize_cgroup(projected,*w['monotonic_ns'])==w['container_cgroup'][role];assert w['container_cgroup'][role]['qualified'];replayed+=1
   native=report['monotonic_captures']['windows'][phase][role];assert native['qualified']
   coverage.append(dict(seed=item['slot']['seed'],role=role,phase=phase,records=native['inside_records'],frame_interpretation=native['frame_interpretation'],pcap_population_reconciled=report['captures'][role]['tcpdump_population_reconciled'],cgroup=w['container_cgroup'][role]))
 m=item['metrics'];c=m['command_summary'];r=report['results'];a=r['command_audit'];sensor=m['sensors']
 cursor=r['checkpoints']['begin']['device']['generation'];uncertain=False;expired_ids=[]
 for command in r['commands']:
  assert not uncertain,'later intent after unresolved/UNKNOWN'
  assert command['expected_generation']==cursor and command['new_generation']==cursor+1
  if command.get('terminal')==4:cursor=command['new_generation']
  elif command.get('terminal')==7:expired_ids.append(command['number'])
  elif command.get('terminal') in (8,None):uncertain=True
 if not uncertain:assert cursor==r['final_device']['generation']
 generation_proofs.append(dict(seed=item['slot']['seed'],known_chain_complete=not uncertain,observed_final_generation=r['final_device']['generation'],last_confirmed_generation=cursor,expired_ids=expired_ids,scope='driver expected-generation chain; expiries do not advance it; final device equality required only without uncertainty'))
 counts={k:v['count'] for k,v in c['by_state_reason'].items()}
 values=dict(attempts=c['attempts'],successes=a['confirmed_successes'],effects=m['effects'],expired=sum(v for k,v in counts.items() if k.startswith('7/')),expired_without_dispatch=audit_result['receiver_expiries_without_dispatch'],unknown=a['unknown'],unresolved=c['unresolved'],not_admitted=c['not_admitted'],rejected=sum(v for k,v in counts.items() if k.startswith('6/')),failed=sum(v for k,v in counts.items() if k.startswith('5/')),skipped_slots=r['skipped_command_slots'])
 for k,v in values.items():totals[k]+=v
 commands.append(dict(seed=item['slot']['seed'],**values,command_paused_after_unknown=r['commands_paused_after_unknown'],maximum_terminal_observation_ms=c['terminal_observation_latency_ms']['maximum'],terminal_by_state_reason=c['by_state_reason'],status_history_omissions=sum(row.get('status_observations_omitted',0) for row in r['commands']),closed_receiver_expiries=audit_result['receiver_expiries'],coordinator_commands_sent=r['final_command_sender']['commands_sent'],receiver_dispatches=r['final_command_receiver']['dispatches'],receiver_start_claims=r['final_command_receiver']['start_claims'],sender_lease_expirations=r['final_command_sender']['lease_expirations'],receiver_lease_expirations=r['final_command_receiver']['lease_expirations'],sender_only=audit_result['sender_only'],receiver_only=audit_result['receiver_only'],status_divergences=audit_result['status_divergences'],competitor_check=report['competitor_check'],profile_probe=report['profile_probe'],closed_state_counts={role:{str(state):sum(entry['state']==state for entry in data['entries'].values()) for state in range(1,9)} for role,data in audit_result['roles'].items()}))
 sensors.append(dict(seed=item['slot']['seed'],source_enabled_seconds=m['windows']['source_enabled']['seconds'],**sensor,age_estimates_qualified=r['age_estimates_qualified'],routes=report['measurement_window']['routes'],age_scope=r['age_scope'],clock_step_count=len(r['clock_steps']),clock_max_offset_step_ns=r['clock_max_offset_step_ns'],clock_max_offset_deviation_ns=r['clock_max_offset_deviation_ns'],clock_max_bracket_width_ns=r['clock_max_bracket_width_ns'],pcap_clock_qualified={phase:w['wire_clock']['qualified'] for phase,w in report['endpoint_measurements']['windows'].items()},pcap_clock_qualification={phase:{role:calibration.get('reason','qualified') for role,calibration in w['wire_clock']['calibrations'].items()} for phase,w in report['endpoint_measurements']['windows'].items()}))
current_binaries=installed_inventory();probe=Path('build/m3-dds-profile-probe/dds_profile_probe');current_binaries[str(probe)]=sha(probe)
assert source_inventory()==plan['source_sha256'] and current_binaries==plan['installed_sha256']
for path,expected in plan['installed_scripts'].items():assert sha(Path(path))==expected
compiled=[p for p in subprocess.check_output(['git','ls-files'],text=True).splitlines() if p.startswith(('src/','ros2/','proto/')) and Path(p).suffix in ('.cpp','.hpp','.h','.proto')]
assert all(Path(p).read_bytes()==subprocess.check_output(['git','show','1bf9bfe:'+p]) for p in compiled)
verification=dict(capture_configuration=pcap_configuration(),source_files_each=len(plan['source_sha256']),run_source_inventories=len(study['rows']),mismatches=[],selected_installed_sha256=current_binaries,installed_scripts=plan['installed_scripts'],unchanged_compiled_sources_since_1bf9bfe=len(compiled),cgroup_windows_replayed_exactly=replayed,VM_boot_ids=sorted({item['metrics']['measurement_scope']['boot_id'] for item in study['rows'] if 'metrics' in item}))
for name,value in [('source-verification.json',verification),('raw-artifacts.json',raw),('journal-audits.json',audits),('isolation.json',isolation),('coverage.json',coverage),('command-outcomes.json',commands),('sensor-populations.json',sensors),('totals.json',totals),('generation-proofs.json',generation_proofs)]:dump(out/name,value)
print('archived',len(study['rows']),'executed cases;',replayed,'exact cgroup windows; totals',totals)
