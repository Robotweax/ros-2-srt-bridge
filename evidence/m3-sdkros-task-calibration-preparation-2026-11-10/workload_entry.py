"""One exact granted SDK/ROS fixture; no build, campaign or retry interface."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from campaign_binding import load
FLAGS=['--skip-build','--monotonic-capture','--command-diagnostics','--provider-diagnostics','--sensor-provider-diagnostics','--start-diagnostics','--sender-diagnostics']
def invocation(freeze):
    from m3_source_preflight import IMAGE
    return ['--output',str(ROOT/freeze['output_relative']/'fixture'),'--profile','N0','--seed','1701','--seconds','10','--runtime-layout','socket-disposition','--image-reference',IMAGE,*FLAGS]
def main(grant):
    freeze=json.loads((HERE/'freeze.json').read_text());load('calibration_scope').activate(grant,freeze)
    return load('workload').main(invocation(freeze),bundle=ROOT/freeze['bundle_relative'],prefix=freeze['prefix']+'-sdkros')
if __name__=='__main__':main(Path(sys.argv[1]))
