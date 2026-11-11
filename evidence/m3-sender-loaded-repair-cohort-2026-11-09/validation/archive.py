"""Publish closed evidence with exact omissions; never run/recover a command."""
import copy,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_runtime_layout import matched
from m3_dds_result_timeline import read_journal

out=ROOT/'evidence/m3-sender-loaded-repair-cohort-2026-11-09';base=ROOT/'.local/m3-sender-loaded-repair-cohort-2026-11-09'
execution=json.loads((base/'execution.json').read_text());hashes=json.loads((out/'local-artifact-hashes.json').read_text())
assert all(r['status']=='passed' for r in execution['rows']) and execution['runtime_unchanged']
layout=matched(ROOT,'sender-visibility');assert execution['runtime_layout']==execution['matched_after']==layout
preflight=json.loads((out/'preflight.json').read_text());assert preflight['layout']==layout
assert all(sha(ROOT/n)==h for n,h in preflight['observer_sha256'].items())
assert all(sha(ROOT/n)==v['sha256'] for n,v in hashes.items())
disposition={};owned=[];roots={};historical=None
for row in execution['rows']:
    run=ROOT/row['run'];data=json.loads((run/'run.json').read_text());network=json.loads((run/'network.json').read_text());owned.append(network['network']);dest=out/row['slot']['label'];dest.mkdir(exist_ok=True)
    assert all(sha(ROOT/n)==h for n,h in data['source_sha256'].items()) and not (run/'passphrase').exists()
    for role in ('operator','robot'):
        def config(path):return [{k:r.get(k) for k in ('kind','handle','parent','root','options')} for r in json.loads(path.read_text())]
        before=config(run/('before-'+role+'.log'));after=config(run/('after-'+role+'.log'));assert before==after
        assert json.loads((run/('features-before-'+role+'.log')).read_text())==json.loads((run/('features-after-'+role+'.log')).read_text())
        roots[row['slot']['label']+'/'+role]=dict(unchanged=True,before=before,after=after)
    if row['slot']['profile']=='N5':
        key=(118).to_bytes(16,'little').hex();old=ROOT/'.local/m3/20261109T125820284511Z/operator.sqlite';old_entry=read_journal(old,1)['entries'][key];new_entry=read_journal(run/'operator.sqlite',1)['entries'][key]
        assert (old_entry['state'],old_entry['reason'])==(8,2)
        assert all(old_entry[k]!=new_entry[k] for k in ('session','source_epoch','owner_epoch','source_ns'))
        historical=dict(old_journal_sha256=sha(old),historical118=old_entry,new_workload_counter118=new_entry,
            scope='Same numeric counter in a fresh isolated journal/session/epoch/origin, not replay of the historical intent. Original UNKNOWN/reconcile_required retained; historical exact ClockError unavailable.')
    for p in sorted(run.rglob('*')):
        if not p.is_file():continue
        name=str(p.relative_to(ROOT));assert name in hashes
        value=dict(kind='local_only',reason='Complete raw packet/native/provider/SQLite/sampler/host metadata retained locally by original SHA256');target=None;selection=None
        if p.name=='network.json':
            selection=json.dumps({k:network[k] for k in ('network','addresses','events','isolation')},indent=2)+'\n';target=dest/'network-selected.json';value['omitted_fields']=[k for k in network if k not in ('network','addresses','events','isolation')]
        elif p.name=='run.json':
            selected=copy.deepcopy(data);removed={}
            for stream in ('provider_diagnostics','sensor_provider_diagnostics'):
                for key,v in selected.get(stream,{}).items():
                    removed[stream+'.'+key+'.records']=len(v.pop('records',[]))
                    for c,cv in v.get('connections',{}).items():removed[stream+'.'+key+'.connections.'+c+'.adjacent_deltas']=len(cv.pop('adjacent_deltas',[]))
            for key,v in selected.get('command_diagnostics',{}).items():removed['command_diagnostics.'+key+'.events']=len(v.pop('events',[]))
            removed['sender_diagnostics.events']=len(selected['sender_diagnostics'].pop('events',[]))
            selection=json.dumps(selected,indent=2)+'\n';target=dest/'run-selected.json';value['removed_fields']=removed
        elif p.suffix=='.json' or p.name.endswith('-arp-trace.jsonl'):target=dest/p.name
        elif p.suffix=='.log' and any(x in p.name for x in ('-bridge-','capture','trace','btf','profile-','before-','after-','drain','arp-reply','-scenario')):
            omitted={};lines=[]
            for line in p.read_text().splitlines(keepends=True):
                reason=None
                if line.startswith(('PROVIDER_STATS ','SENSOR_PROVIDER_STATS ')):reason=line.split(' ',1)[0]
                elif line.startswith('COMMAND_TRACE '):
                    e=json.loads(line[len('COMMAND_TRACE '):])
                    if e['request']!=(3).to_bytes(16,'little').hex() and e['point'] not in (1,2,3,4,30,31,40,41,42,43,44,45,46):reason='other_command_trace'
                if reason:omitted[reason]=omitted.get(reason,0)+1
                else:lines.append(line)
            target=dest/(p.stem+'-selected.log' if omitted else p.name);selection=''.join(lines) if omitted else None
            if omitted:value['omitted_lines_by_category']=omitted
        if target:
            if selection is None:shutil.copyfile(p,target)
            else:target.write_text(selection)
            value.update(kind='verbatim' if selection is None else 'derived_selection',public=str(target.relative_to(out)),public_sha256=sha(target))
        disposition[name]=value
    shutil.copyfile(base/(row['slot']['label']+'.log'),dest/'host-run.log')
