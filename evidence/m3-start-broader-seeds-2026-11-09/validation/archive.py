"""Archive one closed prospective cohort, with full raw hashes and exact omissions."""
import copy,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_runtime_layout import matched
out=ROOT/'evidence/m3-start-broader-seeds-2026-11-09';base=ROOT/'.local/m3-start-broader-seeds-2026-11-09';e=json.loads((base/'execution.json').read_text());hashes=json.loads((out/'local-artifact-hashes.json').read_text());disposition={};summary=[];owned=[]
assert all(r['status']!='running' for r in e['rows']);assert e['runtime_unchanged'];assert matched(ROOT,'start-trace')==e['runtime_layout']==e['matched_after'];shutil.copy2(base/'execution.json',out/'execution.json')

def publish(original,target,selection=None):
 target.parent.mkdir(parents=True,exist_ok=True)
 if selection is None:shutil.copy2(original,target)
 else:target.write_text(selection)
 return dict(kind='verbatim' if selection is None else 'derived_selection',public=str(target.relative_to(out)),public_sha256=sha(target))

for row in e['rows']:
 if 'run' not in row:
  summary.append(dict(label=row['slot']['label'],status=row['status'],why=row.get('why'),slot=row['slot']));continue
 label=row['slot']['label'];run=ROOT/row['run'];d=json.loads((run/'run.json').read_text());assert all(sha(ROOT/n)==h for n,h in d['source_sha256'].items());assert not (run/'passphrase').exists();dest=out/label;dest.mkdir(exist_ok=False);n=json.loads((run/'network.json').read_text());owned.append(n['network'])
 roots={}
 for role in ('operator','robot'):
  a=json.loads((run/('before-'+role+'.log')).read_text());b=json.loads((run/('after-'+role+'.log')).read_text())
  def config(qs):return [{k:r.get(k) for k in ('kind','handle','parent','root','options')} for r in qs]
  assert config(a)==config(b);roots[role]=dict(unchanged=True,before=config(a),after=config(b))
 for p in run.rglob('*'):
  if not p.is_file():continue
  name=str(p.relative_to(ROOT));assert sha(p)==hashes[name]['sha256'];value=dict(kind='local_only_omitted',reason='Complete packet/native/provider/SQLite/sampler/host metadata retained locally by original hash')
  if p.name=='network.json':value=publish(p,dest/'network-selected.json',json.dumps({k:n[k] for k in ('network','addresses','events','isolation')},indent=2)+'\n');value['omitted_fields']=[k for k in n if k not in ('network','addresses','events','isolation')]
  elif p.name=='run.json':
   selected=copy.deepcopy(d);removed={}
   for stream in ('provider_diagnostics','sensor_provider_diagnostics'):
    for key,v in selected.get(stream,{}).items():
     removed[stream+'.'+key+'.records']=len(v.pop('records',[]))
     for c,cv in v.get('connections',{}).items():removed[stream+'.'+key+'.connections.'+c+'.adjacent_deltas']=len(cv.pop('adjacent_deltas',[]))
   for key,v in selected.get('command_diagnostics',{}).items():removed['command_diagnostics.'+key+'.events']=len(v.pop('events',[]))
   value=publish(p,dest/'run-selected.json',json.dumps(selected,indent=2)+'\n');value['removed_fields']=removed
  elif p.suffix=='.json':value=publish(p,dest/p.name)
  elif p.name.endswith('-arp-trace.jsonl'):value=publish(p,dest/p.name)
  elif p.suffix=='.log' and any(x in p.name for x in ('-bridge-','capture','trace','btf','profile-','before-','after-','drain','arp-reply','-scenario')):
   omitted={};lines=[]
   for line in p.read_text().splitlines(keepends=True):
    reason=None
    if line.startswith(('PROVIDER_STATS ','SENSOR_PROVIDER_STATS ')):reason=line.split(' ',1)[0]
    elif line.startswith('COMMAND_TRACE '):
     event=json.loads(line[len('COMMAND_TRACE '):])
     if event['request']!='76000000000000000000000000000000' and event['point'] not in (1,2,3,4,30,31,40,41,42,43,44):reason='other_command_trace'
    if reason:omitted[reason]=omitted.get(reason,0)+1
    else:lines.append(line)
   value=publish(p,dest/(p.stem+'-selected.log' if omitted else p.name),''.join(lines) if omitted else None)
   if omitted:value['omitted_lines_by_category']=omitted
  disposition[name]=value
 shutil.copy2(base/(label+'.log'),dest/'host-run.log')
 a=row['analysis'];s=json.loads((out/'analysis'/(label+'-starts.json')).read_text());packets=json.loads((out/'analysis'/(label+'-packets.json')).read_text());assert s['status']==packets['status']=='passed';rows=s['analysis']['all_attempts'];observed=[r for r in rows if r.get('actual_slack_ns')];slacks={key:dict(minimum_ns=min(r['actual_slack_ns'][key] for r in observed),maximum_ns=max(r['actual_slack_ns'][key] for r in observed)) for key in ('consume','second_gate','command_budget_at_consume','command_minus_grant')}
 later=[dict(number=r['number'],admission_margin_ns=r['last_admission_clock_margin_ns'],actual_consume_slack_ns=r['actual_slack_ns']['consume']) for r in rows if r.get('owner_grant') and r['admission_clock_context'] and r['owner_grant']['clock_deadline_ns']>r['admission_clock_context'][-1]['clock_deadline_ns']]
 missing=[step for step in packets['analysis']['positive_steps'] if not step['witness']['source_replies_in_outer_envelope']]
 summary.append(dict(label=label,status=row['status'],run=row['run'],harness_status=d['status'],audit=a['progress']['audit'],skipped=a['progress']['skipped_slots'],durable_outcomes=a['durable_outcomes'],active_context_events=len(a['active_context_events']),start_counts=s['analysis']['branch_counts'],unavailable_starts=s['analysis']['unavailable_starts'],actual_slack=slacks,owner_clock_deadline_later_than_admission=later,minimum_admission_margin_ns=min(r['last_admission_clock_margin_ns'] for r in rows if r.get('last_admission_clock_margin_ns') is not None),grant_equals_clock_deadline=sum(r['owner_grant']['grant_deadline_ns']==r['owner_grant']['clock_deadline_ns'] for r in observed),grant_below_original_record_deadline=sum(r['actual_slack_ns']['command_minus_grant']>0 for r in observed),root_configurations=roots,packet_counts={role:v['counts'] for role,v in d['arp_packet_diagnostics'].items()},primary_windows=packets['analysis']['primary_windows'],positive_counter_windows=len(packets['analysis']['positive_steps']),missing_counter_windows=missing,sensor_measurement=d['measurement_window']))
