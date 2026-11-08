#!/usr/bin/env python3
"""Linux owned-process negative controls using the real bridge and packet recorder."""
import argparse
import json
from pathlib import Path
import resource
import signal
import socket
import struct
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'ros2/robotweax_srt_bridge_demo/scripts'))
from scenario_processes import stop_children
from m3_sample_trace import summarize
from m3_packet_capture import artifact_footer


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def until(predicate,seconds=10):
    end=time.monotonic()+seconds
    while not predicate():
        if time.monotonic()>end:raise TimeoutError('negative-control readiness timeout')
        time.sleep(.01)


def bridge_case(root,case,index):
    import rclpy
    from rclpy.node import Node
    from rclpy.context import Context
    from robotweax_srt_bridge_msgs.srv import GetBridgeMetrics
    out=root/case;out.mkdir();log=(out/'bridge.log').open('w');wlog=(out/'witness.log').open('w')
    bridge=None;witness=None;node=None;executor=None;context=Context()
    report={}
    try:
        rclpy.init(context=context,domain_id=90+index);node=Node('failure_observer',context=context)
        executor=rclpy.executors.SingleThreadedExecutor(context=context);executor.add_node(node)
        env=dict(__import__('os').environ,ROS_DOMAIN_ID=str(90+index))
        bridge=subprocess.Popen([str(ROOT/'install/m3-ros/robotweax_srt_bridge/lib/robotweax_srt_bridge/bridge_node'),'--ros-args','-p','role:=listener','-p','address:=0.0.0.0','-p','credential_file:=/run/bridge/passphrase','-p','journal_path:='+str(out/'journal.sqlite'),'-p','sample_diagnostics:=true'],stdout=log,stderr=subprocess.STDOUT,env=env)
        resource.prlimit(bridge.pid,resource.RLIMIT_CORE,(0,0))
        client=node.create_client(GetBridgeMetrics,'/bridge/get_metrics')
        if not client.wait_for_service(timeout_sec=10):raise TimeoutError('real bridge metrics service unavailable')
        future=client.call_async(GetBridgeMetrics.Request());executor.spin_until_future_complete(future,timeout_sec=10)
        if not future.done() or future.result().snapshot.worker_fault:raise RuntimeError('real bridge did not initialize cleanly')
        witness=subprocess.Popen([sys.executable,'-u','-c',"import signal,time,sys;signal.signal(signal.SIGINT,lambda *_:sys.exit(0));print('ready',flush=True);time.sleep(60)"],stdout=wlog,stderr=subprocess.STDOUT)
        until(lambda:'ready' in (out/'witness.log').read_text())
        injected=time.monotonic_ns()
        if case=='aborted':bridge.send_signal(signal.SIGABRT);bridge.wait(timeout=5)
        elif case=='killed':bridge.kill();bridge.wait(timeout=5)
        elif case=='preexited':bridge.send_signal(signal.SIGINT);bridge.wait(timeout=5)
        elif case=='stalled':
            bridge.send_signal(signal.SIGSTOP)
            until(lambda:Path('/proc/'+str(bridge.pid)+'/stat').read_text().split(') ')[1].startswith('T'))
        report=stop_children([(witness,'witness',wlog),(bridge,'bridge',log)],wait_seconds=.3 if case=='stalled' else 5)
        b=report['children'][0];w=report['children'][1]
        expected=case in ('clean','missing-footer')
        if report['passed']!=expected or not w['passed']:raise ValueError('failure classification/witness cleanup mismatch')
        if case=='aborted' and b['returncode']!=-signal.SIGABRT:raise ValueError('abort signal not recorded')
        if case=='killed' and b['returncode']!=-signal.SIGKILL:raise ValueError('kill signal not recorded')
        if case=='preexited' and b['initial_returncode']!=0:raise ValueError('premature clean exit not detected')
        if case=='stalled' and (not b['forced_kill'] or b['returncode']!=-signal.SIGKILL):raise ValueError('stalled child not bounded/killed')
        trace_path=out/'bridge.log'
        if case=='missing-footer':
            original=summarize(trace_path)
            if original['status']['attempted']:raise ValueError('unexpected standalone source trace events')
            trace_path=out/'footer-removed-copy.log';trace_path.write_text('\n'.join(l for l in (out/'bridge.log').read_text().splitlines() if not l.startswith('SAMPLE_TRACE_STATUS '))+'\n')
        try:summarize(trace_path);complete=True
        except ValueError:complete=False
        if complete!=(case in ('clean','preexited')):raise ValueError('actual trace completeness classification mismatch')
        report.update(status='passed',case=case,expected_negative=case!='clean',trace_complete=complete,injected_ns=injected,scope='known deliberate negative/control classification; not diagnosis of historical missing footer; real bridge without peer/workload')
    except Exception as error:
        report.update(status='failed',case=case,error=str(error));raise
    finally:
        for p,f in ((bridge,log),(witness,wlog)):
            if p and p.poll() is None:p.kill();p.wait(timeout=5)
            if not f.closed:f.close()
        if executor:executor.shutdown()
        if node:node.destroy_node()
        if context.ok():rclpy.shutdown(context=context)
        write(out/'result.json',report)
    return report


