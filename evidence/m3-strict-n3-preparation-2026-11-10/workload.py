"""Frozen strict nine-case N3 copy of the existing SENSOR host adapter with sidecar release gate.

No dispatcher. Fixed guard admits only the nine predeclared seed/loss cases, with no other stage.
"""
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
from m3_multiroute_capture import verify_captures,verify_two_loss,verify_recovery
from m3_sensor_fault import Selection,install,remove,counters,readback
from m3_source_preflight import ROOT, IMAGE, sha, write, source_inventory
from m3_source_trace import summarize as source_trace
from m3_sample_trace import summarize as sample_trace
from m3_multiroute_accounting import assess
from m3_multiroute_window import budget, verify_window
from disposition_runtime import matched


from sidecar import Sidecar

def selection_for(identity,losses):
    if type(losses) is not int or losses not in (0,1,2):raise ValueError('invalid N3 loss count')
    if not losses:return None
    messages=(8,) if losses==1 else (7,8)
    binding=identity['binding']
    return Selection(identity['initial_sequence'],1,tuple(n-5 for n in messages),messages,binding['socket_id'],binding['source_port'],binding['destination_port'])


def run(out,capture=False,losses=2,seed=4211,seconds=30,runtime_layout='baseline',shutdown_diagnostics=False,shutdown_stacks=False,shutdown_stack_mode='procfs',*,bundle,prefix):
    if type(seed) is not int or type(losses) is not int or seed not in (1701,2903,4211) or losses not in (0,1,2) or (capture,seconds,runtime_layout,shutdown_diagnostics,shutdown_stacks,shutdown_stack_mode)!=(True,30,'socket-disposition',True,False,'procfs'):raise ValueError('only fixed nine-case N3/30s capture+trace scope allowed')
    observer=Sidecar(out,bundle,prefix)
    if shutdown_stack_mode not in ('procfs','gdb') or (shutdown_stack_mode!='procfs' and not shutdown_stacks):raise ValueError('GDB requires explicit shutdown stack observer')
    layout=matched(ROOT,runtime_layout)
    limits=budget(seconds)
    if type(losses) is not int or losses not in (0,1,2) or (losses and not capture):raise ValueError("source faults require independent capture")
    if type(seed) is not int or seed not in SEEDS:raise ValueError("predeclared base seed required")
    selected_numbers=() if losses==0 else (8,) if losses==1 else (7,8)
    out.mkdir(parents=True,exist_ok=False);inside='/workspace/'+str(out.relative_to(ROOT))
    paths=['install/m3-ros/robotweax_srt_bridge_demo/lib/robotweax_srt_bridge_demo/rate_simulator','install/m3-ros/robotweax_srt_bridge/lib/robotweax_srt_bridge/bridge_node','install/bridge-m3/lib/librobotweax_srt_bridge_transport.a','install/bridge-m3/lib/librobotweax_srt_bridge_endpoint.a','install/srt-m0/lib/librobotweax-srt.a']
    if runtime_layout!='baseline':
        paths=[p.replace('install/m3-ros/',layout['ros']+'/',1).replace('install/bridge-m3/',layout['sdk']+'/',1) for p in paths]
        paths+=layout['runtime_paths'][:-1]
    if capture:paths += ['build/m3-monotonic-capture/monotonic_capture','build/m3-netdev-features/netdev_features']
    inventory={p:sha(ROOT/p) for p in paths}
    write(out/'provenance.json',dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),image=IMAGE,source_sha256=source_inventory(ROOT),runtime_sha256=inventory,runtime_layout=layout,seconds=seconds,window_budget=limits,sample_diagnostics=True,source_diagnostics=True,shutdown_diagnostics=shutdown_diagnostics,shutdown_stacks=shutdown_stacks,shutdown_stack_mode=shutdown_stack_mode,capture=capture,losses=losses,base_seed=seed))
    lab=NetworkLab(ROOT,out,IMAGE,monotonic_capture=capture);peers=[];captures=[];fault=None;key=out/'passphrase';key.touch(mode=0o600);key.write_text(secrets.token_urlsafe(32));result=dict(status='running',qualification=False,capture=capture,losses=losses,base_seed=seed,seconds=seconds,scope='bounded source/accounting fixture; no full seeded N3/M3, physical age or resource qualification')
    try:
        lab.start(key)
        for role in lab.containers:
            prefix=lab.inside(role,role+'-selected-ros-prefix',['bash','-c','source /opt/ros/jazzy/setup.bash && source '+shlex.quote(layout['ros']+'/setup.bash')+' && ros2 pkg prefix robotweax_srt_bridge']).strip()
            if prefix!='/workspace/'+layout['ros']+'/robotweax_srt_bridge':raise ValueError('selected ROS prefix mismatch')
        result['clock_proof']={r:lab.inside(r,r+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for r in lab.containers};common_clock(result['clock_proof'])
        configure(lab,'permanent');lab.apply('N0',seed)
        if capture:
            result['features_before']=feature_snapshot(lab,'features-before')
            captures=capture_start(lab,out/'identity','packet-socket')
        for role,name in lab.containers.items():
            log=(out/(role+'-scenario.log')).open('w')
            command='source /opt/ros/jazzy/setup.bash && source '+shlex.quote(layout['ros']+'/setup.bash')+' && exec python3 evidence/m3-strict-n3-preparation-2026-11-10/scenario.py --role '+role+' --run '+shlex.quote(inside)+' --peer '+lab.addresses['operator']+' --seconds '+str(seconds)+' --ros-install '+shlex.quote(layout['ros'])
            command+=(' --shutdown-diagnostics' if shutdown_diagnostics else '')+(' --shutdown-stacks --shutdown-stack-mode '+shutdown_stack_mode if shutdown_stacks else '')
            peers.append((subprocess.Popen(['docker','exec',name,'bash','-c',command],stdout=log,stderr=subprocess.STDOUT),log))
        wait_files(out,[r+'-multiroute-ready.json' for r in lab.containers],peers)
        if capture:
            capture_stop(lab,captures);captures=[]
            result['identity']=identity_capture(out/'identity',lab.addresses)
            result['identity_captures']=validate_capture_populations(out/'identity',lab.addresses,result['identity'],0,'identity')
            captures=capture_start(lab,out/'measurement','packet-socket')
        if losses:
            selection=selection_for(result['identity'],losses)
            fault=install(lab,selection);result['fault']=fault
            if any(c['packets'] or c['drops'] for c in fault['initial_counters']):raise ValueError('nonzero initial selected-source counters')
        (out/'armed').touch()
        wait_files(out,[r+'-multiroute-result.json' for r in lab.containers],peers,timeout=seconds+35)
        if capture:
            if fault:
                result['final_counters']=counters(readback(lab,'sensor-fault-final'),losses)
                if any(c['drops']!=1 for c in result['final_counters']):raise ValueError('selected sources not each dropped exactly once')
                remove(lab,fault)
            capture_stop(lab,captures);captures=[];lab.run=out
            result['features_after']=feature_snapshot(lab,'features-after')
            if result['features_after']!=result['features_before']:raise ValueError('interface features changed')
        observer.arm(lab)
        (out/'release').touch()
        for p,log in peers:
            if p.wait(timeout=25)!=0:raise ValueError('multiroute scenario exit failed; inspect child-shutdown/scenario logs')
            log.close()
        observer.close()
        result['child_shutdown']={role:json.loads((out/(role+'-child-shutdown.json')).read_text()) for role in lab.containers}
        if not all(report['passed'] for report in result['child_shutdown'].values()):raise ValueError('unqualified child shutdown')
        if {p:sha(ROOT/p) for p in paths}!=inventory:raise ValueError('runtime changed during measurement')
        sender=json.loads((out/'robot-multiroute-result.json').read_text());receiver=json.loads((out/'operator-multiroute-result.json').read_text())
        source=source_trace(out/'robot-source.log');local=sample_trace(out/'robot-bridge-0.log');remote=sample_trace(out/'operator-bridge-0.log')
        result['assessment']=assess(source,sender,receiver,local,remote)
        result['window_budget']=verify_window(result['assessment'],seconds,losses)
        if capture:
            result['measurement_captures']=verify_captures(out/'measurement',lab.addresses,result['identity'],local['events'],sender['resume']['monotonic_ns'],sender['pause']['monotonic_ns'],selected_numbers)
            result['assessment']['scope']='bounded source/accounting fixture with independently reconciled capture identities; aggregate loss stages only, no full N3/M3 or physical-age qualification'
        if losses:
            parity=result['measurement_captures']['operator']['selected_parity_ns']
            installed=max(item['end_ns'] for item in fault['install']);removed=fault['remove']['begin_ns']
            if losses==1:result['recovery']=verify_recovery(source,local,remote,receiver,result['identity'],parity,installed,removed)
            else:
                result['two_loss']=verify_two_loss(source,local,remote,receiver,result['identity'],parity,installed,removed)
                if result['assessment']['sdk_without_receiver_decision']!=[7,8] or result['assessment']['window']['losses']['srt_accept_to_receiver_gap']!=2:raise ValueError('two-loss accounting gap mismatch')
        if matched(ROOT,runtime_layout)!=layout:raise ValueError('matched runtime chain changed during measurement')
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
            except subprocess.TimeoutExpired:
                p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill();p.wait(timeout=5)
                result.update(status='failed',scenario_cleanup_forced=True)
            except Exception as error:result.update(status='failed',scenario_cleanup_error=str(error))
            finally:
                if not log.closed:log.close()
        try:
            observer.close()
        except Exception as error:result.update(status='failed',observer_cleanup_error=str(error))
        try:lab.cleanup()
        finally:key.unlink(missing_ok=True);write(out/'result.json',result)
    return result
