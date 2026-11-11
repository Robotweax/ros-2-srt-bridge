#!/usr/bin/env python3
"""Finite synthetic SRT-header selector qualification; no SRT/FEC recovery claim."""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import time
from m3_network import NetworkLab
from m3_neighbor_diagnostics import configure
from m3_sensor_fault import Selection, install, remove, readback, counters
from m3_capture import pcap_options, stop_captures, validate_tcpdump_footer
from m3_monotonic_capture import start, records, feature_snapshot

ROOT = Path(__file__).resolve().parents[1]
MAGIC = b'N3PROBE1'
PORT = 39781


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2)+'\n')


def population(selection):
    base = selection.targets()[0]['sequence'] - selection.positions[0]
    rows = []
    def add(label, seq, msg=1, sid=123, port=10081):
        rows.append(dict(id=len(rows), label=label, sequence=seq & 0x7fffffff,
                         message=msg, socket_id=sid, source_port=port))
    for p in range(4):
        add('source-'+str(p), base+p, p+1)
    # Parity shares the LAST source sequence, including when that source is selected.
    add('parity-same-last-sequence', base+3, 0)
    add('srt-control', base+3, 0)
    rows[-1]['sequence'] |= 0x80000000
    add('other-row', base+4, 1)
    add('other-socket', base+3, 4, sid=124)
    add('other-message', base+3, 5)
    add('control-port', base+3, 4, port=10080)
    add('other-port', base+3, 4, port=39780)
    add('retransmitted-target', base+3, 4 | 0x04000000)
    return rows


def identity(frame):
    if len(frame) < 34 or frame[12:14] != b'\x08\x00' or frame[23] != 17:
        return None
    offset = 14+(frame[14] & 15)*4+8+16
    if frame[offset:offset+8] != MAGIC:
        return None
    return struct.unpack_from('!I', frame, offset+8)[0]


def pcap_ids(path):
    result = []
    count = 0
    with Path(path).open('rb') as file:
        h = file.read(24)
        if len(h) != 24 or h[:4] != b'\xd4\xc3\xb2\xa1' or struct.unpack_from('<I', h, 20)[0] != 1:
            raise ValueError('unsupported probe PCAP')
        while True:
            header = file.read(16)
            if not header:
                break
            if len(header) != 16:
                raise ValueError('truncated PCAP header')
            _, _, size, original = struct.unpack('<IIII', header)
            data = file.read(size)
            if size != original or len(data) != size:
                raise ValueError('truncated PCAP frame')
            count += 1
            value = identity(data)
            if value is not None:
                result.append(value)
    return count, Counter(result)


def receive(args):
    rows = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server:
        server.bind(('0.0.0.0', PORT)); server.settimeout(.05)
        Path(args.ready).touch(); deadline = time.monotonic()+20
        while not Path(args.stop).exists():
            if time.monotonic() > deadline:
                raise RuntimeError('receiver timeout')
            try:
                payload, _ = server.recvfrom(65536)
            except socket.timeout:
                continue
            if len(payload) != 128 or payload[16:24] != MAGIC:
                raise ValueError('unexpected probe payload')
            rows.append(struct.unpack_from('!I', payload, 24)[0])
    write(args.out, rows)


def send(args):
    rows = json.loads(Path(args.plan).read_text())
    for row in rows:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
            client.bind(('0.0.0.0', row['source_port']))
            data = struct.pack('!IIII', row['sequence'], row['message'], 999, row['socket_id'])+MAGIC+struct.pack('!I', row['id'])+bytes(100)
            if client.sendto(data, (args.peer, PORT)) != len(data):
                raise ValueError('short send')
        time.sleep(.01)


