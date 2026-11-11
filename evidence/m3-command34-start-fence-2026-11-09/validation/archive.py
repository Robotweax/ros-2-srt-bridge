"""Read-only controlled journals and preservation of original evidence/runtime."""
import json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_dds_result_timeline import read_journal
base=ROOT/'.local/m3-command34-start-fence';out=ROOT/'evidence/m3-command34-start-fence-2026-11-09';before=json.loads((out/'binary-before.json').read_text());after={n:sha(ROOT/n) for n in before};assert before==after
old=ROOT/'evidence/m3-arp-packet-tracing-2026-11-09';manifest=json.loads((old/'local-artifact-hashes.json').read_text());assert all(sha(ROOT/n)==h['sha256'] for n,h in manifest.items())
controls=[];hashes={};disposition={}
for p in base.rglob('*'):
 if p.is_file():hashes[str(p.relative_to(ROOT))]=dict(sha256=sha(p),bytes=p.stat().st_size)
expected={0:(4,0),1:(6,1),2:(4,0),3:(8,1),4:(7,3),5:(4,0),6:(6,1)}
for label in ('execution_contract','execution_start_ipv4','execution_start_ipv6'):
 run=base/'controls'/label;r=json.loads((run/'result.json').read_text());assert r['exit_code']==0 and r['retries']==0
 dest=out/'controls'/label;dest.mkdir(parents=True,exist_ok=False)
 for name in ('console.log','result.json'):shutil.copy2(run/name,dest/name)
 row=dict(label=label,result=r,phase_journals=[])
 if label!='execution_contract':
  paths=sorted(run.rglob('receiver.sqlite'));assert len(paths)==7
  for p in paths:
   phase=int(p.parent.name);receiver=read_journal(p,2);sender=read_journal(p.parent/'sender.sqlite',1)
   assert len(receiver['entries'])==len(sender['entries'])==1
   rid=next(iter(receiver['entries']));e=receiver['entries'][rid];assert (e['state'],e['reason'])==expected[phase]
   assert rid in sender['entries'] and receiver['entries'][rid]['payload_hash']==sender['entries'][rid]['payload_hash']
   row['phase_journals'].append(dict(phase=phase,receiver_path=str(p.relative_to(ROOT)),receiver=receiver,sender=sender,scope='Closed controlled journal state; effect assertions belong to unchanged test source and passed test console, not inference from invalid result/absence'))
 controls.append(row)
for name in ('probe-build.log','probe.log','host-tests.log'):shutil.copy2(base/name,out/'validation'/name)
for n,h in hashes.items():
 p=ROOT/n;target=None
 if '/controls/' in n and p.name in ('console.log','result.json'):target=out/'controls'/p.parent.name/p.name
 if p.name in ('probe-build.log','probe.log','host-tests.log'):target=out/'validation'/p.name
 disposition[n]=dict(kind='verbatim',public=str(target.relative_to(out)),public_sha256=sha(target)) if target else dict(kind='local_only_omitted',reason='isolated probe binary or complete controlled SQLite streams retained locally by hash; immutable journal selections published')
 assert sha(p)==h['sha256']
for name,v in [('controlled-checks',controls),('local-artifact-hashes',hashes),('public-disposition',disposition),('binary-verification',dict(before=before,after=after,all_unchanged=True,installed_runtime_rebuilt=False)),('original-evidence-verification',dict(original_manifest=str((old/'local-artifact-hashes.json').relative_to(ROOT)),original_manifest_sha256=sha(old/'local-artifact-hashes.json'),original_raw_rehashed=len(manifest),all_original_raw_unchanged=True))]:write(out/(name+'.json'),v)
write(out/'validation/validation-scope.json',dict(host_tests=350,existing_focused_execution_tests=3,full_sdk_tests_new=False,prior_full_sdk=72,prior_ros=41,probe_checks=9,controlled_tests_retries=0,network='none; synthetic loopback only',production_defaults_changed=False,provider_changed=False,installed_runtime_rebuilt=False,pr2_draft=True,m3_complete=False,intrinsic_m4_touched=False))
print('Verified',len(before),'unchanged binaries;',len(manifest),'original raw files;',len(hashes),'new local artifacts; controlled journals immutable')
