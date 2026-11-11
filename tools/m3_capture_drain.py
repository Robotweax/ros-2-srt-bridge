"""Opt-in bounded tcpdump statistics stability check; final footer/file gate unchanged."""
import json,re,time
from pathlib import Path

INFO=re.compile(r'(\d+) packets? captured,\s*(\d+) packets? received by filter,\s*(\d+) packets? dropped by kernel')
SIGNAL_CODE='''import pathlib,os,signal,time,json,sys
name=sys.argv[1];expected=json.loads(sys.argv[2]);begin=time.monotonic_ns();found=[]
for p in pathlib.Path('/proc').glob('[0-9]*/comm'):
 try:
  if p.read_text().strip()!='tcpdump':continue
  pid=int(p.parent.name);stat=(p.parent/'stat').read_text();fields=stat[stat.rindex(')')+2:].split();identity=[pid,int(fields[19])]
  if expected and identity not in expected:raise RuntimeError('recorder identity changed')
  found.append(identity)
 except (FileNotFoundError,ProcessLookupError):pass
if len(found)!=1:raise RuntimeError('requires one owned tcpdump')
for pid,start in found:os.kill(pid,getattr(signal,name))
if name=='SIGSTOP':
 deadline=time.monotonic()+1
 while True:
  stat=pathlib.Path('/proc',str(found[0][0]),'stat').read_text();state=stat[stat.rindex(')')+2:].split()[0]
  if state in ('T','t'):break
  if time.monotonic()>deadline:raise RuntimeError('recorder did not pause')
  time.sleep(.01)
print(json.dumps(dict(begin_ns=begin,end_ns=time.monotonic_ns(),signal=name,identities=found)))
'''


def signal_recorder(lab,role,label,name,expected=None):
    if role not in lab.containers or name not in ('SIGUSR1','SIGSTOP','SIGCONT','SIGINT'):raise ValueError('invalid owned recorder signal')
    return json.loads(lab.inside(role,label,['python3','-c',SIGNAL_CODE,name,json.dumps(expected or [])]))


def live_info(text):
    values=INFO.findall(text)
    if not values:return None
    captured,filtered,dropped=map(int,values[-1]);return dict(captured=captured,filtered=filtered,kernel_drops=dropped)


def stable(previous,current):
    return bool(previous and set(previous)==set(current) and all(current[role]['counts']==previous[role]['counts'] and current[role]['identities']==previous[role]['identities'] and current[role]['counts']['captured']==current[role]['counts']['filtered'] and current[role]['counts']['kernel_drops']==0 for role in current))


def check(lab,run):
    path=Path(run)/'capture-drain.json'
    if path.exists():raise FileExistsError('drain result already exists')
    report=dict(status='running',snapshots=[],clock='host monotonic for controller reads; nested signal brackets are VM monotonic',scope='two unchanged equal captured/filter snapshots before stop; finite timeout, not proof of future silence; final footer/file gate still required')
    previous=None;deadline=time.monotonic()+5;attempt=0
    try:
        while time.monotonic()<deadline:
            attempt+=1;current={}
            for role in lab.containers:
                log=Path(run)/(role+'-capture.log');offset=len(log.read_text());before=time.monotonic_ns()
                identity=signal_recorder(lab,role,'drain-info-'+str(attempt)+'-'+role,'SIGUSR1',previous[role]['identities'] if previous else None)
                wait_until=min(deadline,time.monotonic()+1);info=None
                while time.monotonic()<wait_until:
                    info=live_info(log.read_text()[offset:])
                    if info is not None:break
                    time.sleep(.02)
                if info is None:raise RuntimeError('missing fresh tcpdump live statistics')
                if info['kernel_drops']:raise RuntimeError('kernel drops during drain')
                current[role]=dict(counts=info,identities=identity['identities'],signal=identity,host_read_ns=[before,time.monotonic_ns()])
            report['snapshots'].append(current)
            if stable(previous,current):report['status']='stable_equal';return report
            previous=current;time.sleep(.2)
        raise RuntimeError('capture counters did not settle within drain budget')
    except Exception as error:report.update(status='failed',error=str(error));raise
    finally:
        with path.open('x') as file:file.write(json.dumps(report,indent=2)+'\n')
