"""Single network-none blocked target; only observer retains SYS_ADMIN during wait."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from m3_observer_permissions import SYS_ADMIN,drop_all,target_permissions,restrict_observer,status,require_caps
from shutdown_observer import Observer,identity
from scenario_processes import stop_children

OUT=Path('/out')


def write(name,data):(OUT/name).write_text(json.dumps(data,indent=2)+'\n')


class ScopedObserver(Observer):
    def __init__(self,pid,prefix):
        self.prefix=prefix;self.ready=prefix.with_suffix('.ready.json');self.stop=prefix.with_suffix('.stop');self.output=prefix.with_suffix('.jsonl')
        if any(p.exists() for p in (self.ready,self.stop,self.output)):raise ValueError('observer output exists')
        expected=identity(Path('/proc'),pid);self.log=prefix.with_suffix('.log').open('x')
        try:self.process=subprocess.Popen([sys.executable,'/cal/shutdown_observer.py','--pid',str(pid),'--start-ticks',str(expected['start_ticks']),'--output',str(self.output),'--ready',str(self.ready),'--stop',str(self.stop),'--mode','procfs'],stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=restrict_observer)
        except BaseException:self.log.close();raise
        until=time.monotonic()+1
        while not self.ready.exists() and self.process.poll() is None and time.monotonic()<until:time.sleep(.01)
        self.armed=self.ready.exists()


def main():
    os.umask(0o077);initial=status();require_caps(initial,SYS_ADMIN)
    log=(OUT/'target.log').open('x');target=None;watch=None;report=None;failure=None
    try:
        target=subprocess.Popen(['/cal/blocked_fixture',str(OUT/'stages.jsonl'),str(OUT/'target-ready')],stdout=log,stderr=subprocess.STDOUT,preexec_fn=target_permissions)
        until=time.monotonic()+5
        while not (OUT/'target-ready').exists() and target.poll() is None and time.monotonic()<until:time.sleep(.01)
        if not (OUT/'target-ready').exists():raise ValueError('finite target not ready')
        watch=ScopedObserver(target.pid,OUT/'blocked-target-shutdown-stacks')
        if not watch.armed:raise ValueError('restricted observer not ready')
        drop_all()
        proof=dict(bootstrap_supervisor=initial,supervisor_before_signal=status(),target_before_signal=status(target.pid),observer_before_signal=status(watch.process.pid),observer_pid=watch.process.pid,target_pid=target.pid,observer_filter='Docker default plus additive native-x86_64 deny filter',gdb=False)
        require_caps(proof['supervisor_before_signal'],0);require_caps(proof['target_before_signal'],0);require_caps(proof['observer_before_signal'],SYS_ADMIN)
        if any(int(proof[k]['CapBnd'],16)!=SYS_ADMIN for k in ('supervisor_before_signal','target_before_signal','observer_before_signal')):raise ValueError('unexpected container capability bounding set')
        if any(proof[k]['Seccomp']!='2' for k in ('supervisor_before_signal','target_before_signal','observer_before_signal')):raise ValueError('seccomp not enforced')
        if int(proof['observer_before_signal']['Seccomp_filters'])!=int(proof['supervisor_before_signal']['Seccomp_filters'])+1:raise ValueError('observer additive filter missing')
        write('permission-proof.json',proof)
        report=stop_children([(target,'blocked-target',log)])
    except Exception as error:failure=type(error).__name__+': '+str(error)
    finally:
        drop_all() # Includes bootstrap/preparation errors; never retain the lease in supervisor.
        if target is not None and target.poll() is None:
            if not log.closed:report=stop_children([(target,'blocked-target',log)])
            else:target.kill();target.wait(timeout=2)
        if not log.closed:log.close()
        if watch is not None:
            control=watch.close()
            if report is not None:report['children'][0].update(stack_observer=control,stack_observer_armed=watch.armed)
        if report is not None:write('child-shutdown.json',report)
        write('supervisor-final-permissions.json',status())
    passed=failure is None and report is not None and report['passed']
    write('result.json',dict(status='passed' if passed else 'failed',error=failure,shutdown=report,fixture_hold_seconds=3,child_wait_seconds=5,permission_change_only=True))
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())
