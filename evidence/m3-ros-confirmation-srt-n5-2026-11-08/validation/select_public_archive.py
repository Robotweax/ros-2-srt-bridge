"""Derive a compact public selection, retaining original-file hashes separately."""
from pathlib import Path
import hashlib,json
out=Path('evidence/m3-ros-confirmation-srt-n5-2026-11-08')
execution=json.loads((out/'execution.json').read_text());hashes=json.loads((out/'local-artifact-hashes.json').read_text());selection=[]
for row in execution['rows']:
 if 'run' not in row:continue
 dest=out/row['slot']['label'];p=dest/'run.json';d=json.loads(p.read_text());removed=[]
 for name,v in d.get('provider_diagnostics',{}).items():
  if 'records' in v:
   v['records_omitted_from_public_selection']=len(v.pop('records'));removed.append('provider_diagnostics.'+name+'.records')
  for key,c in v.get('connections',{}).items():
   if 'adjacent_deltas' in c:
    c['adjacent_deltas_omitted_from_public_selection']=len(c.pop('adjacent_deltas'));removed.append('provider_diagnostics.'+name+'.connections.'+key+'.adjacent_deltas')
 target=p.with_name('run-selected.json');target.write_text(json.dumps(d,indent=2)+'\n');p.unlink()
 selection.append(dict(original=row['run']+'/run.json',original_file=hashes[row['run']+'/run.json'],public=str(target.relative_to(out)),removed_fields=removed))
 for p in list(dest.glob('*-bridge-*.log')):
  lines=p.read_text().splitlines(keepends=True);keep=[l for l in lines if not l.startswith('PROVIDER_STATS ')];target=p.with_name(p.stem+'-selected.log');target.write_text(''.join(keep));p.unlink()
  selection.append(dict(original=row['run']+'/'+p.name,original_file=hashes[row['run']+'/'+p.name],public=str(target.relative_to(out)),omitted_provider_sample_lines=len(lines)-len(keep),policy='only PROVIDER_STATS sample lines removed; lifecycle, command trace and final provider/trace footers retained verbatim'))
for item in selection:item['public_sha256']=hashlib.sha256((out/item['public']).read_bytes()).hexdigest()
(out/'public-selection.json').write_text(json.dumps(selection,indent=2)+'\n')
print('Public selection written; original local inputs unchanged')
