#!/usr/bin/env python3
"""One command and persistent external simulator across an explicitly injected crash."""
import argparse
import json
import os
from pathlib import Path
import signal
import sqlite3
import time
import traceback
import rclpy
from rosidl_runtime_py.convert import message_to_ordereddict
from robotweax_srt_bridge_msgs.srv import SetPublishing,GetBridgeMetrics
from m3_scenario import Benchmark,write
from m2_scenario import read
from scenario_processes import stop_children


class Crash(Benchmark):
    def __init__(self,args):super().__init__(args);self.crashes=[]
    def cleanup(self):
        report=stop_children([p for p in self.processes if p[0] not in self.retired])
        self.resources.close();self.endpoint_sampler.close();write(self.run/(self.args.role+'-shutdown.json'),report)
        if not report['passed']:raise RuntimeError('unplanned child shutdown failure')
    def device_snapshot(self):
        return message_to_ordereddict(self.rpc(self.publishing_client,SetPublishing.Request(enabled=False)).snapshot)
    def metrics(self):return message_to_ordereddict(self.rpc(self.metric_client,GetBridgeMetrics.Request()).snapshot)
    def stop_bridge(self,killed=False):
        p=self.bridge;item=next(i for i in self.processes if i[0] is p);before=p.poll();assert before is None
        begin=time.monotonic_ns()
        if killed:p.kill();code=p.wait(timeout=5);assert code==-signal.SIGKILL;item[2].close();report=dict(injected='SIGKILL',exit=code,begin_ns=begin,end_ns=time.monotonic_ns(),pid=p.pid)
        else:
            report=stop_children([item]);assert report['passed']
        self.retired.add(p);self.bridge=None;self.crashes.append(report);return report
    def journal(self):
        with sqlite3.connect('file:'+str(self.run/'robot.sqlite')+'?mode=ro',uri=True) as db:
            return [dict(id=i.hex(),state=s-10) for i,s in db.execute('SELECT id,state FROM entries')]
    def robot(self):
        self.sim=self.start('rate_simulator','robot-source',dict(publishing_enabled='false',response_delay_ms=2500 if self.args.case=='effect' else 0))
        self.wait(lambda:self.device is not None,'external device');self.start_bridge()
        self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified,'ready',40)
        write(self.run/'robot-ready.json',dict(owner=bytes(self.state.owner_epoch).hex(),session=bytes(self.state.session_id).hex(),device=self.device_snapshot()))
        sequence=0
        while True:
            self.spin(.02);self.check_processes();q=read(self.run/'control.json')
            if q.get('sequence',0)<=sequence:continue
            sequence=q['sequence'];action=q['action'];response=dict(sequence=sequence,ok=True)
            if action=='arm_effect_crash':
                write(self.run/'robot-reply.json',response)
                self.wait(lambda:self.device and self.device.effects==1,'observed external effect before worker crash')
                pid=self.worker_pid();assert pid;device=self.device_snapshot();journal=self.journal();assert journal==[dict(id='01'+'00'*15,state=3)],journal
                begin=time.monotonic_ns();os.kill(pid,signal.SIGKILL)
                self.wait(lambda:self.state and self.state.worker_fault!=0,'worker death surfaced',10)
                fault=self.metrics();self.stop_bridge()
                write(self.run/'crashed.json',dict(injected_worker_pid=pid,injected_ns=begin,device=device,journal=journal,fault=fault,retired=self.crashes[-1]));continue
            elif action=='kill_bridge':
                device=self.device_snapshot();journal=self.journal();report=self.stop_bridge(killed=True)
                write(self.run/'crashed.json',dict(device=device,journal=journal,retired=report))
            elif action=='launch_restart':
                assert self.bridge is None;self.start_bridge()
            elif action=='device':response.update(device=self.device_snapshot(),journal=self.journal())
            elif action=='finish':
                response.update(device=self.device_snapshot(),journal=self.journal(),metrics=self.metrics(),crashes=self.crashes)
                write(self.run/'robot-final.json',response);write(self.run/'robot-reply.json',response);return
            else:raise RuntimeError('unknown crash action')
            write(self.run/'robot-reply.json',response)
    def operator(self):
        self.start_bridge();self.wait(lambda:(self.run/'robot-ready.json').exists(),'robot ready',40)
        self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified,'operator ready',40)
        initial=self.metrics();write(self.run/'operator-ready.json',initial)
        if self.args.case=='before':
            self.wait(lambda:(self.run/'cut-active').exists(),'host packet cut')
            self.submit(1,200,0,1);self.wait(lambda:self.metrics()['commands_sent']==1,'actual SDK handoff')
            proof=self.robot_command('device');assert proof['device']['effects']==0 and proof['journal']==[],proof
            self.robot_command('kill_bridge')
        elif self.args.case=='effect':
            self.robot_command('arm_effect_crash');self.submit(1,200,0,1)
            self.wait(lambda:(self.run/'crashed.json').exists(),'effect crash',20)
        else:
            self.submit(1,200,0,1);s=self.terminal(1,4);assert s['result_valid']
            proof=self.robot_command('device');assert proof['device']['effects']==1 and proof['journal']==[dict(id='01'+'00'*15,state=4)],proof
            self.robot_command('kill_bridge')
        self.robot_command('launch_restart');write(self.run/'restart-launched',{})
        self.wait(lambda:(self.run/'restored').exists(),'network restored')
        old=bytes(initial['session_id'])
        self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified and bytes(self.state.session_id)!=old,'new qualified session',40)
        expected=4 if self.args.case=='committed' else 8;status=None;not_found=False;observations=[]
        end=time.monotonic()+10
        while time.monotonic()<end:
            s=self.status(1);observations.append(dict(ns=time.monotonic_ns(),status=message_to_ordereddict(s)))
            not_found=not_found or s.peer_error==3
            if s.found and s.state==expected and (self.args.case!='before' or (not_found and s.reason==2)):
                status=message_to_ordereddict(s)
            self.spin(.2)
        assert status is not None,observations[-1]
        if expected==8:assert not status['result_valid']
        else:assert status['result_valid'] and status['result_rate_hz']==200 and status['result_generation']==1
        final=self.robot_command('finish');device=final['device'];assert device['effects']==(0 if self.args.case=='before' else 1),device
        assert device['generation']==device['effects'] and self.metrics()['commands_sent']==1
        assert not self.bad and not self.direct
        write(self.run/'operator-result.json',dict(initial=initial,end=self.metrics(),status=status,not_found=not_found,observations=observations,device=device,robot=final,bad=self.bad,direct=self.direct))


def main():
    p=argparse.ArgumentParser();p.add_argument('--role',required=True,choices=('robot','operator'));p.add_argument('--case',required=True,choices=('before','effect','committed'));p.add_argument('--run',required=True);p.add_argument('--peer',required=True);a=p.parse_args()
    a.clock_width_ms=200;a.sample_diagnostics=False;a.command_diagnostics=True;a.provider_diagnostics=False
    rclpy.init();d=Crash(a)
    try:getattr(d,a.role)()
    except BaseException:write(d.run/(a.role+'-failure.json'),dict(traceback=traceback.format_exc()));raise
    finally:
        try:d.cleanup()
        finally:d.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
