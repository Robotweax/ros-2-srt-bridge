#!/usr/bin/env python3
"""Run exactly one isolated source preflight; preserve failed runs, no retries."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from m3_source_trace import summarize, qualify

ROOT=Path(__file__).resolve().parents[1]
IMAGE='ros2-srt-m3@sha256:379b2ed9b14c5d3166ba236e219a2068b88ff1f9bb52ee4451207369426eebab'


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    out=Path(a.output).resolve();relative=out.relative_to(ROOT);out.mkdir(parents=True,exist_ok=False)
    runtime=ROOT/'install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo/rate_simulator'
    before=sha(runtime)
    write(out/'provenance.json',dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,runtime_sha256=before,network='none',seconds=10,source_diagnostics=True,bridge=False))
    command=['docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none','-e','ROS_DOMAIN_ID=90','-e','ROS_LOCALHOST_ONLY=1','-v',str(ROOT)+':/workspace','-w','/workspace',IMAGE,'bash','-c','source /opt/ros/jazzy/setup.bash && source install/m3-ros/setup.bash && python3 ros2/robotweax_srt_bridge_demo/scripts/m3_source_preflight.py --output '+str(relative/'run')]
    with (out/'docker.log').open('w') as log:
        code=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,timeout=65).returncode
    try:
        if code:raise ValueError('source fixture failed; see docker.log')
        if sha(runtime)!=before:raise ValueError('runtime changed during measurement')
        result=json.loads((out/'run/observer.json').read_text())
        summary=qualify(summarize(out/'run/source.log'),result)
    except (ValueError,OSError,KeyError) as error:
        summary=dict(passed=False,error=str(error))
    write(out/'summary.json',summary)
    print(json.dumps(summary,indent=2))
    return 0 if summary['passed'] else 1


if __name__=='__main__':sys.exit(main())
