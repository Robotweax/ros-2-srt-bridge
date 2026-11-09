"""Read-only failed-cohort archive. Offline evidence never promotes its verdict."""
import copy,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_runtime_layout import matched
from m3_capture import summarize,validate_tcpdump_footer
from m3_monotonic_capture import summarize_run as native_summary
from m3_admission_diagnostics import analyze as command_analysis
from m3_loaded_start_analysis import analyze as start_analysis

out=ROOT/'evidence/m3-sender-loaded-cohort-2026-11-09';base=ROOT/'.local/m3-sender-loaded-cohort-2026-11-09'
execution=json.loads((base/'execution.json').read_text());hashes=json.loads((out/'local-artifact-hashes.json').read_text())
assert [r['status'] for r in execution['rows']]==['failed','not_executed'] and execution['rows'][0]['exit_code']==1
assert execution['runtime_unchanged'] and execution['matched_after']==execution['runtime_layout']==matched(ROOT,'sender-visibility')
run=ROOT/execution['rows'][0]['run'];original=json.loads((run/'run.json').read_text());network=json.loads((run/'network.json').read_text())
assert original['status']=='failed' and original['capture_error']=="cannot access local variable 'summarize' where it is not associated with a value"
assert all(sha(ROOT/n)==v['sha256'] for n,v in hashes.items())
frozen=json.loads((out/'frozen-source-verification.json').read_text());assert frozen['all_captured_source_hashes_match_before_fix']
changed=[n for n,h in original['source_sha256'].items() if sha(ROOT/n)!=h]
assert changed==['tools/run_m3.py'],changed
before=subprocess.check_output(['git','show',execution['source_commit']+':tools/run_m3.py'],text=True)
import hashlib
assert hashlib.sha256(before.encode()).hexdigest()==original['source_sha256']['tools/run_m3.py']
assert not (run/'passphrase').exists()
captures={}
for role,address in network['addresses'].items():
    value=summarize(sorted(run.glob(role+'.pcap*')),address)
    value.update(validate_tcpdump_footer((run/(role+'-capture.log')).read_text(),value['records']))
    assert value['tcpdump_population_reconciled'] and not value['unaccounted'];captures[role]=value
native=native_summary(run,network['addresses'],original['endpoint_measurements'],allow_udp_fragments=False,features=original['monotonic_capture_config']['features_before'])
assert all(s['complete'] and s['artifact_version']==2 and s['time_namespace_zero'] for s in native['statuses'].values())
audit=command_analysis(original,run);starts=start_analysis(run,hashes)
assert audit['progress']['audit']['all_succeeded'] and len(starts['all_attempts'])==8
sender=original['sender_diagnostics'];assert sender['counts']['45']==0
roots={}
for role in network['addresses']:
    def config(p):return [{k:r.get(k) for k in ('kind','handle','parent','root','options')} for r in json.loads(p.read_text())]
    a=config(run/('before-'+role+'.log'));b=config(run/('after-'+role+'.log'));assert a==b
    assert json.loads((run/('features-before-'+role+'.log')).read_text())==json.loads((run/('features-after-'+role+'.log')).read_text())
    roots[role]=dict(unchanged=True,before=a,after=b)
write(out/'offline-audit.json',dict(original_harness_status='failed',original_exit_code=1,promoted=False,
    capture_redecode=captures,native_redecode=native,commands=audit,starts=starts,sender=sender,
    root_configurations=roots,arp_packet_counts={r:v['counts'] for r,v in original['arp_packet_diagnostics'].items()},
    scope='Post-closure read-only decoding of retained N0 artifacts. Original harness failure and stopped N5 remain. No loaded result or sender deferral captured.'))
dest=out/'sender-N0-1701';dest.mkdir(exist_ok=True);disposition={}
for name,value in hashes.items():
    p=ROOT/name;entry=dict(kind='local_only',reason='Complete packet/native/provider/SQLite/sample or host metadata retained locally by original hash')
    target=None;selection=None
    if p.name=='network.json':
        selection=json.dumps({k:network[k] for k in ('network','addresses','events','isolation')},indent=2)+'\n';target=dest/'network-selected.json';entry['omitted_fields']=[k for k in network if k not in ('network','addresses','events','isolation')]
    elif p.name=='run.json':
        selected=copy.deepcopy(original);removed={}
        for stream in ('provider_diagnostics','sensor_provider_diagnostics'):
            for key,v in selected.get(stream,{}).items():
                removed[stream+'.'+key+'.records']=len(v.pop('records',[]))
                for c,cv in v.get('connections',{}).items():removed[stream+'.'+key+'.connections.'+c+'.adjacent_deltas']=len(cv.pop('adjacent_deltas',[]))
        for key,v in selected.get('command_diagnostics',{}).items():removed['command_diagnostics.'+key+'.events']=len(v.pop('events',[]))
        removed['sender_diagnostics.events']=len(selected['sender_diagnostics'].pop('events',[]))
        selection=json.dumps(selected,indent=2)+'\n';target=dest/'run-selected.json';entry['removed_fields']=removed
    elif p.suffix=='.json' or p.name.endswith('-arp-trace.jsonl'):target=dest/p.name
    elif p.suffix=='.log' and any(x in p.name for x in ('-bridge-','capture','trace','btf','profile-','before-','after-','drain','arp-reply','-scenario')):
        lines=[];omitted={}
        for line in p.read_text().splitlines(keepends=True):
            if line.startswith(('PROVIDER_STATS ','SENSOR_PROVIDER_STATS ')):
                reason=line.split(' ',1)[0];omitted[reason]=omitted.get(reason,0)+1
            else:lines.append(line)
        selection=''.join(lines) if omitted else None;target=dest/(p.stem+'-selected.log' if omitted else p.name)
        if omitted:entry['omitted_lines_by_category']=omitted
    if target:
        if selection is None:shutil.copyfile(p,target)
        else:target.write_text(selection)
        entry.update(kind='verbatim' if selection is None else 'derived_selection',public=str(target.relative_to(out)),public_sha256=sha(target))
    disposition[name]=entry
for src,target in ((base/'execution.json',out/'execution.json'),(base/'sender-N0-1701.log',out/'validation/original-harness.log'),(ROOT/'.local/m3-sender-loaded-live.log',out/'validation/live.log')):shutil.copyfile(src,target)
prior=0
for folder in ('m3-start-broader-seeds-2026-11-09','m3-sender-visibility-2026-11-09'):
    entries=json.loads((ROOT/'evidence'/folder/'local-artifact-hashes.json').read_text());assert all(sha(ROOT/n)==v['sha256'] for n,v in entries.items());prior+=len(entries)
containers=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines();nets=subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines()
assert not any(c.startswith(network['network']) for c in containers) and network['network'] not in nets
assert all(sha(ROOT/n)==v['sha256'] for n,v in hashes.items())
write(out/'public-disposition.json',disposition)
write(out/'cleanup.json',dict(owned_network=network['network'],owned_containers_absent=True,owned_network_absent=True,credentials_removed=True,roots_and_features_unchanged=True))
write(out/'validation/results.json',dict(original_harness_exit_code=1,outer_exit_code=1,cohort_passed=False,N5_executed=False,retried=False,host_before=389,host_after_fix=390,new_raw_rehashed=len(hashes),prior_raw_rehashed=prior,runtime_unchanged=True,observers_unchanged=True,source_change_after_closure=changed,sdk77_ros41_exact_binary_qualification_reused=True,forced_expiry=False,tuning=False,intent118_replayed=False))
print('Archived failed N0 gate, stopped N5, offline8/8 and no sender deferral;',len(hashes),'raw and',prior,'prior raw verified')
