"""Explicit N3 source identities; no inference of FEC origin from observed DATA.

Only fixed-IHL, unfragmented IPv4 is supported. A caller must supply the actual
sender initial sequence and nonzero source message numbers before traffic starts.
This helper does not enable N3 in run_m3 or claim authenticated FEC recovery.
"""
from dataclasses import dataclass
import ipaddress
import json
from m3_control_fault import bracket

PREF = '49149'
MASK = 0x7fffffff


@dataclass(frozen=True)
class Selection:
    initial_sequence: int
    row: int
    positions: tuple
    message_numbers: tuple
    socket_id: int
    source_port: int = 10081
    destination_port: int = 39781

    def __post_init__(self):
        def integer(value, lo, hi):
            return type(value) is int and lo <= value <= hi
        if not integer(self.initial_sequence, 0, MASK) or not integer(self.row, 0, (1 << 28)-1):
            raise ValueError('row must be within the unambiguous first half sequence space')
        if type(self.positions) is not tuple or len(self.positions) not in (1, 2) or any(not integer(p, 0, 3) for p in self.positions) or len(set(self.positions)) != len(self.positions):
            raise ValueError('select one or two distinct positions in one four-source row')
        if type(self.message_numbers) is not tuple or len(self.message_numbers) != len(self.positions) or any(not integer(m, 1, 0x03ffffff) for m in self.message_numbers):
            raise ValueError('explicit nonzero source message numbers required; parity is excluded')
        if not integer(self.socket_id, 1, 0xffffffff):
            raise ValueError('destination socket identity required')
        if any(not integer(p, 1, 65535) for p in (self.source_port, self.destination_port)) or 10081 not in (self.source_port, self.destination_port) or 10080 in (self.source_port, self.destination_port):
            raise ValueError('SENSOR-only UDP tuple required')

    def targets(self):
        return [dict(position=p, sequence=(self.initial_sequence+4*self.row+p)&MASK, message_number=m)
                for p, m in zip(self.positions, self.message_numbers)]


def commands(selection, source, destination):
    addresses = [ipaddress.ip_address(a) for a in (source, destination)]
    if any(a.version != 4 or a.is_loopback or a.is_unspecified or a.is_multicast for a in addresses) or addresses[0] == addresses[1]:
        raise ValueError('distinct owned IPv4 peers required')
    result = []
    for target in selection.targets():
        # Offsets are from the IPv4 header. Exact IHL=5 and no MF/offset guard
        # make UDP/SRT offsets explicit. Full sequence mask also excludes control.
        argv = ['tc', 'filter', 'add', 'dev', 'eth0', 'egress', 'protocol', 'ip', 'pref', PREF, 'u32',
                'match', 'u8', '0x45', '0xff', 'at', '0',
                'match', 'ip', 'protocol', '17', '0xff',
                'match', 'u16', '0', '0x3fff', 'at', '6',
                'match', 'ip', 'src', str(addresses[0])+'/32',
                'match', 'ip', 'dst', str(addresses[1])+'/32',
                'match', 'ip', 'sport', str(selection.source_port), '0xffff',
                'match', 'ip', 'dport', str(selection.destination_port), '0xffff']
        for value, mask, offset in ((target['sequence'], 0xffffffff, 28),
                                    (target['message_number'], 0x03ffffff, 32),
                                    (selection.socket_id, 0xffffffff, 40)):
            argv += ['match', 'u32', hex(value), hex(mask), 'at', str(offset)]
        result.append(argv+['action', 'drop'])
    return result


def readback(lab, label):
    return json.loads(lab.inside('robot', label, ['tc', '-j', '-s', 'filter', 'show', 'dev', 'eth0', 'egress', 'pref', PREF]))


def counters(rules, expected):
    actions = [a for r in rules for a in r.get('options', {}).get('actions', [])]
    if len(actions) != expected or any(r.get('kind') != 'u32' or r.get('protocol') != 'ip' or r.get('pref', int(PREF)) != int(PREF) for r in rules):
        raise ValueError('unexpected SENSOR selector readback')
    values = []
    for action in actions:
        stats = action.get('stats', {})
        if action.get('kind') != 'gact' or action.get('control_action', {}).get('type') != 'drop' or any(type(stats.get(k)) is not int or stats[k] < 0 for k in ('packets', 'drops', 'bytes')) or stats['packets'] != stats['drops']:
            raise ValueError('invalid SENSOR drop counters')
        values.append({k: stats[k] for k in ('packets', 'drops', 'bytes')})
    return values


def install(lab, selection):
    if set(lab.containers) != {'robot', 'operator'}:
        raise ValueError('owned lab endpoints required')
    argv = commands(selection, lab.addresses['robot'], lab.addresses['operator'])
    state = json.loads(lab.inside('robot', 'sensor-fault-qdisc-before', ['tc', '-j', 'qdisc', 'show', 'dev', 'eth0']))
    if any(q['kind'] in ('clsact', 'ingress') for q in state):
        raise ValueError('refusing existing classifier hook')
    lab.inside('robot', 'sensor-fault-hook', ['tc', 'qdisc', 'add', 'dev', 'eth0', 'clsact'])
    fault = dict(targets=selection.targets(), install=[] , restored=False)
    try:
        for i, command in enumerate(argv):
            fault['install'].append(bracket(lab, 'robot', 'sensor-fault-install-'+str(i), command))
        fault['initial_counters'] = counters(readback(lab, 'sensor-fault-installed'), len(argv))
    except Exception:
        remove(lab, fault)
        raise
    return fault


def remove(lab, fault):
    # Only the hook created by install is removed; pre-existing hooks are refused.
    fault['remove'] = bracket(lab, 'robot', 'sensor-fault-remove', ['tc', 'qdisc', 'del', 'dev', 'eth0', 'clsact'])
    if readback(lab, 'sensor-fault-restored'):
        raise ValueError('SENSOR selector remains installed')
    fault['restored'] = True
