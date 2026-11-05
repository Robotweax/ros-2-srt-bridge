"""Sensor-only DDS development baseline; never qualifies journaled commands."""
from m3_network import NetworkLab
import ipaddress
import json


class DdsLab(NetworkLab):
    def __init__(self,root,run,image,transport_profile='system'):
        super().__init__(root,run,image)
        if transport_profile not in ('system','udp1200'):raise ValueError('unsupported DDS transport profile')
        self.transport_profile=transport_profile

    def save(self):
        super().save()
        path=self.run/'network.json'
        data=json.loads(path.read_text())
        data['dds_transport_profile']=self.transport_profile
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
                (['-e','FASTRTPS_DEFAULT_PROFILES_FILE=/workspace/containers/dds-udp1200.xml'] if self.transport_profile=='udp1200' else [])+
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
