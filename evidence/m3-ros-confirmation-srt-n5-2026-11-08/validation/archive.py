from pathlib import Path
import hashlib,json,shutil,sys
root=Path.cwd();sys.path.insert(0,str(root/'tools'))
from m3_dds_result_timeline import read_journal
from m3_n5_progress import command_progress
base=root/'.local/m3-ros-confirmation-srt-n5-2026-11-08';out=root/'evidence/m3-ros-confirmation-srt-n5-2026-11-08';x=json.loads((base/'execution.json').read_text())
assert all(r['status']!='running' for r in x['rows'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(src,dst):dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
copy(base/'execution.json',out/'execution.json');hashes={};sources={};summary=[];audits={}
for row in x['rows']:
 if 'run' not in row:summary.append(row);continue
 label=row['slot']['label'];src=root/row['run'];dest=out/label;dest.mkdir(exist_ok=False)
 report=json.loads((src/'run.json').read_text());sources[label]=dict(source_commit=x['source_commit'],matched=all((root/p).exists() and sha(root/p)==h for p,h in report['source_sha256'].items()))
 for f in src.iterdir():
  if not f.is_file() or f.name=='passphrase':continue
  hashes[str(f.relative_to(root))]=dict(bytes=f.stat().st_size,sha256=sha(f))
  keep=f.suffix=='.json' and f.name!='network.json'
  keep=keep or f.name.endswith('-startup-timeline.jsonl')
  keep=keep or (f.suffix=='.log' and (any(word in f.name for word in ('-bridge-','-command.','-scenario.','-capture.','simulator.','profile-','before-','after-','competitor-process.','discovery-','drain-')) and not any(word in f.name for word in ('inspect','environment','resource'))))
  if keep:copy(f,dest/f.name)
 n=json.loads((src/'network.json').read_text());(dest/'network-summary.json').write_text(json.dumps({k:n[k] for k in ('network','addresses','events','isolation')},indent=2)+'\n')
 copy(base/(label+'.log'),dest/'host-run.log')
 s=dict(label=label,status=row['status'],error=row.get('error'),harness_status=report['status'],pcap_population_reconciled=report.get('pcap_population_reconciled'),seconds=row['slot']['seconds'],seed=row['slot']['seed'])
 if report.get('results',{}).get('commands'):
  p=command_progress(report,src);audits[label]=p;s.update(command_audit=p['audit'],skipped_slots=p['skipped_slots'],max_adjacent_intent_gap_ms=p['maximum_adjacent_intent_gap_ms'],terminal_latency_ms=report['command_summary']['terminal_observation_latency_ms'])
  if 'source_actual_hz' in report['measurement_window']:s['sensors']={k:report['measurement_window'][k] for k in ('source_produced','observer_received','losses','balances','source_actual_hz')}
  else:s['sensors']={r:{k:v[k] for k in ('produced','accepted','missing_before_callback','actual_source_hz')} for r,v in report['measurement_window']['routes'].items()}
 if row['slot']['group']=='ros' and row['slot']['cut']:
  cut=report.get('controlled_discovery',json.loads((src/'controlled-discovery.json').read_text()));s['controlled_discovery']=cut
  journals={r:read_journal(src/(r+'.sqlite'),side) for r,side in [('operator',1),('robot',2)]}
  assert all(not j['entries'] for j in journals.values())
  write=dict(journals=journals,scope='closed fresh journals contain no entries; workload driver barrier never submitted any Execute; not an absence inference for an accepted/UNKNOWN intent')
  (dest/'closed-journal-audit.json').write_text(json.dumps(write,indent=2)+'\n')
  timeline={}
  for r in ('operator','robot'):
   rows=[json.loads(l) for l in (src/(r+'-startup-timeline.jsonl')).read_text().splitlines()];snapshots=[v for v in rows if v['kind']=='snapshot'];assert all(not any(v['typed_counts'].values()) for v in snapshots)
   timeline[r]=dict(snapshots=len(snapshots),all_typed_counts_zero=True,process_epochs=len({tuple(v['command']['process_epoch']) for v in snapshots if v['command']}))
  s['failed_cut_timeline']=timeline
  s['owned_shutdown']={p.name:json.loads(p.read_text()) for p in src.glob('*-shutdown.json')}
 summary.append(s)
(out/'post-run-command-audits.json').write_text(json.dumps(audits,indent=2)+'\n')
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(out/'local-artifact-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
(out/'source-verification.json').write_text(json.dumps(sources,indent=2)+'\n');assert all(v['matched'] for v in sources.values())
assert x['runtime_unchanged'] and x['runtime_before']==x['runtime_after']=={p:sha(root/p) for p in x['runtime_before']}
(out/'post-run-runtime.json').write_text(json.dumps(dict(runtime_sha256=x['runtime_after'],unchanged=True),indent=2)+'\n')
for p in (root/'.local/m3-n5-ros-confirmation-build').glob('*.log'):
 if not p.name.endswith('commit.log'):copy(p,out/'validation'/p.name)
assert all(not (root/r['run']/'passphrase').exists() for r in x['rows'] if 'run' in r)
print('Archived original six-slot matrix; sources and production hashes match')
