"""One authorized N3 prefix; unchanged frozen adapters, no other stage dispatch."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_campaign_dispatcher import slots,dispatch_slot,verify_freeze
from m3_closure_assessor import assess_case,evaluate_sequence,require
from m3_source_preflight import sha,write

FREEZE=ROOT/'evidence/m3-dispatcher-fixture-validation-2026-11-09/campaign-freeze.json'


def execute(grant_path):
    grant_path=Path(grant_path).resolve();grant_bytes=sha(grant_path)
    grant=json.loads(grant_path.read_text());freeze=json.loads(FREEZE.read_text())
    all_cases=slots();cases=all_cases[:9]
    require(len(cases)==9 and all(s['stage']=='N3' for s in cases),'not exact N3 prefix')
    require(grant['schema_version']==1 and grant['execution_authorized'] is True,'missing N3 authorization')
    require(grant['case_ids']==[s['id'] for s in cases] and grant['disabled_case_ids']==[s['id'] for s in all_cases[9:]],'scope must be exact nine N3 cases only')
    require(grant['freeze_sha256']==sha(FREEZE) and grant['driver_sha256']==sha(Path(__file__)),'freeze/driver binding differs')
    out=(ROOT/grant['output_relative']).resolve()
    require(str(out.relative_to(ROOT)).startswith('.local/') and not out.exists(),'output must be fresh and under .local')
    def verify():
        require(sha(grant_path)==grant_bytes and sha(Path(__file__))==grant['driver_sha256'] and sha(FREEZE)==grant['freeze_sha256'],'N3 driver/grant/freeze changed')
        verify_freeze(freeze)
    verify();out.mkdir(parents=True,exist_ok=False)
    write(out/'authorization.json',grant);write(out/'freeze.json',freeze)
    def produce(slot):
        verify();target=out/slot['id'];require(not target.exists(),'case already exists; no retry')
        write(out/'active-case.json',dict(id=slot['id'],status='dispatching',run=str(target.relative_to(ROOT))))
        print('START '+slot['id'],flush=True)
        return dispatch_slot(slot,target)
    def assess(slot,produced):
        print('ASSESS '+slot['id'],flush=True);verify()
        result=assess_case(ROOT/produced['run'],slot,freeze);verify()
        write(out/(slot['id']+'-assessment.json'),result)
        print('PASS '+slot['id'],flush=True);return result
    def record(result):
        result.update(authorized_stage='N3_only',disabled_case_ids=grant['disabled_case_ids'],all_later_stages_disabled=True,driver_sha256=grant['driver_sha256'],freeze_sha256=grant['freeze_sha256'],no_retry=True)
        write(out/'campaign.json',result)
        last=result['rows'][-1]
        if last['status']=='failed':print('STOP '+last['slot']['id']+': '+last['error'],flush=True)
    result=evaluate_sequence(cases,produce,assess,record)
    print('FINAL '+result['status']+'; other29 campaign cases disabled',flush=True)
    return result


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('one exact N3 grant path required')
    raise SystemExit(execute(Path(sys.argv[1]))['status']!='passed')
