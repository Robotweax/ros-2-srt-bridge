#!/usr/bin/env python3
"""Finite authenticated installed-provider SENSOR FEC cases; no ROS acceptance."""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import secrets
import struct
import subprocess
import time
from m3_network import NetworkLab
from m3_neighbor_diagnostics import configure
from m3_sensor_fault import Selection, install, remove, readback, counters
from m3_capture import pcap_options, stop_captures, validate_tcpdump_footer
from m3_monotonic_capture import start, records, decode, feature_snapshot
from m3_dds_result_timeline import common_clock

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2)+'\n')


def wait_files(run, names, peers):
    end = time.monotonic()+12
    while not all((run/name).exists() for name in names):
        if any(p.poll() is not None for p, _ in peers) or time.monotonic() > end:
            raise RuntimeError('peer file barrier failed: '+','.join(names))
        time.sleep(.02)


def header(frame):
    if len(frame) < 34 or frame[12:14] != b'\x08\x00' or frame[23] != 17:
        return None
    if frame[14] != 0x45 or struct.unpack_from('!H', frame, 20)[0] & 0x3fff:
        raise ValueError('unsupported SENSOR IPv4 framing')
    sp, dp, length = struct.unpack_from('!HHH', frame, 34)
    if (sp, dp) != (39781, 10081):
        return None
    if length < 24 or len(frame) < 58:
        raise ValueError('short SENSOR header')
    seq, msg, _, sid = struct.unpack_from('!IIII', frame, 42)
    if seq & 0x80000000:
        return None
    return seq, msg & 0x03ffffff, sid, bool(msg & 0x04000000)


def pcap_population(path):
    values = []; total = 0
    with path.open('rb') as f:
        h = f.read(24)
        if len(h) != 24 or h[:4] != b'\xd4\xc3\xb2\xa1' or struct.unpack_from('<I', h, 20)[0] != 1:
            raise ValueError('unsupported PCAP')
        while True:
            r = f.read(16)
            if not r:
                break
            if len(r) != 16:
                raise ValueError('short PCAP header')
            _, _, n, original = struct.unpack('<IIII', r)
            if not 14 <= n == original <= 65535:
                raise ValueError('invalid PCAP frame size')
            data = f.read(n)
            if len(data) != n:
                raise ValueError('short PCAP frame')
            total += 1; value = header(data)
            if value is not None:
                values.append(value)
    return total, Counter(values)


def validate_outcomes(sender, receiver, losses):
    expected = set(range(16)) - ({6, 7} if losses == 2 else set())
    if [r['id'] for r in sender['entries']] != list(range(16)) or [r['msgno'] for r in sender['entries']] != list(range(1, 17)):
        raise ValueError('sender identity assignment differs')
    ids = [r['id'] for r in receiver['entries']]
    if len(ids) != len(set(ids)) or set(ids) != expected or any(r['msgno'] != r['id']+1 for r in receiver['entries']):
        raise ValueError('receiver delivery/identity outcome differs')
    # Pinned RowFecDecoder::expire_row reports irrecoverable ranges only for
    # arq:onreq. SENSOR arq:never supplies no generic irrecoverable-loss count.
    # Missing IDs are finite observation outcomes, not that provider counter.
    a = sender['final_stats']; b = receiver['final_stats']
    if not sender['connected'] or not receiver['connected'] or a['retransmitted'] or b['undecryptable'] or a['filter_extra_sent'] != 4 or b['filter_extra_received'] != 4 or b['filter_supplied'] != (1 if losses == 1 else 0) or b['filter_loss'] != 0:
        raise ValueError('provider FEC/security counters differ')
    if any(sender['initial_stats'].values()) or any(receiver['initial_stats'].values()):
        raise ValueError('unexpected pre-arm DATA/FEC statistics')
    return dict(delivered_ids=sorted(ids), missing_ids=sorted(set(range(16))-set(ids)), repaired=b['filter_supplied'], filter_loss_reported=b['filter_loss'], retransmitted=a['retransmitted'], undecryptable=b['undecryptable'])


