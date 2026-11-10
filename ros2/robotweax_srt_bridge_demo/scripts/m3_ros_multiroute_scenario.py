#!/usr/bin/env python3
"""Sustained N0 IMU/joints accounting preflight; files coordinate, never relay samples."""
import argparse
import time
import traceback
import rclpy
from robotweax_srt_bridge_msgs.srv import SetPublishing
from m3_ros_sensor_scenario import Finite
from m3_scenario import Benchmark, write
from source_payload import fingerprint
from scenario_processes import stop_children


class Multiroute(Finite):
    def cleanup(self):
        report=stop_children(self.processes,observer_directory=self.run if getattr(self.args,'shutdown_stacks',False) else None,stack_mode=getattr(self.args,'shutdown_stack_mode','procfs'))
        if getattr(self.args,'shutdown_stacks',False):
            report['stack_observer_controls_complete']=all(c.get('stack_observer',{}).get('complete',False) for c in report['children'])
            report['passed']=report['passed'] and report['stack_observer_controls_complete']
        try:
            self.resources.close();self.endpoint_sampler.close()
        except Exception as error:
            report.update(passed=False,observer_cleanup_error=str(error))
        write(self.run/(self.args.role+'-child-shutdown.json'),report)
        if not report['passed']:raise RuntimeError('abnormal child shutdown; see '+self.args.role+'-child-shutdown.json')

    def received(self,route,m):
        counter=round(m.angular_velocity.z) if route==1 else round(m.position[0]*1000)
        self.rows.append(dict(route=route,counter=counter,stamp_sec=m.header.stamp.sec,stamp_nanosec=m.header.stamp.nanosec,payload_sha256=fingerprint(m,route),observed_ns=time.monotonic_ns()))

    def imu(self,m):
        Benchmark.imu(self,m);self.received(1,m)

    def joints(self,m):
        Benchmark.joints(self,m);self.received(2,m)

    def fence(self,enabled):
        r=self.rpc(self.publishing_client,SetPublishing.Request(enabled=enabled))
        s=r.snapshot
        return dict(enabled=r.enabled,monotonic_ns=r.monotonic_ns,imu_published=s.imu_published,joints_published=s.joints_published,rate_hz=s.rate_hz,generation=s.generation,effects=s.effects)

    def measure(self):
        self.start_bridge()
        if self.args.role=='robot':
            self.sim=self.start('rate_simulator','robot-source',dict(publishing_enabled='false',source_diagnostics='true'))
            self.wait(lambda:self.device is not None,'disabled source discovery')
            initial=self.fence(False)
            assert not initial['imu_published'] and not initial['joints_published']
        self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified,'qualified multiroute session',40)
        if self.args.role=='robot':
            self.wait(lambda:self.imu_pub.get_subscription_count()>=2 and self.joint_pub.get_subscription_count()>=1,'both local bridge route subscriptions')
        self.spin(.5);begin=self.stable_metrics()
        assert begin['bridge']['samples_ingress']==begin['bridge']['samples_published']==begin['bridge']['sensor_sent']==0
        write(self.run/(self.args.role+'-multiroute-ready.json'),begin)
        self.wait(lambda:(self.run/'armed').exists(),'host armed',30)
        self.armed_session=bytes(self.state.session_id)
        assert list(self.armed_session)==begin['bridge']['session_id']
        resume=pause=None
        if self.args.role=='robot':
            resume=self.fence(True);self.spin(self.args.seconds);pause=self.fence(False)
            write(self.run/'multiroute-sent.json',dict(resume=resume,pause=pause))
        else:self.wait(lambda:(self.run/'multiroute-sent.json').exists(),'source pause',self.args.seconds+10)
        self.spin(2);end=self.stable_metrics()
        assert not self.bad,self.bad
        assert not self.direct
        assert end['bridge']['session_id']==begin['bridge']['session_id'] and end['bridge']['ready'] and end['bridge']['clock_qualified']
        write(self.run/(self.args.role+'-multiroute-result.json'),dict(status='passed',begin=begin,end=end,rows=self.rows,resume=resume,pause=pause,bad=self.bad,direct=self.direct,nominal_seconds=self.args.seconds))
        self.wait(lambda:(self.run/'release').exists(),'host collection',30)


def main():
    p=argparse.ArgumentParser();p.add_argument('--role',choices=('robot','operator'),required=True);p.add_argument('--run',required=True);p.add_argument('--peer',required=True);p.add_argument('--seconds',type=int,choices=(10,30),default=10);p.add_argument('--shutdown-diagnostics',action='store_true');p.add_argument('--shutdown-stacks',action='store_true');p.add_argument('--shutdown-stack-mode',choices=('procfs','gdb'),default='procfs');p.add_argument('--ros-install',choices=('install/m3-ros','install/m3-start-trace-ros','install/m3-sender-visibility-ros','install/m3-probe-tracing-ros','install/m3-sender-reconcile-ros','install/m3-shutdown-trace-calibration-ros','install/m3-socket-disposition-ros'),default='install/m3-ros');a=p.parse_args()
    if a.shutdown_stack_mode!='procfs' and not a.shutdown_stacks:p.error('GDB requires explicit shutdown stack observer')
    a.clock_width_ms=200;a.provider_diagnostics=False;a.command_diagnostics=False;a.sample_diagnostics=True
    rclpy.init();driver=Multiroute(a)
    try:driver.measure()
    except BaseException:
        write(driver.run/(a.role+'-multiroute-failure.json'),dict(traceback=traceback.format_exc()));raise
    finally:
        try:driver.cleanup()
        finally:driver.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
