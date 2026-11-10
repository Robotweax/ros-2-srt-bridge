#!/usr/bin/env python3
"""M3 steady workload: fixed 200 Hz source, absolute 200 Hz command every 2 s.

Uses M2's device/typed-output checks. File messages coordinate the laboratory;
SENSOR and COMMAND payloads/results cross SRT, never the shared artifact files.
"""
import argparse
import sys
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import traceback

import rclpy
from robotweax_srt_bridge_msgs.msg import CommandStatus
from robotweax_srt_bridge_msgs.srv import ExecuteCommand, GetCommandStatus, GetBridgeMetrics, SetPublishing
ROOT=Path('/workspace')
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(1,str(ROOT/'ros2/robotweax_srt_bridge_demo/scripts'))
HERE=Path(__file__).resolve().parent
from m3_observer_filtering import require_role,status
from shutdown_observer import identity
from m2_scenario import Driver, read, write
from command_workload import record_status_observation


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


from endpoint_measurement import EndpointSampler


class Benchmark(Driver):
    def __init__(self, args):
        super().__init__(args)
        self.last_diagnostic = None
        self.diagnostic_ns = self.unqualified_ns = self.not_ready_ns = 0
        self.diagnostic_count = 0
        self.sessions=set()
        self.last_resource = 0
        self.endpoint_sampler=EndpointSampler(self.run/(args.role+'-endpoint-samples.jsonl'))
        self.first_imu_marker=self.first_joint_marker=None
        self.metric_client=self.create_client(GetBridgeMetrics,'/bridge/get_metrics')
        self.publishing_client=self.create_client(SetPublishing,'/robot/set_publishing')
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
        argv = ['/workspace/'+getattr(self.args,'ros_install','install/m3-ros')+'/'+package+'/lib/'+package+'/'+executable]
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
            'max_clock_interval_ms': self.args.clock_width_ms,
            'provider_diagnostics': str(self.args.provider_diagnostics).lower(),
            'sensor_provider_diagnostics': str(getattr(self.args,'sensor_provider_diagnostics',False)).lower(),
            'sample_diagnostics': str(getattr(self.args,'sample_diagnostics',False)).lower(),
            **({'start_diagnostics':'true'} if getattr(self.args,'start_diagnostics',False) else {}),
            **({'sender_diagnostics':'true'} if getattr(self.args,'sender_diagnostics',False) else {}),
            **({'probe_diagnostics':'true'} if getattr(self.args,'probe_diagnostics',False) else {}),
            **({'shutdown_diagnostics':'true','shutdown_trace_path':str(self.run/(self.args.role+'-shutdown-stages.jsonl'))} if getattr(self.args,'shutdown_diagnostics',False) else {}),
            'command_diagnostics': str(self.args.command_diagnostics).lower()})

    def spin(self, seconds=.05):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            super().spin(min(.05,max(0,end-time.monotonic())))
            roots=[('observer',os.getpid())]
            if self.sim and self.sim.poll() is None:roots.append(('source',self.sim.pid))
            if self.bridge and self.bridge.poll() is None:roots.append(('control',self.bridge.pid))
            self.endpoint_sampler.tick(roots)
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

    def robot_action(self, action, request, response):
        from rosidl_runtime_py.convert import message_to_ordereddict
        if action=='reset_link':
            self.stop(self.bridge);self.bridge=None
            self.start_bridge()
            self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified,'fresh source link ready',30)
            return True
        if action in ('pause','resume'):
            r=self.rpc(self.publishing_client,SetPublishing.Request(enabled=action=='resume'))
            assert r.enabled==(action=='resume')
            response.update(device=message_to_ordereddict(r.snapshot),monotonic_ns=r.monotonic_ns,enabled=r.enabled)
            return True
        if action=='metrics':
            r=self.rpc(self.metric_client,GetBridgeMetrics.Request())
            response.update(bridge=message_to_ordereddict(r.snapshot),monotonic_ns=r.monotonic_ns)
            return True
        return False

    def checkpoint(self, pause):
        from rosidl_runtime_py.convert import message_to_ordereddict
        # Publishing is fenced in the simulator's timer callback group. Drain
        # outstanding 250ms samples and local DDS before taking stable snapshots.
        self.spin(2)
        def take():
            sender=self.robot_command('metrics')
            r=self.rpc(self.metric_client,GetBridgeMetrics.Request())
            return dict(sender=sender['bridge'],receiver=message_to_ordereddict(r.snapshot),
                device=pause['device'],device_pause_monotonic_ns=pause['monotonic_ns'],
                sender_snapshot_monotonic_ns=sender['monotonic_ns'],receiver_snapshot_monotonic_ns=r.monotonic_ns,
                observer=dict(imu=self.remote_imu,joints=self.remote_joints))
        end=time.monotonic()+8
        while time.monotonic()<end:
            before=take();self.spin(.15);after=take()
            stable=lambda data:{key:value for key,value in data.items() if key.startswith('sensor_') or key.startswith('samples_') or key in ('imu_ingress','joint_ingress','transport_samples_received','transport_samples_rejected')}
            empty=all(after[role][key]==0 for role in ('sender','receiver') for key in ('sensor_ingress_pending','sensor_outbound_pending','sensor_receive_pending'))
            if empty and before['observer']==after['observer'] and all(stable(before[role])==stable(after[role]) for role in ('sender','receiver')):
                return after
        raise RuntimeError('sensor pipeline did not reach a stable, empty checkpoint')

    def observe_command(self, row):
        status=self.rpc(self.query,GetCommandStatus.Request(request_id=list(row['number'].to_bytes(16,'little')),route_id=100,refresh=True)).status
        record_status_observation(row,{key:getattr(status,key) for key in
            ('found','state','reason','local_error','revision','query_queued','peer_error')},time.monotonic_ns())
        if not status.found or status.state not in (CommandStatus.SUCCEEDED,CommandStatus.FAILED,CommandStatus.REJECTED,CommandStatus.EXPIRED,CommandStatus.UNKNOWN) or status.reason==2:
            return None
        row.update(terminal=status.state,reason=status.reason,result_valid=status.result_valid,
            result_rate_hz=status.result_rate_hz,result_generation=status.result_generation,result_observed_monotonic_ns=time.monotonic_ns())
        if status.state==CommandStatus.SUCCEEDED:
            assert status.result_valid and status.result_rate_hz==200 and status.result_generation==row['new_generation']
        if status.state==CommandStatus.UNKNOWN:assert not status.result_valid
        return status.state

    def operator(self):
        self.start_bridge()
        self.wait(lambda:(self.run/'robot-ready.json').exists(),'robot source without bridge')
        self.spin(1)
        assert self.direct==self.remote_imu==self.remote_joints==0
        self.robot_command('start')
        self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified and self.remote_imu>20,
                  'qualified typed SRT stream',45)
        self.check_qos()
        paused_source=self.robot_command('pause')
        old_session=bytes(self.state.session_id)
        # The warmup FEC decoder may retain an incomplete row. A fresh source
        # session while publishing is disabled excludes every warmup SAMPLE.
        self.robot_command('reset_link')
        self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified and bytes(self.state.session_id)!=old_session,'fresh measurement session',30)
        begin=self.checkpoint(paused_source)
        assert begin['sender']['samples_ingress']==begin['sender']['sensor_submitted']==begin['sender']['sensor_sent']==0
        fenced_start=time.monotonic_ns()
        resumed=self.robot_command('resume')
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
                terminal=self.observe_command(pending)
                if terminal is not None:
                    if terminal==CommandStatus.SUCCEEDED:generation=pending['result_generation']
                    elif terminal==CommandStatus.UNKNOWN:paused=True
                    pending=None
            self.spin(.025)
            self.check_processes()
        measured_seconds=time.monotonic()-start
        cutoff_ns=time.monotonic_ns()
        pause_response=self.robot_command('pause')
        # No new commands or samples; observe already-admitted command results.
        drain_deadline=time.monotonic()+8
        while pending and time.monotonic()<drain_deadline:
            terminal=self.observe_command(pending)
            if terminal is not None:
                pending['observed_after_data_cutoff']=True
                if terminal==CommandStatus.UNKNOWN:paused=True
                pending=None
            else:self.spin(.1)
        finish=self.checkpoint(pause_response)
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
        fenced_end=time.monotonic_ns();self.spin(.35)
        result=dict(endpoint_fenced_interval_ns=[fenced_start,fenced_end],status='passed',configured_workload=dict(imu_hz=200,joints_hz=50,command_period_s=2),session_ids=sorted(self.sessions),qualification='development; not the complete M3 matrix',
            measured_seconds=measured_seconds,warmup_sensor_history_excluded=True,command_data_cutoff_monotonic_ns=cutoff_ns,command_result_drain_limit_s=8,checkpoints=dict(begin=begin,end=finish),
            publication_interval=dict(resume_monotonic_ns=resumed['monotonic_ns'],pause_monotonic_ns=pause_response['monotonic_ns']),remote_imu=self.remote_imu,remote_joints=self.remote_joints,
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
        self.endpoint_sampler.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ros-install',choices=('install/m3-ros','install/m3-start-trace-ros','install/m3-sender-visibility-ros','install/m3-probe-tracing-ros','install/m3-sender-reconcile-ros','install/m3-shutdown-trace-calibration-ros','install/m3-socket-disposition-ros'),default='install/m3-ros')
    parser.add_argument('--role',choices=['robot','operator'],required=True)
    parser.add_argument('--run',required=True)
    parser.add_argument('--peer',default='')
    parser.add_argument('--seconds',type=float,default=300)
    parser.add_argument('--clock-width-ms',type=int,default=200)
    parser.add_argument('--shutdown-diagnostics',action='store_true')
    parser.add_argument('--start-diagnostics',action='store_true')
    parser.add_argument('--sender-diagnostics',action='store_true')
    parser.add_argument('--probe-diagnostics',action='store_true')
    parser.add_argument('--command-diagnostics',action='store_true')
    parser.add_argument('--provider-diagnostics',action='store_true')
    parser.add_argument('--sensor-provider-diagnostics',action='store_true')
    args=parser.parse_args()
    if args.start_diagnostics and not args.command_diagnostics:parser.error('start diagnostics require command diagnostics')
    if args.sender_diagnostics and not args.command_diagnostics:parser.error('sender diagnostics require command diagnostics')
    if args.probe_diagnostics and not args.command_diagnostics:parser.error('probe diagnostics require command diagnostics')
    if not 10<=args.seconds<=7200:parser.error('duration must be 10..7200 seconds')
    rclpy.init();driver=Benchmark(args)
    try:getattr(driver,args.role)()
    except BaseException:
        write(driver.run/(args.role+'-failure.json'),dict(traceback=traceback.format_exc()))
        raise
    finally:
        driver.cleanup();driver.destroy_node();rclpy.shutdown()


class Diagnostic(Benchmark):
    def start(self, executable, name, parameters=None):
        if executable!='bridge_node':return super().start(executable,name,parameters)
        binary='/workspace/'+self.args.ros_install+'/robotweax_srt_bridge/lib/robotweax_srt_bridge/bridge_node'
        argv=[sys.executable,str(HERE/'bridge_exec.py'),str(self.run/(self.args.role+'-bridge-preexec.json')),binary,'--ros-args']
        for key,value in parameters.items():argv+=['-p',key+':='+str(value)]
        log=(self.run/(name+'.log')).open('w');child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT)
        self.processes.append((child,name,log));return child

    def start_bridge(self):
        super().start_bridge();until=time.monotonic()+5
        while time.monotonic()<until:
            if self.bridge.poll() is not None:raise ValueError('bridge capability-drop/startup failed')
            if (self.run/(self.args.role+'-bridge-preexec.json')).exists():
                require_role(status(self.bridge.pid),0)
                write(self.run/(self.args.role+'-bridge-identity.json'),dict(**identity(Path('/proc'),self.bridge.pid),permissions=status(self.bridge.pid),monotonic_ns=time.monotonic_ns(),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),time_namespace_offsets=Path('/proc/self/timens_offsets').read_text()))
                return
            time.sleep(.01)
        raise ValueError('bridge capability attestation missing')

    def robot_command(self, action, *args, **kwargs):
        if action=='finish':
            (self.run/'n0-shutdown-ready').touch()
            until=time.monotonic()+15
            while not (self.run/'n0-shutdown-release').exists():
                if time.monotonic()>=until:raise ValueError('host observer not ready; no normal shutdown release')
                self.spin(.025)
        return super().robot_command(action,*args,**kwargs)

    def stop(self, process):
        if process is None or process.poll() is not None:return super().stop(process)
        record=dict(name=next(n for p,n,_ in self.processes if p is process),pid=process.pid,forced_kill=False)
        send=process.send_signal;kill=process.kill
        def signal_begin(sig):
            record['signal_begin_ns']=time.monotonic_ns()
            try:return send(sig)
            finally:record['signal_end_ns']=time.monotonic_ns()
        def forced():
            record['forced_kill']=True;return kill()
        process.send_signal=signal_begin;process.kill=forced
        try:
            super().stop(process)
            record['passed']=True
        except BaseException:
            record['passed']=False;raise
        finally:
            process.send_signal=send;process.kill=kill
            record.update(end_ns=time.monotonic_ns(),returncode=process.poll())
            path=self.run/(self.args.role+'-child-shutdown.json')
            report=read(path) if path.exists() else dict(children=[])
            report['children'].append(record);report['passed']=all(x['passed'] and not x['forced_kill'] and x['returncode']==0 for x in report['children'])
            write(path,report)

if __name__=='__main__':
    if '--shutdown-diagnostics' not in sys.argv:raise SystemExit('N0 shutdown tracing required')
    Benchmark=Diagnostic
    main()
