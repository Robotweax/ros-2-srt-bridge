"""Unprivileged unchanged fixture; host releases SIGINT only after sidecar readiness."""
import json
import os
from pathlib import Path
import subprocess
import time
import traceback
from m3_observer_filtering import status,require_role
from shutdown_observer import identity
from scenario_processes import stop_children
OUT=Path('/out')


def write(name,value):(OUT/name).write_text(json.dumps(value,indent=2)+'\n')


def main():
    os.umask(0o077);stage='entry';target=None;log=None;report=None;error=None
    try:
        require_role(status(),0)
        write('target-supervisor-start.json',status())
        stage='target_spawn';log=(OUT/'target.log').open('x')
        target=subprocess.Popen(['/cal/blocked_fixture','/out/stages.jsonl','/out/target-ready'],stdout=log,stderr=subprocess.STDOUT)
        until=time.monotonic()+5
        while not (OUT/'target-ready').exists() and target.poll() is None and time.monotonic()<until:time.sleep(.01)
        if not (OUT/'target-ready').exists():raise ValueError('target not ready')
        require_role(status(target.pid),0)
        write('target-info.json',dict(**identity(Path('/proc'),target.pid),permissions=status(target.pid),supervisor_permissions=status(),monotonic_ns=time.monotonic_ns(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),time_namespace_offsets=Path('/proc/self/timens_offsets').read_text()))
        stage='observer_authorization';until=time.monotonic()+15
        while not (OUT/'authorize-signal.json').exists() and time.monotonic()<until:time.sleep(.01)
        if not (OUT/'authorize-signal.json').exists():raise ValueError('observer signal authorization unavailable')
        authority=json.loads((OUT/'authorize-signal.json').read_text())
        if authority.get('target_pid')!=target.pid or authority.get('scope')!='one-blocked-calibration':raise ValueError('signal authorization mismatch')
        require_role(status(),0);require_role(status(target.pid),0)
        write('target-before-signal.json',dict(target=status(target.pid),supervisor=status()))
        stage='child_shutdown';report=stop_children([(target,'blocked-target',log)])
    except BaseException as failure:error=dict(stage=stage,type=type(failure).__name__,errno=getattr(failure,'errno',None),message=str(failure),traceback=traceback.format_exc())
    finally:
        if target is not None and target.poll() is None and log is not None and not log.closed:report=stop_children([(target,'blocked-target',log)])
        if log is not None and not log.closed:log.close()
        if report is not None:write('child-shutdown.json',report)
        write('target-supervisor-final.json',status())
        write('result.json',dict(status='passed' if error is None and report and report['passed'] else 'failed',error=error,shutdown=report,fixture_hold_seconds=3,child_wait_seconds=5))
        (OUT/'observer.stop').touch()
        # Keep the private PID namespace alive until its observer sidecar exits.
        until=time.monotonic()+5
        while not (OUT/'observer-exited.json').exists() and time.monotonic()<until:time.sleep(.01)
    return 0 if error is None and report and report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
