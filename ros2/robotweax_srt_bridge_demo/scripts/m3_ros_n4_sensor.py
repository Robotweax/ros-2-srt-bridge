#!/usr/bin/env python3
"""Fenced continuous ROS source across a host-coordinated N4 network cut."""
import argparse
import time
import traceback
import rclpy
from m3_ros_multiroute_scenario import Multiroute
from m3_scenario import Benchmark,write


class Freshness(Multiroute):
    def __init__(self,args):super().__init__(args);self.contexts=[]
    def bridge_state(self,m):
        Benchmark.bridge_state(self,m)
        self.contexts.append(dict(ns=time.monotonic_ns(),owner=bytes(m.owner_epoch).hex(),session=bytes(m.session_id).hex(),control_generation=m.control_generation,sensor_generation=m.sensor_generation,ready=m.ready,clock=m.clock_qualified))
        if len(self.contexts)>2000:raise RuntimeError('context observation budget')
    def measure(self):
        self.start_bridge()
        if self.args.role=='robot':
            self.sim=self.start('rate_simulator','robot-source',dict(publishing_enabled='false',source_diagnostics='true'))
            self.wait(lambda:self.device is not None,'source discovery');initial=self.fence(False)
            assert not initial['imu_published'] and not initial['joints_published']
        self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified,'qualified session',40)
        self.spin(.5);begin=self.stable_metrics()
        assert not begin['bridge']['samples_ingress'] and not begin['bridge']['samples_published']
        write(self.run/(self.args.role+'-fresh-ready.json'),begin)
        self.wait(lambda:(self.run/'armed').exists(),'armed')
        resume=pause=None
        if self.args.role=='robot':
            resume=self.fence(True);write(self.run/'load-started.json',resume)
            self.spin(15);pause=self.fence(False);write(self.run/'load-paused.json',pause)
        else:self.wait(lambda:(self.run/'load-paused.json').exists(),'source pause',30)
        self.spin(2);self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified,'restored qualification',20)
        end=self.stable_metrics();assert not self.bad,self.bad;assert not self.direct
        write(self.run/(self.args.role+'-fresh-result.json'),dict(begin=begin,end=end,resume=resume,pause=pause,rows=self.rows,contexts=self.contexts,bad=self.bad,direct=self.direct))
        self.wait(lambda:(self.run/'release').exists(),'collection',30)


def main():
    p=argparse.ArgumentParser();p.add_argument('--role',required=True,choices=('robot','operator'));p.add_argument('--run',required=True);p.add_argument('--peer',required=True);a=p.parse_args()
    a.clock_width_ms=200;a.sample_diagnostics=True;a.command_diagnostics=False;a.provider_diagnostics=False
    rclpy.init();d=Freshness(a)
    try:d.measure()
    except BaseException:write(d.run/(a.role+'-failure.json'),dict(traceback=traceback.format_exc()));raise
    finally:
        try:d.cleanup()
        finally:d.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