def analyze_captures(run, lab, ready, losses):
    origin = ready['sender']['initial_sequence']; sid = ready['receiver']['socket_id']
    excluded = set() if losses == 0 else {7} if losses == 1 else {6, 7}
    expected = Counter([((origin+i)&0x7fffffff, i+1, sid, False) for i in range(16) if i not in excluded] +
                       [((origin+i)&0x7fffffff, 0, sid, False) for i in (3, 7, 11, 15)])
    results = {}
    for role in lab.containers:
        status = json.loads((run/(role+'-monotonic-capture.log')).read_text().splitlines()[-1])
        rows = list(records(run/(role+'.mono')))
        if status.get('artifact_version') != 2 or not status['complete'] or not status['time_namespace_zero'] or status['clock'] != 'kernel_monotonic' or not status['records'] == status['seen'] == status['submitted'] == len(rows) or status['reserve_failed'] or status['copy_failed']:
            raise ValueError('incomplete native capture')
        selected = []; handshake_origins = []
        for row in rows:
            if row['ifindex'] != status['ifindex']:
                raise ValueError('interface changed')
            decode(row, lab.addresses[role])
            if row['gso_segs'] not in (0, 1) or row['gso_size'] or row['vlan_present'] or row['length'] > status['mtu']+14:
                raise ValueError('unqualified native frame')
            value = header(row['prefix'])
            if value is not None:
                if row['packet_type'] != (4 if role == 'robot' else 0):
                    raise ValueError('SENSOR direction differs')
                if not status['ready_ns'] <= ready['sender']['ready_ns'] < row['monotonic_ns'] <= status['stop_before_ns']:
                    raise ValueError('DATA outside ready/capture coverage')
                selected.append(value)
            frame = row['prefix']
            if role == 'robot' and row['packet_type'] == 4 and len(frame) >= 106 and frame[12:14] == b'\x08\x00' and frame[14] == 0x45 and frame[23] == 17 and struct.unpack_from('!HH', frame, 34) == (39781, 10081) and struct.unpack_from('!I', frame, 42)[0] == 0x80000000:
                handshake_origins.append(struct.unpack_from('!I', frame, 66)[0])
        total, pcaps = pcap_population(run/(role+'.pcap'))
        footer = validate_tcpdump_footer((run/(role+'-capture.log')).read_text(), total)
        if Counter(selected) != expected or pcaps != expected or not footer['tcpdump_population_reconciled']:
            raise ValueError('source/parity capture population differs')
        if role == 'robot' and (not handshake_origins or set(handshake_origins) != {origin}):
            raise ValueError('wire handshake does not confirm sender initial sequence')
        results[role] = dict(status=status, footer=footer, source_packets=16-losses, parity_packets=4, identities=[list(v) for v in selected], handshake_initial_sequences=handshake_origins)
    return results