def record_count(path):
    with path.open('rb') as f:
        if len(f.read(24))!=24:raise ValueError('missing PCAP header')
        n=0
        while True:
            h=f.read(16)
            if not h:return n
            if len(h)!=16:raise ValueError('truncated PCAP record')
            _,_,size,original=struct.unpack('<IIII',h)
            if size!=original or len(f.read(size))!=size:raise ValueError('truncated PCAP packet')
            n+=1


def recorder_case(root,case,peer):
    out=root/case;out.mkdir();log=(out/'recorder.log').open('w');p=None;report={}
    try:
        p=subprocess.Popen([sys.executable,'tools/m3_packet_capture.py','--output',str(out/'probe.pcap'),'--ready',str(out/'probe-packet-ready.json'),'--stop',str(out/'stop'),'--status',str(out/'probe-packet-status.json'),'--filter','udp and src port 39001 and dst port 10081'],stdout=log,stderr=subprocess.STDOUT)
        until(lambda:(out/'probe-packet-ready.json').exists() or p.poll() is not None)
        if p.poll() is not None:raise RuntimeError('recorder exited before injection')
        injected=time.monotonic_ns()
        if case=='recorder-killed':p.kill()
        else:
            if case=='recorder-write-limit':resource.prlimit(p.pid,resource.RLIMIT_FSIZE,(64,64))
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
                sock.bind(('0.0.0.0',39001))
                for n in range(6):sock.sendto(b'failure-detection-'+bytes([n])+b'.'*100,(peer,10081))
            time.sleep(.2);(out/'stop').touch()
        code=p.wait(timeout=8);log.close()
        try:
            count=record_count(out/'probe.pcap');footer=artifact_footer(out,'probe',count);accepted=True
        except (ValueError,OSError,json.JSONDecodeError) as error:count=None;footer=dict(error=str(error));accepted=False
        if case=='recorder-clean':
            if code or not accepted or count!=6:raise ValueError('positive recorder control failed')
        elif code==0 or accepted:raise ValueError('failed recorder accepted as complete')
        report=dict(status='passed',case=case,expected_negative=case!='recorder-clean',injected_ns=injected,recorder_exit=code,accepted=accepted,records=count,footer=footer,scope='real killed/write-limited recorder rejected; known six synthetic UDP sends, no SRT delivery claim')
    except Exception as error:
        report.update(status='failed',case=case,error=str(error));raise
    finally:
        if p and p.poll() is None:p.kill();p.wait(timeout=5)
        if not log.closed:log.close()
        write(out/'result.json',report)
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--peer',required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False);rows=[]
    try:
        for i,case in enumerate(('clean','aborted','killed','preexited','stalled','missing-footer')):rows.append(bridge_case(a.output,case,i))
        for case in ('recorder-clean','recorder-killed','recorder-write-limit'):rows.append(recorder_case(a.output,case,a.peer))
    finally:write(a.output/'result.json',dict(cases=rows,passed=len(rows)==9 and all(r['status']=='passed' for r in rows)))


if __name__=='__main__':main()
