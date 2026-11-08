from pathlib import Path
import hashlib,json,re,shutil,subprocess,sys
root=Path.cwd();sys.path.insert(0,str(root/'tools'))
from m3_dds_result_timeline import read_journal
from m3_n5_progress import RUNTIMES
base=root/'.local/m3-controlled-clock-build';out=root/'evidence/m3-controlled-clock-rejection-2026-11-08';validation=out/'validation';validation.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,value):p.write_text(json.dumps(value,indent=2)+'\n')
log=(base/'sdk.log').read_text();assert '100% tests passed, 0 tests failed out of 71' in log
last=root/'build/m3-sdk/Testing/Temporary/LastTest.log';text=last.read_text()
protocol=[json.loads(line.split(' ',1)[1]) for line in text.splitlines() if line.startswith('CLOCK_REJECTION_CONTRACT ')]
native=[json.loads(line.split(' ',1)[1]) for line in text.splitlines() if line.startswith('CLOCK_REJECTION_NATIVE ')]
assert len(protocol)==3 and [p['case'] for p in protocol]==['control','expired','future'];assert len(native)==2
assert protocol[1]['age_error']==2 and protocol[1]['clock_error']==2 and protocol[2]['age_error']==9 and protocol[2]['clock_error']==0
assert all(n['sdk_handoffs']==1 and n['closed_unknown'] and n['effects']==0 for n in native)
threshold=(base/'runtime-before.json').stat().st_mtime
core=[p for p in (root/'build/m3-sdk/src/robotweax_srt_bridge_core').glob('admission-rejection-*') if p.stat().st_mtime>=threshold]
peers=[p.parent for p in (root/'build/m3-sdk/tests/native').glob('wire-errors-*/receiver-clock/sender.sqlite') if p.stat().st_mtime>=threshold]
assert len(core)==1 and len(peers)==2
journals={};hashes={}
for directory in [core[0]/'expired',core[0]/'future',*peers]:
 sender=read_journal(directory/'sender.sqlite',1);receiver=read_journal(directory/'receiver.sqlite',2)
 assert len(sender['entries'])==1 and not receiver['entries']
 entry=next(iter(sender['entries'].values()));assert entry['state']==8 and entry['reason']==2 and entry['revision']==0 and not entry['result_valid'] and entry['deadline_ns']-entry['source_ns']==5_000_000_000
 journals[str(directory.relative_to(root))]=dict(sender=sender,receiver=receiver,scope='closed controlled fixture journal audit only; absence/NOT_FOUND is not durable negative proof or replay authority')
 for p in directory.iterdir():
  if p.is_file():hashes[str(p.relative_to(root))]=dict(bytes=p.stat().st_size,sha256=sha(p))
before=json.loads((base/'runtime-before.json').read_text());after={p:sha(root/p) for p in RUNTIMES};assert before==after
assert after['install/srt-m0/lib/librobotweax-srt.a']==json.loads((root/'baselines/dependencies.json').read_text())['srt']['installed_library_sha256']
source=subprocess.check_output(['git','rev-parse','HEAD'],text=True,cwd=root).strip()
paths=['src/robotweax_srt_bridge_core/CMakeLists.txt','tests/protocol/admission_rejection_tests.cpp','tests/native/error_transport_tests.cpp']
source_hashes={p:sha(root/p) for p in paths}
assert all(hashlib.sha256(subprocess.check_output(['git','show',source+':'+p],cwd=root)).hexdigest()==h for p,h in source_hashes.items())
for name,value in [('results',dict(status='passed',source_commit=source,protocol_cases=protocol,native_cases=native,scope='controlled protocol and real SRT loopback uncertainty contracts, not N5 cause reproduction/acceptance',sdk_tests=71,host_tests=267,ros_tests_new=False,prior_ros_tests=41)),('closed-journal-audits',journals),('local-artifact-hashes',hashes),('runtime-verification',dict(before=before,after=after,unchanged=True)),('source-verification',dict(source_commit=source,sha256=source_hashes,matched=True)),('binaries', {str(p.relative_to(root)):sha(p) for p in [root/'build/m3-sdk/src/robotweax_srt_bridge_core/admission_rejection_tests',root/'build/m3-sdk/tests/native/error_transport_tests']})]:write(out/(name+'.json'),value)
for p in [base/'sdk.log',base/'host.log',last,Path(__file__)]:shutil.copy2(p,validation/p.name)
displays=[]
for p in validation.glob('*.log'):
 raw=p.read_bytes();p.write_text(''.join(l.rstrip()+'\n' for l in p.read_text().splitlines()));displays.append(dict(file=p.name,original_sha256=hashlib.sha256(raw).hexdigest(),public_sha256=sha(p),transform='trailing whitespace in validation console display only; local originals unchanged'))
write(validation/'display-normalization.json',displays)
print('Archived 3 protocol cases, 2 native family cases, 4 closed journal pairs, all8 runtime hashes unchanged')
