"""Container-owned M3 impairments. Never executes tc in the host namespace."""
from dataclasses import dataclass
import ipaddress
import json
from pathlib import Path
import secrets
import subprocess
import time

SEEDS = (1701, 2903, 4211)


@dataclass(frozen=True)
class Profile:
    name: str
    delay_ms: int = 0
    jitter_ms: int = 0
    loss_percent: int = 0
    rate_kbit: int = 0
    queue_packets: int = 256

    def commands(self, seed):
        if not 0 < seed < 2**32:
            raise ValueError('seed must fit a nonzero uint32')
        prefix = ['tc', 'qdisc', 'replace', 'dev', 'eth0', 'root', 'handle', '1:']
        if self.name == 'N0':
            return [prefix + ['netem', 'limit', str(self.queue_packets), 'seed', str(seed)]]
        if self.name == 'N3':
            raise ValueError('N3 requires deterministic SRT DATA/FEC selection; random netem is not N3')
        if self.rate_kbit:
            return [prefix + ['tbf', 'rate', str(self.rate_kbit)+'kbit', 'burst', '4096', 'limit', '32768'],
                    ['tc', 'qdisc', 'replace', 'dev', 'eth0', 'parent', '1:1', 'handle', '10:',
                     'netem', 'limit', str(self.queue_packets), 'seed', str(seed)]]
        netem = prefix + ['netem', 'limit', str(self.queue_packets)]
        if self.delay_ms:
            netem += ['delay', str(self.delay_ms)+'ms', str(self.jitter_ms)+'ms', 'distribution', 'normal']
        if self.loss_percent:
            netem += ['loss', 'random', str(self.loss_percent)+'%']
        return [netem + ['seed', str(seed)]]


PROFILES = {p.name: p for p in (Profile('N0'), Profile('N1', 20, 5, 1),
            Profile('N2', 60, 15, 3), Profile('N3'), Profile('N4', loss_percent=100),
            Profile('N5', rate_kbit=512, queue_packets=16))}


class NetworkLab:
    def __init__(self, root, run, image, *, monotonic_capture=False):
        self.root, self.run, self.image = Path(root), Path(run), image
        self.monotonic_capture=monotonic_capture
        self.name = 'ros2-srt-m3-' + secrets.token_hex(6)
        self.containers = {}
        self.addresses = {}
        self.commands = []
        self.events = []
        self.network_created = False

    def save(self):
        (self.run/'network.json').write_text(json.dumps(dict(network=self.name,
            containers=self.containers, addresses=self.addresses, commands=self.commands,
            events=self.events, isolation='internal Docker bridge; separate ROS domains; localhost DDS'), indent=2)+'\n')

    def execute(self, label, argv, check=True):
        item = dict(label=label, argv=argv, started_monotonic_ns=time.monotonic_ns())
        self.commands.append(item)
        self.save()
        result = subprocess.run(argv, cwd=self.root, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        item.update(exit_code=result.returncode, finished_monotonic_ns=time.monotonic_ns())
        (self.run/(label+'.log')).write_text(result.stdout+result.stderr)
        self.save()
        if check and result.returncode:
            raise RuntimeError(label+' failed: '+result.stderr.strip())
        return result.stdout

    def inside(self, role, label, argv):
        if role not in self.containers:
            raise ValueError('not an owned container')
        return self.execute(label, ['docker', 'exec', self.containers[role]]+argv)

    def start(self, credential):
        self.execute('network-create', ['docker', 'network', 'create', '--internal', self.name])
        self.network_created = True
        for role, domain in [('operator', 42), ('robot', 41)]:
            name = self.name+'-'+role
            self.containers[role] = name  # also clean up partially created containers
            self.execute(role+'-create', ['docker', 'run', '-d', '--pull=never', '--platform', 'linux/amd64',
                '--network', self.name, '--name', name, '--cap-add', 'NET_ADMIN']+
                (['--cap-add','BPF'] if self.monotonic_capture else [])+[
                '-e', 'ROS_DOMAIN_ID='+str(domain), '-e', 'ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST',
                '-e', 'RMW_IMPLEMENTATION=rmw_fastrtps_cpp', '-v', str(self.root)+':/workspace',
                '-v', str(credential)+':/run/bridge/passphrase:ro', '-w', '/workspace', self.image, 'sleep', 'infinity'])
            info = json.loads(self.execute(role+'-inspect', ['docker', 'inspect', name]))[0]
            address = info['NetworkSettings']['Networks'][self.name]['IPAddress']
            assert not ipaddress.ip_address(address).is_loopback
            assert not info['HostConfig']['Privileged'] and not info['HostConfig']['PortBindings']
            self.addresses[role] = address
            self.inside(role, role+'-environment', ['sh', '-c',
                'uname -a; tc -V; cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets; ip -j address show eth0'])
        self.save()

    def apply(self, profile, seed, roles=('operator', 'robot'), label='profile'):
        for role in roles:
            actual_seed = seed + (role == 'operator')
            for index, command in enumerate(PROFILES[profile].commands(actual_seed)):
                self.inside(role, label+'-'+role+'-'+str(index), command)
            state = json.loads(self.inside(role, label+'-'+role+'-readback', ['tc', '-j', '-s', 'qdisc', 'show', 'dev', 'eth0']))
            if profile in PROFILES:
                netem = next(q for q in state if q['kind'] == 'netem')
                if netem['options'].get('seed') != actual_seed:
                    raise RuntimeError('kernel did not retain the requested netem seed')
                assert netem['options']['limit'] == PROFILES[profile].queue_packets
                if profile=='N0':
                    assert netem['options'].get('loss-random',{}).get('loss',0)==0
                    assert netem['options'].get('delay',{}).get('delay',0)==0
            if profile == 'N5':
                tbf = next(q for q in state if q['kind'] == 'tbf')
                assert tbf['options']['rate'] == 64000  # tc JSON rates are bytes/s
            self.events.append(dict(role=role, profile=profile, seed=actual_seed,
                                    readback=state, monotonic_ns=time.monotonic_ns()))
            self.save()

    def snapshot(self, label):
        for role in self.containers:
            self.inside(role, label+'-'+role, ['tc', '-j', '-s', 'qdisc', 'show', 'dev', 'eth0'])
            self.inside(role, label+'-'+role+'-links', ['ip', '-j', '-s', 'link', 'show', 'dev', 'eth0'])

    def cleanup(self):
        for role, name in reversed(list(self.containers.items())):
            self.execute(role+'-remove', ['docker', 'rm', '-f', name], check=False)
        if self.network_created:
            self.execute('network-remove', ['docker', 'network', 'rm', self.name], check=False)
