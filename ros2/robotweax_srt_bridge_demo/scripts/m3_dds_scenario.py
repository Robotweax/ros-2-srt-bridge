#!/usr/bin/env python3
"""Direct Best Effort sensor baseline. File coordination carries controls only.

Optional --commands adds the journaled Reliable DDS coordinator and steady load.
All participants run in the same Linux VM/time namespace; header age is a
realtime estimate, deliberately distinct from SRT's conservative clock bound.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import subprocess
import time
import traceback

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Imu, JointState
from robotweax_srt_bridge_msgs.srv import SetPublishing
from rosidl_runtime_py.convert import message_to_ordereddict
from m2_scenario import write, read
from dds_clock import clock_sample, ClockMonitor
from endpoint_measurement import EndpointSampler
import os
from scenario_timeline import Timeline
from scenario_processes import stop_children


def empty_route():
    return dict(received=0,accepted=0,stale=0,invalid=0,clock_rejected=0,age_estimate_histogram_ms=[0]*251)


class DdsScenario(Node):
    def __init__(self,args):
        super().__init__('m3_dds_'+args.role)
        self.args=args;self.run=Path(args.run);self.process=None
        self.endpoint_sampler=EndpointSampler(self.run/(args.role+'-endpoint-samples.jsonl'))
        self.counts={name:empty_route() for name in ('imu','joints')}
        self.markers=dict(imu=0,joints=0);self.boundary_errors=[];self.window_begin=None
        self.qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,history=HistoryPolicy.KEEP_LAST)
        self.client=self.create_client(SetPublishing,'/robot/set_publishing') if args.role=='robot' else None
        self.subs=[]
        if args.role=='operator':
            self.subs=[self.create_subscription(Imu,'/robot/imu',lambda m:self.sample('imu',m),self.qos),
                       self.create_subscription(JointState,'/robot/joint_states',lambda m:self.sample('joints',m),self.qos)]
        samples=[clock_sample() for _ in range(8)]
        self.clock_reference=min((interval for _,interval in samples),key=lambda x:x[1]-x[0])
        if self.clock_reference[1]-self.clock_reference[0]>1000000:raise RuntimeError('cannot establish clock reference')
        self.clock=ClockMonitor(self.clock_reference)
        self.phase="initializing"
        self.timeline=Timeline(self.run/(args.role+"-startup-timeline.jsonl"))
        self.load=None
        if args.commands:
            from dds_command_load import DdsCommandLoad
            self.load=DdsCommandLoad(self)

    def sample(self,route,m):
        row=self.counts[route];row['received']+=1
        wall,interval=clock_sample()
        clock_ok=self.clock.observe(wall,interval)
        valid=True
        if route=='imu':
            marker=int(m.angular_velocity.z)
            valid=(m.header.frame_id=='demo_imu' and m.orientation.w==1. and m.linear_acceleration.z==9.81 and m.angular_velocity.x==200.)
        else:
            marker=round(m.position[0]*1000) if m.position else 0
            valid=(m.header.frame_id=='demo_base' and m.name==['joint_'+str(i+1) for i in range(6)] and
                len(m.position)==len(m.velocity)==len(m.effort)==6 and all(v==200. for v in m.velocity) and
                all(abs((m.position[i]-m.position[0])-i)<1e-10 for i in range(6)))
        if marker<=self.markers[route]:valid=False
        self.markers[route]=max(marker,self.markers[route])
        if self.window_begin and marker<=self.window_begin[route] and len(self.boundary_errors)<16:
            self.boundary_errors.append('sample from before begin fence: '+route)
        if not valid:row['invalid']+=1;return
        age=wall-(m.header.stamp.sec*1000000000+m.header.stamp.nanosec)
        if age<0 or not clock_ok:row['clock_rejected']+=1;return
        if age>250000000:row['stale']+=1;return
        row['accepted']+=1;row['age_estimate_histogram_ms'][math.ceil(age/1000000)]+=1

    def spin(self,seconds=.05):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            peer="robot" if self.args.role=="operator" else "operator"
            if (self.run/"abort").exists() or (self.run/(peer+"-failure.json")).exists():raise RuntimeError("scenario aborted; inspect peer/parent failure")
            if self.load:self.load.tick()
            rclpy.spin_once(self,timeout_sec=min(.025,max(0,end-time.monotonic())))
            if self.process and self.process.poll() is not None:raise RuntimeError('simulator exited')
            if self.load:self.load.check()
            roots=[('observer',os.getpid())]
            if self.process is not None and self.process.poll() is None:roots.append(('source',self.process.pid))
            if self.load and self.load.process and self.load.process.poll() is None:roots.append(('control',self.load.process.pid))
            self.endpoint_sampler.tick(roots)
            self.timeline.observe(self.phase,self.load.snapshot() if self.load and self.load.state else None,{r:c["received"] for r,c in self.counts.items()})

    def wait(self,predicate,label,seconds=45):
        self.phase=label
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            if predicate():return
            self.spin()
        raise RuntimeError('timeout: '+label)

    def publishing(self,enabled):
        self.wait(lambda:self.client.service_is_ready(),'local publishing service')
        future=self.client.call_async(SetPublishing.Request(enabled=enabled))
        self.wait(future.done,'source publication fence')
        response=future.result()
        if response.enabled!=enabled:raise RuntimeError('publication state mismatch')
        return dict(device=message_to_ordereddict(response.snapshot),monotonic_ns=response.monotonic_ns)

    def stable(self):
        # Best Effort has no application replay/FEC. Allow more than the 250ms
        # age budget plus profile delay; reject any pre-fence callback thereafter.
        self.spin(2)
        end=time.monotonic()+8
        while time.monotonic()<end:
            before=copy.deepcopy(self.counts);self.spin(.3)
            if before==self.counts:return copy.deepcopy(self.counts)
        raise RuntimeError('receiver did not quiesce')

    def robot(self):
        log=(self.run/'simulator.log').open('w')
        argv=['/workspace/install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo/rate_simulator']
        if self.load and self.args.startup=='control-first':argv+=['--ros-args','-p','publishing_enabled:=false']
        self.process=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT)
        try:
            if self.load:self.load.launch()
            if self.args.discovery_fragment_cut:self.wait(lambda:(self.run/'discovery-restored.json').exists(),'controlled discovery restoration',90)
            if self.load and self.args.startup=='control-first':
                self.wait(self.load.ready,'control-first receiver ready')
                paused=self.publishing(False)
                if paused['device']['imu_published'] or paused['device']['joints_published']:raise RuntimeError('control-first source published before readiness')
                paused['command_state']=self.load.snapshot()
                write(self.run/'control-ready.json',paused)
                self.wait(lambda:(self.run/'warmup-request.json').exists(),'warmup request')
                write(self.run/'warmup-source.json',self.publishing(True))
            write(self.run/'robot-ready.json',dict(ready=True))
            for phase,enabled in [('begin',False),('resume',True),('end',False)]:
                self.wait(lambda:(self.run/(phase+'-request.json')).exists(),phase+' request',self.args.seconds+90)
                if self.load and phase=='begin':self.wait(self.load.ready,'journaled DDS receiver ready')
                response=self.publishing(enabled)
                if self.load:response['command_state']=self.load.snapshot()
                write(self.run/(phase+'-source.json'),response)
            if self.load:
                self.wait(lambda:(self.run/'final-request.json').exists(),'final device snapshot')
                response=self.publishing(False);self.spin(.25)
                response['command_state']=self.load.snapshot()
                write(self.run/'final-source.json',response)
            self.wait(lambda:(self.run/'finished.json').exists(),'observer finished')
        finally:
            report=stop_children([(self.process,'simulator',log)])
            write(self.run/'robot-simulator-shutdown.json',report)
            self.process=None
            if not report['passed']:raise RuntimeError('simulator child shutdown failed')

    def operator(self):
        if self.load:
            self.load.launch()
            if self.args.discovery_fragment_cut:self.wait(lambda:(self.run/'discovery-restored.json').exists(),'controlled discovery restoration',90)
            self.wait(self.load.ready,'journaled DDS sender ready')
            if self.args.startup=='control-first':
                self.wait(lambda:(self.run/'control-ready.json').exists(),'control-first source ready')
                write(self.run/'warmup-request.json',{})
        self.wait(lambda:all(self.counts[r]['received']>20 for r in self.counts),'typed DDS stream')
        for sub in self.subs:
            q=sub.qos_profile
            if q.reliability!=ReliabilityPolicy.BEST_EFFORT or q.depth!=1 or q.durability!=DurabilityPolicy.VOLATILE:
                raise RuntimeError('sensor subscription QoS mismatch')
        discovered={}
        for topic in ('/robot/imu','/robot/joint_states'):
            endpoints=self.get_publishers_info_by_topic(topic)
            if len(endpoints)!=1 or any(e.qos_profile.reliability!=ReliabilityPolicy.BEST_EFFORT or e.qos_profile.durability!=DurabilityPolicy.VOLATILE for e in endpoints):
                raise RuntimeError('discovered publisher QoS mismatch: '+topic)
            discovered[topic]=[str(e.qos_profile) for e in endpoints]
        write(self.run/'begin-request.json',{})
        self.wait(lambda:(self.run/'begin-source.json').exists(),'begin source fence')
        begin_source=read(self.run/'begin-source.json')
        begin=dict(device=begin_source['device'],observer=self.stable())
        if self.load:
            begin['command_sender']=self.load.snapshot();begin['command_receiver']=begin_source['command_state']
            if begin['device']['effects'] or begin['device']['generation'] or begin['command_sender']['commands_sent'] or begin['command_receiver']['start_claims']:raise RuntimeError('command history before measurement window')
        self.window_begin=dict(imu=begin['device']['imu_published'],joints=begin['device']['joints_published'])
        fenced_start=time.monotonic_ns()
        write(self.run/'resume-request.json',{})
        self.wait(lambda:(self.run/'resume-source.json').exists(),'resume source fence')
        resumed=read(self.run/'resume-source.json')
        write(self.run/'measurement-start.json',dict(observer_monotonic_ns=time.monotonic_ns()))
        if self.load:self.load.begin(begin['device']['generation'])
        self.phase="measurement"
        self.spin(self.args.seconds)
        if self.load:self.load.cutoff()
        write(self.run/'end-request.json',{})
        self.wait(lambda:(self.run/'end-source.json').exists(),'end source fence')
        paused=read(self.run/'end-source.json')
        command_report={}
        if self.load:
            from command_workload import audit_commands
            drain_deadline=self.load.cutoff_ns/1e9+8
            while self.load.pending and time.monotonic()<drain_deadline:self.spin(.05)
            self.load.freeze()
            write(self.run/'final-request.json',{})
            self.wait(lambda:(self.run/'final-source.json').exists(),'final device snapshot')
            final_source=read(self.run/'final-source.json')
            if any(final_source['device'][key]!=paused['device'][key] for key in ('imu_published','joints_published')):raise RuntimeError('publication changed after source fence')
            self.spin(.25)
            end_sender=self.load.snapshot();end_receiver=final_source['command_state']
            for role,last in [('command_sender',end_sender),('command_receiver',end_receiver)]:
                if begin[role]['process_epoch']!=last['process_epoch']:raise RuntimeError('command owner restarted during measurement')
            command_report=dict(commands=self.load.rows,command_audit=audit_commands(self.load.rows,begin['device'],final_source['device'],cutoff_ns=self.load.cutoff_ns),
                command_data_cutoff_monotonic_ns=self.load.cutoff_ns,command_result_drain_limit_s=8,skipped_command_slots=self.load.cadence.skipped,
                commands_paused_after_unknown=self.load.paused,unresolved_command=self.load.pending,
                final_device=final_source['device'],final_command_sender=end_sender,final_command_receiver=end_receiver,
                command_scope='absolute 200Hz intents every 2s; one pending intent; UNKNOWN pauses new work; result latency includes bounded drain')
        end=dict(device=paused['device'],observer=self.stable())
        if self.boundary_errors:raise RuntimeError(str(self.boundary_errors))
        for route,key in [('imu','imu_published'),('joints','joints_published')]:
            if self.markers[route]>end['device'][key]:raise RuntimeError('callback after end source fence')
        fenced_end=time.monotonic_ns();self.spin(.35)
        write(self.run/'operator-result.json',dict(endpoint_fenced_interval_ns=[fenced_start,fenced_end],status='passed',sensor_only=not bool(self.load),commands_qualified=False,**command_report,
            checkpoints=dict(begin=begin,end=end),publication_interval=dict(resume_monotonic_ns=resumed['monotonic_ns'],pause_monotonic_ns=paused['monotonic_ns']),
            sensor_count_checks_passed=True,age_estimates_qualified=self.clock.qualified,clock_steps=self.clock.steps,
            clock_max_offset_step_ns=self.clock.max_step_ns,clock_max_offset_deviation_ns=self.clock.max_deviation_ns,clock_max_bracket_width_ns=self.clock.max_width_ns,qos_checked=True,publisher_qos=discovered,
            age_scope='shared-VM realtime estimate, not conservative SRT clock-interval bound'))
        write(self.run/'finished.json',{})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role',choices=['robot','operator'],required=True)
    parser.add_argument('--run',required=True);parser.add_argument('--seconds',type=int,required=True)
    parser.add_argument('--startup',choices=['simultaneous','control-first'],default='simultaneous')
    parser.add_argument('--commands',action='store_true',help='journaled Reliable DDS commands every two seconds')
    parser.add_argument('--discovery-fragment-cut',action='store_true')
    args=parser.parse_args()
    if args.discovery_fragment_cut and (not args.commands or args.startup!='control-first'):parser.error('discovery cut requires journaled control-first fixture')
    if not 10<=args.seconds<=7200:parser.error('duration must be 10..7200 seconds')
    rclpy.init();driver=DdsScenario(args)
    try:getattr(driver,args.role)()
    except BaseException:
        write(driver.run/(args.role+'-failure.json'),dict(traceback=traceback.format_exc(),
            command_state=driver.load.snapshot() if driver.load and driver.load.state else None));raise
    finally:
        try:
            if driver.load:driver.load.stop()
        finally:driver.timeline.close();driver.endpoint_sampler.close();driver.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
