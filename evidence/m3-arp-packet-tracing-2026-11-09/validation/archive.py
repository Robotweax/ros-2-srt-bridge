"""Archive closed original runs, retain failures and make every omission explicit."""
import copy,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_n5_progress import RUNTIMES
from m3_session_sensor_diagnostics import OBSERVERS
out=ROOT/'evidence/m3-arp-packet-tracing-2026-11-09';hashes={};disposition={};sourcechecks={};networks=[];summary=[]
cohorts=[('calibration-v1',ROOT/'.local/m3-arp-packet-tracing-2026-11-09'),('calibration-v2',ROOT/'.local/m3-arp-packet-tracing-v2-2026-11-09'),('loaded',ROOT/'.local/m3-loaded-arp-packet-tracing-2026-11-09')]

def publish(p,target,transform=None):
    target.parent.mkdir(parents=True,exist_ok=True)
    if transform is None:shutil.copy2(p,target)
    else:target.write_text(transform)
    return dict(kind='verbatim' if transform is None else 'derived_selection',public=str(target.relative_to(out)),public_sha256=sha(target))

def check_sources(label,commit,sources):
    changed=[]
    for name,h in sources.items():
        if sha(ROOT/name)!=h:
            blob=subprocess.check_output(['git','show',commit+':'+name],cwd=ROOT)
            assert hashlib.sha256(blob).hexdigest()==h,name
            changed.append(name)
    sourcechecks[label]=dict(frozen_source=commit,all_current_or_original_git_blobs_verified=True,changed_after_closure=changed)

