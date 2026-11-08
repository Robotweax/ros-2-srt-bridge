#!/usr/bin/env python3
"""One sustained multiroute preflight; optional closed captures and one row fault."""
import argparse
import json
from pathlib import Path
import secrets
import shlex
import subprocess
from m3_network import NetworkLab, SEEDS
from m3_neighbor_diagnostics import configure
from m3_dds_result_timeline import common_clock
from m3_ros_sensor import wait_files, capture_start, capture_stop, identity_capture, validate_capture_populations
from m3_monotonic_capture import feature_snapshot
from m3_sensor_fault import Selection, install, remove, counters, readback
from m3_multiroute_capture import verify_captures, verify_recovery, verify_two_loss
from m3_source_preflight import ROOT, IMAGE, sha, write
from m3_source_trace import summarize as source_trace
from m3_sample_trace import summarize as sample_trace
from m3_multiroute_accounting import assess


def run(out,capture=False,losses=0,seed=1701):
    if type(losses) is not int or losses not in (0,1,2) or (losses and not capture):raise ValueError("source faults require independent capture")
    if type(seed) is not int or seed not in SEEDS:raise ValueError("predeclared base seed required")
    selected_numbers=() if not losses else (8,) if losses==1 else (7,8)
    out.mkdir(parents=True,exist_ok=False);inside='/workspace/'+str(out.relative_to(ROOT))
    paths=['install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo/rate_simulator','install/m3-ros/robotweax_srt_bridge/lib/robotweax_srt_bridge/bridge_node','install/bridge-m3/lib/librobotweax_srt_bridge_transport.a','install/bridge-m3/lib/librobotweax_srt_bridge_endpoint.a','install/srt-m0/lib/librobotweax-srt.a']
    if capture:paths += ['build/m3-monotonic-capture/monotonic_capture','build/m3-netdev-features/netdev_features']
    inventory={p:sha(ROOT/p) for p in paths}
    write(out/'provenance.json',dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,runtime_sha256=inventory,seconds=10,sample_diagnostics=True,source_diagnostics=True,capture=capture,losses=losses,base_seed=seed))
    lab=NetworkLab(ROOT,out,IMAGE,monotonic_capture=capture);peers=[];captures=[];fault=None;key=out/'passphrase';key.touch(mode=0o600);key.write_text(secrets.token_urlsafe(32));result=dict(status='running',qualification=False,capture=capture,losses=losses,base_seed=seed,scope='ten-second source/accounting fixture; no full seeded N3/M3, physical age or resource qualification')
    try:
        lab.start(key)
        result['clock_proof']={r:lab.inside(r,r+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for r in lab.containers};common_clock(result['clock_proof'])
        configure(lab,'permanent');lab.apply('N0',seed)
        if capture:
            result['features_before']=feature_snapshot(lab,'features-before')
            captures=capture_start(lab,out/'identity','packet-socket')
        for role,name in lab.containers.items():
            log=(out/(role+'-scenario.log')).open('w')
            command='source /opt/ros/jazzy/setup.bash && source install/m3-ros/setup.bash && exec python3 ros2/robotweax_srt_bridge_demo/scripts/m3_ros_multiroute_scenario.py --role '+role+' --run '+shlex.quote(inside)+' --peer '+lab.addresses['operator']
            peers.append((subprocess.Popen(['docker','exec',name,'bash','-c',command],stdout=log,stderr=subprocess.STDOUT),log))
        wait_files(out,[r+'-multiroute-ready.json' for r in lab.containers],peers)
        if capture:
            capture_stop(lab,captures);captures=[]
            result['identity']=identity_capture(out/'identity',lab.addresses)
            result['identity_captures']=validate_capture_populations(out/'identity',lab.addresses,result['identity'],0,'identity')
            captures=capture_start(lab,out/'measurement','packet-socket')
            if losses:
                binding=result['identity']['binding']
                selection=Selection(result['identity']['initial_sequence'],1,tuple(n-5 for n in selected_numbers),selected_numbers,binding['socket_id'],binding['source_port'],binding['destination_port'])
                fault=install(lab,selection);result['fault']=fault
                if any(c['packets'] or c['drops'] for c in fault['initial_counters']):raise ValueError('nonzero initial selected-source counters')
        (out/'armed').touch()
        wait_files(out,[r+'-multiroute-result.json' for r in lab.containers],peers)
        if capture:
            if fault:
                result['final_counters']=counters(readback(lab,'sensor-fault-final'),losses)
                if any(c['drops']!=1 for c in result['final_counters']):raise ValueError('selected sources not each dropped exactly once')
                # Both result barriers include the selected typed observation if
                # present. Keep the classifier installed through those barriers.
                remove(lab,fault)
            capture_stop(lab,captures);captures=[];lab.run=out
            result['features_after']=feature_snapshot(lab,'features-after')
            if result['features_after']!=result['features_before']:raise ValueError('interface features changed')
        (out/'release').touch()
        for p,log in peers:
            if p.wait(timeout=25)!=0:raise ValueError('multiroute scenario exit failed; inspect child-shutdown/scenario logs')
            log.close()
        result['child_shutdown']={role:json.loads((out/(role+'-child-shutdown.json')).read_text()) for role in lab.containers}
        if not all(report['passed'] for report in result['child_shutdown'].values()):raise ValueError('unqualified child shutdown')
        if {p:sha(ROOT/p) for p in paths}!=inventory:raise ValueError('runtime changed during measurement')
        sender=json.loads((out/'robot-multiroute-result.json').read_text());receiver=json.loads((out/'operator-multiroute-result.json').read_text())
        source=source_trace(out/'robot-source.log');local=sample_trace(out/'robot-bridge-0.log');remote=sample_trace(out/'operator-bridge-0.log')
        result['assessment']=assess(source,sender,receiver,local,remote)
        if capture:
            result['measurement_captures']=verify_captures(out/'measurement',lab.addresses,result['identity'],local['events'],sender['resume']['monotonic_ns'],sender['pause']['monotonic_ns'],selected_numbers)
            result['assessment']['scope']='ten-second source/accounting fixture with independently reconciled capture identities; aggregate loss stages only, no full N3/M3 or physical-age qualification'
            if losses==2:
                result['two_loss']=verify_two_loss(source,local,remote,receiver,result['identity'],result['measurement_captures']['operator']['selected_parity_ns'],max(item['end_ns'] for item in fault['install']),fault['remove']['begin_ns'])
                if result['assessment']['sdk_without_receiver_decision']!=[7,8] or result['assessment']['window']['losses']['srt_accept_to_receiver_gap']!=2:raise ValueError('two-loss accounting gap mismatch')
            elif losses==1:result['recovery']=verify_recovery(source,local,remote,receiver,result['identity'],result['measurement_captures']['operator']['selected_parity_ns'],fault['install'][0]['end_ns'],fault['remove']['begin_ns'])
        result['status']='passed' if result['assessment']['passed'] else 'failed'
        if result['status']=='failed':result['error']='measured source cadence outside predeclared tolerance'
    except Exception as error:result.update(status='failed',error=str(error))
    finally:
        if fault and not fault['restored']:
            try:remove(lab,fault)
            except Exception as error:result.update(status='failed',cleanup_error=str(error))
        if captures:
            try:capture_stop(lab,captures)
            except Exception as error:result.update(status='failed',capture_stop_error=str(error))
        lab.run=out
        (out/'release').touch()
        if result['status']!='passed':(out/'abort').touch()
        for p,log in peers:
            try:p.wait(timeout=25)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
            if not log.closed:log.close()
        try:lab.cleanup()
        finally:key.unlink(missing_ok=True);write(out/'result.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);p.add_argument('--capture',action='store_true');p.add_argument('--losses',type=int,choices=(0,1,2),default=0);p.add_argument('--seed',type=int,choices=SEEDS,default=1701);a=p.parse_args();result=run(a.output.resolve(),a.capture,a.losses,a.seed);print(json.dumps(dict(status=result['status'],error=result.get('error'),assessment=result.get('assessment',{}).get('window')),indent=2));raise SystemExit(result['status']!='passed')
