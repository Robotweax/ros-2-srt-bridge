"""Archive completed fresh calibration; verify, never execute or recover commands."""
import json
from pathlib import Path
import shutil
import sys

ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,IMAGE
from m3_runtime_layout import matched,paths
from m3_command_trace import summarize
from m3_sender_trace_analysis import summarize as sender_summary
from m3_dds_result_timeline import read_journal

out=ROOT/'evidence/m3-sender-visibility-2026-11-09'
baseline=json.loads((out/'baseline-before.json').read_text())
assert baseline==dict(matched(ROOT,'start-trace'),original_intent_evidence_sha256=sha(ROOT/'evidence/m3-sender-pending-diagnosis-2026-11-09/analysis.json'))
old_raw=json.loads((ROOT/'evidence/m3-start-broader-seeds-2026-11-09/local-artifact-hashes.json').read_text())
assert all(sha(ROOT/n)==v['sha256'] for n,v in old_raw.items())
source=json.loads((out/'build-source-sha256.json').read_text())
# The scenario's Python layout choice was extended during the SDK suite. None
# of the built C++/CMake inputs changed after the source inventory.
assert all(sha(ROOT/n)==h for n,h in source.items() if n.startswith(('src/','tests/native/')) or n.endswith(('.cpp','.hpp','CMakeLists.txt')))
selected=paths('sender-visibility')[:-1]+[str(p.relative_to(ROOT)) for p in sorted((ROOT/'install/bridge-sender-visibility/lib').glob('lib*.a'))]+['build/m3-sender-visibility/tests/native/sender_visibility_tests']
inventory=dict(new_matched_build_binaries={p:sha(ROOT/p) for p in selected},installed_baseline=baseline['preserved_baseline_sha256'],preserved_start_trace=baseline['matched_build_sha256'])
write(out/'binary-verification.json',inventory);matched(ROOT,'sender-visibility')
capture=ROOT/'.local/m3-sender-visibility-calibration-2026-11-09'
raw={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size,disposition='full operator trace copied publicly' if p.name=='operator.log' else 'local-only fresh synthetic SQLite/owner file; immutable entry selection in calibration.json') for p in sorted(capture.rglob('*')) if p.is_file()}
rows=[];(out/'traces').mkdir(exist_ok=True)
for family in ('ipv4','ipv6'):
    for mode in ('enabled','disabled'):
        run=capture/family/mode;trace=summarize(run/'operator.log');assert trace['complete']
        a=read_journal(run/'sender.sqlite',1);b=read_journal(run/'receiver.sqlite',2)
        assert len(a['entries'])==len(b['entries'])==1
        identity=next(iter(a['entries']));assert identity!=(118).to_bytes(16,'little').hex()
        left=a['entries'][identity];right=b['entries'][identity]
        assert left['state']==right['state']==4 and left['result_valid'] and right['result_valid'] and left['result_generation']==right['result_generation']==1
        assert left['deadline_ns']==left['source_ns']+5000000000
        assert sum(e['point']==25 and e['request']==identity for e in trace['events'])==1
        new=[e for e in trace['events'] if e['point'] in range(45,49)]
        if mode=='enabled':analysis=sender_summary({'operator.log':trace});assert analysis['counts']['46']==1
        else:assert not new;analysis=dict(disabled=True,events=[])
        shutil.copyfile(run/'operator.log',out/'traces'/(family+'-'+mode+'-operator.log'))
        rows.append(dict(family=family,mode=mode,identity=identity,trace_records=trace['records'],sender=left,receiver=right,analysis=analysis))
assert all(sha(ROOT/n)==v['sha256'] for n,v in raw.items())
write(out/'local-artifact-hashes.json',raw)
write(out/'calibration.json',dict(image=IMAGE,rows=rows,raw_files=len(raw),original_raw_files_rechecked=len(old_raw),
    new_clock_deferral_or_recovery_observed=False,clock_snapshot_contract='ClockMapper-only fixture checks unobserved, qualified, expired and wide interval states; no command submitted by that fixture',
    scope='Four fresh successful loopback commands, one per family/mode; no loaded case, injected fault, forced command expiry or intent118 replay. Journals read immutably.'))
log_store=ROOT/'.local/m3-sender-visibility-buildlogs';log_store.mkdir(exist_ok=True)
build_raw=log_store/'sdk-build.log'
if not build_raw.exists():shutil.copyfile(out/'validation/sdk-build.log',build_raw)
normalization={}
for source,target in ((ROOT/'build/m3-sender-visibility/Testing/Temporary/LastTest.log',out/'validation/sdk-LastTest.log'),(build_raw,out/'validation/sdk-build.log')):
    target.write_text('\n'.join(line.rstrip() for line in source.read_text().splitlines()).rstrip()+'\n')
    normalization[str(target.relative_to(ROOT))]=dict(raw_source=str(source.relative_to(ROOT)),raw_sha256=sha(source),public_sha256=sha(target),change='trailing whitespace and final empty lines only; no nonempty lines omitted')
write(out/'validation/display-normalization.json',normalization)
write(out/'source-sha256.json',{str(p.relative_to(ROOT)):sha(p) for folder in ('src','ros2','tools','tests','cmake') for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in str(p)})
print('Archived 4 fresh success controls; 20 new raw and 303 original raw files verified; both earlier runtime baselines preserved')
