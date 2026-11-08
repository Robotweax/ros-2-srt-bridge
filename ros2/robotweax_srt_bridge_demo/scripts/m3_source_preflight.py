#!/usr/bin/env python3
"""One disabled/resume/pause source window, local typed observer, no bridge."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_prefix
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu, JointState
from robotweax_srt_bridge_msgs.srv import SetPublishing
from source_payload import fingerprint


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--seconds',type=int,choices=(10,),default=10);a=p.parse_args()
    out=Path(a.output);out.mkdir(parents=True,exist_ok=False)
    rclpy.init();node=Node('source_preflight_observer');observed=[]
    def sample(route,m):
        counter=round(m.angular_velocity.z) if route==1 else round(m.position[0]*1000)
        observed.append(dict(route=route,counter=counter,stamp_sec=m.header.stamp.sec,stamp_nanosec=m.header.stamp.nanosec,payload_sha256=fingerprint(m,route)))
    subscriptions=[node.create_subscription(Imu,'/robot/imu',lambda m:sample(1,m),qos_profile_sensor_data),node.create_subscription(JointState,'/robot/joint_states',lambda m:sample(2,m),qos_profile_sensor_data)]
    client=node.create_client(SetPublishing,'/robot/set_publishing')
    def spin_until(predicate,seconds):
        deadline=time.monotonic()+seconds
        while not predicate():
            if time.monotonic()>=deadline:raise TimeoutError('source preflight timeout')
            rclpy.spin_once(node,timeout_sec=.01)
    def fence(enabled):
        q=SetPublishing.Request();q.enabled=enabled;f=client.call_async(q);spin_until(f.done,15);r=f.result()
        return dict(enabled=r.enabled,monotonic_ns=r.monotonic_ns,imu_published=r.snapshot.imu_published,joints_published=r.snapshot.joints_published,rate_hz=r.snapshot.rate_hz,generation=r.snapshot.generation,effects=r.snapshot.effects)
    child=None
    try:
        with (out/'source.log').open('w') as log:
            child=subprocess.Popen([str(Path(get_package_prefix('robotweax_srt_bridge_demo'))/'lib/robotweax_srt_bridge_demo/rate_simulator'),'--ros-args','-p','publishing_enabled:=false','-p','source_diagnostics:=true'],stdout=log,stderr=subprocess.STDOUT)
            if not client.wait_for_service(timeout_sec=15):raise TimeoutError('source service unavailable')
            spin_until(lambda: all(node.count_publishers(topic)==1 for topic in ('/robot/imu','/robot/joint_states')),15)
            # Discovery while source is disabled; no measurement data discarded.
            until=time.monotonic()+2
            spin_until(lambda:time.monotonic()>=until,3)
            initial=fence(False)
            if initial['imu_published'] or initial['joints_published'] or observed:raise ValueError('nonempty initial source')
            resume=fence(True);until=time.monotonic()+a.seconds
            spin_until(lambda:time.monotonic()>=until,a.seconds+2)
            pause=fence(False);until=time.monotonic()+2
            spin_until(lambda:time.monotonic()>=until,3)
            (out/'observer.json').write_text(json.dumps(dict(initial=initial,resume=resume,pause=pause,observed=observed),indent=2)+'\n')
    finally:
        if child:
            child.terminate()
            try:child.wait(timeout=10)
            except subprocess.TimeoutExpired:child.kill();child.wait()
        node.destroy_node();rclpy.shutdown()
    if not subscriptions:raise RuntimeError('subscriptions unavailable')


if __name__=='__main__':main()
