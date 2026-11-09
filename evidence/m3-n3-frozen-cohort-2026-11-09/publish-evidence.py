"""Close and index retained artifacts only; never starts or retries a case."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_campaign_dispatcher import verify_freeze
from m3_closure_assessor import cleanup
out=Path(__file__).resolve().parent
preflight=json.loads((out/'preflight.json').read_text());base=ROOT/preflight['output_relative']
grant=json.loads((out/'authorization.json').read_text());freeze=json.loads((base/'freeze.json').read_text());verify_freeze(freeze)
assert sha(out/'run-n3-only.py')==grant['driver_sha256']
campaign=json.loads((base/'campaign.json').read_text());assert campaign['all_later_stages_disabled'] and len(campaign['disabled_case_ids'])==29
assert len(campaign['rows'])==9 and [r['status'] for r in campaign['rows']]==['passed']*8+['failed']
assert {p.name for p in base.iterdir() if p.is_dir()}==set(grant['case_ids'])
containers=set(subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines())
networks=set(subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines())
rows=[]
for row in campaign['rows']:
    slot=row['slot'];run=base/slot['id'];result=json.loads((run/'result.json').read_text());cleanup(run)
    network=json.loads((run/'network.json').read_text());assert network['network'] not in networks and not (set(network['containers'].values())&containers)
    child={role:json.loads((run/(role+'-child-shutdown.json')).read_text()) for role in ('operator','robot')}
    assessment=result.get('assessment');proof=base/(slot['id']+'-assessment.json')
    if proof.is_file():
        destination=out/'assessments';destination.mkdir(exist_ok=True);shutil.copyfile(proof,destination/proof.name)
    entry=dict(id=slot['id'],seed=slot['seed'],losses=slot['losses'],status=row['status'],run=str(run.relative_to(ROOT)),inner_status=result['status'],inner_error=result.get('error'),strict_error=row.get('error'),source_seconds=slot['source_seconds'],
        result_sha256=sha(run/'result.json'),provenance_sha256=sha(run/'provenance.json'),child_shutdown=child,
        fault_restored=result.get('fault',{}).get('restored'),selected_fault_counters=result.get('final_counters'),
        cleanup=dict(recorded_owned_removal='passed',containers_absent=True,network_absent=True,credential_absent=True))
    if assessment:
        entry.update(cadence=assessment['cadence'],balances=assessment['window']['balances'],age_upper_histograms=assessment['window']['age_upper_histograms'],
            source_trace_status=assessment['source_trace_status'],sender_trace_status=assessment['sender_trace_status'],receiver_trace_status=assessment['receiver_trace_status'],strict_assessment_sha256=sha(proof))
    else:entry.update(unassessed_gates='source/SDK/receiver/typed accounting and measurement capture revalidation not reached after abnormal child exit; no inferred pass')
    rows.append(entry)
failed=base/grant['case_ids'][-1];failure=out/'failure';failure.mkdir(exist_ok=True)
for name in ('result.json','operator-child-shutdown.json','robot-child-shutdown.json','operator-scenario.log','robot-scenario.log'):
    shutil.copyfile(failed/name,failure/name)
historical=json.loads((ROOT/'evidence/m3-n3-thirty-second-matrix-2026-11-09/local-artifact-hashes.json').read_text())
historical_results={p:r for p,r in historical.items() if p.endswith('/result.json')}
assert len(historical_results)==9 and all(sha(ROOT/p)==r['sha256'] for p,r in historical_results.items())
last=rows[-1]['child_shutdown']['operator']['children'][0]
write(out/'gate-report.json',dict(status='failed',candidate_id='sender-reconcile-929d1f7c7727',candidate_manifest_sha256=freeze['candidate_manifest_sha256'],frozen_source_commit=preflight['source_commit'],original_freeze_sha256=grant['freeze_sha256'],driver_sha256=grant['driver_sha256'],
    authorized_cases=9,executed_cases=9,strict_passed=8,failed_case=grant['case_ids'][-1],no_retry=True,no_tuning=True,production_rebuild=False,
    first_failed_gate=dict(gate='scenario_owned_child_shutdown',role='operator',child=last['name'],wait_budget_seconds=5,forced_kill=last['forced_kill'],returncode=last['returncode'],error=last['error'],signal_to_reap_ns=last['end_ns']-last['signal_begin_ns'],cause='not established from this cohort; no rerun or threshold change'),
    disabled_case_ids=grant['disabled_case_ids'],all_later_stages_disabled=True,M3_complete=False,PR2_keep_draft=True,M4_started=False,rows=rows))
write(out/'campaign.json',campaign)
raw={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(base.rglob('*')) if p.is_file()}
write(out/'local-artifact-hashes.json',raw)
write(out/'postflight.json',dict(status='passed',original_freeze_matches=True,candidate_manifest_entries_unchanged=13,native_inputs_unchanged=86,all9_owned_namespaces_removed=True,all_credentials_absent=True,no_other_stage_directories=True,local_files_hashed=len(raw),local_bytes_hashed=sum(r['bytes'] for r in raw.values()),local_artifact_manifest_sha256=sha(out/'local-artifact-hashes.json'),driver_sha256=sha(out/'run-n3-only.py'),authorization_sha256=sha(out/'authorization.json'),historical_result_hashes_unchanged=9))
print('Closed cohort:8 strict passes, final case failed child shutdown;29 other cases disabled; all owned lab objects removed.')
