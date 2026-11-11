import hashlib,json,os,signal,socket,subprocess,sys,time
from pathlib import Path
from collections import Counter
sys.path.insert(0,'tools')
from m3_network import NetworkLab
from m3_capture import pcap_options,stop_captures,validate_tcpdump_footer
import m3_monotonic_capture as mono
from m3_tap_probe import probe_id,pcap_records
root=Path.cwd();base=root/'.local/v2-observer-study-dev/ring-capacity-verified';base.mkdir(exist_ok=False)
image=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64','ros2-srt-m3:20261105'],text=True))[0]['RepoDigests'][0]
results=[]
for number,buffer in enumerate((4096,32768),1):
 run=base/str(buffer);run.mkdir();inside='/workspace/'+str(run.relative_to(root));cred=run/'passphrase';cred.touch(mode=0o600);cred.write_text('unused-probe-credential')
 lab=NetworkLab(root,run,image,monotonic_capture=True);caps=[];server=None
 def signal_pcap(name):
  for role in lab.containers:
   code='import pathlib,os,signal,time\npids=[p.parent for p in pathlib.Path("/proc").glob("[0-9]*/comm") if p.read_text().strip()=="tcpdump"]\nassert len(pids)==1\np=pids[0];os.kill(int(p.name),getattr(signal,"'+name+'"));time.sleep(.05)\nstate=next(x for x in (p/"status").read_text().splitlines() if x.startswith("State:"))\nassert ("T" in state)==('+str(name=='SIGSTOP')+')\nprint(state)'
   lab.inside(role,role+'-signal-'+name,['python3','-c',code])
 try:
  lab.start(cred);lab.inside('robot','warm',['ping','-c','1','-W','1',lab.addresses['operator']])
  for role,name in lab.containers.items():
   log=(run/(role+'-capture.log')).open('w');p=subprocess.Popen(['docker','exec','-e','LD_PRELOAD=/workspace/.local/v2-observer-study-dev/ring_trace.so',name]+pcap_options(buffer_kib=buffer)+['-w',inside+'/'+role+'.pcap','udp'],stdout=log,stderr=subprocess.STDOUT);caps.append((p,log))
  mono.start(run,inside,lab,caps)
  log=(run/'receiver.log').open('w');server=subprocess.Popen(['docker','exec',lab.containers['operator'],'python3','tools/m3_tap_probe.py','receive','--out',inside+'/received.json','--ready',inside+'/ready','--stop',inside+'/stop'],stdout=log,stderr=subprocess.STDOUT)
  deadline=time.monotonic()+5
  while not (run/'ready').exists() or not all('listening on eth0' in (run/(r+'-capture.log')).read_text() for r in lab.containers):
   if time.monotonic()>deadline:raise RuntimeError('not ready')
   time.sleep(.01)
  signal_pcap('SIGSTOP');time.sleep(.05)
  lab.inside('robot','send',['python3','tools/m3_tap_probe.py','send','--peer',lab.addresses['operator'],'--case',str(number),'--count','400','--out',inside+'/sent.json'])
  signal_pcap('SIGCONT');time.sleep(.2)
  lab.inside('robot','control',['python3','tools/m3_tap_probe.py','send','--peer',lab.addresses['operator'],'--case',str(number+1000),'--count','1','--out',inside+'/control.json'])
  time.sleep(.1);(run/'stop').touch();assert server.wait(timeout=5)==0;log.close();server=None
 finally:
  try:
   signal_pcap('SIGCONT')
   if server and server.poll() is None:server.terminate();server.wait(timeout=5)
   stop_captures(lab)
   for p,log in caps:p.wait(timeout=5);log.close()
  finally:lab.cleanup();cred.unlink(missing_ok=True)
 app=json.loads((run/'received.json').read_text());assert len(app['rows'])==401;result=dict(buffer_kib=buffer,application_datagrams=400,endpoints={})
 for role in ('robot','operator'):
  native=[r for r in mono.records(run/(role+'.mono')) if probe_id(r['prefix'])];pcap=[r for r in pcap_records(run/(role+'.pcap')) if r['identity']]
  status=json.loads((run/(role+'-monotonic-capture.log')).read_text().splitlines()[-1]);assert status['complete'] and not status['reserve_failed'] and not status['copy_failed'] and len(native)==401
  footer=(run/(role+'-capture.log')).read_text();import re
  drops=int(re.findall(r'(\d+) packets? dropped by kernel',footer)[-1]);geometry=re.search(r'M3_RING_GEOMETRY block_size=(\d+) block_count=(\d+) frame_size=(\d+) frame_count=(\d+) bytes=(\d+) rc=0',footer);assert geometry
  try:c=validate_tcpdump_footer(footer,len(pcap));rejected=False
  except ValueError:rejected=True
  if buffer==4096:assert drops>0 and len(pcap)<401 and rejected
  else:assert not drops and len(pcap)==401 and not rejected and Counter((*probe_id(r['prefix']),r['length']) for r in native)==Counter((*r['identity'],r['length']) for r in pcap)
  assert sum(r['identity'][0]==number+1000 for r in pcap)==1
  result['endpoints'][role]=dict(native_known=401,pcap_known=len(pcap),kernel_drops=drops,file_gate_rejected=rejected,geometry=dict(zip(('block_size','block_count','frame_size','frame_count','allocated_bytes'),map(int,geometry.groups()))))
 results.append(result);(base/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(result,flush=True)
