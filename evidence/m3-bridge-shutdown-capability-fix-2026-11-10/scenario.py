"""Evidence-local opt-in wrapper; preserves the existing SENSOR scenario and stop helper."""
import os
from pathlib import Path
import sys
import time
ROOT=Path('/workspace')
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(1,str(ROOT/'ros2/robotweax_srt_bridge_demo/scripts'))
import m3_ros_multiroute_scenario as original
from m3_observer_filtering import require_role,status
from shutdown_observer import identity
from m3_scenario import write
HERE=Path(__file__).resolve().parent


class Diagnostic(original.Multiroute):
    def start(self,executable,name,parameters=None):
        if executable!='bridge_node':return super().start(executable,name,parameters)
        import subprocess
        package='robotweax_srt_bridge'
        binary='/workspace/'+self.args.ros_install+'/'+package+'/lib/'+package+'/bridge_node'
        argv=[sys.executable,str(HERE/'bridge_exec.py'),str(self.run/(self.args.role+'-bridge-preexec.json')),binary,'--ros-args']
        for key,value in parameters.items():argv+=['-p',key+':='+str(value)]
        log=(self.run/(name+'.log')).open('w');child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT)
        self.processes.append((child,name,log));return child
    def start_bridge(self):
        super().start_bridge();until=time.monotonic()+5
        while time.monotonic()<until:
            if self.bridge.poll() is not None:raise ValueError('bridge capability-drop/startup failed')
            if (self.run/(self.args.role+'-bridge-preexec.json')).exists():
                require_role(status(self.bridge.pid),0)
                write(self.run/(self.args.role+'-bridge-identity.json'),dict(**identity(Path('/proc'),self.bridge.pid),permissions=status(self.bridge.pid),monotonic_ns=time.monotonic_ns(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),time_namespace_offsets=Path('/proc/self/timens_offsets').read_text()))
                return
            time.sleep(.01)
        raise ValueError('bridge capability attestation missing')

if __name__=='__main__':
    if '--shutdown-stacks' in sys.argv:raise SystemExit('in-container observer forbidden; native sidecar only')
    original.Multiroute=Diagnostic
    original.main()
