import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from m3_provider_stats import summarize, COUNTERS, GAUGES


class ProviderStatsTest(unittest.TestCase):
    def rows(self):
        row = dict(sequence=1, begin_ns=100, end_ns=110, generation=1, socket=42,
                   owner_epoch='01'*16, session='02'*16, state_before=5, state_after=5,
                   available=1, unavailable=0, idle_timeout_available=1,
                   idle_timeout_ms=5000, before_close=0)
        row.update({key: 2 for key in COUNTERS + GAUGES})
        other = dict(row, sequence=2, begin_ns=200, end_ns=210, data_sent=4)
        return [row, other]

    def parse(self, rows, **status):
        final = dict(attempted=len(rows), dropped=0, exhausted=0, limit=75000)
        final.update(status)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bridge.log'
            path.write_text(''.join('PROVIDER_STATS '+json.dumps(row)+'\n' for row in rows)
                            +'PROVIDER_STATS_STATUS '+json.dumps(final)+'\n')
            return summarize(path)

    def test_brackets_cadence_and_delta(self):
        result = self.parse(self.rows())
        self.assertTrue(result['complete'])
        self.assertEqual(result['max_read_duration_ns'], 10)
        self.assertEqual(result['max_sample_start_gap_ns'], 100)
        group = next(iter(result['connections'].values()))
        self.assertEqual(group['adjacent_deltas'][0]['counters']['data_sent'], 2)
        self.assertNotIn('rtt_ms', group['adjacent_deltas'][0]['counters'])
        self.assertEqual(group['adjacent_deltas'][0]['previous_read_ns'], [100, 110])
        self.assertEqual(group['adjacent_deltas'][0]['current_read_ns'], [200, 210])

    def test_connection_reset_is_not_counter_regression(self):
        for key, value in [('generation', 2), ('owner_epoch', '03'*16), ('socket', 43)]:
            rows = self.rows(); rows[1][key] = value; rows[1]['data_sent'] = 0
            result = self.parse(rows)
            self.assertEqual(len(result['connections']), 2)
            self.assertTrue(all(not g['adjacent_deltas'] for g in result['connections'].values()))

    def test_regression_rejected(self):
        rows = self.rows(); rows[1]['data_sent'] = 0
        with self.assertRaisesRegex(ValueError, 'regressed'): self.parse(rows)

    def test_unavailable_is_not_zero_counter(self):
        rows = self.rows(); rows[1].update(available=0, unavailable=3)
        rows[1].pop('data_sent')
        result = self.parse(rows)
        self.assertEqual(result['unavailable'], {'3': 1})
        self.assertFalse(next(iter(result['connections'].values()))['adjacent_deltas'])

    def test_loss_budget_and_missing(self):
        rows = self.rows(); rows[1]['sequence'] = 3
        self.assertFalse(self.parse(rows, attempted=3, dropped=1)['complete'])
        self.assertFalse(self.parse(self.rows(), exhausted=1)['complete'])
        with self.assertRaisesRegex(ValueError, 'unaccounted'): self.parse(rows, attempted=3)
        with self.assertRaisesRegex(ValueError, 'sequence'): self.parse(rows)
        self.assertFalse(self.parse([])['complete'])

    def test_bad_brackets_sequence_identity_and_gauge(self):
        for key, value in [('end_ns', 0), ('sequence', 0), ('owner_epoch', 'oops'),
                           ('rtt_ms', float('nan')), ('available', 0)]:
            rows = self.rows(); rows[1][key] = value
            with self.assertRaises(ValueError): self.parse(rows)

    def test_saturation_is_explicit(self):
        rows = self.rows(); rows[1]['ack_sent'] = 2147483647
        group = next(iter(self.parse(rows)['connections'].values()))
        self.assertEqual(group['potentially_saturated'], ['ack_sent'])
