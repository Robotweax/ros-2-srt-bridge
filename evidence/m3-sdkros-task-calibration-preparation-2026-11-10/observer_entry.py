"""Native observer entry: explicit pre-exec stages/errors, no preexec_fn."""
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import traceback
import time
from m3_observer_filtering import architecture,status,require_role

OUT=Path('/out')


def emit(kind,**values):
    with (OUT/'observer-exec.jsonl').open('a') as f:f.write(json.dumps(dict(kind=kind,monotonic_ns=time.monotonic_ns(),**values))+'\n');f.flush()


def main():
    os.umask(0o077);stage='entry'
    try:
        emit('entry',pid=os.getpid(),process_architecture=platform.machine(),permissions=status())
        stage='native_architecture'
        expected=json.loads((Path('/cal')/'observer-architecture.json').read_text())
        if architecture(platform.machine())!=expected['native'] or architecture(expected['daemon'])!=expected['native']:raise ValueError('observer architecture is not daemon-native')
        stage='role_permissions';require_role(status(),1<<21)
        stage='profile_identity';digest=hashlib.sha256((Path('/cal')/'observer-seccomp.json').read_bytes()).hexdigest()
        if digest!=expected['profile_sha256']:raise ValueError('observer profile source differs')
        stage='collector_binding';binding=json.loads((Path('/cal')/'collector-binding.json').read_text())
        collector_sha=hashlib.sha256((Path('/cal')/'shutdown_observer.py').read_bytes()).hexdigest()
        if collector_sha!=binding['sha256'] or binding['task_visibility'] is not True:raise ValueError('collector binding differs')
        emit('preexec_verified',task_visibility=True,collector_sha256=collector_sha,permissions=status(),native_architecture=expected['native'],profile_sha256=digest,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),time_namespace_offsets=Path('/proc/self/timens_offsets').read_text())
        if sys.argv[1:]==['--self-check']:
            import shutdown_observer
            emit('self_check_passed',collector_source=shutdown_observer.__file__);return 0
        stage='activation'
        if sys.argv[1:]!=['--task-visibility']:raise ValueError('explicit task visibility calibration activation required')
        stage='target_identity';target=json.loads((OUT/'target-info.json').read_text())
        from shutdown_observer import same_identity
        identity=dict(pid=target['pid'],start_ticks=target['start_ticks'])
        if not same_identity(Path('/proc'),identity):raise ValueError('registered target identity unavailable')
        argv=[sys.executable,'/cal/shutdown_observer.py','--pid',str(target['pid']),'--start-ticks',str(target['start_ticks']),'--output','/out/blocked-target-shutdown-stacks.jsonl','--ready','/out/blocked-target-shutdown-stacks.ready.json','--stop','/out/observer.stop','--mode','procfs','--task-visibility']
        stage='exec';emit('exec_begin',executable=sys.executable,target=identity,task_visibility=True,collector_sha256=collector_sha)
        os.execv(sys.executable,argv)
    except BaseException as error:
        record=dict(stage=stage,type=type(error).__name__,errno=getattr(error,'errno',None),message=str(error),traceback=traceback.format_exc())
        try:emit('exec_failed',**record)
        finally:print(json.dumps(record),file=sys.stderr,flush=True)
        return 125


if __name__=='__main__':raise SystemExit(main())
