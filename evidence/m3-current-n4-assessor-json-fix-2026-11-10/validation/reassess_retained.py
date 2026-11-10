"""Read-only diagnostic assessment; never runs cases or rewrites their decisions."""
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
PREP = ROOT / 'evidence/m3-current-n4-preparation-2026-11-10'
EXEC = ROOT / 'evidence/m3-current-n4-execution-2026-11-10'
sys.path[:0] = [str(PREP), str(ROOT / 'tools')]
from m3_source_preflight import sha, source_inventory
from n4_fixture import native_layout
from disposition_runtime import matched


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def integrity(freeze):
    assert source_inventory() == freeze['source_sha256']
    assert matched(ROOT, 'socket-disposition') == freeze['runtime_layout']
    assert native_layout(ROOT, 'socket-disposition')['binding'] == freeze['native_fixture_binding']
    for path, digest in freeze['inputs_sha256'].items():
        assert sha(ROOT / path) == digest, path
    indexes = dict(freeze['retained_indexes'])
    for path in [PREP / 'public-artifact-hashes.json', EXEC / 'public-artifact-hashes.json', EXEC / 'local-artifact-hashes.json']:
        indexes[str(path.relative_to(ROOT))] = sha(path)
    counts = {}
    for path, digest in indexes.items():
        assert sha(ROOT / path) == digest, path
        records = json.loads((ROOT / path).read_text())
        for name, record in records.items():
            assert sha(ROOT / name) == record['sha256'], name
        counts[path] = len(records)
    return counts


def main():
    candidate = load('offline_json_candidate', HERE / 'assess.py')
    original = load('offline_json_original', PREP / 'assess.py')
    freeze = json.loads((PREP / 'freeze.json').read_text())
    counts = integrity(freeze)
    root = ROOT / freeze['output_relative']
    cohort = json.loads((root / 'cohort.json').read_text())
    assert [row['status'] for row in cohort['rows']] == ['passed'] * 16 + ['failed'] + ['not_executed'] * 2
    decisions = {str(p): sha(p) for p in [root / 'cohort.json', *root.glob('*/strict-assessment.json')]}
    rows = []
    for row in cohort['rows']:
        slot = row['slot']
        path = root / slot['id']
        if row['status'] == 'not_executed':
            assert not path.exists()
            rows.append(dict(id=slot['id'],original_status=row['status'],offline_assessed=False))
            continue
        result = candidate.assess_case(path, slot, freeze)
        assert result['status'] == 'passed'
        rows.append(dict(id=slot['id'],original_status=row['status'],offline_assessed=True,candidate_retained_consistency='passed'))
    try:
        original.assess_case(root / 'N4-ROS-crash-before', freeze['cases'][16], freeze)
    except ValueError as error:
        assert str(error) == 'ROS crash audit differs'
        reproduced = str(error)
    else:
        raise AssertionError('original failure not reproduced')
    assert integrity(freeze) == counts
    assert all(sha(Path(path)) == digest for path, digest in decisions.items())
    report = dict(
        status='offline_retained_consistency_passed_not_live_qualification',
        original_failure_reproduced=reproduced,
        retained_started_cases_assessed=17,
        candidate_retained_consistency_passed=17,
        original_results=dict(passed=16,failed=1,not_executed=2),
        original_cohort_and_strict_decisions_unchanged=decisions,
        raw_public_and_frozen_integrity_verified_before_and_after=counts,
        live_cases_run=0,Docker_calls=0,builds=0,new_freeze=False,new_authorization=False,
        no_tuning=True,no_automatic_retries=True,remaining_N4_cases_disabled=2,
        other_unexecuted_cases_disabled=9,completed_cases_excluded=10,M3_complete=False,
        rows=rows,
    )
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
