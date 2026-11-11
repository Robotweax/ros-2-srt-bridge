"""Closed SDK/ROS calibration archive; original installed baseline stays fixed."""
import hashlib,json,re,shutil,subprocess,sys
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_command_trace import summarize
from m3_start_trace_analysis import analyze
from m3_dds_result_timeline import read_journal
out=ROOT/'evidence/m3-start-tracing-2026-11-09';base=ROOT/'.local/m3-start-tracing';build=ROOT/'build/m3-start-trace-qualified';pre=json.loads((out/'preflight.json').read_text());raw=set(p for p in base.rglob('*') if p.is_file() and not p.is_symlink());raw.add(build/'Testing/Temporary/LastTest.log');sources={};changed=[]
for name,h in pre['source_sha256'].items():
 if sha(ROOT/name)!=h:
  original=subprocess.check_output(['git','show',pre['source_commit']+':'+name],cwd=ROOT);assert hashlib.sha256(original).hexdigest()==h;changed.append(name)
assert set(changed)=={'tools/m3_start_trace_analysis.py','tools/run_m3.py','tests/test_m3_start_trace_analysis.py'}
for name,h in pre['binaries'].items():assert sha(ROOT/name)==h
baseline=json.loads((out/'baseline-before.json').read_text());assert all(sha(ROOT/n)==h for n,h in baseline.items())
old=ROOT/'evidence/m3-command34-start-fence-2026-11-09/binary-before.json';old_binaries=json.loads(old.read_text());assert all(sha(ROOT/n)==h for n,h in old_binaries.items())
old_manifests=[ROOT/'evidence/m3-arp-packet-tracing-2026-11-09/local-artifact-hashes.json',ROOT/'evidence/m3-command34-start-fence-2026-11-09/local-artifact-hashes.json'];original_count=0
for p in old_manifests:
 m=json.loads(p.read_text());assert all(sha(ROOT/n)==v['sha256'] for n,v in m.items());original_count+=len(m)
summary=[];journals=[];disposition={};selection={}
old_joins=json.loads((out/'calibration-joins.json').read_text());old_branches={r['path']:[x['branch'] for x in r['branches']] for r in old_joins}
for folder in sorted((build/'tests/native').glob('start-trace-*')):
 for phase in range(4):
  run=folder/str(phase);raw.update(p for p in run.rglob('*') if p.is_file());target=out/'calibration'/folder.name/str(phase);target.mkdir(parents=True,exist_ok=False)
  for role in ('robot','operator'):
   p=run/(role+'.log');r=summarize(p);assert r['complete'];rows=analyze(r['events']);shutil.copy2(p,target/p.name);raw.add(p);selection[p]=target/p.name
   if role=='robot':
    assert old_branches[str(p.relative_to(ROOT))]==[x['branch'] for x in rows]
    summary.append(dict(run=folder.name,phase=phase,trace_records=r['records'],branches=rows,trace_complete=True,scope='Two independent fixture invocations corresponding to passing IPv4/IPv6 CTests; paths retain process IDs, no IP family field is invented in events'))
  for side,number in (('sender',1),('receiver',2)):
   p=run/(side+'.sqlite');r=read_journal(p,number);assert len(r['entries'])==1;raw.add(p);journals.append(dict(path=str(p.relative_to(ROOT)),fixture=folder.name,phase=phase,side=side,**r))
for folder in sorted((build/'tests/native').glob('execution-start-*')):
 for p in folder.rglob('*'):
  if p.is_file():raw.add(p)
 for p in sorted(folder.glob('*/receiver.sqlite')):
  journals.append(dict(path=str(p.relative_to(ROOT)),fixture=folder.name,phase=int(p.parent.name),side='receiver',**read_journal(p,2)))
ros=ROOT/'build/m3-start-trace-ros'
for p in ros.rglob('*.xml'):
 if 'test_results' in p.parts:raw.add(p)
for p in ros.rglob('LastTest.log'):raw.add(p)
log=(build/'Testing/Temporary/LastTest.log').read_text();worker_rows=[];current=''
for line in log.splitlines():
 if ' Testing: ' in line:current=line.split(' Testing: ',1)[1]
 if line.startswith('WORKER_START_OBSERVATION '):worker_rows.append(dict(test=current,**json.loads(line.split(' ',1)[1])))
assert len(worker_rows)==12
assert '100% tests passed, 0 tests failed out of 75' in (base/'sdk-tests.log').read_text();assert 'Summary: 41 tests, 0 errors, 0 failures, 0 skipped' in (base/'ros-tests.log').read_text();assert 'Ran 364 tests' in (base/'host-final-guards.log').read_text()
for p in sorted(raw):
 name=str(p.relative_to(ROOT));target=selection.get(p)
 if p==build/'Testing/Temporary/LastTest.log':target=out/'validation/sdk-LastTest.log'
 elif p.parent==base and p.suffix=='.log':target=out/'validation'/p.name
 if target:
  target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists():shutil.copy2(p,target)
  disposition[name]=dict(kind='verbatim',public=str(target.relative_to(out)),public_sha256=sha(target))
 else:disposition[name]=dict(kind='local_only_omitted',reason='Controlled SQLite streams or complete compiler/ROS test metadata retained locally by hash; immutable journal and test-log selections published')
hashes={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(raw)}
newpaths=[*pre['binaries'],*[str(p.relative_to(ROOT)) for p in (ROOT/'install/bridge-start-trace-qualified').rglob('*') if p.is_file() and (p.suffix=='.a' or p.name=='robotweax-journal-worker')],*[str(p.relative_to(ROOT)) for p in (ROOT/'install/m3-start-trace-ros').rglob('*') if p.is_file() and p.name in ('bridge_node','ros_rate_worker','dds_command_node','rate_simulator')]]
containers=subprocess.check_output(['docker','ps','-a','--filter','ancestor='+pre['image'],'--format','{{.ID}}'],text=True).splitlines();assert not containers
for name,value in [('calibration-joins-final',summary),('closed-journals',journals),('worker-consume-calibration',worker_rows),('local-artifact-hashes',hashes),('public-disposition',disposition),('source-verification',dict(frozen_source=pre['source_commit'],producers_and_cpp_tests_unchanged=True,original_source_git_blobs_verified=True,reader_only_changes_after_closed_sdk=changed,final_reader_sha256=sha(ROOT/'tools/m3_start_trace_analysis.py'))),('binary-verification',dict(installed_baseline=baseline,baseline_unchanged=True,previous_fourteen_unchanged=True,new_matched_build_binaries={n:sha(ROOT/n) for n in newpaths},provider_commit=subprocess.check_output(['git','-C','.deps/srt','rev-parse','HEAD'],text=True).strip())),('validation/results',dict(sdk_tests=75,ros_tests=41,host_tests=364,all_passed=True,original_raw_rehashed=original_count,new_raw_files=len(hashes),new_native_fixture_cases=8,new_native_trace_loss=0,original_failures_reclassified=False,installed_baseline_changed=False,no_tuning=True,no_new_n5_cohort=True,pinned_image_containers_remaining=0,failed_build_preparation_retained=True,pr2_draft=True,m3_complete=False,intrinsic_m4_touched=False))]:write(out/(name+'.json'),value)
print('Archived',len(hashes),'new raw files;',original_count,'old raw hashes verified; original baseline and prior14 binaries fixed;8 trace cases complete')
