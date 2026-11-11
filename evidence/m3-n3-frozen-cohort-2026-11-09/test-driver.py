"""Offline controls for the scoped entry point; all live boundaries mocked."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('n3_only',Path(__file__).with_name('run-n3-only.py'));driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)

class ScopeTests(unittest.TestCase):
    def run_mocked(self,fail=None):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t).resolve();freeze=root/'freeze.json';freeze.write_text('{}');grant=root/'grant.json'
            cases=driver.slots();auth=dict(schema_version=1,execution_authorized=True,case_ids=[s['id'] for s in cases[:9]],disabled_case_ids=[s['id'] for s in cases[9:]],freeze_sha256=driver.sha(freeze),driver_sha256=driver.sha(Path(driver.__file__)),output_relative='.local/test')
            grant.write_text(json.dumps(auth));seen=[]
            def dispatch(slot,out):
                seen.append(slot['id']);out.mkdir();return dict(run=str(out.relative_to(root)),inner_status='passed')
            def assess(run,slot,frozen):
                if fail==slot['ordinal']:raise ValueError('strict gate rejected')
                return dict(status='passed')
            with patch.object(driver,'ROOT',root),patch.object(driver,'FREEZE',freeze),patch.object(driver,'verify_freeze'),patch.object(driver,'dispatch_slot',side_effect=dispatch),patch.object(driver,'assess_case',side_effect=assess):result=driver.execute(grant)
        return result,seen
    def test_nine_only_even_if_all_pass(self):
        result,seen=self.run_mocked();self.assertEqual(len(seen),9);self.assertTrue(all(s.startswith('N3-') for s in seen));self.assertEqual(len(result['disabled_case_ids']),29);self.assertTrue(result['all_later_stages_disabled'])
    def test_first_strict_failure_stops_remaining_n3(self):
        result,seen=self.run_mocked(2);self.assertEqual(len(seen),2);self.assertEqual([r['status'] for r in result['rows']],['passed','failed']+['not_executed']*7);self.assertFalse(result['complete_M3_acceptance'])

if __name__=='__main__':unittest.main()