def run_case(run, image, losses):
    run.mkdir(); inside = '/workspace/'+str(run.relative_to(ROOT))
    lab = NetworkLab(ROOT, run, image, monotonic_capture=True)
    captures = []; peers = []; fault = None
    key = run/'passphrase'; key.touch(mode=0o600); key.write_text(secrets.token_urlsafe(32))
    result = dict(status='running', losses=losses, qualification=False)
    try:
        lab.start(key); result['clock_proof'] = {r:lab.inside(r, r+'-clock-proof', ['sh', '-c', 'cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for r in lab.containers}; common_clock(result['clock_proof'])
        configure(lab, 'permanent'); lab.apply('N0', 1701)
        result['features_before'] = feature_snapshot(lab, 'features-before')
        for role, name in lab.containers.items():
            log = (run/(role+'-capture.log')).open('w')
            captures.append((subprocess.Popen(['docker', 'exec', name]+pcap_options()+['-w', inside+'/'+role+'.pcap', 'udp'], stdout=log, stderr=subprocess.STDOUT), log))
        start(run, inside, lab, captures)
        end = time.monotonic()+5
        while not all('listening on eth0' in (run/(r+'-capture.log')).read_text() for r in lab.containers):
            if time.monotonic() > end:
                raise ValueError('tcpdump not ready')
            time.sleep(.05)
        for role, mode in (('operator', 'receive'), ('robot', 'send')):
            if role == 'robot':
                wait_files(run, ['listening'], peers)
            log = (run/(mode+'-peer.log')).open('w')
            peers.append((subprocess.Popen(['docker', 'exec', lab.containers[role], 'build/m3-sensor-peer/m3_sensor_peer', mode, inside, lab.addresses['operator'], '/run/bridge/passphrase'], stdout=log, stderr=subprocess.STDOUT), log))
        wait_files(run, ['sender-ready.json', 'receiver-ready.json'], peers)
        ready = {side:json.loads((run/(side+'-ready.json')).read_text()) for side in ('sender', 'receiver')}; result['ready'] = ready
        if ready['sender']['initial_sequence'] != ready['receiver']['initial_sequence']:
            raise ValueError('negotiated origins differ')
        if losses:
            selection = Selection(ready['sender']['initial_sequence'], 1, (3,) if losses == 1 else (2, 3), (8,) if losses == 1 else (7, 8), ready['receiver']['socket_id'], 39781, 10081)
            result['selection'] = asdict(selection); fault = install(lab, selection); result['fault'] = fault
        (run/'armed').touch(); wait_files(run, ['sent'], peers)
        time.sleep(1)
        (run/'finish-receiver').touch(); (run/'finish-sender').touch()
        wait_files(run, ['sender-result.json', 'receiver-result.json'], peers)
        if fault:
            result['final_counters'] = counters(readback(lab, 'sensor-fault-final'), losses)
            if any(c['drops'] != 1 for c in result['final_counters']):
                raise ValueError('selected drop counts differ')
            remove(lab, fault)
        result['outcome'] = validate_outcomes(json.loads((run/'sender-result.json').read_text()), json.loads((run/'receiver-result.json').read_text()), losses)
        (run/'release').touch()
        for p, log in peers:
            if p.wait(timeout=5) != 0:
                raise ValueError('peer exit failed')
            log.close()
        stop_captures(lab, drain_check=True)
        for p, log in captures:
            if p.wait(timeout=5) != 0:
                raise ValueError('capture exit failed')
            log.close()
        result['features_after'] = feature_snapshot(lab, 'features-after')
        if result['features_before'] != result['features_after']:
            raise ValueError('features changed')
        result['captures'] = analyze_captures(run, lab, ready, losses)
        result.update(status='passed', scope='finite installed-provider authenticated SENSOR FEC over owned IPv4 veth; no ROS publication/age, CONTROL commands, physical delivery or full M3 acceptance')
    except Exception as error:
        result.update(status='failed', error=str(error)); raise
    finally:
        if fault and not fault['restored']:
            try:
                remove(lab, fault)
            except Exception as error:
                result['cleanup_error'] = str(error)
        (run/'release').touch(); (run/'finish-sender').touch(); (run/'finish-receiver').touch()
        for p, log in peers:
            if p.poll() is None:
                p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill(); p.wait(timeout=5)
            if not log.closed:
                log.close()
        try:
            if any(p.poll() is None for p, _ in captures):
                stop_captures(lab)
            for p, log in captures:
                p.wait(timeout=5)
                if not log.closed:
                    log.close()
        finally:
            lab.cleanup(); key.unlink(missing_ok=True); write(run/'result.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', required=True, type=Path); p.add_argument('--losses', type=int, choices=(0, 1, 2), nargs='+', default=[0, 1, 2]); args = p.parse_args()
    run = args.out.resolve(); run.mkdir(parents=True, exist_ok=False)
    image = json.loads(subprocess.check_output(['docker', 'image', 'inspect', '--platform', 'linux/amd64', 'ros2-srt-m3:20261105'], text=True))[0]['RepoDigests'][0]
    report = dict(status='running', image=image, cases=[])
    try:
        for losses in args.losses:
            report['cases'].append(run_case(run/str(losses), image, losses))
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error=str(error)); raise
    finally:
        write(run/'result.json', report)
