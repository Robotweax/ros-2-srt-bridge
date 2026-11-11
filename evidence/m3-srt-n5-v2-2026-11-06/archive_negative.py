from pathlib import Path
import hashlib,json,shutil
out=Path('evidence/m3-srt-n5-v2-2026-11-06');dest=out/'development-competitor-stop';dest.mkdir(exist_ok=True);dev=Path('.local/srt-n5-v2-dev');d=json.loads((dev/'competitor-fault.json').read_text());run=Path(d['run'])
for name in ('competitor-fault.json','competitor_fault.py','python-tests.log'):shutil.copyfile(dev/name,dest/name)
for name in ('run.json','robot-capture.log','operator-capture.log','robot-monotonic-capture.log','operator-monotonic-capture.log','profile-robot-readback.log','profile-operator-readback.log'):
 if (run/name).exists():shutil.copyfile(run/name,dest/name)
raw=[]
for p in run.iterdir():
 if p.suffix in ('.sqlite','.mono','.jsonl') or '.pcap' in p.name or p.name=='competing-traffic.json':raw.append(dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
(dest/'raw-artifacts.json').write_text(json.dumps(raw,indent=2)+'\n')
(dest/'README.md').write_text('''# Expected negative competitor-stop test

This is deliberately interrupted development coverage, separate from the frozen
three-repetition positive N5 cohort. A real measurement-start marker precedes
SIGINT to the sole iperf client in the owned robot container. The runner returns
failed with the competitor-exited error, despite valid offered load up to the
stop. This proves that an early-ended competitor cannot leave an uncontended
remainder accepted as N5. Early abort lacks endpoint_measurements, so capture
window analysis also fails; no complete workload, capture-window or closed-
journal acceptance is claimed. Raw artifacts remain local with hashes.
''')
shutil.copyfile(dev/'archive_negative.py',out/'archive_negative.py');print('archived expected negative test')
