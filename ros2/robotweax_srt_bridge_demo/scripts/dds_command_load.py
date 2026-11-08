"""Nonblocking journaled DDS workload adapter for the steady sensor driver."""
import subprocess
import time
from rosidl_runtime_py.convert import message_to_ordereddict
from robotweax_srt_bridge_msgs.msg import DdsCommandState,CommandStatus
from robotweax_srt_bridge_msgs.srv import ExecuteCommand,GetCommandStatus
from command_workload import Cadence,record_status_observation
from m2_scenario import write
from scenario_processes import stop_children


class DdsCommandLoad:
    def __init__(self,node):
        self.node=node;self.state=None;self.process=None;self.log=None;self.last_diagnostic_write_ns=0;self.last_ready=None
        self.sender=node.args.role=='operator';self.rows=[];self.pending=None
        self.cadence=None;self.generation=0;self.paused=False;self.cutoff_ns=None;self.frozen=False
        self.execute_future=self.query_future=None;self.next_poll=0
        side='sender' if self.sender else 'receiver'
        self.subscription=node.create_subscription(DdsCommandState,'/dds/commands/'+side+'/state',self.diagnostic,1)
        self.execute=node.create_client(ExecuteCommand,'/bridge/execute_command') if self.sender else None
        self.query=node.create_client(GetCommandStatus,'/bridge/get_command_status') if self.sender else None

    def diagnostic(self,state):
        self.state=state
        stamp=time.monotonic_ns()
        if stamp-self.last_diagnostic_write_ns>=1000000000 or state.ready!=self.last_ready or state.failed:
            write(self.node.run/(self.node.args.role+'-command-state.json'),message_to_ordereddict(state))
            self.last_diagnostic_write_ns=stamp;self.last_ready=state.ready
        if state.failed:raise RuntimeError('DDS command coordinator failed')

    def launch(self):
        executable='/workspace/install/m3-ros/robotweax_srt_bridge/lib/robotweax_srt_bridge/dds_command_node'
        self.log=(self.node.run/(self.node.args.role+'-command.log')).open('w')
        self.process=subprocess.Popen([executable,'--ros-args','-p','role:='+('sender' if self.sender else 'receiver'),
            '-p','journal_path:='+str(self.node.run/(self.node.args.role+'.sqlite'))],stdout=self.log,stderr=subprocess.STDOUT)

    def check(self):
        if self.process and self.process.poll() is not None:raise RuntimeError('DDS command coordinator exited')

    def ready(self):
        return self.state and self.state.ready and (not self.sender or (self.execute.service_is_ready() and self.query.service_is_ready()))

    def snapshot(self):
        if self.state is None:raise RuntimeError('missing command diagnostics')
        return message_to_ordereddict(self.state)

    def begin(self,generation):
        self.generation=generation;self.cadence=Cadence(time.monotonic())

    def cutoff(self):
        self.cutoff_ns=time.monotonic_ns()

    def freeze(self):
        self.frozen=True

    def tick(self):
        if not self.sender or self.cadence is None or self.frozen:return
        now=time.monotonic()
        if self.cutoff_ns is not None and time.monotonic_ns()>=self.cutoff_ns+8000000000:
            self.freeze();return
        if self.execute_future is not None and self.execute_future.done():
            response=self.execute_future.result();self.execute_future=None
            self.pending.update(submission=response.submission,queued_response_monotonic_ns=time.monotonic_ns())
            if response.submission!=ExecuteCommand.Response.QUEUED:
                self.pending['terminal']='not_admitted';self.pending=None
        if self.query_future is not None and self.query_future.done():
            status=self.query_future.result().status;self.query_future=None
            if self.pending:record_status_observation(self.pending,message_to_ordereddict(status),time.monotonic_ns())
            if self.pending and status.found and status.state in (4,5,6,7,8) and status.reason!=2:
                observed=time.monotonic_ns()
                if self.cutoff_ns is not None and observed>self.cutoff_ns+8000000000:
                    self.freeze();return
                row=self.pending
                row.update(terminal=status.state,reason=status.reason,result_valid=status.result_valid,
                    result_rate_hz=status.result_rate_hz,result_generation=status.result_generation,
                    result_observed_monotonic_ns=observed,observed_after_data_cutoff=self.cutoff_ns is not None)
                if status.state==CommandStatus.SUCCEEDED:
                    if not status.result_valid or status.result_rate_hz!=200 or status.result_generation!=row['new_generation']:raise RuntimeError('invalid confirmed DDS command result')
                    self.generation=status.result_generation
                elif status.state==CommandStatus.UNKNOWN:
                    if status.result_valid:raise RuntimeError('UNKNOWN has a valid result')
                    self.paused=True
                self.pending=None
        if self.pending and self.execute_future is None and self.query_future is None and now>=self.next_poll:
            self.next_poll=now+.2
            self.query_future=self.query.call_async(GetCommandStatus.Request(request_id=list(self.pending['number'].to_bytes(16,'little')),route_id=100,refresh=True))
        if self.cutoff_ns is None and self.cadence.due(now,self.pending is None and not self.paused):
            number=len(self.rows)+1
            row=dict(number=number,expected_generation=self.generation,new_generation=self.generation+1,submitted_monotonic_ns=time.monotonic_ns())
            self.rows.append(row);self.pending=row
            self.execute_future=self.execute.call_async(ExecuteCommand.Request(request_id=list(number.to_bytes(16,'little')),route_id=100,
                rate_hz=200,expected_generation=self.generation,new_generation=self.generation+1))

    def stop(self):
        if self.process:
            report=stop_children([(self.process,'dds-command',self.log)])
            write(self.node.run/(self.node.args.role+'-command-shutdown.json'),report)
            self.process=None;self.log=None
            if not report['passed']:raise RuntimeError('DDS command child shutdown failed')
