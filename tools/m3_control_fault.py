"""Development-only CONTROL egress fault, restricted to NetworkLab-owned peers."""
import ipaddress
import json

PREF = '49152'
# Record VM time around tc, never compare host monotonic epochs with VM clocks.
BRACKET = '''import json,subprocess,sys,time
argv=json.loads(sys.argv[1]);begin=time.monotonic_ns()
p=subprocess.run(argv,capture_output=True,text=True);end=time.monotonic_ns()
print(json.dumps(dict(begin_ns=begin,end_ns=end,argv=argv,exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr)))
sys.exit(p.returncode)
'''


def selector(role, peer):
    if role not in ('operator', 'robot'): raise ValueError('invalid fault role')
    address = ipaddress.ip_address(peer)
    if address.version != 4 or address.is_loopback or address.is_unspecified:
        raise ValueError('fault requires owned nonloopback IPv4 peer')
    return ['tc', 'filter', 'add', 'dev', 'eth0', 'egress', 'protocol', 'ip', 'pref', PREF,
            'u32', 'match', 'ip', 'protocol', '17', '0xff', 'match', 'ip', 'dst', str(address)+'/32',
            'match', 'ip', 'sport' if role == 'operator' else 'dport', '10080', '0xffff', 'action', 'drop']


def counters(filters):
    actions = [a for rule in filters for a in rule.get('options', {}).get('actions', [])]
    if len(actions) != 1 or actions[0].get('kind') != 'gact' or actions[0].get('control_action', {}).get('type') != 'drop':
        raise ValueError('ambiguous CONTROL drop action')
    # The preference-scoped tc query can omit pref in its JSON output.
    if any(rule.get('pref', int(PREF)) != int(PREF) or rule.get('kind') != 'u32' or rule.get('protocol') != 'ip' for rule in filters):
        raise ValueError('unexpected CONTROL filter')
    stats = actions[0]['stats']
    if any(type(stats.get(k)) is not int or stats[k] < 0 for k in ('packets', 'drops', 'bytes')):
        raise ValueError('invalid CONTROL action counters')
    if stats['packets'] != stats['drops']: raise ValueError('CONTROL action did not drop all matches')
    return {k: stats[k] for k in ('packets', 'drops', 'bytes')}


def bracket(lab, role, label, argv):
    result = json.loads(lab.inside(role, label, ['python3', '-c', BRACKET, json.dumps(argv)]))
    if result['exit_code'] or not 0 < result['begin_ns'] <= result['end_ns']:
        raise ValueError('invalid CONTROL tc execution bracket')
    return result


def readback(lab, role, label):
    return json.loads(lab.inside(role, label, ['tc', '-j', '-s', 'filter', 'show', 'dev', 'eth0', 'egress', 'pref', PREF]))


def start(lab, role):
    peer = 'robot' if role == 'operator' else 'operator'
    if role not in lab.containers or peer not in lab.containers: raise ValueError('fault requires owned endpoints')
    state = json.loads(lab.inside(role, 'control-fault-qdisc-before', ['tc', '-j', 'qdisc', 'show', 'dev', 'eth0']))
    if any(q['kind'] in ('clsact', 'ingress') for q in state): raise ValueError('refusing existing classifier hook')
    lab.inside(role, 'control-fault-hook', ['tc', 'qdisc', 'add', 'dev', 'eth0', 'clsact'])
    installed = bracket(lab, role, 'control-fault-install', selector(role, lab.addresses[peer]))
    try:
        state = readback(lab, role, 'control-fault-filter-installed')
        initial = counters(state)
    except Exception:
        # A validation failure must not leave the fault active until outer teardown.
        # The bracket/log remains evidence, including a failed removal.
        bracket(lab, role, 'control-fault-abort-remove', ['tc', 'filter', 'del', 'dev', 'eth0', 'egress', 'protocol', 'ip', 'pref', PREF])
        raise
    return dict(role=role, peer=peer, install=installed, initial_counters=initial, restored=False,
                scope='known CONTROL-only tc egress drop; owned IPv4 peers; SENSOR selector excluded; not historical cause or N4 phase qualification')


def stop(lab, fault):
    role = fault['role']
    try:
        state = readback(lab, role, 'control-fault-filter-final')
        fault['final_counters'] = counters(state)
    finally:
        # Even a bad statistics readback must not prolong the installed fault.
        fault['remove'] = bracket(lab, role, 'control-fault-remove', ['tc', 'filter', 'del', 'dev', 'eth0', 'egress', 'protocol', 'ip', 'pref', PREF])
        if readback(lab, role, 'control-fault-filter-restored'): raise ValueError('CONTROL filter still present')
        fault['restored'] = True
        fault['guaranteed_active_ns'] = [fault['install']['end_ns'], fault['remove']['begin_ns']]
    if fault['final_counters']['drops'] <= 0: raise ValueError('CONTROL fault matched no packets')
    return fault
