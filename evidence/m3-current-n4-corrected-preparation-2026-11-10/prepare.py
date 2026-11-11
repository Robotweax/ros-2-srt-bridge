"""Create one disabled fresh N4 freeze; read-only runtime inspection, never launch."""
import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
from m3_source_preflight import IMAGE, sha, source_inventory, write
from cases import cases, disabled_ids, completed_ids, SCOPE
from n4_fixture import native_layout

PRIOR = ROOT / 'evidence/m3-current-n4-preparation-2026-11-10'
STOPPED = ROOT / 'evidence/m3-current-n4-execution-2026-11-10'
FIX = ROOT / 'evidence/m3-current-n4-assessor-json-fix-2026-11-10'


def bind_corrected_assessor():
    binding = json.loads((FIX / 'assessor-binding.json').read_text())
    origin = ROOT / binding['candidate_assessor']['path']
    expected = binding['candidate_assessor']['sha256']
    if sha(origin) != expected or sha(HERE / 'assess.py') != expected:
        raise ValueError('corrected assessor differs from offline-verified candidate')
    return dict(path=str((HERE / 'assess.py').relative_to(ROOT)), sha256=expected,
                verified_candidate_path=str(origin.relative_to(ROOT)),
                verified_candidate_binding=str((FIX / 'assessor-binding.json').relative_to(ROOT)))


def main():
    if (HERE / 'freeze.json').exists():
        raise ValueError('already frozen; no replacement or automatic retry')
    f = json.loads((PRIOR / 'freeze.json').read_text())
    if source_inventory() != f['source_sha256']:
        raise ValueError('frozen source drift')
    inputs = dict(f['inputs_sha256'])
    for path, digest in inputs.items():
        if sha(ROOT / path) != digest:
            raise ValueError('prior frozen input drift: ' + path)
    for path, digest in f['reused_native_inputs_sha256'].items():
        if sha(ROOT / path) != digest:
            raise ValueError('native input drift: ' + path)
    selected = native_layout(ROOT, 'socket-disposition')
    layout = selected['layout']
    # Only the copied manifest's location changes, never its bytes or build.
    expected_layout = dict(f['runtime_layout'], calibration=layout['calibration'])
    if layout != expected_layout or selected['binding'] != f['native_fixture_binding']:
        raise ValueError('matched build or existing fixture differs')
    assessor = bind_corrected_assessor()
    indexes = dict(f['retained_indexes'])
    for folder in (PRIOR, STOPPED, FIX):
        for name in ('public-artifact-hashes.json', 'local-artifact-hashes.json'):
            path = folder / name
            if path.exists():
                indexes[str(path.relative_to(ROOT))] = sha(path)
    for index, digest in indexes.items():
        if sha(ROOT / index) != digest:
            raise ValueError('retained index drift: ' + index)
        for path, value in json.loads((ROOT / index).read_text()).items():
            if sha(ROOT / path) != value['sha256']:
                raise ValueError('retained public/raw drift: ' + path)
            if not index.endswith('local-artifact-hashes.json'):
                inputs[path] = value['sha256']
        inputs[index] = digest
    stop = json.loads((STOPPED / 'cohort.json').read_text())
    if [r['status'] for r in stop['rows']] != ['passed'] * 16 + ['failed'] + ['not_executed'] * 2:
        raise ValueError('historical stopped cohort changed')
    fix = json.loads((FIX / 'postflight.json').read_text())
    if fix['status'] != 'offline_fix_and_retained_verification_passed' or fix['retained_started_cases_consistent'] != 17:
        raise ValueError('offline fix prerequisite differs')
    for name, count in (('preparation-suite.log', 20), ('binding-suite.log', 8), ('json-regressions.log', 10), ('existing-suite.log', 511)):
        text = (HERE / 'validation' / name).read_text()
        if 'Ran ' + str(count) + ' tests' not in text or not text.rstrip().endswith('OK'):
            raise ValueError('offline tests failed: ' + name)
    for path in HERE.rglob('*.py'):
        compile(path.read_text(), str(path), 'exec')
    current = json.loads(subprocess.check_output(['docker', 'version', '--format', '{{json .Server.Components}}'], text=True))
    if current != f['runtime_version']:
        raise ValueError('calibrated runtime differs')
    if subprocess.check_output(['docker', 'info', '--format', '{{.Architecture}}'], text=True).strip() != 'aarch64':
        raise ValueError('daemon architecture differs')
    if subprocess.check_output(['docker', 'image', 'inspect', '--platform', 'linux/amd64', IMAGE, '--format', '{{.Architecture}}'], text=True).strip() != 'amd64':
        raise ValueError('target image differs')
    if subprocess.check_output(['docker', 'ps', '-q'], text=True).strip():
        raise ValueError('live containers remain')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output = '.local/current-n4-corrected-cohort-' + stamp
    if (ROOT / output).exists():
        raise ValueError('future output exists')
    write(HERE / 'case-plan.json', dict(execution_enabled=False, cases=cases(), disabled_case_ids=disabled_ids(), completed_case_ids_not_reexecuted=completed_ids(), no_tuning=True, no_automatic_retries=True, stop_first_failed_gate=True))
    write(HERE / 'assessor-binding.json', assessor)
    inputs.update(selected['runtime_sha256'])
    for path in HERE.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            inputs[str(path.relative_to(ROOT))] = sha(path)
    freeze = dict(f, execution_enabled=False, authorization_supplied=False, scope=SCOPE,
                  cases=cases(), disabled_case_ids=disabled_ids(), completed_case_ids_not_reexecuted=completed_ids(),
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  runtime_layout=layout, corrected_assessor=assessor, retained_indexes=indexes,
                  inputs_sha256=inputs, output_relative=output, prefix='current-n4-corrected-' + stamp.lower(),
                  live_runs=0, previous_freeze_sha256=sha(PRIOR / 'freeze.json'),
                  previous_stopped_results=dict(passed=16, failed=1, not_executed=2),
                  no_tuning=True, no_automatic_retries=True, stop_first_failed_gate=True,
                  historical_failures_preserved=True)
    write(HERE / 'freeze.json', freeze)
    write(HERE / 'readiness.json', dict(status='fresh_N4_corrected_assessor_prepared_execution_disabled', freeze_sha256=sha(HERE / 'freeze.json'), corrected_assessor=assessor, cases_prepared=19, native_cases=13, ROS_freshness_cases=3, ROS_crash_cases=3, live_runs=0, authorization_file_created=False, fixture_rebuilt=False, preparation_tests_passed=20, binding_tests_passed=8, json_regressions_passed=10, existing_tests_passed=511, matched_entries=14, preserved_shutdown_entries=13, native_source_inputs_unchanged=87, fixture_bound_files=37, other_unexecuted_cases_disabled=9, completed_cases_excluded=10, no_tuning=True, no_automatic_retries=True, stop_first_failed_gate=True))
    write(HERE / 'postflight.json', dict(status='prepared_only_no_execution', frozen_source_inputs_matched_build_fixture_and_old_evidence_unchanged=True, original_live_results_preserved=dict(passed=16, failed=1, not_executed=2), corrected_assessor_bytes_bound=True, no_live_case_or_experiment=True, no_build=True, runtime_inspection_read_only=True, future_output_absent=True, new_authorization_absent=True, other_unexecuted_cases_disabled=9, completed_cases_excluded=10, M3_complete=False))
    print(json.dumps(dict(status='prepared_only', freeze_sha256=sha(HERE / 'freeze.json'), corrected_assessor_sha256=assessor['sha256'], cases=19, live_runs=0, output_relative=output)))


if __name__ == '__main__':
    main()
