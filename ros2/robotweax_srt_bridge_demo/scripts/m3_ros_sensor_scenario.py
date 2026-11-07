#!/usr/bin/env python3
"""Finite IMU ROS N3 driver; coordination files never carry samples between peers."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import traceback
import rclpy
from rosidl_runtime_py.convert import message_to_ordereddict
from sensor_msgs.msg import Imu
from robotweax_srt_bridge_msgs.srv import GetBridgeMetrics
from m3_scenario import Benchmark, write


def digest(message):
    return hashlib.sha256(json.dumps(message_to_ordereddict(message), sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class Finite(Benchmark):
    def __init__(self, args):
        super().__init__(args)
        self.rows = []; self.armed_session = None

    def imu(self, message):
        super().imu(message)
        self.rows.append(dict(id=int(message.angular_velocity.z)-1, payload_sha256=digest(message), observed_ns=time.monotonic_ns()))

    def bridge_state(self, message):
        super().bridge_state(message)
        if self.armed_session is not None and (bytes(message.session_id) != self.armed_session or not message.ready or not message.clock_qualified):
            self.bad.append('session/readiness/clock changed while armed')

    def metrics(self):
        value = self.rpc(self.metric_client, GetBridgeMetrics.Request())
        return dict(bridge=message_to_ordereddict(value.snapshot), monotonic_ns=value.monotonic_ns)

    def stable_metrics(self):
        previous = None
        end = time.monotonic()+8
        while time.monotonic() < end:
            value = self.metrics()
            sensor = {k:v for k,v in value['bridge'].items() if k.startswith(('sensor_', 'samples_', 'transport_samples_', 'imu_age_', 'joint_age_'))}
            empty = all(value['bridge'][k] == 0 for k in ('sensor_ingress_pending', 'sensor_outbound_pending', 'sensor_receive_pending'))
            if previous == sensor and empty:
                return value
            previous = sensor; self.spin(.15)
        raise RuntimeError('stable empty pipeline timeout')

    def finite(self):
        self.start_bridge()
        self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified, 'qualified finite session', 40)
        if self.args.role == 'robot':
            self.wait(lambda:self.imu_pub.get_subscription_count()>0, 'local typed publisher discovery')
        self.spin(.5); begin = self.stable_metrics()
        assert begin['bridge']['samples_ingress'] == begin['bridge']['samples_published'] == begin['bridge']['sensor_sent'] == 0
        write(self.run/(self.args.role+'-finite-ready.json'), begin)
        self.wait(lambda:(self.run/'armed').exists(), 'host selector and measurement capture armed', 30)
        self.armed_session = bytes(self.state.session_id)
        assert list(self.armed_session) == begin['bridge']['session_id']
        start = time.monotonic_ns()
        if self.args.role == 'robot':
            for i in range(19):
                message = Imu(); message.header.stamp = self.get_clock().now().to_msg(); message.header.frame_id = 'demo_imu'
                message.orientation.w = 1.; message.angular_velocity.x = 200.; message.angular_velocity.y = 17.25
                message.angular_velocity.z = float(i+1); message.linear_acceleration.z = 9.81
                before = time.monotonic_ns(); self.imu_pub.publish(message); after = time.monotonic_ns()
                self.rows.append(dict(id=i, payload_sha256=digest(message), begin_ns=before, end_ns=after))
                self.spin(.05)
            stop = time.monotonic_ns(); write(self.run/'finite-sent.json', dict(count=19, start_ns=start, stop_ns=stop))
        else:
            self.wait(lambda:(self.run/'finite-sent.json').exists(), 'finite source complete', 10)
            stop = time.monotonic_ns()
        self.spin(2); end = self.stable_metrics()
        assert not self.bad, self.bad
        assert end['bridge']['session_id'] == begin['bridge']['session_id']
        assert end['bridge']['ready'] and end['bridge']['clock_qualified']
        assert self.direct == 0
        write(self.run/(self.args.role+'-finite-result.json'), dict(status='passed', begin=begin, end=end, rows=self.rows, start_ns=start, stop_ns=stop, direct=self.direct, bad=self.bad))
        self.wait(lambda:(self.run/'release').exists(), 'host evidence collected', 30)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--role', choices=('robot','operator'), required=True); p.add_argument('--run', required=True); p.add_argument('--peer', required=True)
    args = p.parse_args(); args.clock_width_ms=200; args.provider_diagnostics=False; args.command_diagnostics=False; args.seconds=10
    rclpy.init(); driver=Finite(args)
    try:
        driver.finite()
    except BaseException:
        write(driver.run/(args.role+'-finite-failure.json'), dict(traceback=traceback.format_exc())); raise
    finally:
        driver.cleanup(); driver.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main()