def run_case(run, image, count):
    run.mkdir(); inside = '/workspace/'+str(run.relative_to(ROOT))
    lab = NetworkLab(ROOT, run, image, monotonic_capture=True)
    captures = []; server = None; log = None; fault = None
    key = run/'passphrase'; key.touch(mode=0o600); key.write_text(secrets.token_urlsafe(32))
    selection = Selection(0x7ffffffc, 0, (3,) if count == 1 else (2, 3), (4,) if count == 1 else (3, 4), 123)
    rows = population(selection); write(run/'sent-plan.json', rows)
    dropped = [r['id'] for r in rows if any(r['sequence'] == t['sequence'] and r['message'] & 0x03ffffff == t['message_number'] and r['socket_id'] == selection.socket_id and r['source_port'] == 10081 for t in selection.targets())]
    expected = Counter(r['id'] for r in rows if r['id'] not in dropped)
    result = dict(status='running', selection=asdict(selection), sent=len(rows), expected_drop_ids=dropped, qualification=False)
    try:
        lab.start(key); configure(lab, 'permanent'); lab.apply('N0', 1701)
        before = feature_snapshot(lab, 'features-before')
        for role, name in lab.containers.items():
            capture_log = (run/(role+'-capture.log')).open('w')
            captures.append((subprocess.Popen(['docker', 'exec', name]+pcap_options()+['-w', inside+'/'+role+'.pcap', 'udp'], stdout=capture_log, stderr=subprocess.STDOUT), capture_log))
        start(run, inside, lab, captures)
        log = (run/'receiver.log').open('w')
        server = subprocess.Popen(['docker', 'exec', lab.containers['operator'], 'python3', 'tools/m3_sensor_fault_probe.py', 'receive', '--out', inside+'/received.json', '--ready', inside+'/ready', '--stop', inside+'/stop'], stdout=log, stderr=subprocess.STDOUT)
        deadline = time.monotonic()+5
        while not (run/'ready').exists() or not all('listening on eth0' in (run/(r+'-capture.log')).read_text() for r in lab.containers):
            if server.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('probe readiness failed')
            time.sleep(.05)
        fault = install(lab, selection); result['fault'] = fault
        lab.inside('robot', 'send', ['python3', 'tools/m3_sensor_fault_probe.py', 'send', '--peer', lab.addresses['operator'], '--plan', inside+'/sent-plan.json'])
        time.sleep(.3)
        result['final_counters'] = counters(readback(lab, 'sensor-fault-final'), count)
        if sum(c['drops'] for c in result['final_counters']) != len(dropped):
            raise ValueError('drop counter mismatch')
        remove(lab, fault)
        # Same sockets/identities forward after selector removal.
        restored = rows[3].copy(); restored['id'] = 100
        write(run/'restore-plan.json', [restored])
        lab.inside('robot', 'restored-send', ['python3', 'tools/m3_sensor_fault_probe.py', 'send', '--peer', lab.addresses['operator'], '--plan', inside+'/restore-plan.json'])
        expected[100] = 1; time.sleep(.3)
        (run/'stop').touch()
        if server.wait(timeout=5) != 0:
            raise ValueError('receiver failed')
        server = None; log.close()
        stop_captures(lab, drain_check=True)
        for process, capture_log in captures:
            if process.wait(timeout=5) != 0:
                raise ValueError('capture process failed')
            capture_log.close()
        if feature_snapshot(lab, 'features-after') != before:
            raise ValueError('interface features changed')
        result['features'] = before; result['captures'] = {}
        for role in lab.containers:
            status = json.loads((run/(role+'-monotonic-capture.log')).read_text().splitlines()[-1]); native = list(records(run/(role+'.mono')))
            if not status['complete'] or not status['records'] == status['seen'] == status['submitted'] == len(native) or status['reserve_failed'] or status['copy_failed']:
                raise ValueError('native capture incomplete')
            ids = Counter(identity(r['prefix']) for r in native if identity(r['prefix']) is not None)
            total, pids = pcap_ids(run/(role+'.pcap'))
            footer = validate_tcpdump_footer((run/(role+'-capture.log')).read_text(), total)
            if not footer['tcpdump_population_reconciled'] or ids != expected or pids != expected:
                raise ValueError('capture identity populations differ')
            result['captures'][role] = dict(footer=footer, native_status=status, known_ids=dict(ids))
        received = Counter(json.loads((run/'received.json').read_text()))
        if received != expected:
            raise ValueError('receiver identity population differs')
        result.update(status='passed', received_ids=dict(received), features_unchanged=True,
                      scope='synthetic public SRT headers only; exact selected source identities removed before tap; parity/control/negative identities forwarded; no authentication, FEC repair, ROS or M3 acceptance claim')
    except Exception as error:
        result.update(status='failed', error=str(error)); raise
    finally:
        if fault and not fault['restored']:
            try:
                remove(lab, fault)
            except Exception as error:
                result['cleanup_error'] = str(error)
        if server is not None and server.poll() is None:
            (run/'stop').touch()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.terminate(); server.wait(timeout=5)
        if log is not None and not log.closed:
            log.close()
        try:
            if any(p.poll() is None for p, _ in captures):
                stop_captures(lab)
            for p, capture_log in captures:
                p.wait(timeout=5)
                if not capture_log.closed:
                    capture_log.close()
        finally:
            lab.cleanup(); key.unlink(missing_ok=True); write(run/'result.json', result)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='mode', required=True)
    r = sub.add_parser('receive')
    for flag in ('out', 'ready', 'stop'):
        r.add_argument('--'+flag, required=True)
    s = sub.add_parser('send'); s.add_argument('--peer', required=True); s.add_argument('--plan', required=True)
    r = sub.add_parser('run'); r.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    if args.mode == 'receive':
        receive(args)
    elif args.mode == 'send':
        send(args)
    else:
        run = args.out.resolve(); run.mkdir(parents=True, exist_ok=False)
        image = json.loads(subprocess.check_output(['docker', 'image', 'inspect', '--platform', 'linux/amd64', 'ros2-srt-m3:20261105'], text=True))[0]['RepoDigests'][0]
        report = dict(status='running', image=image, cases=[])
        try:
            for count in (1, 2):
                report['cases'].append(run_case(run/str(count), image, count))
            report['status'] = 'passed'
        except Exception as error:
            report.update(status='failed', error=str(error)); raise
        finally:
            write(run/'result.json', report)
