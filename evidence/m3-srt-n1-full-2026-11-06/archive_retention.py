from pathlib import Path
import hashlib,json,shutil
out=Path('evidence/m3-srt-n1-full-2026-11-06');dev=Path('.local/srt-n1-full-dev');base=dev/'retention-probe';dest=out/'retention-probe';dest.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
shutil.copyfile(base/'results.json',dest/'results.json');shutil.copyfile(dev/'retention_probe.py',dest/'retention_probe.py');raw=[];isolation={}
for count in ('2','4'):
 run=base/count;sub=dest/count;sub.mkdir(exist_ok=True);isolation[count]={}
 for p in run.iterdir():
  if p.name in ('robot-capture.log','operator-capture.log','robot-monotonic-capture.log','operator-monotonic-capture.log','sent.json','control.json','received.json'):shutil.copyfile(p,sub/p.name)
  if p.suffix=='.mono' or '.pcap' in p.name:raw.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p)))
 for role in ('robot','operator'):
  host=json.loads((run/(role+'-inspect.log')).read_text())[0]['HostConfig'];assert not host['Privileged'] and not host['PortBindings'];isolation[count][role]=dict(cap_add=host['CapAdd'],privileged=False,published_ports=False,cgroup_namespace=host.get('CgroupnsMode'))
for name,d in [('raw-artifacts.json',raw),('isolation.json',isolation)]: (dest/name).write_text(json.dumps(d,indent=2)+'\n')
shutil.copyfile(dev/'python-tests.log',out/'python-tests.log');shutil.copyfile(dev/'archive_retention.py',out/'archive_retention.py')
print('archived bounded retention mechanism probe')
