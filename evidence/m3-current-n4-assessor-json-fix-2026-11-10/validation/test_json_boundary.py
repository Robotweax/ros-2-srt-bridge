"""Offline JSON-boundary regression tests; no live driver or subprocess calls."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
PREP = ROOT / 'evidence/m3-current-n4-preparation-2026-11-10'
sys.path[:0] = [str(PREP), str(ROOT / 'tools')]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


candidate = load('json_boundary_candidate', HERE / 'assess.py')
original = load('json_boundary_original', PREP / 'assess.py')
from cases import cases


class JsonBoundaryTests(unittest.TestCase):
    def fixture(self, mode='before'):
        expected = 4 if mode == 'committed' else 8
        return dict(
            sender_journal=dict(sha256='sender-sha', entries={'01': dict(state=expected, reason=2, deadline_ns=5000, result_valid=mode == 'committed')}),
            receiver_journal=dict(sha256='receiver-sha', entries={}),
            sender_trace=dict(complete=True, attempted=2, dropped=0, counts={'provider_sent': 1}, events=[dict(point=25, request='01')], point_names={1: 'endpoint_started', 25: 'provider_sent'}, reason_names={0: 'none', 5: 'deadline'}),
            status=dict(state=expected, result_valid=mode == 'committed'),
            device=dict(effects=0 if mode == 'before' else 1),
            controlled_traces=[dict(name='operator-bridge-0.log', complete=True)],
            expected_crashes=[dict(exit=-9)],
        )

    def assess(self, proof, *, recorded=None, module=candidate, mode='before', error=None, report_delta=None):
        slot = next(s for s in cases() if s['id'] == 'N4-ROS-crash-' + mode)
        report = dict(status='passed', mode=mode, clock_proof={}, shutdown={r: dict(passed=True) for r in ('operator', 'robot')}, crash=json.loads(json.dumps(proof)) if recorded is None else recorded)
        report.update(report_delta or {})
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / 'result.json').write_text(json.dumps(report))
            (out / 'provenance.json').write_text('{}')
            with patch.object(module, 'provenance'), patch.object(module, 'common_clock'), patch.object(module, 'cleanup') as cleanup, patch.object(module, 'check_crash', return_value=proof, side_effect=error) as check:
                try:
                    result = module.assess_case(out, slot, {})
                except ValueError:
                    cleanup.assert_not_called()
                    raise
                check.assert_called_once_with(out, mode)
                cleanup.assert_called_once_with(out)
                return result

    def test_original_reproduces_integer_string_key_failure(self):
        with self.assertRaisesRegex(ValueError, 'ROS crash audit differs'):
            self.assess(self.fixture(), module=original)

    def test_all_three_crash_modes_cross_real_JSON_persistence(self):
        for mode in ('before', 'effect', 'committed'):
            with self.subTest(mode=mode):
                proof = self.fixture(mode)
                before = copy.deepcopy(proof)
                result = self.assess(proof, mode=mode)
                self.assertEqual(result['status'], 'passed')
                self.assertEqual(result['proof'], json.loads(json.dumps(proof)))
                self.assertEqual(proof, before)

    def test_returned_proof_is_stable_across_second_persistence(self):
        result = self.assess(self.fixture())
        self.assertEqual(result, json.loads(json.dumps(result)))

    def test_actual_command_trace_schema_uses_integer_maps(self):
        from m3_command_trace import summarize
        raw = ROOT / '.local/current-n4-cohort-20261110T141000377424Z/N4-ROS-crash-before/operator-bridge-0.log'
        trace = summarize(raw)
        self.assertTrue(all(type(k) is int for k in trace['point_names']))
        self.assertTrue(all(type(k) is int for k in trace['reason_names']))
        proof = self.fixture()
        proof['sender_trace'] = trace
        self.assertEqual(self.assess(proof)['status'], 'passed')

    def test_genuine_durable_and_trace_changes_are_rejected(self):
        proof = self.fixture()
        paths = [
            ('sender_journal', 'sha256'),
            ('sender_journal', 'entries', '01', 'deadline_ns'),
            ('sender_journal', 'entries', '01', 'state'),
            ('sender_journal', 'entries', '01', 'reason'),
            ('sender_journal', 'entries', '01', 'result_valid'),
            ('receiver_journal', 'sha256'),
            ('device', 'effects'),
            ('status', 'state'),
            ('sender_trace', 'attempted'),
            ('sender_trace', 'complete'),
            ('sender_trace', 'point_names', '25'),
            ('sender_trace', 'reason_names', '5'),
            ('controlled_traces', 0, 'complete'),
            ('expected_crashes', 0, 'exit'),
            ('sender_trace', 'events', 0, 'request'),
        ]
        for path in paths:
            with self.subTest(path=path):
                recorded = json.loads(json.dumps(proof))
                target = recorded
                for key in path[:-1]:
                    target = target[key]
                old = target[path[-1]]
                target[path[-1]] = not old if type(old) is bool else old + 1 if type(old) is int else old + '-changed'
                with self.assertRaisesRegex(ValueError, 'ROS crash audit differs'):
                    self.assess(proof, recorded=recorded)

    def test_missing_extra_and_reordered_evidence_refused(self):
        proof = self.fixture()
        proof['sender_trace']['events'].append(dict(point=9, request='01'))
        for change in ('missing', 'extra', 'event-order', 'map-entry-missing'):
            with self.subTest(change=change):
                recorded = json.loads(json.dumps(proof))
                if change == 'missing':
                    del recorded['receiver_journal']
                elif change == 'extra':
                    recorded['extra'] = True
                elif change == 'event-order':
                    recorded['sender_trace']['events'].reverse()
                else:
                    del recorded['sender_trace']['point_names']['25']
                with self.assertRaisesRegex(ValueError, 'ROS crash audit differs'):
                    self.assess(proof, recorded=recorded)

    def test_gate_exceptions_propagate_without_cleanup_or_success(self):
        for message in ('deadline extended or accepted command replayed', 'wrong recovered outcome/effect count', 'receiver admitted cut command', 'controlled incarnation command trace incomplete'):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.assess(self.fixture(), error=ValueError(message))

    def test_failed_inner_result_or_shutdown_cannot_pass(self):
        for delta, message in [(dict(status='failed'), 'N4 inner harness failed'), (dict(shutdown=dict(operator=dict(passed=False), robot=dict(passed=True))), 'ROS N4 shutdown incomplete')]:
            with self.subTest(delta=delta), self.assertRaisesRegex(ValueError, message):
                self.assess(self.fixture(), report_delta=delta)

    def test_nonfinite_recomputed_proof_refused(self):
        for value in (float('nan'), float('inf'), float('-inf')):
            proof = self.fixture()
            proof['unexpected_nonfinite'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.assess(proof)

    def test_candidate_changes_only_crash_representation_boundary(self):
        old = (PREP / 'assess.py').read_text()
        new = (HERE / 'assess.py').read_text()
        self.assertEqual(new, old.replace("proof=check_crash(run,slot['phase']);", "proof=json.loads(json.dumps(check_crash(run,slot['phase']),allow_nan=False));"))
        old_tree, new_tree = ast.parse(old), ast.parse(new)
        # All pre-assessment imports and provenance checks remain byte-equivalent ASTs.
        self.assertEqual([ast.dump(n) for n in old_tree.body[:-1]], [ast.dump(n) for n in new_tree.body[:-1]])


if __name__ == '__main__':
    unittest.main()
