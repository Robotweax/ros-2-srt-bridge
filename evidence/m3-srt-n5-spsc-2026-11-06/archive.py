from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys,sqlite3
sys.path.insert(0,'tools')
from m3_dds_result_timeline import read_journal
from m3_observer_study import source_inventory,installed_inventory
from m3_accounting import summarize_window
from m3_window_measurement import read_samples,summarize_cgroup
import m3_monotonic_capture as mono
from m3_command_trace import summarize as trace_summary
BASE=Path('.local/srt-n5-spsc/20261106');OUT=Path('evidence/m3-srt-n5-spsc-2026-11-06');DEV=Path('.local/srt-n5-spsc-dev')
plan=json.loads((BASE/'plan.json').read_text());study=json.loads((BASE/'study.json').read_text());assert study['status']!='running'
OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
for n in ('plan.json','study.json'):shutil.copy2(BASE/n,OUT/n)
for n in ('run_full.py','archive.py'):shutil.copy2(DEV/n,OUT/n)
rows=[];raw=[];replayed=0;audits=[];images=set();container_images=set();image_refs=set()
for item in study['rows']:
 run=Path(item['run']);r=json.loads((run/'run.json').read_text());dest=OUT/item['slot']['label'];dest.mkdir(exist_ok=True)
 assert r['source_sha256']==plan['source_sha256']
 for name,h in r['source_sha256'].items():assert hashlib.sha256(subprocess.check_output(['git','show',plan['base_commit']+':'+name])).hexdigest()==h
 images.add(r['image_platform_id'])
 names=['run.json','operator-result.json','robot-final-device-state.json','measurement-start.json']
 for role in ('robot','operator'):
  names += [role+s for s in ('-capture.log','-monotonic-capture.log','-monotonic-ready.json','-recorder-samples.jsonl','-recorder-ready.json','-recorder-diagnostics.log','-final-bridge-state.json','-scenario.log')]
  names += ['profile-'+role+'-readback.log','before-'+role+'.log','after-'+role+'.log']
 names += [p.name for p in run.glob('*-bridge-*.log')]
 for name in names:
  if (run/name).exists():shutil.copy2(run/name,dest/name)
 net=json.loads((run/'network.json').read_text());write(dest/'profile-commands.json',[dict(label=c['label'],argv=c['argv']) for c in net['commands'] if re.fullmatch(r'profile-(robot|operator)-[01]',c['label'])])
 for role in ('robot','operator'):
  q=json.loads((run/('profile-'+role+'-readback.log')).read_text());tbf=next(x['options'] for x in q if x['kind']=='tbf');nem=next(x['options'] for x in q if x['kind']=='netem')
  assert tbf['rate']==64000 and tbf['burst']==4096 and tbf.get('lat')==448000 and nem['limit']==16 and nem['seed']==item['slot']['seed']+(role=='operator')
  inspect=json.loads((run/(role+'-inspect.log')).read_text())[0];container_images.add(inspect['Image']);image_refs.add(inspect['Config']['Image']);h=inspect['HostConfig'];assert not h['Privileged'] and not h['PortBindings']
  write(dest/(role+'-isolation.json'),dict(privileged=False,published_ports=False,cap_add=h['CapAdd'],clock_proof=r['clock_namespace_proof'][role],container_image=inspect['Image'],configured_image=inspect['Config']['Image']))
 for p in run.iterdir():
  if p.is_file() and ('.pcap' in p.name or p.suffix in ('.mono','.sqlite','.jsonl') or p.name=='competing-traffic.json'):raw.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
 trace_reanalysis={p.name:trace_summary(p) for p in run.glob('*-bridge-*.log')};write(dest/'trace-independent-reanalysis.json',dict(original_status=r['status'],scope='retains diagnostic loss; no missing record reconstructed and no overall gate waiver',traces=trace_reanalysis))
 row=dict(seed=item['slot']['seed'],cohort_case_status=item['status'],harness_status=r['status'],errors={k:v for k,v in r.items() if k.endswith('error')},pcap={},command_summary=r.get('command_summary'),trace_summary={name:dict(complete=t['complete'],records=t['records'],dropped=t['dropped'],counts=t['counts']) for name,t in trace_reanalysis.items()})
 for role in ('robot','operator'):
  footer=(run/(role+'-capture.log')).read_text();row['pcap'][role]={k:int(re.findall(pattern,footer)[-1]) for k,pattern in [('captured',r'(\d+) packets? captured'),('filter_received',r'(\d+) packets? received by filter'),('kernel_drops',r'(\d+) packets? dropped by kernel')]}
  row['pcap'][role]['file_records']=r.get('captures',{}).get(role,{}).get('records')
 if 'results' in r:
  result=r['results'];m=r['measurement_window'];assert summarize_window(result['checkpoints']['begin'],result['checkpoints']['end'],result['publication_interval'])==m
  row.update(effects=result['device']['effects'],skipped=result['skipped_command_slots'],measurement=m,competitor_check=r.get('competitor_check'))
  sender=read_journal(run/'operator.sqlite',1);receiver=read_journal(run/'robot.sqlite',2)
  for role,journal in (('operator',sender),('robot',receiver)):
   p=run/(role+'.sqlite')
   with sqlite3.connect(p.resolve().as_uri()+'?mode=ro&immutable=1',uri=True) as db:
    for id,b in db.execute('SELECT id,record FROM entries'):
     journal['entries'][id.hex()]['result_rate']=int.from_bytes(b[160:164],'big')
   assert sha(p)==journal['sha256']
  common=sender['entries'].keys()&receiver['entries'].keys();divergent=[]
  for id in common:
   a=sender['entries'][id];b=receiver['entries'][id];assert a['payload_hash']==b['payload_hash'] and a['route']==b['route']
   if any(a[k]!=b[k] for k in ('state','reason','revision','result_valid','result_generation','result_rate')):divergent.append(id)
  audit=dict(seed=item['slot']['seed'],sender=sender,receiver=receiver,common=len(common),divergent=divergent,sender_only=sorted(sender['entries'].keys()-receiver['entries'].keys()),receiver_only=sorted(receiver['entries'].keys()-sender['entries'].keys()))
  audits.append(audit);write(dest/'journal-audit.json',audit)
  row['journal_unknown_ids']=[id for id,e in sender['entries'].items() if e['state']==8];row['sender_only']=audit['sender_only'];row['divergent']=divergent
  for role in ('robot','operator'):
   projected=[dict(begin_ns=s['begin_ns'],end_ns=s['end_ns'],cgroup=s['cgroup']) for s in read_samples(run/(role+'-endpoint-samples.jsonl'))]
   (dest/(role+'-cgroup-samples.jsonl')).write_text(''.join(json.dumps(s)+'\n' for s in projected))
   for phase,w in r['endpoint_measurements']['windows'].items():assert summarize_cgroup(projected,*w['monotonic_ns'])==w['container_cgroup'][role];replayed+=1
  native=mono.summarize_run(run,net['addresses'],r['endpoint_measurements'],allow_udp_fragments=False,features=r['monotonic_capture_config']['features_before'])
  write(dest/'native-independent-reanalysis.json',dict(original_status=r['status'],scope='independent native observations do not rescue failed PCAP or command/overall gates',**native))
  row['realtime_window_qualification']={phase:w['wire_clock']['qualified'] for phase,w in r['endpoint_measurements']['windows'].items()}
 rows.append(row)
