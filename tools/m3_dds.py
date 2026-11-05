"""Sensor-only DDS development baseline; never qualifies journaled commands."""
from m3_network import NetworkLab
import ipaddress
import json
import hashlib
from pathlib import Path


DDS_PROFILES={'system':None,'udp1200':'containers/dds-udp1200.xml','paced-sensors':'containers/dds-paced-sensors.xml'}


def profile_environment(profile):
    if profile not in DDS_PROFILES:raise ValueError('unsupported DDS transport profile')
    result={}
    if DDS_PROFILES[profile]:result['FASTRTPS_DEFAULT_PROFILES_FILE']='/workspace/'+DDS_PROFILES[profile]
    if profile=='paced-sensors':result['RMW_FASTRTPS_USE_QOS_FROM_XML']='1'
    return result


def verify_profile(root,run,image,profile,execute,*,build_probe=False):
    """Isolated native provider preflight; never joins the measured lab network."""
    root=Path(root);run=Path(run);result=dict(dds_profile_environment=profile_environment(profile))
    if profile!='system':result['dds_transport_xml_sha256']=hashlib.sha256((root/DDS_PROFILES[profile]).read_bytes()).hexdigest()
    if profile!='paced-sensors':return result
    docker=['docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none']
    mount=['-v',str(root)+':/workspace','-w','/workspace',image,'bash','-c']
    if build_probe:
        execute('dds-profile-probe-build',docker+mount+[
            'set -e; source /opt/ros/jazzy/setup.bash; source install/m3-ros/setup.bash; '
            'cmake -S tools/dds_profile_probe -B build/m3-dds-profile-probe -G Ninja -DCMAKE_BUILD_TYPE=Release; '
            'cmake --build build/m3-dds-profile-probe --parallel 2'])
    probe=root/'build/m3-dds-profile-probe/dds_profile_probe'
    result['profile_probe_binary_sha256']=hashlib.sha256(probe.read_bytes()).hexdigest()
    execute('dds-profile-probe',docker+[arg for key,value in profile_environment(profile).items() for arg in ('-e',key+'='+value)]+
        ['-e','ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST','-e','RMW_IMPLEMENTATION=rmw_fastrtps_cpp']+mount+[
            'source /opt/ros/jazzy/setup.bash; source install/m3-ros/setup.bash; exec build/m3-dds-profile-probe/dds_profile_probe'])
    result['profile_probe']=json.loads((run/'dds-profile-probe.log').read_text())
    if result['profile_probe'].get('verified') is not True:raise RuntimeError('DDS profile probe did not verify settings')
    result['sensor_output_policy']='explicit asynchronous sensor-only shared 1600-byte/50ms controller; KeepLast(1); not an Ethernet rate guarantee'
    return result


def summarize_competitor(data):
    """Whole-run offered UDP load; not a matched-window delivery measurement."""
    setup=data['start']['test_start'];total=data['end']['sum']
    if setup.get('protocol')!='UDP' or setup.get('target_bitrate')!=128000 or setup.get('blksize')!=1024:
        raise ValueError('unexpected N5 competitor configuration')
    if data.get('error') not in (None,'interrupt - the client has terminated'):
        raise ValueError('N5 competitor error: '+str(data['error']))
    rate=total.get('bits_per_second',0)
    if not data.get('intervals') or total.get('bytes',0)<=0 or total.get('seconds',0)<=0 or not 115200<=rate<=140800:
        raise ValueError('N5 competitor offered load not established')
    return dict(protocol='UDP',target_bitrate=128000,block_bytes=1024,bytes=total['bytes'],seconds=total['seconds'],
        offered_bits_per_second=rate,scope='whole-run iperf client offered load; process liveness checked during scenario; not per-window delivery/loss')


class DdsLab(NetworkLab):
    def __init__(self,root,run,image,transport_profile='system'):
        super().__init__(root,run,image)
        if transport_profile not in DDS_PROFILES:raise ValueError('unsupported DDS transport profile')
        self.transport_profile=transport_profile

    def save(self):
        super().save()
        path=self.run/'network.json'
        data=json.loads(path.read_text())
        data['dds_transport_profile']=self.transport_profile
        data['dds_profile_environment']=profile_environment(self.transport_profile)
        data['isolation']='internal Docker bridge; shared ROS domain 60, explicit static peers; DDS over container eth0; no SRT processes'
        path.write_text(json.dumps(data,indent=2)+'\n')

    def start(self):
        self.execute('network-create',['docker','network','create','--internal',self.name])
        self.network_created=True
        for role in ('robot','operator'):
            name=self.name+'-'+role
            self.containers[role]=name
            self.execute(role+'-create',['docker','run','-d','--pull=never','--platform','linux/amd64',
                '--network',self.name,'--name',name,'--cap-add','NET_ADMIN',
                '-e','ROS_DOMAIN_ID=60','-e','ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET',
                '-e','RMW_IMPLEMENTATION=rmw_fastrtps_cpp']+
                [arg for key,value in profile_environment(self.transport_profile).items() for arg in ('-e',key+'='+value)]+
                ['-v',str(self.root)+':/workspace',
                '-w','/workspace',self.image,'sleep','infinity'])
            info=json.loads(self.execute(role+'-inspect',['docker','inspect',name]))[0]
            address=info['NetworkSettings']['Networks'][self.name]['IPAddress']
            assert not ipaddress.ip_address(address).is_loopback
            assert not info['HostConfig']['Privileged'] and not info['HostConfig']['PortBindings']
            self.addresses[role]=address
            self.inside(role,role+'-environment',['sh','-c',
                'uname -a; tc -V; cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets; ip -j address show eth0'])
        self.save()


def summarize_sensor_window(begin,end,enabled_interval):
    seconds=(enabled_interval['pause_monotonic_ns']-enabled_interval['resume_monotonic_ns'])/1e9
    if seconds<=0:raise ValueError('invalid enabled interval')
    result={}
    for route,key in [('imu','imu_published'),('joints','joints_published')]:
        produced=end['device'][key]-begin['device'][key]
        start=begin['observer'][route];stop=end['observer'][route]
        fields=('received','accepted','stale','invalid','clock_rejected')
        row={k:stop[k]-start[k] for k in fields}
        if produced<0 or any(n<0 for n in row.values()):raise ValueError('counter reset')
        missing=produced-row['received']
        if missing<0:raise ValueError('received more than fenced source population')
        if row['received']!=sum(row[k] for k in fields[1:]):raise ValueError('receiver accounting mismatch')
        row.update(produced=produced,missing_before_callback=missing,actual_source_hz=produced/seconds,
            total_not_accepted=produced-row['accepted'])
        bins=[b-a for a,b in zip(start['age_estimate_histogram_ms'],stop['age_estimate_histogram_ms'])]
        if len(start['age_estimate_histogram_ms'])!=251 or len(stop['age_estimate_histogram_ms'])!=251 or any(n<0 for n in bins) or sum(bins)!=row['accepted']:
            raise ValueError('histogram population mismatch')
        row['age_estimate_histogram_ms']=bins
        result[route]=row
    return dict(source_enabled_seconds=seconds,routes=result,
        scope='source-fenced direct DDS callback counts; missing_before_callback includes source middleware/kernel/network/receiver history; not physical WAN packet loss',
        age_scope='shared-VM ROS realtime timestamp estimate, rounded up to 1ms; not SRT conservative clock-interval age')