for cohort,base in cohorts:
    e=json.loads((base/'execution.json').read_text());assert all(r['status']!='running' for r in e['rows'])
    destination=out/cohort;destination.mkdir(exist_ok=False);shutil.copy2(base/'execution.json',destination/'execution.json')
    rows=[]
    for r in e['rows']:
        label=r['slot']['label'] if 'slot' in r else r['profile'];p=ROOT/r['run'] if 'run' in r else base/label
        s=dict(label=label,status=r['status'],error=r.get('error'));rows.append(s)
        if not p.is_dir():continue
        assert not (p/'passphrase').exists()
        resultfile=p/('run.json' if cohort=='loaded' else 'result.json');d=json.loads(resultfile.read_text());target=destination/label;target.mkdir()
        sources=d['source_sha256'] if cohort=='loaded' else e['source_sha256'];check_sources(cohort+'/'+label,e['source_commit'],sources)
        n=json.loads((p/'network.json').read_text());networks.append(n['network']);configs={}
        for role in ('operator','robot'):
            a=json.loads((p/('before-'+role+'.log')).read_text());b=json.loads((p/('after-'+role+'.log')).read_text())
            def config(qs):return [{k:x.get(k) for k in ('kind','root','handle','parent','options')} for x in qs]
            assert config(a)==config(b),('root settings changed',label,role)
            configs[role]=dict(unchanged=True,before=config(a),after=config(b))
        s['root_configurations']=configs
        for f in p.rglob('*'):
            if not f.is_file():continue
            name=str(f.relative_to(ROOT));hashes[name]=dict(bytes=f.stat().st_size,sha256=sha(f));item=dict(kind='local_only_omitted',reason='Full raw packet/native/provider/journal/sampler/host metadata retained locally by hash')
            if f==p/'network.json':item=publish(f,target/'network-selected.json',json.dumps({k:n[k] for k in ('network','addresses','events','isolation')},indent=2)+'\n');item['omitted_fields']=[k for k in n if k not in ('network','addresses','events','isolation')]
            elif f==resultfile:
                v=copy.deepcopy(d);removed={}
                if cohort=='loaded':
                    for stream in ('provider_diagnostics','sensor_provider_diagnostics'):
                        for key,value in v.get(stream,{}).items():
                            removed[stream+'.'+key+'.records']=len(value.pop('records',[]))
                            for conn,cv in value.get('connections',{}).items():removed[stream+'.'+key+'.connections.'+conn+'.adjacent_deltas']=len(cv.pop('adjacent_deltas',[]))
                    for key,value in v.get('command_diagnostics',{}).items():removed['command_diagnostics.'+key+'.events']=len(value.pop('events',[]))
                item=publish(f,target/(resultfile.stem+'-selected.json'),json.dumps(v,indent=2)+'\n');item['removed_fields']=removed
            elif f.suffix=='.json':item=publish(f,target/f.name)
            elif f.name.endswith('-arp-trace.jsonl') or f.name=='trace.jsonl':item=publish(f,target/f.name)
            elif f.suffix=='.log' and any(word in f.name for word in ('capture','trace','btf','profile-','before-','after-','drain','arp-reply','-scenario','receiver','flood','requests','-bridge-')):
                lines=f.read_text().splitlines(keepends=True);keep=[];omitted={}
                for line in lines:
                    category=None
                    if line.startswith(('PROVIDER_STATS ','SENSOR_PROVIDER_STATS ')):category=line.split(' ',1)[0]
                    elif line.startswith('COMMAND_TRACE '):
                        ev=json.loads(line[len('COMMAND_TRACE '):])
                        if ev['request']!='22000000000000000000000000000000' and ev['point'] not in (1,2,3,4,30,31):category='other_command_trace'
                    if category:omitted[category]=omitted.get(category,0)+1
                    else:keep.append(line)
                item=publish(f,target/(f.stem+'-selected.log' if omitted else f.name),''.join(keep) if omitted else None)
                if omitted:item['omitted_lines_by_category']=omitted
            disposition[name]=item
        if cohort=='loaded':
            a=r.get('analysis',{});s.update(run=r['run'],harness_status=d['status'],audit=a.get('progress',{}).get('audit'),skipped=a.get('progress',{}).get('skipped_slots'),durable_outcomes=a.get('durable_outcomes'),active_context_events=len(a.get('active_context_events',[])),packet_counts={role:v['counts'] for role,v in d['arp_packet_diagnostics'].items()},trace_status={role:v['status'] for role,v in d['arp_packet_diagnostics'].items()},sensor_measurement=d['measurement_window'])
            s['non_success_commands']=[c for c in d['results']['commands'] if c.get('terminal')!=4]
            s['non_success_journal_audits']=[v for v in a['progress']['entries'] if v['terminal']!=4]
        else:s.update(run=str(p.relative_to(ROOT)),trace_status=d.get('analysis',{}).get('trace',{}),packet_counts=d.get('analysis',{}).get('counts',{}))
    summary.append(dict(cohort=cohort,source_commit=e['source_commit'],rows=rows))
    if cohort=='loaded':assert e['runtime_unchanged'];before={**e['runtime_before'],**e['observer_before']};assert before=={**e['runtime_after'],**e['observer_after']}
    else:assert e['binaries_unchanged'];before=e['binaries_before'];assert before==e['binaries_after']
    # Tracer V1 intentionally differs after diagnostic bugfix. Existing10 never differ.
    assert all(sha(ROOT/name)==before[name] for name in RUNTIMES+OBSERVERS)
containers=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines();nets=subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines();assert not any(c.startswith(n) for c in containers for n in networks);assert not set(nets)&set(networks)
for name,v in hashes.items():assert sha(ROOT/name)==v['sha256']
for name,v in [('local-artifact-hashes',hashes),('public-disposition',disposition),('source-verification',sourcechecks),('summary',summary),('cleanup',dict(owned_networks=networks,owned_networks_present=False,owned_containers_present=False,credentials_removed=True,raw_files=len(hashes)))]:write(out/(name+'.json'),v)
for name in ('loaded-live.log','live.log','live-v2.log','posthoc-host-tests.log'):shutil.copy2(ROOT/'.local/m3-arp-packet-trace-build'/name,out/'validation'/name)
print('Archived',len(hashes),'raw files and',len(networks),'removed owned networks; all source/binary/hash checks pass')
