"""Capability-zero supervisor for exactly one controlled task target."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from m3_observer_filtering import status,require_role
from shutdown_observer import identity
from scenario_processes import stop_children
OUT=Path('/out')
def write(name,value):
    path=OUT/name;temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)
class WaitWitness:
    """Write only after unchanged stop_children has recorded signal_end_ns."""
    def __init__(self,process,context):self.process=process;self.context=context;self.witnessed=False
    def __getattr__(self,name):return getattr(self.process,name)
    def wait(self,timeout):
        if not self.witnessed:
            self.witnessed=True;write('signal-wait.json',dict(**self.context,wait_enter_ns=time.monotonic_ns()))
        return self.process.wait(timeout=timeout)
def main(calibration_id):
    os.umask(0o077);target=None;log=None;report=None;error=None
    try:
        require_role(status(),0);write('target-supervisor-start.json',status())
        log=(OUT/'target.log').open('x');target=subprocess.Popen([sys.executable,'/cal/task_target.py','/out',calibration_id],stdout=log,stderr=subprocess.STDOUT)
        until=time.monotonic()+5
        while not (OUT/'fixture-ready.json').exists() and target.poll() is None and time.monotonic()<until:time.sleep(.01)
        if not (OUT/'fixture-ready.json').exists():raise ValueError('fixture readiness missing')
        info=dict(**identity(Path('/proc'),target.pid),permissions=status(target.pid),supervisor_permissions=status(),calibration_id=calibration_id,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),time_namespace_offsets=Path('/proc/self/timens_offsets').read_text())
        require_role(info['permissions'],0);write('target-info.json',info)
        until=time.monotonic()+15
        while not (OUT/'authorize-signal.json').exists() and target.poll() is None and time.monotonic()<until:time.sleep(.01)
        if not (OUT/'authorize-signal.json').exists():raise ValueError('signal authority absent')
        authority=json.loads((OUT/'authorize-signal.json').read_text())
        if authority!=dict(scope='one-post-sigint-task-assessment-calibration',calibration_id=calibration_id,target_pid=target.pid,target_start_ticks=info['start_ticks']):raise ValueError('signal authority differs')
        require_role(status(target.pid),0);write('target-before-signal.json',dict(target=status(target.pid),supervisor=status()))
        context=json.loads((OUT/'fixture-ready.json').read_text());report=stop_children([(WaitWitness(target,context),'task-target',log)])
    except BaseException as failure:error=dict(type=type(failure).__name__,message=str(failure),traceback=traceback.format_exc())
    finally:
        if target is not None and target.poll() is None and log is not None and not log.closed:report=stop_children([(target,'task-target',log)])
        if log is not None and not log.closed:log.close()
        if report is not None:write('child-shutdown.json',report)
        write('result.json',dict(status='passed' if error is None and report and report['passed'] else 'failed',error=error,shutdown=report,calibration_id=calibration_id));write('target-supervisor-final.json',status());(OUT/'observer.stop').touch()
        until=time.monotonic()+5
        while not (OUT/'observer-exited.json').exists() and time.monotonic()<until:time.sleep(.01)
    return 0 if error is None and report and report['passed'] else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
