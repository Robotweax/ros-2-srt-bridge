"""Retained failed preparation audit only; no process launch/calibration retry."""
from pathlib import Path
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory
from m3_runtime_layout import matched
out=Path(__file__).resolve().parent;freeze=json.loads((out/'freeze.json').read_text());base=ROOT/freeze['output_relative']
assert matched(ROOT,'shutdown-tracing')==freeze['runtime_layout'] and source_inventory()==freeze['source_sha256']
assert all(sha(ROOT/p)==h for p,h in freeze['inputs_sha256'].items())
r=json.loads((base/'result.json').read_text());cal=json.loads((base/'calibration.json').read_text());child=r['shutdown']['children'][0];commands=json.loads((base/'commands.json').read_text())
assert cal['status']=='failed' and r['status']=='failed' and r['error']=='SubprocessError: Exception occurred in preexec_fn.'
assert child['passed'] and child['returncode']==0 and not child['forced_kill']
assert not (base/'permission-proof.json').exists() and not (base/'blocked-target-shutdown-stacks.ready.json').exists() and not (base/'blocked-target-shutdown-stacks.jsonl').exists()
assert len([c for c in commands if c['label']=='one-blocked-slot'])==1
assert all(next(c for c in commands if c['label']==label)['exit_code']==0 for label in ('container-remove','volume-remove'))
assert freeze['container'] not in subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines()
assert freeze['volume'] not in subprocess.check_output(['docker','volume','ls','--format','{{.Name}}'],text=True).splitlines()
architecture=subprocess.check_output(['docker','info','--format','{{.Architecture}}'],text=True).strip()
final=json.loads((base/'supervisor-final-permissions.json').read_text());assert int(final['CapPrm'],16)==int(final['CapEff'],16)==0 and final['NoNewPrivs']=='1'
old=ROOT/'evidence/m3-shutdown-live-calibration-2026-11-09';assert all(sha(old/p)==h for p,h in json.loads((old/'evidence-index.json').read_text()).items())
original=json.loads((ROOT/'evidence/m3-n3-frozen-cohort-2026-11-09/local-artifact-hashes.json').read_text());assert len(original)==913 and all(sha(ROOT/p)==record['sha256'] for p,record in original.items())
raw={str(p.relative_to(ROOT)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in sorted(base.rglob('*')) if p.is_file()}
write(out/'local-artifact-hashes.json',raw)
write(out/'gate-report.json',dict(status='failed_observer_preexec_setup',blocked_target_runs=1,observer_armed=False,stack_capture_attempted=False,kernel_stacks_captured=0,
    target_cleanup=dict(returncode=0,forced_kill=False,signal_to_reap_ns=child['end_ns']-child['signal_begin_ns'],existing_wait_seconds=5),
    failure=dict(error=r['error'],exact_preexec_errno='not retained by Popen; no attribution to a specific call',known_compatibility_blocker='native-x86_64-only additive seccomp filter versus aarch64 Docker daemon; image/process architecture is not sufficient preflight',daemon_architecture=architecture,selected_image_architecture='amd64',missed_preflight_check=True),
    permissions=dict(container_policy='one SYS_ADMIN capability, read-only minimal bundle/private PID/network-none/NNP/default Docker seccomp',per_role_before_signal_attestation='not reached; observer preexec failed',supervisor_final=final,permissions_persist=False,container_removed=True,output_volume_removed=True),
    original_fixture_unchanged=True,matched_build_entries_unchanged=13,original_N3_raw_files_unchanged=913,prior_stack_calibration_failure_unchanged=True,
    no_tuning=True,retry_two_loss_4211=False,additional_target_attempts=0,remaining_campaign_cases_disabled=29,M3_complete=False,PR2_keep_draft=True,M4_started=False))
write(out/'postflight.json',dict(status='passed_integrity_and_cleanup_only',freeze_matches=True,source_matches=True,inputs_and_read_only_bundle_match=True,matched_inventory_entries=13,old_N3_raw_files=913,raw_files=len(raw),raw_bytes=sum(v['bytes'] for v in raw.values()),container_absent=True,volume_absent=True,supervisor_active_capabilities_final=0,observer_not_armed=True,remaining_campaign_cases_disabled=29))
for name in ('result.json','child-shutdown.json','supervisor-final-permissions.json','stages.jsonl','calibration.json'): (out/name).write_bytes((base/name).read_bytes())
print('One failed observer-setup attempt retained; target exits0; no observer/stack data; capability container+volume removed; no retry.')
