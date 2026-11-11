#!/usr/bin/env python3
"""Two-container acceptance driver. Shared files coordinate faults, never samples/RPCs."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import traceback

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rosidl_runtime_py.convert import message_to_ordereddict
from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter, ParameterValue, ParameterType
from sensor_msgs.msg import Imu, JointState
from robotweax_srt_bridge_msgs.msg import BridgeState, SimulatorState, CommandStatus
from robotweax_srt_bridge_msgs.srv import ExecuteCommand, GetCommandStatus


from scenario_files import read, write


class Driver(Node):
    def __init__(self, args):
        super().__init__('m2_' + args.role + '_checker')
        self.args = args
        self.run = Path(args.run)
        self.processes = []
        self.control_sequence = 0
        self.retired = set()
        self.bridge = None
        self.sim = None
        self.state = None
        self.device = None
        self.remote_imu = self.remote_joints = self.direct = self.source = 0
        self.bad = []
        self.last_imu = None
        self.imu_marker = self.joint_marker = 0.0
        self.sequence = {}
        self.shutdowns = []
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT,
                         durability=DurabilityPolicy.VOLATILE)
        self.subs = [self.create_subscription(BridgeState, '/bridge/state', self.bridge_state, 1)]
        if args.role == 'robot':
            self.subs += [self.create_subscription(SimulatorState, '/robot/simulator_state', self.device_state, 1),
                          self.create_subscription(Imu, '/robot/imu', self.source_sample, qos)]
            self.imu_pub = self.create_publisher(Imu, '/robot/imu', qos)
            self.joint_pub = self.create_publisher(JointState, '/robot/joint_states', qos)
            self.parameters = self.create_client(SetParameters, '/rate_simulator/set_parameters')
        else:
            self.subs += [self.create_subscription(Imu, '/remote/robot/imu', self.imu, qos),
                          self.create_subscription(JointState, '/remote/robot/joint_states', self.joints, qos),
                          self.create_subscription(Imu, '/robot/imu', self.direct_sample, qos),
                          self.create_subscription(JointState, '/robot/joint_states', self.direct_sample, qos)]
            self.execute = self.create_client(ExecuteCommand, '/bridge/execute_command')
            self.query = self.create_client(GetCommandStatus, '/bridge/get_command_status')

    def bridge_state(self, m):
        self.state = m
        write(self.run / (self.args.role + '-state.json'), dict(bridge=message_to_ordereddict(m), remote_imu=self.remote_imu, remote_joints=self.remote_joints, source=self.source, direct=self.direct))
        sid = bytes(m.session_id).hex()
        for route, sequence in [('imu', m.imu_sequence), ('joint', m.joint_sequence)]:
            key = sid + route
            if sequence and self.sequence.get(key, 0) > sequence:
                self.bad.append('sequence regressed in session')
            if sequence:
                self.sequence[key] = sequence

    def device_state(self, m):
        self.device = m

    def source_sample(self, m):
        self.source += 1

    def direct_sample(self, m):
        self.direct += 1

    def imu(self, m):
        self.remote_imu += 1
        if m.angular_velocity.z <= self.imu_marker:
            self.bad.append('old/duplicate Imu payload after publication or reconnect')
        self.imu_marker = m.angular_velocity.z
        self.last_imu = m
        if (m.header.frame_id != 'demo_imu' or m.header.stamp.sec <= 0 or
                m.orientation.w != 1.0 or m.linear_acceleration.z != 9.81 or
                m.angular_velocity.x not in (200., 100., 75., 50.)):
            self.bad.append('invalid remote Imu fields')

    def joints(self, m):
        self.remote_joints += 1
        if not m.position or m.position[0] <= self.joint_marker:
            self.bad.append('old/duplicate JointState payload after publication or reconnect')
        if m.position:
            self.joint_marker = m.position[0]
        if (m.header.frame_id != 'demo_base' or len(m.name) != 6 or
                m.name != ['joint_' + str(i + 1) for i in range(6)] or
                len(m.position) != 6 or len(m.velocity) != 6 or len(m.effort) != 6 or
                any(abs((m.position[i] - m.position[0]) - i) > 1e-10 for i in range(6))):
            self.bad.append('invalid remote JointState fields')

    def spin(self, seconds=.05):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            rclpy.spin_once(self, timeout_sec=min(.05, max(0, until-time.monotonic())))

    def wait(self, predicate, label, timeout=20):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if predicate():
                return
            self.spin()
            self.check_processes()
        raise RuntimeError('timeout: ' + label)

    def check_processes(self):
        for p, name, _ in self.processes:
            if p.poll() is not None and p is not self.bridge and p not in self.retired:
                raise RuntimeError(name + ' exited ' + str(p.returncode))
        if self.bridge and self.bridge.poll() is not None:
            raise RuntimeError('bridge exited ' + str(self.bridge.returncode))

    def start(self, executable, name, parameters=None):
        path = '/workspace/install/m2-ros/' + ('robotweax_srt_bridge_demo' if executable == 'rate_simulator' else 'robotweax_srt_bridge')
        package = Path(path).name
        argv = [path + '/lib/' + package + '/' + executable]
        if parameters:
            argv += ['--ros-args']
            for key, value in parameters.items():
                argv += ['-p', key + ':=' + str(value)]
        log = (self.run / (name + '.log')).open('w')
        p = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)
        self.processes.append((p, name, log))
        return p

    def start_bridge(self):
        self.state = None
        self.bridge = self.start('bridge_node', self.args.role + '-bridge-' + str(len(self.processes)), {
            'role': 'caller' if self.args.role == 'robot' else 'listener',
            'address': self.args.peer if self.args.role == 'robot' else '0.0.0.0',
            'credential_file': '/run/bridge/passphrase',
            'journal_path': str(self.run / (self.args.role + '.sqlite'))})

    def stop(self, p):
        if p and p.poll() is None:
            worker = self.worker_pid() if p is self.bridge else None
            begin = time.monotonic()
            p.send_signal(signal.SIGINT)
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
                raise RuntimeError('shutdown exceeded five seconds')
            if worker:
                assert not Path("/proc/" + str(worker)).exists(), "worker survived bridge shutdown"
            self.retired.add(p)
            self.shutdowns.append({'seconds': time.monotonic()-begin, 'exit_code': p.returncode})
            if p.returncode != 0:
                raise RuntimeError('unclean shutdown ' + str(p.returncode))

    def rpc(self, client, request, timeout=6):
        self.wait(lambda: client.service_is_ready(), 'ROS service available', timeout)
        future = client.call_async(request)
        self.wait(future.done, 'ROS service response', timeout)
        return future.result()

    def set_delay(self, milliseconds):
        request = SetParameters.Request(parameters=[Parameter(name='response_delay_ms',
            value=ParameterValue(type=ParameterType.PARAMETER_INTEGER, integer_value=milliseconds))])
        response = self.rpc(self.parameters, request)
        assert response.results[0].successful

    def robot_command(self, action, **values):
        self.control_sequence += 1
        sequence = self.control_sequence
        write(self.run / 'control.json', dict(sequence=sequence, action=action, **values))
        self.wait(lambda: read(self.run / 'robot-reply.json').get('sequence') == sequence,
                  'robot action ' + action)
        response = read(self.run / 'robot-reply.json')
        assert response.get('ok'), response
        return response

    def worker_pid(self):
        children = set()
        for task in Path('/proc/' + str(self.bridge.pid) + '/task').iterdir():
            try:
                children.update(map(int, (task / 'children').read_text().split()))
            except FileNotFoundError:
                pass
        for pid in children:
            try:
                if b'ros_rate_worker' in Path('/proc/' + str(pid) + '/cmdline').read_bytes():
                    return pid
            except FileNotFoundError:
                pass
        return None

    def robot_action(self, action, request, response):
        return False

    def robot(self):
        self.sim = self.start('rate_simulator', 'simulator')
        self.wait(lambda: self.device and self.source > 20, 'simulator source')
        negative = self.start('bridge_node', 'wrong-hash', {'expected_imu_hash': 'RIHS01_' + '0'*64})
        negative.wait(timeout=10)
        self.processes = [v for v in self.processes if v[0] is not negative]
        assert negative.returncode == 1
        assert 'ROS type hash mismatch' in (self.run / 'wrong-hash.log').read_text()
        write(self.run / 'robot-ready.json', {'source_samples': self.source, 'wrong_hash_rejected': True})
        sequence = 0
        while True:
            self.spin()
            self.check_processes()
            request = read(self.run / 'control.json')
            if request.get('sequence', 0) <= sequence:
                continue
            sequence = request['sequence']
            action = request['action']
            response = {'sequence': sequence, 'ok': True}
            if action in ('start', 'restart'):
                self.start_bridge()
                self.wait(lambda: self.state and self.state.ready and self.state.clock_qualified,
                          'robot bridge ready', 30)
                assert self.state.sensor_qos_verified
            elif action == 'invalid':
                old = self.state.oversize_samples + self.state.invalid_samples
                for _ in range(12):
                    m = Imu(); m.header.frame_id = 'x'*65; self.imu_pub.publish(m)
                    j = JointState(); j.name = ['x']*7; self.joint_pub.publish(j)
                    j = JointState(); j.name = ['x']*6; j.position = [1.]*5; self.joint_pub.publish(j)
                    self.spin(.1)
                self.wait(lambda: self.state.oversize_samples + self.state.invalid_samples > old,
                          'invalid local samples rejected')
                assert self.state.oversize_samples > 0 and self.state.invalid_samples > 0
                response.update(oversize=self.state.oversize_samples, invalid=self.state.invalid_samples)
            elif action == 'delay':
                self.set_delay(request['milliseconds'])
            elif action == 'device':
                response.update(rate=self.device.rate_hz, generation=self.device.generation, effects=self.device.effects)
            elif action == 'arm_crash':
                self.set_delay(2500)
                write(self.run / 'robot-reply.json', response)
                self.wait(lambda: self.device.effects >= request['effects'], 'device effect before worker crash')
                pid = self.worker_pid()
                assert pid
                os.kill(pid, signal.SIGKILL)
                self.wait(lambda: self.state and self.state.worker_fault != 0, 'worker failure surfaced')
                self.stop(self.bridge)
                self.bridge = None
                write(self.run / 'crashed.json', {'effects': self.device.effects, 'generation': self.device.generation,
                                                 'rate': self.device.rate_hz, 'worker_killed': True})
                continue
            elif action == 'finish':
                self.stop(self.bridge); self.bridge = None
                self.stop(self.sim); self.sim = None
                write(self.run / 'robot-final.json', {'shutdowns': self.shutdowns, 'source_samples': self.source})
                write(self.run / 'robot-reply.json', response)
                return
            elif self.robot_action(action, request, response):
                pass
            else:
                raise RuntimeError('unknown robot action')
            write(self.run / 'robot-reply.json', response)

    def submit(self, number, rate, expected, new):
        request = ExecuteCommand.Request(request_id=[number] + [0]*15, route_id=100,
                                        rate_hz=rate, expected_generation=expected, new_generation=new)
        response = self.rpc(self.execute, request)
        assert response.submission == response.QUEUED, response

    def status(self, number):
        return self.rpc(self.query, GetCommandStatus.Request(request_id=[number]+[0]*15,
                                                             route_id=100, refresh=True)).status

    def terminal(self, number, state, reason=None):
        end = time.monotonic() + 25
        while time.monotonic() < end:
            status = self.status(number)
            if status.found and status.state == state and (reason is None or status.reason == reason):
                return {'state': status.state, 'reason': status.reason, 'revision': status.revision,
                        'result_valid': status.result_valid, 'rate': status.result_rate_hz,
                        'generation': status.result_generation}
            self.spin(.1)
        raise RuntimeError('terminal status missing ' + str(number) + ': ' + str(status))

    def check_qos(self):
        for topic in ('/remote/robot/imu', '/remote/robot/joint_states'):
            endpoints = self.get_publishers_info_by_topic(topic)
            assert len(endpoints) == 1, endpoints
            qos = endpoints[0].qos_profile
            assert qos.reliability == ReliabilityPolicy.BEST_EFFORT
            assert qos.durability == DurabilityPolicy.VOLATILE
            # Fast-RTPS discovery does not advertise history/depth (reports 0).
            # The bridge checks actual local QoS on each publisher/subscription.
            assert self.state.sensor_qos_verified

    def operator(self):
        self.start_bridge()
        self.wait(lambda: (self.run / 'robot-ready.json').exists(), 'robot source without bridge')
        self.spin(2)
        assert self.remote_imu == self.remote_joints == self.direct == 0
        self.robot_command('start')
        self.wait(lambda: self.state and self.state.ready and self.state.clock_qualified and
                  self.remote_imu > 40 and self.remote_joints > 10, 'typed sensors over SRT', 35)
        self.check_qos()
        invalid_ingress = self.robot_command('invalid')
        results = {}
        self.submit(1, 100, 0, 1)
        results['succeeded'] = self.terminal(1, CommandStatus.SUCCEEDED)
        assert results['succeeded']['result_valid'] and results['succeeded']['rate'] == 100
        self.wait(lambda: self.last_imu.angular_velocity.x == 100 and self.last_imu.angular_velocity.y == 1,
                  'actual publisher rate changed')
        self.submit(1, 100, 0, 1)
        self.terminal(1, CommandStatus.SUCCEEDED)
        assert self.robot_command('device')['effects'] == 1
        self.submit(2, 150, 0, 1)
        results['generation_conflict'] = self.terminal(2, CommandStatus.FAILED, 4)
        assert self.robot_command('device')['effects'] == 1
        self.robot_command('delay', milliseconds=2500)
        self.submit(3, 75, 1, 2)
        results['lost_reply'] = self.terminal(3, CommandStatus.UNKNOWN, 6)
        assert not results['lost_reply']['result_valid']
        assert self.robot_command('device')['effects'] == 2
        self.submit(3, 75, 1, 2)
        self.spin(.5)
        assert self.robot_command('device')['effects'] == 2
        old_session = bytes(self.state.session_id)
        self.robot_command('arm_crash', effects=3)
        self.submit(4, 50, 2, 3)
        self.wait(lambda: (self.run / 'crashed.json').exists(), 'crash after actual effect')
        outage_begin = time.monotonic()
        self.spin(1)
        before = self.remote_imu + self.remote_joints
        self.spin(1)
        assert self.remote_imu + self.remote_joints == before, 'publication continued after bridge stopped'
        outage_seconds = time.monotonic() - outage_begin
        assert outage_seconds >= 2
        self.robot_command('restart')
        self.wait(lambda: self.state and self.state.ready and self.state.clock_qualified and bytes(self.state.session_id) != old_session, 'new session reconnected')
        results['crash_recovery'] = self.terminal(4, CommandStatus.UNKNOWN, 1)
        assert not results['crash_recovery']['result_valid']
        self.submit(4, 50, 2, 3)
        self.spin(1)
        device = self.robot_command('device')
        assert device['effects'] == 3 and device['generation'] == 3 and device['rate'] == 50
        assert self.state.commands_sent == 4, 'duplicate/unknown intent transmitted again'
        command_frames = self.state.commands_sent
        assert not self.bad, self.bad[:10]
        assert self.direct == 0
        self.robot_command('finish')
        self.stop(self.bridge); self.bridge = None
        report = {'status': 'passed', 'results': results, 'remote_imu': self.remote_imu,
                  'remote_joints': self.remote_joints, 'direct_dds_samples': self.direct,
                  'typed_errors': self.bad, 'qos_checked': True, 'shutdowns': self.shutdowns,
                  'device': device, 'invalid_ingress': invalid_ingress, 'command_frames': command_frames,
                  'new_session_after_crash': True, 'outage_seconds': outage_seconds,
                  'payload_markers_monotonic': True, 'no_publication_after_stop': True}
        write(self.run / 'operator-result.json', report)

    def cleanup(self):
        for p, _, log in reversed(self.processes):
            if p.poll() is None:
                p.send_signal(signal.SIGINT)
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill(); p.wait()
            log.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role', choices=['robot', 'operator'], required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--peer', default='')
    args = parser.parse_args()
    rclpy.init()
    driver = Driver(args)
    try:
        getattr(driver, args.role)()
    except BaseException:
        write(driver.run / (args.role + '-failure.json'), {'traceback': traceback.format_exc()})
        raise
    finally:
        driver.cleanup()
        driver.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
