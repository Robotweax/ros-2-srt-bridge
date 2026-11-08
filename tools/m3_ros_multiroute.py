#!/usr/bin/env python3
"""One N0 sustained multiroute preflight; no fault/capture/seed-matrix verdict."""
import argparse
import json
from pathlib import Path
import secrets
import shlex
import subprocess
from m3_network import NetworkLab
from m3_neighbor_diagnostics import configure
from m3_dds_result_timeline import common_clock
from m3_ros_sensor import wait_files
from m3_source_preflight import ROOT, IMAGE, sha, write
from m3_source_trace import summarize as source_trace
from m3_sample_trace import summarize as sample_trace
from m3_multiroute_accounting import assess


def run(out):
    out.mkdir(parents=True,exist_ok=False);inside='/workspace/'+str(out.relative_to(ROOT))
    paths=['install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo/rate_simulator','install/m3-ros/robotweax_srt_bridge/lib/robotweax_srt_bridge/bridge_node','install/bridge-m3/lib/librobotweax_srt_bridge_transport.a','install/bridge-m3/lib/librobotweax_srt_bridge_endpoint.a','install/srt-m0/lib/librobotweax-srt.a']
    inventory={p:sha(ROOT/p) for p in paths}
    write(out/'provenance.json',dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,runtime_sha256=inventory,seconds=10,sample_diagnostics=True,source_diagnostics=True,capture=False))
    lab=NetworkLab(ROOT,out,IMAGE);peers=[];key=out/'passphrase';key.touch(mode=0o600);key.write_text(secrets.token_urlsafe(32));result=dict(status='running',qualification=False)
    try:
        lab.start(key)
        result['clock_proof']={r:lab.inside(r,r+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for r in lab.containers};common_clock(result['clock_proof'])
        configure(lab,'permanent');lab.apply('N0',1701)
        for role,name in lab.containers.items():
            log=(out/(role+'-scenario.log')).open('w')
            command='source /opt/ros/jazzy/setup.bash && source install/m3-ros/setup.bash && exec python3 ros2/robotweax_srt_bridge_demo/scripts/m3_ros_multiroute_scenario.py --role '+role+' --run '+shlex.quote(inside)+' --peer '+lab.addresses['operator']
            peers.append((subprocess.Popen(['docker','exec',name,'bash','-c',command],stdout=log,stderr=subprocess.STDOUT),log))
        wait_files(out,[r+'-multiroute-ready.json' for r in lab.containers],peers)
        (out/'armed').touch()
        wait_files(out,[r+'-multiroute-result.json' for r in lab.containers],peers)
        (out/'release').touch()
        for p,log in peers:
            if p.wait(timeout=12)!=0:raise ValueError('multiroute scenario exit failed')
            log.close()
        if {p:sha(ROOT/p) for p in paths}!=inventory:raise ValueError('runtime changed during measurement')
        sender=json.loads((out/'robot-multiroute-result.json').read_text());receiver=json.loads((out/'operator-multiroute-result.json').read_text())
        result['assessment']=assess(source_trace(out/'robot-source.log'),sender,receiver,sample_trace(out/'robot-bridge-0.log'),sample_trace(out/'operator-bridge-0.log'))
        result['status']='passed' if result['assessment']['passed'] else 'failed'
        if result['status']=='failed':result['error']='measured source cadence outside predeclared tolerance'
    except Exception as error:result.update(status='failed',error=str(error))
    finally:
        (out/'release').touch()
        if result['status']!='passed':(out/'abort').touch()
        for p,log in peers:
            try:p.wait(timeout=12)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
            if not log.closed:log.close()
        lab.cleanup();key.unlink(missing_ok=True);write(out/'result.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();result=run(a.output.resolve());print(json.dumps(dict(status=result['status'],error=result.get('error'),assessment=result.get('assessment',{}).get('window')),indent=2));raise SystemExit(result['status']!='passed')
