"""Archive fresh, closed probe calibration; never execute or recover commands."""
import json,shutil,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,IMAGE
from m3_runtime_layout import matched,paths
from m3_command_trace import summarize
from m3_probe_trace_analysis import summarize as probes
from m3_dds_result_timeline import read_journal

out=ROOT/'evidence/m3-probe-tracing-2026-11-09';before=json.loads((out/'baseline-before.json').read_text());assert before==matched(ROOT,'sender-visibility')
source=json.loads((out/'build-source-sha256.json').read_text());assert all(sha(ROOT/n)==h for n,h in source.items())
selected=paths('probe-tracing')[:-1]+[str(p.relative_to(ROOT)) for p in sorted((ROOT/'install/bridge-probe-tracing/lib').glob('lib*.a'))]+['build/m3-probe-tracing/tests/native/probe_trace_tests']
write(out/'binary-verification.json',dict(new_matched_build_binaries={n:sha(ROOT/n) for n in selected},installed_baseline=before['preserved_baseline_sha256'],preserved_start_trace=before['preserved_start_trace_sha256'],preserved_sender_visibility=before['matched_build_sha256']))
layout=matched(ROOT,'probe-tracing');capture=ROOT/'.local/m3-probe-tracing-calibration-2026-11-09'
raw={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size,disposition='complete trace copied publicly' if p.suffix=='.log' else 'fresh synthetic SQLite/owner file retained locally; immutable journal selection in calibration.json') for p in sorted(capture.rglob('*')) if p.is_file()}
rows=[];(out/'traces').mkdir(exist_ok=True)
for family in ('ipv4','ipv6'):
    for mode in ('enabled','disabled'):
        run=capture/family/mode;traces={r+'-bridge-0.log':summarize(run/(r+'.log')) for r in ('operator','robot')};assert all(t['complete'] for t in traces.values())
        sender=read_journal(run/'sender.sqlite',1);receiver=read_journal(run/'receiver.sqlite',2)
        assert len(sender['entries'])==len(receiver['entries'])==1;identity=next(iter(sender['entries']));assert identity!=(118).to_bytes(16,'little').hex()
        a=sender['entries'][identity];b=receiver['entries'][identity]
        assert a['state']==b['state']==4 and a['revision']==b['revision']==3 and a['result_valid'] and b['result_valid'] and a['result_generation']==b['result_generation']==1
        assert a['deadline_ns']==a['source_ns']+5000000000
        if mode=='enabled':
            analysis=probes(traces);assert len(analysis['lifecycles'])>=4 and sum(l['qualified_mapper_admissions'] for l in analysis['lifecycles'])>=4
            assert all(l['queue']['value']==0 and len([e for e in l['sdk'] if e['value']==0])==1 and l['peer_admission'] and l['reply_queue'] and len([e for e in l['reply_sdk'] if e['value']==0])==1 and l['qualified_mapper_admissions']==1 for l in analysis['lifecycles'])
        else:assert not any(e['point']>=50 for t in traces.values() for e in t['events']);analysis=dict(disabled=True)
        for role in ('operator','robot'):shutil.copyfile(run/(role+'.log'),out/'traces'/(family+'-'+mode+'-'+role+'.log'))
        rows.append(dict(family=family,mode=mode,identity=identity,sender=a,receiver=b,probe_analysis=analysis))
assert all(sha(ROOT/n)==v['sha256'] for n,v in raw.items());prior_count=0
for folder in ('m3-start-broader-seeds-2026-11-09','m3-sender-visibility-2026-11-09','m3-sender-loaded-cohort-2026-11-09','m3-sender-loaded-repair-cohort-2026-11-09'):
    entries=json.loads((ROOT/'evidence'/folder/'local-artifact-hashes.json').read_text());assert all(sha(ROOT/n)==v['sha256'] for n,v in entries.items());prior_count+=len(entries)
write(out/'local-artifact-hashes.json',raw);write(out/'calibration.json',dict(image=IMAGE,rows=rows,new_raw_files=len(raw),prior_raw_rechecked=prior_count,scope='Four fresh successful loopback commands and reciprocal healthy probe renewals. No loaded cohort, live fault, forced command expiry or historical118 replay. No application journal recovery.'))
store=ROOT/'.local/m3-probe-tracing-buildlogs';store.mkdir(exist_ok=True);build_raw=store/'sdk-build.log'
if not build_raw.exists():shutil.copyfile(out/'validation/sdk-build.log',build_raw)
normalization={}
for raw_log,target in ((build_raw,out/'validation/sdk-build.log'),(ROOT/'build/m3-probe-tracing/Testing/Temporary/LastTest.log',out/'validation/sdk-LastTest.log')):
    target.write_text('\n'.join(line.rstrip() for line in raw_log.read_text().splitlines()).rstrip()+'\n');normalization[str(target.relative_to(ROOT))]=dict(raw_source=str(raw_log.relative_to(ROOT)),raw_sha256=sha(raw_log),public_sha256=sha(target),change='Trailing whitespace/final empty lines only; no nonempty lines omitted')
write(out/'validation/display-normalization.json',normalization)
assert matched(ROOT,'probe-tracing')==layout
write(out/'source-sha256.json',{str(p.relative_to(ROOT)):sha(p) for folder in ('src','ros2','tools','tests','cmake') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in str(p)})
print('Archived4 fresh success controls,8 qualified correlated probe renewals;',len(raw),'newraw and',prior_count,'priorraw fixed; old runtime baselines preserved')
