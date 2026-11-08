"""Validate optional CONTROL provider observations; never qualification authority.

Counters exclude keepalive/handshake/ACKACK and cannot prove UDP delivery.
Gauge values (including RTT zero without an estimate) are not counter deltas.
"""
import json
import math

COUNTERS = ('data_sent', 'data_received', 'retransmitted', 'ack_sent', 'ack_received',
            'nak_sent', 'nak_received', 'undecrypt', 'bytes_sent', 'bytes_received')
GAUGES = ('send_buffer_packets', 'send_buffer_bytes', 'receive_buffer_packets',
          'receive_buffer_bytes', 'flight_packets', 'rtt_ms')
INT32_COUNTERS = COUNTERS[2:8]

SENSOR_EXTRA_COUNTERS = ('unique_sent', 'unique_received', 'sender_loss', 'receiver_loss',
                         'sender_drop', 'receiver_drop', 'sender_filter_extra',
                         'receiver_filter_extra', 'receiver_filter_supply', 'receiver_filter_loss')
SENSOR_COUNTERS = COUNTERS + SENSOR_EXTRA_COUNTERS
SENSOR_GAUGES = GAUGES + ('flow_window_packets', 'congestion_window_packets')
SENSOR_UNAVAILABLE_DIMENSIONS = ['per-insertion rejection reasons/window boundaries',
    'applied retirement versus local gap expiry drop reasons', 'per-message application delivery',
    'encrypted typed SAMPLE association']


def summarize(path, *, sensor=False):
    counters = SENSOR_COUNTERS if sensor else COUNTERS
    gauges = SENSOR_GAUGES if sensor else GAUGES
    prefix = 'SENSOR_PROVIDER_STATS' if sensor else 'PROVIDER_STATS'
    rows = []; statuses = []
    with path.open() as file:
        for line in file:
            if line.startswith(prefix+' '): rows.append(json.loads(line[len(prefix)+1:]))
            elif line.startswith(prefix+'_STATUS '): statuses.append(json.loads(line[len(prefix+'_STATUS '):]))
            if len(rows) > 75000: raise ValueError('provider record bound exceeded')
    if len(statuses) != 1: raise ValueError('missing or duplicate provider final status')
    status = statuses[0]
    if sensor and (status.get('schema_version') != 1 or status.get('channel') != 1):
        raise ValueError('invalid SENSOR provider schema/channel')
    for key in ('attempted', 'dropped', 'limit'):
        if type(status.get(key)) is not int or status[key] < 0: raise ValueError('invalid provider accounting')
    if not 0 < status['limit'] <= 75000 or status['attempted'] > status['limit']:
        raise ValueError('invalid provider budget')
    if status.get('exhausted') not in (0, 1): raise ValueError('invalid exhaustion flag')
    if len(rows) + status['dropped'] != status['attempted']: raise ValueError('unaccounted provider records')
    previous = None; groups = {}; unavailable = {}; last_sequence = 0; max_gap = 0; max_read = 0
    for row in rows:
        if sensor and (row.get('schema_version') != 1 or row.get('channel') != 1):raise ValueError('invalid SENSOR provider schema/channel')
        seq = row['sequence']
        if type(seq) is not int or not last_sequence < seq <= status['attempted']: raise ValueError('invalid provider sequence')
        last_sequence = seq
        for key in ('begin_ns', 'end_ns', 'generation', 'state_before', 'state_after', 'unavailable'):
            if type(row[key]) is not int or row[key] < 0: raise ValueError('invalid provider observation')
        if row['begin_ns'] <= 0 or row['end_ns'] < row['begin_ns']: raise ValueError('invalid provider read bracket')
        if previous and row['begin_ns'] < previous['end_ns']: raise ValueError('overlapping provider reads')
        max_read = max(max_read, row['end_ns'] - row['begin_ns'])
        if previous: max_gap = max(max_gap, row['begin_ns'] - previous['begin_ns'])
        for key in ('owner_epoch', 'session'):
            if len(row[key]) != 32 or len(bytes.fromhex(row[key])) != 16: raise ValueError('invalid provider identity')
        for key in ('available', 'idle_timeout_available', 'before_close'):
            if row[key] not in (0, 1): raise ValueError('invalid provider flag')
        if row['unavailable'] not in (0, 1, 2, 3) or bool(row['available']) != (row['unavailable'] == 0):
            raise ValueError('inconsistent provider availability')
        if row['idle_timeout_available'] and (type(row['idle_timeout_ms']) is not int or row['idle_timeout_ms'] <= 0):
            raise ValueError('invalid idle timeout readback')
        if row['available']:
            if type(row['socket']) is not int or row['socket'] < 0 or not row['generation']:
                raise ValueError('invalid provider connection')
            for key in counters:
                if type(row[key]) is not int or row[key] < 0: raise ValueError('invalid provider counter')
            for key in gauges:
                if not isinstance(row[key], (int, float)) or not math.isfinite(row[key]) or row[key] < 0:
                    raise ValueError('invalid provider gauge')
            identity = (row['owner_epoch'], row['generation'], row['socket'])
            name = ':'.join(map(str, identity))
            group = groups.setdefault(name, dict(records=0, adjacent_deltas=[], potentially_saturated=[]))
            group['records'] += 1
            for key in (INT32_COUNTERS + SENSOR_EXTRA_COUNTERS[2:] if sensor else INT32_COUNTERS):
                if row[key] >= 2147483647 and key not in group['potentially_saturated']: group['potentially_saturated'].append(key)
            if previous and previous['available'] and (previous['owner_epoch'], previous['generation'], previous['socket']) == identity:
                delta = {key: row[key] - previous[key] for key in counters}
                if any(value < 0 for value in delta.values()): raise ValueError('provider counter regressed within connection')
                group['adjacent_deltas'].append(dict(previous_read_ns=[previous['begin_ns'], previous['end_ns']], current_read_ns=[row['begin_ns'], row['end_ns']], counters=delta))
        else:
            reason = str(row['unavailable']); unavailable[reason] = unavailable.get(reason, 0) + 1
        previous = row
    return dict(complete=bool(rows) and status['dropped'] == 0 and not status['exhausted'],
                status=status, records=rows, connections=groups, unavailable=unavailable,
                max_sample_start_gap_ns=max_gap, max_read_duration_ns=max_read,
                channel='SENSOR' if sensor else 'CONTROL',
                unavailable_dimensions=SENSOR_UNAVAILABLE_DIMENSIONS if sensor else [],
                scope=('SENSOR existing aggregate provider counters; no exact retirement/insertion reason or application mapping; ' if sensor else 'CONTROL only; ')+'SDK mutex/bookkeeping observer cost; cumulative DATA/ACK/NAK counters exclude other UDP types; smoothed buffer gauges, not interval deltas; no delivery or qualification authority')


def summarize_run(run, *, sensor=False):
    results = {p.name: summarize(p,sensor=sensor) for p in sorted(run.glob('*-bridge-*.log'))}
    if not all(any(name.startswith(role + '-bridge-') for name in results) for role in ('robot', 'operator')):
        raise ValueError('missing provider endpoints')
    if not all(result['complete'] for result in results.values()): raise ValueError('incomplete provider diagnostics')
    return results
