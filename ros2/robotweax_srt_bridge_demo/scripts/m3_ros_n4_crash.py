#!/usr/bin/env python3
"""One command and persistent external simulator across an explicitly injected crash."""
import argparse
import json
import os
from pathlib import Path
import signal
import time
import traceback
import rclpy
from rosidl_runtime_py.convert import message_to_ordereddict
from robotweax_srt_bridge_msgs.srv import SetPublishing,GetBridgeMetrics
from m3_scenario import Benchmark,write
from m2_scenario import read
from scenario_processes import stop_children
from scenario_journal import visible_entries,copied_entries


class Crash(Benchmark):
    def __init__(self,args):super().__init__(args);self.crashes=[]
    def bridge_state(self,m):
        super().bridge_state(m)
        with (self.run/(self.args.role+'-contexts.jsonl')).open('a') as out:
            out.write(json.dumps(dict(ns=time.monotonic_ns(),owner=bytes(m.owner_epoch).hex(),session=bytes(m.session_id).hex(),ready=m.ready,clock=m.clock_qualified,fault=m.fault,worker_fault=m.worker_fault,commands_sent=m.commands_sent))+'\n')

    def cleanup(self):
        report=stop_children([p for p in self.processes if p[0] not in self.retired])
        self.resources.close();self.endpoint_sampler.close();write(self.run/(self.args.role+'-shutdown.json'),report)
        if not report['passed']:raise RuntimeError('unplanned child shutdown failure')
    def device_snapshot(self):
        return message_to_ordereddict(self.rpc(self.publishing_client,SetPublishing.Request(enabled=False)).snapshot)
    def metrics(self):return message_to_ordereddict(self.rpc(self.metric_client,GetBridgeMetrics.Request()).snapshot)
    def stop_bridge(self,killed=False):
        p=self.bridge;item=next(i for i in self.processes if i[0] is p);before=p.poll();assert before is None
        worker=self.worker_pid();begin=time.monotonic_ns()
        if killed:p.kill();code=p.wait(timeout=5);assert code==-signal.SIGKILL;item[2].close();report=dict(injected='SIGKILL',exit=code,begin_ns=begin,end_ns=time.monotonic_ns(),pid=p.pid)
        else:
            report=stop_children([item]);assert report['passed']
        if killed and worker:
            def gone():
                stat=Path('/proc/'+str(worker)+'/stat')
                return not stat.exists() or stat.read_text().split(') ')[1][0]=='Z'
            deadline=time.monotonic()+5
            while not gone():
                if time.monotonic()>=deadline:raise RuntimeError('owned worker still running after killed bridge')
                time.sleep(.01)
            report.update(old_worker_pid=worker,old_worker_gone_or_zombie_ns=time.monotonic_ns())
        self.retired.add(p);self.bridge=None;self.crashes.append(report);return report
    def journal(self):return visible_entries(self.run/'robot.sqlite')
    def robot(self):
        self.sim=self.start('rate_simulator','robot-source',dict(publishing_enabled='false',response_delay_ms=2500 if self.args.case=='effect' else 0))
        self.wait(lambda:self.device is not None,'external device');self.start_bridge()
        self.wait(lambda:self.state and self.state.ready and self.state.clock_qualified,'ready',40)
        write(self.run/'robot-ready.json',dict(owner=bytes(self.state.owner_epoch).hex(),session=bytes(self.state.session_id).hex(),device=self.device_snapshot()))
        sequence=0
        while True:
            self.spin(.02);self.check_processes()
            if (self.run/'release').exists():raise RuntimeError('host aborted crash fixture')
            if self.bridge and self.state and self.state.worker_fault:raise RuntimeError('unexpected receiver worker fault '+str(self.state.worker_fault))
            q=read(self.run/'control.json')
            if q.get('sequence',0)<=sequence:continue
            sequence=q['sequence'];action=q['action'];response=dict(sequence=sequence,ok=True)
            if action=='arm_effect_crash':
                write(self.run/'robot-reply.json',response)
                self.wait(lambda:self.device and self.device.effects==1,'observed external effect before worker crash')
                pid=self.worker_pid();assert pid;device=self.device_snapshot()
                os.kill(pid,signal.SIGSTOP);end=time.monotonic()+1
                while Path('/proc/'+str(pid)+'/stat').read_text().split(') ')[1][0]!='T':
                    if time.monotonic()>end:raise RuntimeError('owned worker did not stop for journal snapshot')
                    time.sleep(.002)
                assert self.worker_pid()==pid
                journal=copied_entries(self.run/'robot.sqlite',self.run/'prekill-journal-copy');assert journal==[dict(id='01'+'00'*15,state=3)],journal
                begin=time.monotonic_ns();os.kill(pid,signal.SIGKILL)
                self.wait(lambda:self.state and self.state.worker_fault!=0,'worker death surfaced',10)
                fault=self.metrics();self.stop_bridge()
                write(self.run/'crashed.json',dict(injected_worker_pid=pid,injected_ns=begin,device=device,journal=journal,fault=fault,retired=self.crashes[-1]));continue
            elif action=='kill_bridge':
                device=self.device_snapshot();report=self.stop_bridge(killed=True);journal=self.journal()
                write(self.run/'crashed.json',dict(device=device,journal=journal,retired=report))
            elif action=='launch_restart':
                assert self.bridge is None;old_owner=bytes(self.state.owner_epoch) if self.state else b'';self.start_bridge()
                self.wait(lambda:self.state and bytes(self.state.owner_epoch)!=old_owner,'new receiver owner observed',10)
                response.update(restarted=self.metrics())
                if response['restarted']['worker_fault']:raise RuntimeError('restarted worker failed '+str(response['restarted']['worker_fault']))
            elif action=='device':response.update(device=self.device_snapshot())
            elif action=='finish':
                response.update(device=self.device_snapshot(),metrics=self.metrics(),crashes=self.crashes)
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
            proof=self.robot_command('device');assert proof['device']['effects']==0,proof
            self.robot_command('kill_bridge')
        elif self.args.case=='effect':
            self.robot_command('arm_effect_crash');self.submit(1,200,0,1)
            self.wait(lambda:(self.run/'crashed.json').exists(),'effect crash',20)
        else:
            self.submit(1,200,0,1);s=self.terminal(1,4);assert s['result_valid']
            proof=self.robot_command('device');assert proof['device']['effects']==1,proof
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
        write(self.run/'operator-observations.json',dict(status=status,not_found=not_found,observations=observations))
        assert status is not None,observations[-1]
        if expected==8:assert not status['result_valid']
        else:assert status['result_valid'] and status['result_rate_hz']==200 and status['result_generation']==1
        final=self.robot_command('finish');device=final['device'];assert device['effects']==(0 if self.args.case=='before' else 1),device
        assert device['generation']==device['effects'] and self.metrics()['commands_sent']==1
        assert not self.bad and not self.direct
        write(self.run/'operator-result.json',dict(initial=initial,end=self.metrics(),status=status,not_found=not_found,observations=observations,device=device,robot=final,bad=self.bad,direct=self.direct))


def main():
    p=argparse.ArgumentParser();p.add_argument('--role',required=True,choices=('robot','operator'));p.add_argument('--case',required=True,choices=('before','effect','committed'));p.add_argument('--run',required=True);p.add_argument('--peer',required=True);p.add_argument('--ros-install',choices=('install/m3-ros','install/m3-start-trace-ros','install/m3-sender-visibility-ros','install/m3-probe-tracing-ros','install/m3-sender-reconcile-ros'),default='install/m3-ros');a=p.parse_args()
    a.clock_width_ms=200;a.sample_diagnostics=False;a.command_diagnostics=True;a.provider_diagnostics=False
    rclpy.init();d=Crash(a)
    try:getattr(d,a.role)()
    except BaseException:write(d.run/(a.role+'-failure.json'),dict(traceback=traceback.format_exc()));raise
    finally:
        try:d.cleanup()
        finally:d.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
