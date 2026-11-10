"""Controlled task lifecycle only; no bridge, SDK, transport or workload command."""
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
def main(out,calibration_id,proc=Path('/proc')):
    out=Path(out);root=identity(proc,os.getpid());release=threading.Event();started=threading.Event();stop=threading.Event();lock=threading.Lock();sequence=0;failure=[]
    def stage(point,**fields):
        nonlocal sequence
        with lock:
            sequence+=1
            with (out/'task-stages.jsonl').open('a') as log:log.write(json.dumps(dict(sequence=sequence,point=point,monotonic_ns=time.monotonic_ns(),pid=root['pid'],tid=threading.get_native_id(),calibration_id=calibration_id,**fields))+'\n')
    def worker():
        try:
            tid=threading.get_native_id();task=task_identity(read_limited(proc/str(root['pid'])/'task'/str(tid)/'stat'),tid)
            if task['status']!='known':raise ValueError('worker identity unavailable')
            stage('worker_started',task_identity=task['identity'])
            write(out/'worker-info.json',dict(parent=dict(pid=root['pid'],start_ticks=root['start_ticks']),task_identity=task['identity'],calibration_id=calibration_id));started.set()
            if not release.wait(20):raise ValueError('worker release deadline exceeded')
            stage('worker_return')
        except BaseException as error:failure.append(str(error));started.set()
    previous=signal.signal(signal.SIGINT,lambda *args:stop.set())
    child=threading.Thread(target=worker,name='calibration-task');child.start()
    try:
        if not started.wait(5) or failure:raise ValueError('worker startup failed: '+str(failure))
        info=json.loads((out/'worker-info.json').read_text());context=dict(calibration_id=calibration_id,target_pid=root['pid'],target_start_ticks=root['start_ticks'],worker_tid=info['task_identity']['tid'],worker_start_ticks=info['task_identity']['start_ticks'])
        stage('fixture_ready');write(out/'fixture-ready.json',context)
        until=time.monotonic()+15
        while not (out/'release-worker.json').exists() and not stop.is_set() and time.monotonic()<until:time.sleep(.01)
        if not (out/'release-worker.json').exists() or stop.is_set():raise ValueError('worker release unavailable')
        bound(json.loads((out/'release-worker.json').read_text()),context);release_ns=time.monotonic_ns();stage('worker_release',release_ns=release_ns);release.set();child.join(timeout=3)
        if child.is_alive() or failure:raise ValueError('worker did not join cleanly: '+str(failure))
        stage('worker_joined');write(out/'worker-joined.json',dict(**context,joined=True,release_ns=release_ns,monotonic_ns=time.monotonic_ns()))
        if not stop.wait(15):raise ValueError('final signal deadline exceeded')
        stage('fixture_sigint');stage('fixture_exit');return 0
    finally:
        release.set();child.join(timeout=5);signal.signal(signal.SIGINT,previous)
if __name__=='__main__':raise SystemExit(main(Path(sys.argv[1]),sys.argv[2]))
