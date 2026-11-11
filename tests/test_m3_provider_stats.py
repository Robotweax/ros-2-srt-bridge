import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from m3_provider_stats import summarize, COUNTERS, GAUGES, SENSOR_COUNTERS, SENSOR_GAUGES


class ProviderStatsTest(unittest.TestCase):
    def rows(self):
        row = dict(sequence=1, begin_ns=100, end_ns=110, generation=1, socket=42,
                   owner_epoch='01'*16, session='02'*16, state_before=5, state_after=5,
                   available=1, unavailable=0, idle_timeout_available=1,
                   idle_timeout_ms=5000, before_close=0)
        row.update({key: 2 for key in COUNTERS + GAUGES})
        other = dict(row, sequence=2, begin_ns=200, end_ns=210, data_sent=4)
        return [row, other]

    def parse(self, rows, sensor=False, **status):
        final = dict(attempted=len(rows), dropped=0, exhausted=0, limit=75000)
        if sensor:final.update(schema_version=1,channel=1)
        final.update(status)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bridge.log'
            prefix='SENSOR_PROVIDER_STATS' if sensor else 'PROVIDER_STATS'
            path.write_text(''.join(prefix+' '+json.dumps(row)+'\n' for row in rows)
                            +prefix+'_STATUS '+json.dumps(final)+'\n')
            return summarize(path,sensor=sensor)

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


class SensorProviderStatsTest(ProviderStatsTest):
    # Re-run availability, budget, identity, regression and gauge guards for SENSOR.
    def rows(self):
        rows=super().rows()
        for row in rows:
            row.update(schema_version=1,channel=1)
            row.update({k:2 for k in SENSOR_COUNTERS+SENSOR_GAUGES if k not in row})
        return rows

    def parse(self,rows,**status):return super().parse(rows,sensor=True,**status)

    def test_sensor_counter_and_gauge_semantics(self):
        rows=self.rows();rows[1].update(receiver_drop=5,unique_received=7,flow_window_packets=0)
        result=self.parse(rows);g=next(iter(result['connections'].values()))
        self.assertEqual(g['adjacent_deltas'][0]['counters']['receiver_drop'],3)
        self.assertEqual(g['adjacent_deltas'][0]['counters']['unique_received'],5)
        self.assertNotIn('flow_window_packets',g['adjacent_deltas'][0]['counters'])
        self.assertTrue(result['unavailable_dimensions']);self.assertEqual(result['channel'],'SENSOR')

    def test_sensor_channel_schema_and_required_fields(self):
        for key,value in [('channel',0),('schema_version',2)]:
            rows=self.rows();rows[0][key]=value
            with self.assertRaisesRegex(ValueError,'schema/channel'):self.parse(rows)
        rows=self.rows();rows[1].pop('receiver_drop')
        with self.assertRaises(KeyError):self.parse(rows)
        with self.assertRaisesRegex(ValueError,'schema/channel'):self.parse(self.rows(),channel=0)

    def test_sensor_extended_saturation_and_regression(self):
        rows=self.rows();rows[1]['receiver_drop']=2147483647
        self.assertIn('receiver_drop',next(iter(self.parse(rows)['connections'].values()))['potentially_saturated'])
        rows=self.rows();rows[1]['unique_received']=0
        with self.assertRaisesRegex(ValueError,'regressed'):self.parse(rows)


class ProviderStreamIsolationTest(unittest.TestCase):
    def test_independent_streams_in_one_log(self):
        control=ProviderStatsTest().rows();sensor=SensorProviderStatsTest().rows()
        # Counter trajectories, sequences and sockets are independent per stream.
        sensor[1]['data_sent']=100
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'bridge.log';lines=[]
            for prefix,rows in [('PROVIDER_STATS',control),('SENSOR_PROVIDER_STATS',sensor)]:
                lines.extend(prefix+' '+json.dumps(r)+'\n' for r in rows)
                final=dict(attempted=2,dropped=0,exhausted=0,limit=75000)
                if prefix.startswith('SENSOR'):final.update(schema_version=1,channel=1)
                lines.append(prefix+'_STATUS '+json.dumps(final)+'\n')
            p.write_text(''.join(lines))
            self.assertEqual(next(iter(summarize(p)['connections'].values()))['adjacent_deltas'][0]['counters']['data_sent'],2)
            self.assertEqual(next(iter(summarize(p,sensor=True)['connections'].values()))['adjacent_deltas'][0]['counters']['data_sent'],98)
