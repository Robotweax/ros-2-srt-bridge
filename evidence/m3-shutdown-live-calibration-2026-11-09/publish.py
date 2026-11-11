"""Index already closed calibration evidence; never launches or retries a slot."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory
from m3_runtime_layout import matched
from m3_closure_assessor import cleanup
out=Path(__file__).resolve().parent
freeze=json.loads((out/'freeze.json').read_text());base=ROOT/freeze['output_relative'];report=json.loads((base/'calibration.json').read_text())
assert matched(ROOT,'shutdown-tracing')==freeze['runtime_layout'] and source_inventory()==freeze['source_sha256']
assert all(sha(ROOT/p)==h for p,h in freeze['driver_and_fixture_sha256'].items())
assert [r['status'] for r in report['rows']]==['passed','passed','failed'] and report['remaining_campaign_cases_disabled']==29
containers=set(subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines());networks=set(subprocess.check_output(['docker','network','ls','--format','{{.Name}}'],text=True).splitlines())
rows=[]
for row in report['rows']:
    slot=row['slot'];run=base/slot['id'];result=json.loads((run/'result.json').read_text())
    entry=dict(slot=slot,status=row['status'],inner_status=result['status'],strict_error=row.get('error'),run=str(run.relative_to(ROOT)))
    if slot['kind']=='sensor':
        cleanup(run);network=json.loads((run/'network.json').read_text());assert network['network'] not in networks and not(set(network['containers'].values())&containers)
        entry.update(cadence=result['assessment']['cadence'],balances=result['assessment']['window']['balances'],ages=result['assessment']['window']['age_upper_histograms'],cleanup='recorded removals and absent owned objects',roles={})
        for role in ('operator','robot'):
            child=next(c for c in result['child_shutdown'][role]['children'] if '-bridge-' in c['name'])
            details=dict(child=child,signal_to_reap_ns=child['end_ns']-child['signal_begin_ns'])
            if slot['diagnostics']:
                proof=row['assessment']['proofs'][role];details.update(stage_records=proof['stages']['records'],stage_points=proof['stages']['points'],observer=proof['observer'])
                shutil.copyfile(run/(role+'-shutdown-stages.jsonl'),out/(role+'-shutdown-stages.jsonl'))
            entry['roles'][role]=details
    else:
        entry.update(shutdown=result['shutdown'],observer_coverage=json.loads((run/'observer-coverage.json').read_text()))
        for name in ('stages.jsonl','child-shutdown.json','observer-coverage.json','blocked-target-shutdown-stacks.jsonl'):
            shutil.copyfile(run/name,out/name)
    rows.append(entry)
old=matched(ROOT,'sender-reconcile');old_raw=json.loads((ROOT/'evidence/m3-n3-frozen-cohort-2026-11-09/local-artifact-hashes.json').read_text());assert len(old_raw)==913 and all(sha(ROOT/p)==r['sha256'] for p,r in old_raw.items())
prep=json.loads((ROOT/'evidence/m3-shutdown-visibility-preparation-2026-11-09/compilation-artifacts.json').read_text())['files'];assert all(sha(ROOT/p)==h for p,h in prep.items())
write(out/'gate-report.json',dict(status='failed_stack_access_gate',calibration_slots=3,executed_slots=3,passed_slots=2,failed_slot='independent-blocked-procfs',stage_tracing_calibration='passed healthy N0 shutdown only',default_off_calibration='passed',independent_observer_post_signal_sampling='passed controlled three-second blocked target',kernel_stack_calibration='failed;22 post-signal reads PermissionError/errno13',userspace_GDB_calibration='not run; tool absent in pinned image, procfs selected prospectively',production_tuning=False,retry_two_loss_4211=False,remaining_campaign_cases_disabled=29,original_N3_cohort='unchanged8PASS/1FAIL',M3_complete=False,PR2_keep_draft=True,M4_started=False,rows=rows))
write(out/'calibration.json',report)
raw={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(base.rglob('*')) if p.is_file()}
write(out/'local-artifact-hashes.json',raw)
write(out/'postflight.json',dict(status='passed_integrity_cleanup',new_matched_inventory_entries=len(freeze['runtime_layout']['matched_build_sha256']),preserved_sender_reconcile_entries=len(old['matched_build_sha256']),preserved_preparation_artifacts=len(prep),preserved_original_N3_raw_files=913,new_raw_files=len(raw),new_raw_bytes=sum(r['bytes'] for r in raw.values()),source_freeze_matches=True,driver_fixture_matches=True,all_owned_sensor_containers_networks_absent=True,blocked_fixture_container_auto_removed=True,live_debugger_attaches=0,no_capability_image_or_permission_change=True,no_tuning=True,no_retry=True,remaining_campaign_cases_disabled=29))
print('Closed calibration: default-off and shutdown stages PASS; independent wait coverage11samples PASS;22 kernel stack reads denied FAIL. No retry or campaign stage.')
