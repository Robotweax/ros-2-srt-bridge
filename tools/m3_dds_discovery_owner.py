#!/usr/bin/env python3
"""Linux owned native probe supervisor with explicit bounded shutdown evidence."""
import argparse
from pathlib import Path
import resource
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ros2/robotweax_srt_bridge_demo/scripts'))
from scenario_processes import stop_children
from scenario_files import write


def main():
    p=argparse.ArgumentParser();p.add_argument('--role',required=True,choices=['operator','robot']);p.add_argument('--local',required=True);p.add_argument('--peer',required=True);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    out=a.out;log=(out/(a.role+'-probe.log')).open('x');child=None;error=None
    try:
        child=subprocess.Popen([str(ROOT/'build/m3-dds-discovery-peer/m3_dds_discovery_peer'),a.role,a.local,a.peer,str(out)],stdout=log,stderr=subprocess.STDOUT)
        resource.prlimit(child.pid,resource.RLIMIT_CORE,(0,0))
        write(out/(a.role+'-owner.json'),dict(pid=child.pid,start_ticks=int(Path('/proc/'+str(child.pid)+'/stat').read_text().split(') ')[1].split()[19])))
        end=time.monotonic()+115
        while not (out/'release').exists():
            if child.poll() is not None:raise RuntimeError('native DDS peer exited before controlled shutdown')
            if (out/'abort').exists():raise RuntimeError('parent aborted fixture')
            if time.monotonic()>end:raise RuntimeError('owner watchdog exceeded')
            time.sleep(.02)
    except Exception as e:error=str(e)
    finally:
        result=stop_children([(child,'native-dds',log)]) if child else dict(passed=False,error='child not started')
        if error:result.update(passed=False,error=error)
        write(out/(a.role+'-shutdown.json'),result)
    if not result['passed']:raise RuntimeError('probe owner failed; inspect shutdown report')


if __name__=='__main__':main()