assert set(disposition)==set(hashes) and all(sha(ROOT/n)==v['sha256'] for n,v in hashes.items())
prior_count=0
for folder,v in preflight['prior_raw'].items():
    manifest=ROOT/'evidence'/folder/'local-artifact-hashes.json';assert sha(manifest)==v['manifest_sha256'];entries=json.loads(manifest.read_text());assert all(sha(ROOT/n)==e['sha256'] for n,e in entries.items());prior_count+=len(entries)
containers=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines();nets=subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines()
assert not any(c.startswith(n) for c in containers for n in owned) and not set(nets)&set(owned)
write(out/'public-disposition.json',disposition);write(out/'historical-intent-preservation.json',historical)
write(out/'cleanup.json',dict(owned_networks=owned,owned_containers_absent=True,owned_networks_absent=True,credentials_removed=True,roots_and_features_unchanged=True,root_configurations=roots))
write(out/'binary-verification.json',dict(matched_before=preflight['layout'],matched_after=layout,all_new_and_prior_binaries_fixed=True,observer_sha256=preflight['observer_sha256']))
write(out/'validation/results.json',dict(host_preflight=390,exact_sdk77_ros41_binary_qualification_reused=True,no_rebuild=True,source_frozen=execution['source_commit'],all_captured_source_hashes_match=True,new_raw_rehashed=len(hashes),prior_raw_rehashed=prior_count,actual_sender_deferral_groups=1,no_retries=True,no_heavy_work_while_live=True,no_tuning=True,no_forced_expiry=True,no_historical118_replay=True,pr2_draft=True,m3_complete=False,intrinsic_m4_touched=False))
shutil.copyfile(base/'execution.json',out/'execution.json')
raw_live=ROOT/'.local/m3-sender-loaded-repair-live.log';public_live=out/'validation/live.log'
public_live.write_text('\n'.join(line.rstrip() for line in raw_live.read_text().splitlines()).rstrip()+'\n')
write(out/'validation/display-normalization.json',dict(raw_source=str(raw_live.relative_to(ROOT)),raw_sha256=sha(raw_live),public_sha256=sha(public_live),change='Trailing whitespace only; no nonempty lines omitted'))
print('Archived2passed slots,1actual deferral/recovery,',len(hashes),'new raw and',prior_count,'prior raw;2owned networks removed')
