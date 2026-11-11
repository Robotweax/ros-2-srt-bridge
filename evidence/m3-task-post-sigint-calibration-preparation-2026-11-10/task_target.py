"""One controlled worker released and observed absent after SIGINT; no SDK/ROS."""
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time
from shutdown_observer import identity,read_limited,task_identity

def write(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value)+'\n');temporary.replace(path)
def bound(value,context):
    if value!=context:raise ValueError('foreign fixture control')
def wait_file(path,deadline):
    while not path.exists() and time.monotonic()<deadline:time.sleep(.01)
    if not path.exists():raise ValueError('fixture control deadline exceeded: '+path.name)
    return json.loads(path.read_text())
def main(out,calibration_id,proc=Path('/proc')):
    out=Path(out);root=identity(proc,os.getpid());release=threading.Event();started=threading.Event();stop=threading.Event();lock=threading.Lock();sequence=0;failure=[]
    def stage(point,**fields):
        nonlocal sequence
        with lock:
            sequence+=1;stamp=time.monotonic_ns()
            with (out/'task-stages.jsonl').open('a') as log:log.write(json.dumps(dict(sequence=sequence,point=point,monotonic_ns=stamp,pid=root['pid'],tid=threading.get_native_id(),dropped_before=0,calibration_id=calibration_id,**fields))+'\n')
            return stamp
    def worker():
        try:
            tid=threading.get_native_id();task=task_identity(read_limited(proc/str(root['pid'])/'task'/str(tid)/'stat'),tid)
            if task['status']!='known':raise ValueError('worker identity unavailable')
            stage('worker_started',task_identity=task['identity']);write(out/'worker-info.json',dict(task_identity=task['identity']));started.set()
            if not release.wait(20):raise ValueError('worker release deadline exceeded')
            stage('worker_return')
        except BaseException as error:failure.append(str(error));started.set()
    previous=signal.signal(signal.SIGINT,lambda *args:stop.set());child=threading.Thread(target=worker,name='calibration-task');child.start()
    try:
        if not started.wait(5) or failure:raise ValueError('worker startup failed: '+str(failure))
        info=json.loads((out/'worker-info.json').read_text());context=dict(calibration_id=calibration_id,target_pid=root['pid'],target_start_ticks=root['start_ticks'],worker_tid=info['task_identity']['tid'],worker_start_ticks=info['task_identity']['start_ticks'])
        stage('fixture_ready');write(out/'fixture-ready.json',context)
        if not stop.wait(15):raise ValueError('initial signal deadline exceeded')
        seen=stage('fixture_sigint');write(out/'signal-seen.json',dict(**context,monotonic_ns=seen));deadline=time.monotonic()+4
        waiting=wait_file(out/'signal-wait.json',deadline);bound({k:v for k,v in waiting.items() if k!='wait_enter_ns'},context)
        authority=wait_file(out/'release-worker.json',deadline);bound(authority,dict(**context,phase='post-sigint',wait_enter_ns=waiting['wait_enter_ns']))
        if time.monotonic_ns()<waiting['wait_enter_ns']:raise ValueError('signal wait clock differs')
        release_ns=stage('worker_release');release.set();child.join(timeout=3)
        if child.is_alive() or failure:raise ValueError('worker did not join cleanly: '+str(failure))
        joined=stage('worker_joined');write(out/'worker-joined.json',dict(**context,joined=True,release_ns=release_ns,monotonic_ns=joined))
        authority=wait_file(out/'allow-exit.json',deadline);absence_end=authority.get('absence_end_ns')
        if type(absence_end) is not int or not joined<=absence_end<=time.monotonic_ns():raise ValueError('absence acknowledgement time differs')
        bound(authority,dict(**context,phase='post-sigint-exit',absence_end_ns=absence_end));stage('absence_acknowledged',absence_end_ns=absence_end);stage('fixture_exit');return 0
    finally:
        release.set();child.join(timeout=5);signal.signal(signal.SIGINT,previous)
if __name__=='__main__':raise SystemExit(main(Path(sys.argv[1]),sys.argv[2]))
