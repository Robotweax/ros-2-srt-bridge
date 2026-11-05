#!/usr/bin/env python3
"""Direct Best Effort sensor baseline. File coordination carries controls only.

No command execution is substituted for the fully journaled command contract.
All participants run in the same Linux VM/time namespace; header age is a
realtime estimate, deliberately distinct from SRT's conservative clock bound.
"""
import argparse
import copy
import json
import math
from pathlib import Path
import signal
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


def empty_route():
    return dict(received=0,accepted=0,stale=0,invalid=0,clock_rejected=0,age_estimate_histogram_ms=[0]*251)


class DdsScenario(Node):
    def __init__(self,args):
        super().__init__('m3_dds_'+args.role)
        self.args=args;self.run=Path(args.run);self.process=None
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
            rclpy.spin_once(self,timeout_sec=min(.025,max(0,end-time.monotonic())))
            if self.process and self.process.poll() is not None:raise RuntimeError('simulator exited')

    def wait(self,predicate,label,seconds=45):
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
        self.process=subprocess.Popen(['/workspace/install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo/rate_simulator'],stdout=log,stderr=subprocess.STDOUT)
        try:
            write(self.run/'robot-ready.json',dict(ready=True))
            for phase,enabled in [('begin',False),('resume',True),('end',False)]:
                self.wait(lambda:(self.run/(phase+'-request.json')).exists(),phase+' request',self.args.seconds+90)
                write(self.run/(phase+'-source.json'),self.publishing(enabled))
            self.wait(lambda:(self.run/'finished.json').exists(),'observer finished')
        finally:
            self.process.send_signal(signal.SIGINT)
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
            self.process=None;log.close()

    def operator(self):
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
        begin=dict(device=read(self.run/'begin-source.json')['device'],observer=self.stable())
        self.window_begin=dict(imu=begin['device']['imu_published'],joints=begin['device']['joints_published'])
        write(self.run/'resume-request.json',{})
        self.wait(lambda:(self.run/'resume-source.json').exists(),'resume source fence')
        resumed=read(self.run/'resume-source.json')
        write(self.run/'measurement-start.json',dict(observer_monotonic_ns=time.monotonic_ns()))
        self.spin(self.args.seconds)
        write(self.run/'end-request.json',{})
        self.wait(lambda:(self.run/'end-source.json').exists(),'end source fence')
        paused=read(self.run/'end-source.json')
        end=dict(device=paused['device'],observer=self.stable())
        if self.boundary_errors:raise RuntimeError(str(self.boundary_errors))
        for route,key in [('imu','imu_published'),('joints','joints_published')]:
            if self.markers[route]>end['device'][key]:raise RuntimeError('callback after end source fence')
        write(self.run/'operator-result.json',dict(status='passed',sensor_only=True,commands_qualified=False,
            checkpoints=dict(begin=begin,end=end),publication_interval=dict(resume_monotonic_ns=resumed['monotonic_ns'],pause_monotonic_ns=paused['monotonic_ns']),
            sensor_count_checks_passed=True,age_estimates_qualified=self.clock.qualified,clock_steps=self.clock.steps,
            clock_max_offset_step_ns=self.clock.max_step_ns,clock_max_offset_deviation_ns=self.clock.max_deviation_ns,clock_max_bracket_width_ns=self.clock.max_width_ns,qos_checked=True,publisher_qos=discovered,
            age_scope='shared-VM realtime estimate, not conservative SRT clock-interval bound'))
        write(self.run/'finished.json',{})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role',choices=['robot','operator'],required=True)
    parser.add_argument('--run',required=True);parser.add_argument('--seconds',type=int,required=True)
    args=parser.parse_args();rclpy.init();driver=DdsScenario(args)
    try:getattr(driver,args.role)()
    except BaseException:
        write(driver.run/(args.role+'-failure.json'),dict(traceback=traceback.format_exc()));raise
    finally:driver.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
