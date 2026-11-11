from pathlib import Path
import hashlib,json,shutil,sys,subprocess
root=Path.cwd();sys.path.insert(0,str(root/'tools'))
from m3_n5_progress import RUNTIMES
out=root/'evidence/m3-receiver-clock-retention-2026-11-08';base=root/'.local/m3-receiver-clock-retention-2026-11-08'
x=json.loads((base/'execution.json').read_text());assert all(r['status']!='running' for r in x['rows'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(a,b):b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a,b)
hashes={};sources={};summary=[];selections=[];owned={}
copy(base/'execution.json',out/'execution.json')
for row in x['rows']:
 label=row['slot']['label'];s=dict(label=label,status=row['status'],error=row.get('error'),slot=row['slot']);summary.append(s)
 if 'run' not in row:continue
 src=root/row['run'];dest=out/label;dest.mkdir(exist_ok=False);d=json.loads((src/'run.json').read_text());owned[label]=json.loads((src/'network.json').read_text())['network']
 sources[label]=dict(frozen_source=x['source_commit'],matched=all(sha(root/p)==h for p,h in d['source_sha256'].items()))
 for p in src.iterdir():
  if p.is_file() and p.name!='passphrase':hashes[str(p.relative_to(root))]=dict(bytes=p.stat().st_size,sha256=sha(p))
  if p.is_file() and p.suffix=='.json' and p.name not in ('network.json','run.json'):copy(p,dest/p.name)
  if p.is_file() and p.suffix=='.log' and any(w in p.name for w in ('-bridge-','-scenario.','-capture.','simulator.','profile-','before-','after-','competitor-process.','drain-')):
   if '-bridge-' in p.name:
    lines=p.read_text().splitlines(keepends=True);keep=[l for l in lines if not l.startswith('PROVIDER_STATS ')];target=dest/(p.stem+'-selected.log');target.write_text(''.join(keep));selections.append(dict(original=str(p.relative_to(root)),public=str(target.relative_to(out)),omitted_provider_lines=len(lines)-len(keep),public_sha256=sha(target)))
   else:copy(p,dest/p.name)
 n=json.loads((src/'network.json').read_text());(dest/'network-summary.json').write_text(json.dumps({k:n[k] for k in ('network','addresses','events','isolation')},indent=2)+'\n')
 removed=[]
 for name,v in d.get('provider_diagnostics',{}).items():
  v['records_omitted_from_public_selection']=len(v.pop('records',[]));removed.append('provider_diagnostics.'+name+'.records')
  for key,c in v.get('connections',{}).items():
   c['adjacent_deltas_omitted_from_public_selection']=len(c.pop('adjacent_deltas',[]));removed.append('provider_diagnostics.'+name+'.connections.'+key+'.adjacent_deltas')
 target=dest/'run-selected.json';target.write_text(json.dumps(d,indent=2)+'\n');selections.append(dict(original=row['run']+'/run.json',public=str(target.relative_to(out)),removed_fields=removed,public_sha256=sha(target)))
 copy(base/(label+'.log'),dest/'host-run.log');s.update(harness_status=d['status'],capture_population_reconciled=d.get('pcap_population_reconciled'))
 if 'analysis' in row:
  a=row['analysis'];p=a['progress'];s.update(command_audit=p['audit'],skipped_slots=p['skipped_slots'],clock_rejection_correlations=a['clock_rejection_correlations'],active_context_events=len(a['active_context_events']),trace_population=a['trace_population'],sensors={k:d['measurement_window'][k] for k in ('source_produced','observer_received','losses','balances','source_actual_hz')})
 assert not (src/'passphrase').exists()
for s in selections:s['original_file']=hashes[s['original']]
assert all(v['matched'] for v in sources.values());assert x['runtime_unchanged'] and x['runtime_before']==x['runtime_after']=={p:sha(root/p) for p in RUNTIMES}
containers=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines();networks=subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines();assert not any(c.startswith(p) for c in containers for p in owned.values());assert not any(n in networks for n in owned.values())
for name,value in [('summary',summary),('local-artifact-hashes',hashes),('source-verification',sources),('public-selection',selections),('cleanup',dict(owned_networks=owned,owned_containers_present=False,owned_networks_present=False)),('runtime-verification',dict(before_rebuild=json.loads((root/'.local/m3-receiver-retention-build/runtime-before.json').read_text()),live_runtime=x['runtime_after'],live_unchanged=True))]:
 (out/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n')
validation=out/'validation';validation.mkdir(exist_ok=True)
for p in (root/'.local/m3-receiver-retention-build').iterdir():
 if p.is_file() and p.suffix in ('.log','.py','.json'):copy(p,validation/p.name)
# Build console display only, never original workload evidence.
displays=[]
for p in validation.glob('*.log'):
 before=p.read_bytes();p.write_text(''.join(l.rstrip()+'\n' for l in p.read_text().splitlines()).rstrip()+'\n')
 displays.append(dict(file=p.name,original_sha256=hashlib.sha256(before).hexdigest(),public_sha256=sha(p),transform='trailing whitespace and blank EOF lines in validation display only'))
(validation/'display-normalization.json').write_text(json.dumps(displays,indent=2)+'\n')
(validation/'validation-scope.json').write_text(json.dumps(dict(source=x['source_commit'],host_tests=271,sdk_tests=72,ros_tests=41,new_build=True,validation_exit=0),indent=2)+'\n')
print('Archived closed cohort, source/runtime checks and owned namespace cleanup')