assert len(container_images)==len(image_refs)==1
assert source_inventory()==plan['source_sha256'] and installed_inventory()==plan['installed_sha256']
assert all(sha(Path(p))==h for p,h in plan['installed_scripts'].items())
write(OUT/'outcomes.json',dict(status=study['status'],rows=rows,unexecuted_seeds=[s['seed'] for s in plan['slots'][len(study['rows']):]],complete_m3_acceptance=False))
write(OUT/'raw-artifacts.json',raw)
write(OUT/'verification.json',dict(sources=len(plan['source_sha256']),all_sources_match_frozen=True,all_selected_binaries_and_scripts_constant=True,selected_installed_sha256=installed_inventory(),reported_image_platform_ids=sorted(images),container_image_ids=sorted(container_images),configured_image_refs=sorted(image_refs),image_reporting_note='raw reported image_platform_id varies between manifest/config-like IDs; original reports retained; container Image and immutable configured reference match across both cases; no canonical config ID invented',cgroup_windows_replayed=replayed,journal_audits=len(audits),scope='source/manifests/read-only closed journals/cgroup replay; no physical/realtime/cost or transport-superiority qualification'))
print(json.dumps([dict(seed=r['seed'],status=r['cohort_case_status'],effects=r.get('effects'),commands=r['command_summary'],pcap=r['pcap']) for r in rows],indent=2))
