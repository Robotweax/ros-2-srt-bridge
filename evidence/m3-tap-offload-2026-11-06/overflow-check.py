import json,signal,socket,subprocess,time
from pathlib import Path
out=Path('.local/tap-offload-dev/overflow-v2');out.mkdir(exist_ok=False)
with (out/'capture.log').open('w') as log:
 p=subprocess.Popen(['build/m3-monotonic-capture/monotonic_capture','lo',str(out/'packets.bin'),str(out/'ready.json'),'4096'],stdout=log,stderr=subprocess.STDOUT)
 try:
  deadline=time.monotonic()+5
  while not (out/'ready.json').exists():
   if p.poll() is not None or time.monotonic()>deadline:raise RuntimeError('not ready')
   time.sleep(.01)
  p.send_signal(signal.SIGSTOP);time.sleep(.05)
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as receiver,socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
   receiver.bind(('127.0.0.1',0))
   for _ in range(1000):sender.sendto(b'overflow-test',receiver.getsockname())
  p.send_signal(signal.SIGCONT);time.sleep(.2);p.send_signal(signal.SIGINT);code=p.wait(timeout=5)
 finally:
  if p.poll() is None:p.send_signal(signal.SIGCONT);p.terminate();p.wait(timeout=5)
r=json.loads((out/'capture.log').read_text().splitlines()[-1]);assert code==2 and r['complete'] is False and r['reserve_failed']>0 and r['seen']==r['submitted']+r['reserve_failed']+r['copy_failed']
(out/'result.json').write_text(json.dumps(dict(status='passed',expected_exit=2,actual_exit=code,capture=r,scope='intentional 4KiB ring overflow with stopped userspace; no measured application'),indent=2)+'\n');print((out/'result.json').read_text())
