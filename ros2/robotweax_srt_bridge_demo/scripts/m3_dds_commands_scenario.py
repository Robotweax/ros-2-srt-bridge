#!/usr/bin/env python3
"""DDS command development acceptance: durable duplicate/conflict/UNKNOWN/crash.

Shared files coordinate startup/faults and diagnostic snapshots. Commands and
journal status use Reliable DDS, never file payload transport. Common VM only.
"""
import argparse
from pathlib import Path
import signal
import subprocess
import time
import traceback
import rclpy
from rosidl_runtime_py.convert import message_to_ordereddict
from robotweax_srt_bridge_msgs.msg import DdsCommandState, CommandStatus
from robotweax_srt_bridge_msgs.srv import ExecuteCommand,GetCommandStatus
from m2_scenario import Driver,read,write


class CommandDriver(Driver):
    def __init__(self,args):
        super().__init__(args)
        self.command_state=None;self.results=[]
        side='receiver' if args.role=='robot' else 'sender'
        self.subs.append(self.create_subscription(DdsCommandState,'/dds/commands/'+side+'/state',self.command_diagnostic,1))

    def command_diagnostic(self,state):
        self.command_state=state
        write(self.run/(self.args.role+'-command-state.json'),message_to_ordereddict(state))
        if state.failed:raise RuntimeError('DDS command worker failed')

    def start(self,executable,name,parameters=None):
        package='robotweax_srt_bridge_demo' if executable=='rate_simulator' else 'robotweax_srt_bridge'
        argv=['/workspace/install/m3-ros/'+package+'/lib/'+package+'/'+executable]
        if parameters:
            argv+=['--ros-args']
            for key,value in parameters.items():argv+=['-p',key+':='+str(value)]
        log=(self.run/(name+'.log')).open('w')
        p=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT);self.processes.append((p,name,log));return p

    def start_bridge(self):
        self.command_state=None
        self.bridge=self.start('dds_command_node',self.args.role+'-dds-'+str(len(self.processes)),
            dict(role='receiver' if self.args.role=='robot' else 'sender',journal_path=str(self.run/(self.args.role+'.sqlite'))))

    def ready(self):
        self.wait(lambda:self.command_state and self.command_state.ready,'DDS command session',40)

    def robot(self):
        self.sim=self.start('rate_simulator','simulator')
        self.wait(lambda:self.device and self.source>20,'live sensor simulator')
        self.start_bridge();write(self.run/'robot-ready.json',dict(ready=True))
        sequence=0
        while True:
            self.spin();self.check_processes();q=read(self.run/'control.json')
            if q.get('sequence',0)<=sequence:continue
            sequence=q['sequence'];action=q['action'];response=dict(sequence=sequence,ok=True)
            if action=='ready':self.ready()
            elif action=='metrics':
                self.spin(.2);response['command_state']=message_to_ordereddict(self.command_state)
            elif action=='delay':self.set_delay(q['milliseconds'])
            elif action=='device':
                if 'effects' in q:self.wait(lambda:self.device.effects>=q['effects'],'expected device effect')
                response.update(rate=self.device.rate_hz,generation=self.device.generation,effects=self.device.effects)
            elif action=='arm_crash':
                self.set_delay(4500);write(self.run/'robot-reply.json',response)
                self.wait(lambda:self.device.effects>=q['effects'],'effect before receiver crash')
                self.bridge.kill();self.bridge.wait(timeout=5);self.retired.add(self.bridge);self.bridge=None
                write(self.run/'crashed.json',dict(effects=self.device.effects,generation=self.device.generation))
                continue
            elif action=='restart':self.start_bridge();self.ready()
            elif action=='finish':
                self.stop(self.bridge);self.bridge=None;self.stop(self.sim);self.sim=None
                write(self.run/'robot-final.json',dict(effects=self.device.effects,generation=self.device.generation,shutdowns=self.shutdowns))
                write(self.run/'robot-reply.json',response);return
            else:raise RuntimeError('unknown DDS control action '+action)
            write(self.run/'robot-reply.json',response)

    def submit(self,number,rate,expected,new):
        response=self.rpc(self.execute,ExecuteCommand.Request(request_id=list(number.to_bytes(16,'little')),route_id=100,rate_hz=rate,expected_generation=expected,new_generation=new))
        assert response.submission==ExecuteCommand.Response.QUEUED,response.submission

    def result(self,number,state,timeout=25):
        end=time.monotonic()+timeout;last=None
        while time.monotonic()<end:
            last=self.rpc(self.query,GetCommandStatus.Request(request_id=list(number.to_bytes(16,'little')),route_id=100,refresh=True)).status
            if last.found and last.state==state and last.reason!=2:
                self.results.append(dict(number=number,status=message_to_ordereddict(last)))
                return last
            self.spin(.1)
        raise RuntimeError('status timeout '+str(number)+': '+str(last))

    def operator(self):
        self.wait(lambda:(self.run/'robot-ready.json').exists(),'robot')
        self.start_bridge();self.ready();self.robot_command('ready')
        initial_epoch=bytes(self.command_state.process_epoch)
        self.submit(1,100,0,1);first=self.result(1,CommandStatus.SUCCEEDED)
        assert first.result_valid and first.result_rate_hz==100 and first.result_generation==1
        self.submit(1,100,0,1);self.result(1,CommandStatus.SUCCEEDED)
        self.spin(.3);assert self.robot_command('device')['effects']==1
        assert self.command_state.commands_sent==1
        # Same id/different payload is a local durable conflict, never a send.
        self.submit(1,75,0,1);self.spin(.3)
        conflict=self.rpc(self.query,GetCommandStatus.Request(request_id=list((1).to_bytes(16,'little')),route_id=100,refresh=False)).status
        assert conflict.local_error==3,conflict
        self.results.append(dict(number=1,conflict=message_to_ordereddict(conflict)))
        assert self.command_state.commands_sent==1
        assert self.robot_command('device')['effects']==1
        lease_before=dict(sender=self.command_state.lease_expirations,receiver=self.robot_command('metrics')['command_state']['lease_expirations'])
        self.robot_command('delay',milliseconds=4500)
        self.submit(2,75,1,2);uncertain=self.result(2,CommandStatus.UNKNOWN)
        assert not uncertain.result_valid
        self.submit(2,75,1,2);self.result(2,CommandStatus.UNKNOWN)
        self.spin(.3);device=self.robot_command('device');assert device['effects']==2 and device['generation']==2
        lease_after=dict(sender=self.command_state.lease_expirations,receiver=self.robot_command('metrics')['command_state']['lease_expirations'])
        assert lease_after==lease_before,(lease_before,lease_after)
        self.robot_command('delay',milliseconds=0)
        self.ready();self.robot_command('ready')
        self.robot_command('arm_crash',effects=3)
        self.submit(3,50,2,3)
        self.wait(lambda:(self.run/'crashed.json').exists(),'receiver killed after effect',10)
        self.wait(lambda:self.command_state.commands_sent>=3,'sender diagnostic records third durable send')
        before_restart=message_to_ordereddict(self.command_state)
        assert before_restart['commands_sent']==3
        # Kill the sender before it can reconcile receiver status. Reopening
        # its unfinished durable admission must QUERY, never resend COMMAND.
        self.bridge.kill();self.bridge.wait(timeout=5);self.retired.add(self.bridge);self.bridge=None
        self.start_bridge();self.robot_command('restart');self.ready();self.robot_command('ready')
        assert bytes(self.command_state.process_epoch)!=initial_epoch
        self.result(3,CommandStatus.UNKNOWN)
        self.submit(3,50,2,3);self.result(3,CommandStatus.UNKNOWN)
        self.spin(.3);assert self.command_state.commands_sent==0
        assert self.command_state.queries_sent>0
        assert self.robot_command('device')['effects']==3
        # Recovery does not guess the next generation; here an explicit device
        # reconciliation is part of this laboratory test before new intent 4.
        self.robot_command('delay',milliseconds=0)
        self.submit(4,200,3,4);self.result(4,CommandStatus.SUCCEEDED)
        device=self.robot_command('device',effects=4);assert device['effects']==4 and device['generation']==4
        self.wait(lambda:self.command_state.commands_sent>=1,'sender diagnostic records new intent')
        final=message_to_ordereddict(self.command_state)
        assert final['commands_sent']==1
        self.robot_command('finish');self.stop(self.bridge);self.bridge=None
        write(self.run/'operator-result.json',dict(status='passed',common_vm_only=True,commands_qualified_for_complete_m3=False,
            results=self.results,blocked_handler_lease_counts=dict(before=lease_before,after=lease_after),before_sender_restart=before_restart,after_sender_restart=final,device=device,
            checks=['durable sender/receiver journals','one command send per new durable intent','duplicate no effect','same-id conflict no send',
                'unobserved handler reply is UNKNOWN','receiver crash after effect recovers UNKNOWN','sender crash/reopen queries without replay','new intent after explicit device reconciliation'],
            scope='DDS command development acceptance, not full impairment matrix; no cross-host clock or DDS encryption qualification'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--role',choices=['robot','operator'],required=True)
    parser.add_argument('--run',required=True);parser.add_argument('--peer',default='')
    args=parser.parse_args();rclpy.init();driver=CommandDriver(args)
    try:getattr(driver,args.role)()
    except BaseException:
        write(driver.run/(args.role+'-failure.json'),dict(traceback=traceback.format_exc()));raise
    finally:driver.cleanup();driver.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
