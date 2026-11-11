"""One declared member of a separately granted fresh single fresh N1/2903 cohort."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from campaign_binding import load
FLAGS=['--skip-build','--monotonic-capture','--command-diagnostics','--provider-diagnostics','--sensor-provider-diagnostics','--start-diagnostics','--sender-diagnostics']
def invocation(freeze,slot):
    from m3_source_preflight import IMAGE
    if slot not in load('cases').cases():raise ValueError('only exact fresh N1/2903/600s case settings')
    return ['--output',str(ROOT/freeze['output_relative']/slot['id']),'--profile',slot['profile'],'--seed',str(slot['seed']),'--seconds',str(slot['source_seconds']),'--runtime-layout','socket-disposition','--image-reference',IMAGE,*FLAGS]
def main(grant,case_id):
    freeze=json.loads((HERE/'freeze.json').read_text());scope=load('campaign_scope');scope.activate(grant,freeze,case_id);slot=scope.select(case_id)
    return load('workload').main(invocation(freeze,slot),bundle=ROOT/freeze['bundle_relative'],prefix=freeze['prefix']+'-'+slot['id'].lower())
if __name__=='__main__':main(Path(sys.argv[1]),sys.argv[2])
