"""Offline binding checks; no cases, builds or Docker calls."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
PRIOR = ROOT / 'evidence/m3-current-n4-preparation-2026-11-10'
FIX = ROOT / 'evidence/m3-current-n4-assessor-json-fix-2026-11-10'
EXEC = ROOT / 'evidence/m3-current-n4-execution-2026-11-10'
sys.path[:0] = [str(HERE), str(ROOT / 'tools')]
spec = importlib.util.spec_from_file_location('corrected_N4_preparation', HERE / 'prepare.py')
preparation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preparation)
from cases import authorize


class FreezeBindingTests(unittest.TestCase):
    def test_candidate_exact_bytes_and_hash_bound(self):
        binding = preparation.bind_corrected_assessor()
        self.assertEqual(binding['sha256'], preparation.sha(FIX / 'assess.py'))
        self.assertEqual((HERE / 'assess.py').read_bytes(), (FIX / 'assess.py').read_bytes())
        self.assertNotEqual(preparation.sha(PRIOR / 'assess.py'), binding['sha256'])

    def test_stale_local_assessor_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'assess.py').write_bytes((PRIOR / 'assess.py').read_bytes())
            with patch.object(preparation, 'HERE', path), self.assertRaisesRegex(ValueError, 'corrected assessor differs'):
                preparation.bind_corrected_assessor()

    def test_verified_candidate_drift_refused(self):
        actual = preparation.sha
        def drift(path):
            return 'changed' if Path(path) == FIX / 'assess.py' else actual(path)
        with patch.object(preparation, 'sha', side_effect=drift), self.assertRaisesRegex(ValueError, 'corrected assessor differs'):
            preparation.bind_corrected_assessor()

    def test_previous_execution_grant_cannot_authorize_new_freeze(self):
        old = json.loads((EXEC / 'authorization.json').read_text())
        with self.assertRaises(ValueError):
            authorize(old, 'fresh-freeze-hash')

    def test_unchanged_driver_and_phase_scripts_only_ROS_path_rebound(self):
        for name in ('run.py', 'cases.py', 'n4_fixture.py', 'native_adapter.py', 'ros_sensor.py', 'ros_crash.py', 'emergency_cleanup.py', 'binary-verification.json', 'disposition_runtime.py'):
            self.assertEqual((HERE / name).read_bytes(), (PRIOR / name).read_bytes(), name)
        expected = (PRIOR / 'ros_adapter.py').read_text().replace(str(PRIOR.relative_to(ROOT)), str(HERE.relative_to(ROOT)))
        self.assertEqual((HERE / 'ros_adapter.py').read_text(), expected)

    def test_stopped_decisions_and_two_unexecuted_directories_preserved(self):
        report = json.loads((EXEC / 'cohort.json').read_text())
        self.assertEqual([r['status'] for r in report['rows']], ['passed'] * 16 + ['failed'] + ['not_executed'] * 2)
        old = json.loads((PRIOR / 'freeze.json').read_text())
        for row in report['rows'][-2:]:
            self.assertFalse((ROOT / old['output_relative'] / row['slot']['id']).exists())

    def test_fresh_interpreter_runtime_import_order_selects_exact_assessor(self):
        code = "import sys;sys.path[:0]=sys.argv[1:];import run;import assess;from pathlib import Path;print(Path(assess.__file__).resolve());print(run.sha(Path(assess.__file__)))"
        result = subprocess.check_output([sys.executable, '-c', code, str(HERE), str(ROOT / 'tools')], text=True).splitlines()
        self.assertEqual(result, [str(HERE / 'assess.py'), preparation.sha(FIX / 'assess.py')])

    def test_existing_freeze_refused_before_any_runtime_inspection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'freeze.json').write_text('{}')
            with patch.object(preparation, 'HERE', path), patch.object(preparation.subprocess, 'check_output', side_effect=AssertionError('no Docker')), self.assertRaisesRegex(ValueError, 'already frozen'):
                preparation.main()


if __name__ == '__main__':
    unittest.main()
