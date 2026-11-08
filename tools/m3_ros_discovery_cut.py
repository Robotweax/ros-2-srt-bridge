"""Opt-in ROS discovery-only continuation-fragment cut before workload admission."""
import json
import time
from m3_dds_discovery_loss import selector,counters,PREF
from m3_control_fault import bracket
from m3_source_preflight import write

FIELDS=('control_publishers','control_subscribers','hello_publishers','hello_subscribers')


def full(state):return state['ready'] and all(state[k]>0 for k in FIELDS) and not state['failed']


def blocked(states):
    if any(s['failed'] or not all(s[k] for k in ('journal_ready','handler_ready','qos_verified')) for s in states.values()):raise ValueError('ROS local owner not eligible')
    if all(states['operator'][k]>0 for k in FIELDS):raise ValueError('fragment cut did not withhold operator endpoint discovery')
    if any(s['commands_sent'] or s['start_claims'] or s['effects'] for s in states.values()):raise ValueError('work admitted during discovery-only barrier')
    if any(s['hellos_sent']<30 for s in states.values()):raise ValueError('HELLO producer not established')


def recovered(initial,states):
    if not all(full(s) for s in states.values()):raise ValueError('ROS discovery/session not recovered')
    if any(initial[r]['process_epoch']!=s['process_epoch'] for r,s in states.items()):raise ValueError('coordinator owner restarted')
    if any(s['commands_sent'] or s['start_claims'] or s['effects'] for s in states.values()):raise ValueError('work admitted before restored qualification')
    if any(s['hellos_received']<3 for s in states.values()):raise ValueError('no restored HELLO callback progress')


class DiscoveryCut:
    def __init__(self,lab,run):
        self.lab=lab;self.run=run;self.live=False;self.started=time.monotonic();self.removed_at=None
        self.report=dict(status='installed',restored=False,scope='ROS N0 control-first discovery-only continuation cut; not loaded N5 mitigation or original cause proof')
        qs=json.loads(lab.inside('robot','discovery-qdisc-before',['tc','-j','qdisc','show','dev','eth0']))
        if any(q['kind'] in ('clsact','ingress') for q in qs):raise ValueError('existing classifier hook refused')
        lab.inside('robot','discovery-hook',['tc','qdisc','add','dev','eth0','clsact']);self.live=True
        try:
            self.report['install']=bracket(lab,'robot','discovery-install',selector(lab.addresses['robot'],lab.addresses['operator']))
            self.report['initial_counters']=counters(self.readback('discovery-initial'))
            if self.report['initial_counters'][0]['packets']:raise ValueError('nonzero initial discovery counters')
        except Exception:
            self.close();raise
        self.save()

    def save(self):write(self.run/'controlled-discovery.json',self.report)
    def readback(self,label):return json.loads(self.lab.inside('robot',label,['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF]))
    def states(self):
        paths={r:self.run/(r+'-command-state.json') for r in ('operator','robot')}
        return {r:json.loads(p.read_text()) for r,p in paths.items()} if all(p.exists() for p in paths.values()) else None

    def tick(self):
        if self.report['status']=='recovered':return
        s=self.states()
        if not s:return
        if any(x['failed'] for x in s.values()):raise ValueError('coordinator failed during discovery diagnostic')
        if self.live and all(all(x[k] for k in ('journal_ready','handler_ready','qos_verified')) for x in s.values()):
            self.report['initial']=s;self.report['hold']=json.loads(self.lab.inside('robot','discovery-hold',['python3','-c','import time,json;b=time.monotonic_ns();time.sleep(8);print(json.dumps(dict(begin_ns=b,end_ns=time.monotonic_ns())))']))
            self.report['blocked']=self.states();self.report['drops']=counters(self.readback('discovery-final'))
            self.close();self.removed_at=time.monotonic();self.report['status']='awaiting_recovery';self.save()
            if self.report['hold']['end_ns']-self.report['hold']['begin_ns']<8_000_000_000 or self.report['drops'][0]['drops']<1:raise ValueError('controlled loss not established')
            blocked(self.report['blocked'])
        elif not self.live and self.removed_at is not None:
            if time.monotonic()-self.removed_at>45:raise ValueError('ROS restored discovery deadline exceeded')
            if all(full(x) and x['hellos_received']>=3 for x in s.values()):
                recovered(self.report['initial'],s);self.report['recovered']=s;self.report['checkpoint']=bracket(self.lab,'robot','discovery-recovered-checkpoint',['true']);self.report['status']='recovered';self.save()
                write(self.run/'discovery-restored.json',dict(qualified=True,checkpoint=self.report['checkpoint']))

    def close(self):
        if self.live:
            self.report['remove']=bracket(self.lab,'robot','discovery-remove',['tc','qdisc','del','dev','eth0','clsact']);self.live=False
            if self.readback('discovery-restored-selector'):raise ValueError('discovery selector remains')
            self.report['restored']=True;self.save()