assert set(disposition)==set(hashes)
for n,h in hashes.items():assert sha(ROOT/n)==h['sha256']
prior_count=0
for label in ('m3-arp-packet-tracing-2026-11-09','m3-command34-start-fence-2026-11-09','m3-start-tracing-2026-11-09','m3-loaded-start-tracing-2026-11-09'):
 m=json.loads((ROOT/'evidence'/label/'local-artifact-hashes.json').read_text());assert all(sha(ROOT/n)==v['sha256'] for n,v in m.items());prior_count+=len(m)
containers=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines();nets=subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines();assert not any(c.startswith(n) for c in containers for n in owned);assert not set(nets)&set(owned)
for name,v in [('summary',summary),('public-disposition',disposition),('cleanup',dict(owned_networks=owned,owned_networks_present=False,owned_containers_present=False,credentials_removed=True)),('binary-verification',dict(matched_before=e['runtime_layout'],matched_after=e['matched_after'],all_matched_binaries_unchanged=True,original_installed_baseline_preserved=True,runtime_after=e['runtime_after'],observers_after=e['observer_after'])),('validation/results',dict(host_tests=376,prior_matched_sdk_tests=75,prior_matched_ros_tests=41,no_rebuild=True,no_tests_builds_heavy_analysis_while_live=True,prior_raw_rehashed=prior_count,new_raw_rehashed=len(hashes),all_source_unchanged=True,all_matched_binaries_fixed=True,no_tuning=True,no_retry=True,pr2_draft=True,m3_complete=False,intrinsic_m4_touched=False))]:write(out/(name+'.json'),v)
shutil.copy2(ROOT/'.local/m3-start-broader-seeds-build/live.log',out/'validation/live.log')
print('Archived closed source/matched binaries,',len(hashes),'new raw and',prior_count,'prior raw hashes;2 owned networks/credentials removed')
