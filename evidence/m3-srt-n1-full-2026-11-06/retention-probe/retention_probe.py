"""Bounded UDP volume probe: distinguish rotating-file overwrite from kernel drops."""
import hashlib,json,subprocess,sys,time
from collections import Counter
from pathlib import Path
sys.path.insert(0,'tools')
from m3_network import NetworkLab
from m3_capture import pcap_options,stop_captures,validate_tcpdump_footer
from m3_tap_probe import probe_id,pcap_records
import m3_monotonic_capture as mono
root=Path.cwd();base=root/'.local/srt-n1-full-dev/retention-probe';base.mkdir(exist_ok=False)
image=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64','ros2-srt-m3:20261105'],text=True))[0]['RepoDigests'][0];results=[]
for number,files in enumerate((2,4),1):
 run=base/str(files);run.mkdir();inside='/workspace/'+str(run.relative_to(root));cred=run/'passphrase';cred.touch(mode=0o600);cred.write_text('unused-probe-credential')
 lab=NetworkLab(root,run,image,monotonic_capture=True);caps=[];server=None
 try:
  lab.start(cred);lab.inside('robot','warm',['ping','-c','1','-W','1',lab.addresses['operator']])
  for role,name in lab.containers.items():
   log=(run/(role+'-capture.log')).open('w');p=subprocess.Popen(['docker','exec',name]+pcap_options()+['-C','1','-W',str(files),'-w',inside+'/'+role+'.pcap','udp'],stdout=log,stderr=subprocess.STDOUT);caps.append((p,log))
  mono.start(run,inside,lab,caps)
  log=(run/'receiver.log').open('w');server=subprocess.Popen(['docker','exec',lab.containers['operator'],'python3','tools/m3_tap_probe.py','receive','--out',inside+'/received.json','--ready',inside+'/ready','--stop',inside+'/stop'],stdout=log,stderr=subprocess.STDOUT)
  deadline=time.monotonic()+5
  while not (run/'ready').exists() or not all('listening on eth0' in (run/(r+'-capture.log')).read_text() for r in lab.containers):
   if time.monotonic()>deadline:raise RuntimeError('not ready')
   time.sleep(.01)
  lab.inside('robot','send',['python3','tools/m3_tap_probe.py','send','--peer',lab.addresses['operator'],'--case',str(number),'--count','2000','--out',inside+'/sent.json'])
  lab.inside('robot','control',['python3','tools/m3_tap_probe.py','send','--peer',lab.addresses['operator'],'--case',str(number+1000),'--count','1','--out',inside+'/control.json'])
  time.sleep(.1);(run/'stop').touch();assert server.wait(timeout=5)==0;log.close();server=None
 finally:
  try:
   if server and server.poll() is None:server.terminate();server.wait(timeout=5)
   stop_captures(lab)
   for p,log in caps:p.wait(timeout=5);log.close()
  finally:lab.cleanup();cred.unlink(missing_ok=True)
 assert len(json.loads((run/'received.json').read_text())['rows'])==2001;result=dict(file_megabytes=1,file_count=files,application_datagrams=2001,endpoints={})
 for role in ('robot','operator'):
  native=[r for r in mono.records(run/(role+'.mono')) if probe_id(r['prefix'])];pcap=[r for p in sorted(run.glob(role+'.pcap*')) for r in pcap_records(p) if r['identity']]
  status=json.loads((run/(role+'-monotonic-capture.log')).read_text().splitlines()[-1]);assert status['complete'] and not status['reserve_failed'] and not status['copy_failed'] and len(native)==2001
  footer=(run/(role+'-capture.log')).read_text();import re
  drops=int(re.findall(r'(\d+) packets? dropped by kernel',footer)[-1]);captured=int(re.findall(r'(\d+) packets? captured',footer)[-1]);assert drops==0 and captured==2001
  try:validate_tcpdump_footer(footer,len(pcap));rejected=False
  except ValueError:rejected=True
  if files==2:assert len(pcap)<2001 and rejected
  else:assert len(pcap)==2001 and not rejected and Counter((*probe_id(r['prefix']),r['length']) for r in native)==Counter((*r['identity'],r['length']) for r in pcap)
  assert sum(r['identity'][0]==number+1000 for r in pcap)==1
  result['endpoints'][role]=dict(native_known=2001,pcap_known=len(pcap),reported_captured=captured,kernel_drops=drops,file_gate_rejected=rejected,files_written=len(list(run.glob(role+'.pcap*'))),retained_bytes=sum(p.stat().st_size for p in run.glob(role+'.pcap*')))
 results.append(result);(base/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(result,flush=True)
