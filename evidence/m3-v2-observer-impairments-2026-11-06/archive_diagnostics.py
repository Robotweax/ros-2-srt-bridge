import hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,'.local/v2-observer-study-dev')
from audit_journals import audit
out=Path('evidence/m3-v2-observer-impairments-2026-11-06');dev=Path('.local/v2-observer-study-dev')
def dump(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
initial=out/'failed-buffer4096';initial.mkdir(exist_ok=True);base=Path('.local/m3-observer-study/20261106-v2')
for name in ('plan.json','study.json'):shutil.copyfile(base/name,initial/name)
study=json.loads((base/'study.json').read_text());assert study['status']=='failed' and len(study['rows'])==8
raw=[];audits=[]
for row in study['rows']:
 run=Path(row['run']);dest=initial/row['slot']['label'];dest.mkdir(exist_ok=True)
 for name in ('run.json','operator-result.json','robot-capture.log','operator-capture.log','robot-monotonic-capture.log','operator-monotonic-capture.log'):
  if (run/name).exists():shutil.copyfile(run/name,dest/name)
 audits.append(audit(run))
 for p in run.iterdir():
  if p.suffix in ('.mono','.sqlite','.jsonl') or '.pcap' in p.name:raw.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
dump(initial/'journal-audits.json',audits);dump(initial/'raw-artifacts.json',raw)
diag=out/'ring-diagnostic';diag.mkdir(exist_ok=True)
for name in ('ring_trace.c','ring_probe.py','ring-4096.log','ring-16384.log','ring-32768.log'):
 shutil.copyfile(dev/name,diag/name)
base=dev/'ring-capacity-verified';shutil.copyfile(base/'results.json',diag/'results.json');raw=[]
for buffer in ('4096','32768'):
 dest=diag/buffer;dest.mkdir(exist_ok=True)
 for p in (base/buffer).iterdir():
  if p.name in ('robot-capture.log','operator-capture.log','robot-monotonic-capture.log','operator-monotonic-capture.log','robot-signal-SIGSTOP.log','operator-signal-SIGSTOP.log','robot-signal-SIGCONT.log','operator-signal-SIGCONT.log','sent.json','control.json','received.json'):
   shutil.copyfile(p,dest/p.name)
  if p.suffix in ('.mono','.pcap'):raw.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
dump(diag/'raw-artifacts.json',raw)
shutil.copyfile(dev/'archive_study.py',out/'archive_study.py');shutil.copyfile(dev/'archive_diagnostics.py',out/'archive_diagnostics.py')
print('archived failed eight-case study and verified ring diagnostic')
