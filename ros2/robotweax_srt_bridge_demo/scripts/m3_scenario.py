#!/usr/bin/env python3
"""M3 steady workload: fixed 200 Hz source, absolute 200 Hz command every 2 s.

Uses M2's device/typed-output checks. File messages coordinate the laboratory;
SENSOR and COMMAND payloads/results cross SRT, never the shared artifact files.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import traceback

import rclpy
from robotweax_srt_bridge_msgs.msg import CommandStatus
from robotweax_srt_bridge_msgs.srv import ExecuteCommand, GetCommandStatus
from m2_scenario import Driver, read, write


def histogram(values, maximum):
    values=[int(v) for v in values]
    count = sum(values)
    result = {'count': count, 'bucket_width_ms': 1, 'rounding': 'up', 'maximum_ns': maximum}
    for label, percentage in [('p50_ms', 50), ('p95_ms', 95), ('p99_ms', 99)]:
        rank = (count * percentage + 99)//100
        cumulative = 0
        result[label] = None
        for value, amount in enumerate(values):
            cumulative += amount
            if count and cumulative >= rank:
                result[label] = value
                break
    return result


class Benchmark(Driver):
    def __init__(self, args):
        super().__init__(args)
        self.last_diagnostic = None
        self.diagnostic_ns = self.unqualified_ns = self.not_ready_ns = 0
        self.diagnostic_count = 0
        self.sessions=set()
        self.last_resource = 0
        self.first_imu_marker=self.first_joint_marker=None
        self.resources = (self.run/(args.role+'-resources.jsonl')).open('w')

    def imu(self, message):
        if self.first_imu_marker is None:self.first_imu_marker=int(message.angular_velocity.z)
        super().imu(message)

    def joints(self, message):
        if self.first_joint_marker is None and message.position:self.first_joint_marker=round(message.position[0]*1000)
        super().joints(message)

    def bridge_state(self, message):
        stamp = time.monotonic_ns()
        if self.last_diagnostic:
            previous, previous_stamp = self.last_diagnostic
            elapsed = stamp-previous_stamp
            self.diagnostic_ns += elapsed
            if not previous.clock_qualified:self.unqualified_ns += elapsed
            if not previous.ready:self.not_ready_ns += elapsed
        self.last_diagnostic = (message, stamp)
        self.diagnostic_count += 1
        self.state = message
        sid = bytes(message.session_id).hex()
        if any(message.session_id):self.sessions.add(sid)
        for route, sequence in [('imu', message.imu_sequence), ('joint', message.joint_sequence)]:
            key = sid+route
            if sequence and self.sequence.get(key, 0)>sequence:self.bad.append('envelope sequence regressed')
            if sequence:self.sequence[key]=sequence

    def start(self, executable, name, parameters=None):
        package = 'robotweax_srt_bridge_demo' if executable=='rate_simulator' else 'robotweax_srt_bridge'
        argv = ['/workspace/install/m3-ros/'+package+'/lib/'+package+'/'+executable]
        if parameters:
            argv += ['--ros-args']
            for key, value in parameters.items():argv += ['-p', key+':='+str(value)]
        log = (self.run/(name+'.log')).open('w')
        p = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT)
        self.processes.append((p,name,log))
        return p

    def start_bridge(self):
        self.state = None
        self.bridge = self.start('bridge_node', self.args.role+'-bridge-'+str(len(self.processes)), {
            'role': 'caller' if self.args.role=='robot' else 'listener',
            'address': self.args.peer if self.args.role=='robot' else '0.0.0.0',
            'credential_file':'/run/bridge/passphrase',
            'journal_path':str(self.run/(self.args.role+'.sqlite')),
            'max_clock_interval_ms': self.args.clock_width_ms})

    def spin(self, seconds=.05):
        super().spin(seconds)
        stamp = time.monotonic_ns()
        if stamp-self.last_resource<1000000000:return
        self.last_resource=stamp
        todo=[p.pid for p,_,_ in self.processes if p.poll() is None]
        seen=set();rows=[]
        while todo:
            pid=todo.pop()
            if pid in seen:continue
            seen.add(pid)
            try:
                proc=Path('/proc/'+str(pid));raw=(proc/'stat').read_text();fields=raw[raw.rfind(')')+2:].split()
                rows.append(dict(pid=pid,comm=(proc/'comm').read_text().strip(),start_ticks=int(fields[19]),
                                 cpu_ticks=int(fields[11])+int(fields[12]),rss_bytes=int(fields[21])*os.sysconf('SC_PAGE_SIZE')))
                for task in (proc/'task').iterdir():
                    try:todo.extend(map(int,(task/'children').read_text().split()))
                    except FileNotFoundError:pass
            except FileNotFoundError:pass
        self.resources.write(json.dumps(dict(monotonic_ns=stamp,clock_ticks_per_second=os.sysconf('SC_CLK_TCK'),processes=rows))+'\n')
        self.resources.flush()

    def operator(self):
        self.start_bridge()
        self.wait(lambda:(self.run/'robot-ready.json').exists(),'robot source without bridge')
        self.spin(1)
        assert self.direct==self.remote_imu==self.remote_joints==0
        self.robot_command('start')
        self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified and self.remote_imu>20,
                  'qualified typed SRT stream',45)
        self.check_qos()
        start=time.monotonic();next_command=start;next_poll=start
        beginning_counts=(self.remote_imu,self.remote_joints)
        commands=[];pending=None;generation=0;paused=False;skipped=0
        write(self.run/'measurement-start.json',dict(monotonic_ns=time.monotonic_ns(),seconds=self.args.seconds))
        while time.monotonic()-start<self.args.seconds:
            now=time.monotonic()
            if now>=next_command:
                slots=int((now-next_command)//2)+1
                skipped+=slots-1
                next_command+=slots*2
                if pending or paused:skipped+=1
                else:
                    number=len(commands)+1
                    request=ExecuteCommand.Request(request_id=list(number.to_bytes(16,'little')),route_id=100,
                        rate_hz=200,expected_generation=generation,new_generation=generation+1)
                    invoked=time.monotonic_ns()
                    response=self.rpc(self.execute,request)
                    row=dict(number=number,submission=response.submission,submitted_monotonic_ns=invoked,queued_response_monotonic_ns=time.monotonic_ns(),
                             expected_generation=generation,new_generation=generation+1)
                    commands.append(row)
                    if response.submission==response.QUEUED:pending=row
                    else:row['terminal']='not_admitted'
            if pending and now>=next_poll:
                next_poll=now+.2
                number=pending['number']
                status=self.rpc(self.query,GetCommandStatus.Request(request_id=list(number.to_bytes(16,'little')),route_id=100,refresh=True)).status
                if status.found and status.state in (CommandStatus.SUCCEEDED,CommandStatus.FAILED,
                        CommandStatus.REJECTED,CommandStatus.EXPIRED,CommandStatus.UNKNOWN) and status.reason!=2:
                    pending.update(terminal=status.state,reason=status.reason,result_valid=status.result_valid,
                        result_rate_hz=status.result_rate_hz,result_generation=status.result_generation,
                        result_observed_monotonic_ns=time.monotonic_ns())
                    if status.state==CommandStatus.SUCCEEDED:
                        assert status.result_valid and status.result_rate_hz==200 and status.result_generation==pending['new_generation']
                        generation=status.result_generation
                    elif status.state==CommandStatus.UNKNOWN:
                        assert not status.result_valid
                        paused=True  # device generation is uncertain; never guess/replay
                    pending=None
            self.spin(.025)
            self.check_processes()
        measured_seconds=time.monotonic()-start
        end_counts=(self.remote_imu,self.remote_joints)
        device=self.robot_command('device')
        self.spin(.2)
        state=self.state
        assert state and not self.bad,self.bad[:10]
        assert self.direct==0
        assert state.samples_published==sum(state.imu_age_upper_histogram_ms)+sum(state.joint_age_upper_histogram_ms)
        assert state.imu_age_upper_max_ns<=250000000 and state.joint_age_upper_max_ns<=250000000
        assert device['effects']<=sum(c['submission']==0 for c in commands)
        for c in commands:
            if c.get('terminal')==CommandStatus.SUCCEEDED:assert c['result_generation']<=device['generation']
        from rosidl_runtime_py.convert import message_to_ordereddict
        result=dict(status='passed',configured_workload=dict(imu_hz=200,joints_hz=50,command_period_s=2),session_ids=sorted(self.sessions),qualification='development; not the complete M3 matrix',
            measured_seconds=measured_seconds,remote_imu=self.remote_imu,remote_joints=self.remote_joints,
            steady_window_imu=end_counts[0]-beginning_counts[0],steady_window_joints=end_counts[1]-beginning_counts[1],
            direct_dds_samples=self.direct,typed_errors=self.bad,commands=commands,skipped_command_slots=skipped,
            source_marker_spans=dict(imu=int(self.imu_marker)-self.first_imu_marker+1,
                joints=round(self.joint_marker*1000)-self.first_joint_marker+1),
            missing_within_observed_source_span=dict(imu=int(self.imu_marker)-self.first_imu_marker+1-self.remote_imu,
                joints=round(self.joint_marker*1000)-self.first_joint_marker+1-self.remote_joints),
            missing_scope='counter gaps between first/last observed payload only; unknown leading/trailing losses are not estimated',
            unresolved_command=pending,commands_paused_after_unknown=paused,device=device,
            diagnostic_observation=dict(samples=self.diagnostic_count,elapsed_ns=self.diagnostic_ns,
                unqualified_ns=self.unqualified_ns,not_ready_ns=self.not_ready_ns,method='previous-state hold between observed 100ms diagnostics; gaps included'),
            publication_age_upper=dict(scope='all publications in last received diagnostic snapshot, including startup/transients; up to one diagnostic interval of tail is not represented',
                snapshot_observed_monotonic_ns=self.last_diagnostic[1],
                imu=histogram(state.imu_age_upper_histogram_ms,state.imu_age_upper_max_ns),
                joints=histogram(state.joint_age_upper_histogram_ms,state.joint_age_upper_max_ns)),
            final_bridge_state=message_to_ordereddict(state),qos_checked=True,
            resource_scope='simulator, bridge and their supervised children; excludes test observer and packet capture')
        self.robot_command('finish')
        self.stop(self.bridge);self.bridge=None
        result['shutdowns']=self.shutdowns
        write(self.run/'operator-result.json',result)

    def stop(self, process):
        # Preserve the sender's final observed diagnostics before it disappears.
        # These are explicitly snapshots, not an exact shutdown tail count.
        from rosidl_runtime_py.convert import message_to_ordereddict
        if process is self.bridge and self.state is not None:
            write(self.run/(self.args.role+'-final-bridge-state.json'),dict(
                observed_monotonic_ns=self.last_diagnostic[1],bridge=message_to_ordereddict(self.state)))
        if process is self.sim and self.device is not None:
            write(self.run/'robot-final-device-state.json',message_to_ordereddict(self.device))
        super().stop(process)

    def cleanup(self):
        super().cleanup()
        self.resources.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role',choices=['robot','operator'],required=True)
    parser.add_argument('--run',required=True)
    parser.add_argument('--peer',default='')
    parser.add_argument('--seconds',type=float,default=300)
    parser.add_argument('--clock-width-ms',type=int,default=200)
    args=parser.parse_args()
    if not 10<=args.seconds<=7200:parser.error('duration must be 10..7200 seconds')
    rclpy.init();driver=Benchmark(args)
    try:getattr(driver,args.role)()
    except BaseException:
        write(driver.run/(args.role+'-failure.json'),dict(traceback=traceback.format_exc()))
        raise
    finally:
        driver.cleanup();driver.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
