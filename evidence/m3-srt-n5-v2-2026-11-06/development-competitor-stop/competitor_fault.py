from pathlib import Path
import json,subprocess,sys,time
root=Path.cwd();base=Path('.local/m3');existing={p.name for p in base.iterdir() if p.is_dir()};log=Path('.local/srt-n5-v2-dev/competitor-fault.log').open('w');p=subprocess.Popen([sys.executable,'tools/run_m3.py','--profile','N5','--smoke','--skip-build','--monotonic-capture'],stdout=log,stderr=subprocess.STDOUT);run=None;injected=False
try:
 deadline=time.monotonic()+90
 while time.monotonic()<deadline and p.poll() is None:
  new=[q for q in base.iterdir() if q.is_dir() and q.name not in existing and (q/'run.json').exists()]
  if new:
   assert len(new)==1;run=new[0]
   if (run/'measurement-start.json').exists():
    net=json.loads((run/'network.json').read_text());robot=net['containers']['robot'];assert robot.startswith('ros2-srt-m3-') and robot.endswith('-robot')
    code='import pathlib,os,signal\npids=[p.parent for p in pathlib.Path("/proc").glob("[0-9]*/comm") if p.read_text().strip()=="iperf3"]\nassert len(pids)==1\nos.kill(int(pids[0].name),signal.SIGINT)'
    subprocess.run(['docker','exec',robot,'python3','-c',code],check=True);injected=True;break
  time.sleep(.2)
 if not injected:raise RuntimeError('no qualified measurement marker before fault injection')
 assert p.wait(timeout=40)!=0
 d=json.loads((run/'run.json').read_text());assert d['status']=='failed' and d['error']=='N5 competitor exited before scenario completion'
 result=dict(run=str(run),injected_after_measurement_marker=True,expected_failure_observed=True,status=d['status'],error=d['error'],competitor_check=d.get('competitor_check'),capture_error=d.get('capture_error'),scope='development negative test only; deliberately interrupted workload/capture windows; not full N5 acceptance or a replacement case')
 Path('.local/srt-n5-v2-dev/competitor-fault.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
finally:
 if p.poll() is None:p.terminate();p.wait(timeout=30)
 log.close()
