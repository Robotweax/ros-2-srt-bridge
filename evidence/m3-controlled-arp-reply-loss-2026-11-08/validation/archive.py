from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path.cwd();out=root/'evidence/m3-controlled-arp-reply-loss-2026-11-08';base=root/'.local/m3-arp-reply-build';hashes={};disposition={};selection=[];owned=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists() and dst.read_bytes()!=src.read_bytes():raise ValueError('refusing changed archived output '+str(dst))
 if not dst.exists():shutil.copy2(src,dst)
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
datasets=[(base/n,out/'preparation'/n) for n in ('schema-preflight','schema-preflight-u32','schema-preflight-u32-final')]+[(root/'.local/m3-controlled-arp-reply-loss-2026-11-08',out/'failed-v1'),(root/'.local/m3-controlled-arp-reply-loss-v2-2026-11-08',out/'qualified-v2')]
for source,dest in datasets:
 for p in sorted(source.rglob('*')):
  if not p.is_file() or p.name=='passphrase':continue
  name=str(p.relative_to(root));hashes[name]=dict(bytes=p.stat().st_size,sha256=sha(p));target=dest/p.relative_to(source)
  if p.name=='network.json':
   n=json.loads(p.read_text());owned.append(n['network']);target=target.with_name('network-summary.json');data={k:n[k] for k in ('network','addresses','events','isolation')}
   if target.exists():assert json.loads(target.read_text())==data
   else:write(target,data)
   disposition[name]=dict(kind='derived_network_selection',public=str(target.relative_to(out)));selection.append(dict(original=name,public=str(target.relative_to(out)),retained_fields=list(data),public_sha256=sha(target)))
  elif p.suffix in ('.json','.jsonl') or p.suffix=='.log' and any(token in p.name for token in ('reply-','capture','neighbor-','before-','after-','features-','clock-proof','controller','receiver','original-send','fresh-send')):
   if dest.parent.name=='preparation' and p.suffix=='.log':target=target.with_suffix(target.suffix+'.txt')
   copy(p,target);disposition[name]=dict(kind='verbatim',public=str(target.relative_to(out)))
  else:disposition[name]=dict(kind='local_only_omitted',original_hash=hashes[name])
# Verify the successful cohort source before subsequent documentation-only edits.
x=json.loads((root/'.local/m3-controlled-arp-reply-loss-v2-2026-11-08/execution.json').read_text());assert x['status']=='passed' and x['runtime_unchanged'];assert all(sha(root/n)==h for n,h in x['source_sha256'].items());assert all(sha(root/n)==h for n,h in x['runtime_observers_after'].items())
assert json.loads((out/'failed-v1/execution.json').read_text())['status']=='failed';assert json.loads((out/'failed-v1/execution.json').read_text())['rows'][1]['status']=='not_executed'
containers=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines();networks=subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines();assert not any(c.startswith(p) for c in containers for p in owned);assert not any(n in networks for n in owned)
for source,dest in datasets:assert not list(source.rglob('passphrase'))
write(out/'local-artifact-hashes.json',hashes);write(out/'public-disposition.json',disposition);write(out/'public-selection.json',selection);write(out/'cleanup.json',dict(owned_networks=owned,containers_present=False,networks_present=False,credentials_removed=True))
validation=out/'validation';validation.mkdir(exist_ok=True)
for p in base.iterdir():
 if p.is_file() and p.suffix in ('.py','.json','.log'):copy(p,validation/p.name)
write(validation/'analysis-history.json',dict(ad_hoc_display_error='KeyError: pcap_file_packets; read-only console summary used wrong footer key',corrected_display=True,original_measurements_changed=False,no_live_repeat_by_display=True))
write(out/'source-runtime-verification.json',dict(frozen_v2_source=x['source_commit'],v1_source_verified_before_revision=True,v2_original_source_hashes_match=True,runtime8_observers2_fixed=True,provider_source=subprocess.check_output(['git','-C','.deps/srt','rev-parse','HEAD'],text=True).strip(),provider_tracked_source_clean=not subprocess.check_output(['git','-C','.deps/srt','status','--porcelain','--untracked-files=no'],text=True).strip(),host_v1=316,host_v2=317,prior_sdk_tests=72,prior_ros_tests=41,new_build=False,synthetic_only=True))
print('Archived all three preparations, failed V1 and passed V2; raw files',len(hashes),'owned networks',len(owned))
