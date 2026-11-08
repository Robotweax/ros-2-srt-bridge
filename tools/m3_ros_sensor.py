#!/usr/bin/env python3
"""Finite ROS SENSOR row fault with closed pre-arm identity capture."""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import ipaddress
import json
from pathlib import Path
import secrets
import struct
import subprocess
import time
from m3_network import NetworkLab
from m3_neighbor_diagnostics import configure
from m3_sensor_fault import Selection, install, remove, counters, readback
from m3_capture import pcap_options, stop_captures, validate_tcpdump_footer
from m3_monotonic_capture import start, records, decode, feature_snapshot
from m3_dds_result_timeline import common_clock
from m3_accounting import summarize_window
import m3_sample_trace
from m3_packet_capture import artifact_footer

ROOT=Path(__file__).resolve().parents[1]
# Finite fixture only: CONTROL/probe traffic stays live during the source fence.
# Exclude ongoing keepalive/ACK chatter from the PCAP stability population.
PCAP_FILTER='udp port 10081 and (udp[8] & 128 = 0 or udp[8:2] = 32768)'


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2)+'\n')


def sensor_header(row, address):
    value=decode(row,address)
    if not value or '/sensor_' not in value[0]:
        return None
    f=row['prefix']
    if f[14]!=0x45:
        raise ValueError('only fixed IPv4 IHL qualified')
    sp,dp,length=struct.unpack_from('!HHH',f,34)
    if len(f)<58 or length<24:
        raise ValueError('short SENSOR header')
    seq,msg,_,sid=struct.unpack_from('!IIII',f,42)
    return dict(direction=value[0].split('/')[0],source=str(ipaddress.ip_address(f[26:30])),destination=str(ipaddress.ip_address(f[30:34])),source_port=sp,destination_port=dp,sequence=seq,message_number=msg&0x03ffffff,socket_id=sid,retransmitted=bool(msg&0x04000000),control=bool(seq&0x80000000),monotonic_ns=row['monotonic_ns'])


def captured(path, address):
    status=json.loads((path.parent/(path.stem+'-monotonic-capture.log')).read_text().splitlines()[-1]); rows=list(records(path))
    if not status['complete'] or status.get('artifact_version')!=2 or status['clock']!='kernel_monotonic' or not status['time_namespace_zero'] or not status['records']==status['seen']==status['submitted']==len(rows) or status['reserve_failed'] or status['copy_failed']:
        raise ValueError('incomplete capture')
    for row in rows:
        if row['ifindex']!=status['ifindex'] or row['gso_segs'] not in (0,1) or row['gso_size'] or row['vlan_present'] or row['length']>status['mtu']+14:
            raise ValueError('unsupported frame/interface metadata')
    return status,[(r,sensor_header(r,address)) for r in rows]


def identity_capture(run, addresses):
    status,pairs=captured(run/'robot.mono',addresses['robot'])
    data=[h for _,h in pairs if h and h['direction']=='out' and not h['control']]
    # Fresh fixture, no source publisher before arming: exactly one SENSOR_BIND.
    if len(data)!=1 or data[0]['message_number']!=1 or data[0]['retransmitted'] or not data[0]['socket_id']:
        raise ValueError('requires exactly one pre-arm source binding and no samples/parity')
    binding=data[0]; origins=[]
    for row,h in pairs:
        if not h or h['direction']!='out' or not h['control'] or h['source_port']!=binding['source_port'] or h['destination_port']!=10081:
            continue
        f=row['prefix']
        if struct.unpack_from('!I',f,42)[0]==0x80000000 and len(f)>=106:
            origins.append(struct.unpack_from('!I',f,66)[0])
    if not origins or set(origins)!={binding['sequence']}:
        raise ValueError('handshake origin does not agree with first binding')
    _,other=captured(run/'operator.mono',addresses['operator'])
    received=[h for _,h in other if h and h['direction']=='in' and not h['control']]
    keys=('source','destination','source_port','destination_port','sequence','message_number','socket_id','retransmitted')
    if len(received)!=1 or any(received[0][k]!=binding[k] for k in keys):
        raise ValueError('receiver binding identity differs')
    return dict(binding=binding,initial_sequence=origins[0],origin_evidence='closed same-fixture handshake and exact single binding at both taps; outer headers are routing observations, not cryptographic identity proof',capture_stop_before_ns=status['stop_before_ns'])


def frame_key(frame, flow):
    if len(frame)<58 or frame[12:14]!=b'\x08\x00' or frame[14]!=0x45 or frame[23]!=17:
        return None
    if frame[26:30]!=ipaddress.ip_address(flow['source']).packed or frame[30:34]!=ipaddress.ip_address(flow['destination']).packed or struct.unpack_from('!HH',frame,34)!=(flow['source_port'],flow['destination_port']):
        return None
    seq,msg,_,sid=struct.unpack_from('!IIII',frame,42)
    if seq&0x80000000:
        return None
    return seq,msg&0x03ffffff,sid,bool(msg&0x04000000)


def pcap_count(path, flow):
    count=0; keys=[]
    with path.open('rb') as f:
        h=f.read(24)
        if len(h)!=24 or h[:4]!=b'\xd4\xc3\xb2\xa1' or struct.unpack_from('<I',h,20)[0]!=1:
            raise ValueError('unsupported PCAP')
        while True:
            r=f.read(16)
            if not r:
                break
            if len(r)!=16:
                raise ValueError('short PCAP record')
            _,_,n,original=struct.unpack('<IIII',r)
            if not 14<=n==original<=65535:
                raise ValueError('invalid PCAP size')
            data=f.read(n)
            if len(data)!=n:
                raise ValueError('truncated PCAP')
            count+=1; k=frame_key(data,flow)
            if k is not None:
                keys.append(k)
    return count,Counter(keys)


def validate_capture_populations(path, addresses, identity, losses, phase):
    flow=identity['binding']; origin=identity['initial_sequence']; sid=flow['socket_id']
    excluded=set() if losses==0 else {7} if losses==1 else {6,7}
    expected=Counter([(origin,1,sid,False)]) if phase=='identity' else Counter([((origin+i)&0x7fffffff,i+1,sid,False) for i in range(1,20) if i not in excluded]+[((origin+i)&0x7fffffff,0,sid,False) for i in (3,7,11,15,19)])
    result={}
    for role,address in addresses.items():
        status,pairs=captured(path/(role+'.mono'),address)
        keys=Counter(frame_key(r['prefix'],flow) for r,h in pairs if frame_key(r['prefix'],flow) is not None)
        count,pcaps=pcap_count(path/(role+'.pcap'),flow)
        footer=artifact_footer(path,role,count)
        if keys!=expected or pcaps!=expected or not footer['population_reconciled']:
            raise ValueError('exact '+phase+' DATA/parity population differs')
        result[role]=dict(status=status,footer=footer,known_source_parity_records=sum(keys.values()))
    return result


def outcomes(sender, receiver, losses):
    sent=sender['rows']; seen=receiver['rows']
    missing={5,6} if losses==2 else set()
    if [r['id'] for r in sent]!=list(range(19)) or [r['id'] for r in seen]!=[i for i in range(19) if i not in missing]:
        raise ValueError('finite ROS identity/order population differs')
    hashes={r['id']:r['payload_sha256'] for r in sent}
    if any(r['payload_sha256']!=hashes[r['id']] for r in seen):
        raise ValueError('typed payload digest differs')
    def checkpoint(side):
        a=sender[side];b=receiver[side]
        return dict(sender=a['bridge'],receiver=b['bridge'],device=dict(imu_published=0 if side=='begin' else 19,joints_published=0),observer=dict(imu=0 if side=='begin' else len(seen),joints=0))
    summary=summarize_window(checkpoint('begin'),checkpoint('end'),dict(resume_monotonic_ns=sender['start_ns'],pause_monotonic_ns=sender['stop_ns']))
    if summary['source_produced']!=19 or summary['published']!=19-len(missing) or summary['observer_received']!=19-len(missing) or summary['missing']!=len(missing):
        raise ValueError('ROS stage populations differ')
    nonzero={k:v for k,v in summary['losses'].items() if v}
    if nonzero!=({'srt_accept_to_receiver_gap':2} if losses==2 else {}):
        raise ValueError('unexpected stage loss')
    b=receiver['end']['bridge']
    if b['imu_age_upper_max_ns']>250000000 or b['joint_age_upper_max_ns'] or sender['bad'] or receiver['bad'] or sender['direct'] or receiver['direct']:
        raise ValueError('publication age/session/isolation gate failed')
    for role in (sender,receiver):
        for point in ('begin','end'):
            state=role[point]['bridge']
            if not state['ready'] or not state['clock_qualified'] or not state['sensor_qos_verified']:
                raise ValueError('unqualified endpoint checkpoint')
        if role['begin']['bridge']['session_id']!=role['end']['bridge']['session_id']:
            raise ValueError('session changed')
    if sender['begin']['bridge']['session_id']!=receiver['begin']['bridge']['session_id']:
        raise ValueError('peer sessions differ')
    return dict(window=summary,missing_ids_at_cutoff=sorted(missing),received_ids=[r['id'] for r in seen],typed_payload_hashes_match=True,publication_age_upper_max_ns=b['imu_age_upper_max_ns'])


def diagnostic_window(sender, receiver, losses=0, late_repair=False):
    # Separate traced finite cases; the original strict19-source outcomes gate
    # is unchanged. Preserve BUSY separately from the two-loss transport gap.
    def point(side):
        return dict(sender=sender[side]['bridge'],receiver=receiver[side]['bridge'],device=dict(imu_published=0 if side=='begin' else 19,joints_published=0),observer=dict(imu=0 if side=='begin' else len(receiver['rows']),joints=0))
    window=summarize_window(point('begin'),point('end'),dict(resume_monotonic_ns=sender['start_ns'],pause_monotonic_ns=sender['stop_ns']))
    busy=sender['end']['bridge']['samples_submit_busy']-sender['begin']['bridge']['samples_submit_busy']
    expected_gap=2 if losses==2 else 0
    expected_rejected=1 if late_repair else 0
    if window['source_produced']!=19 or window['published']!=19-busy-expected_gap-expected_rejected or any(v for k,v in window['losses'].items() if k not in ('admission','srt_accept_to_receiver_gap','receiver_rejected')) or window['losses']['admission']!=busy or window['losses']['srt_accept_to_receiver_gap']!=expected_gap or window['losses']['receiver_rejected']!=expected_rejected:
        raise ValueError('trace diagnostic has unexplained stage loss')
    for role in (sender,receiver):
        if role['bad'] or role['direct'] or role['begin']['bridge']['session_id']!=role['end']['bridge']['session_id']:
            raise ValueError('trace diagnostic session/isolation failed')
        for side in ('begin','end'):
            if not all(role[side]['bridge'][k] for k in ('ready','clock_qualified','sensor_qos_verified')):
                raise ValueError('trace diagnostic unqualified endpoint')
    if sender['begin']['bridge']['session_id']!=receiver['begin']['bridge']['session_id']:
        raise ValueError('trace diagnostic peer sessions differ')
    if receiver['end']['bridge']['imu_age_upper_max_ns']>250000000:
        raise ValueError('trace diagnostic age gate failed')
    return window


def selected_sources(mapped, losses, late_repair=False):
    if losses not in (0,1,2):raise ValueError('invalid finite fault count')
    if late_repair and losses!=1:raise ValueError('late repair requires exactly one source loss')
    messages={5} if late_repair else set() if not losses else {8} if losses==1 else {7,8}
    selected=[m for m in mapped if m['message_number'] in messages]
    if len(selected)!=len(messages) or {m['message_number'] for m in selected}!=messages:
        raise ValueError('selected row identities were not each SDK-accepted once')
    if len({m['source_id'] for m in mapped})!=len(mapped):
        raise ValueError('ambiguous admitted source identity')
    absent={m['source_id'] for m in selected} if losses==2 or late_repair else set()
    observed=sorted(m['source_id'] for m in mapped if m['source_id'] not in absent)
    return selected,observed


def repair_horizon(first_successor_ns,parity_ns):
    # Pinned SENSOR repair gaps are marked with20ms deadline. These native
    # arrivals bracket wire observation, not provider processing or physical age.
    elapsed=parity_ns-first_successor_ns
    if first_successor_ns<=0 or not 0<=elapsed<20000000:
        raise ValueError('row parity outside predeclared native20ms gap horizon')
    return elapsed


def verify_late_receiver(mapped,remote,receiver,source_epoch,selected,parity_ns):
    by_message={m['message_number']:m for m in mapped};decisions={}
    state=receiver['begin']['bridge'];session=bytes(state['session_id']).hex();owner=bytes(state['owner_epoch']).hex()
    for e in remote['events']:
        if e['point']!=4:raise ValueError('unexpected late-test receiver trace event')
        m=by_message.get(e['message_number'])
        if not m or e['message_number'] in decisions or e['origin_ns']!=m['origin_ns'] or e['envelope_sequence']!=m['envelope_sequence'] or e['route']!=1 or e['source_epoch']!=source_epoch or e['session']!=session or e['owner_epoch']!=owner or any(e[k]!=state[k] for k in ('control_generation','sensor_generation')):
            raise ValueError('receiver decision/source/context identity mismatch')
        decisions[e['message_number']]=e
    if set(decisions)!=set(by_message) or len(selected)!=1:raise ValueError('receiver decisions incomplete')
    target=selected[0];target_message=target['message_number']
    if target_message!=5 or any(e['result']!=(12 if number==target_message else 0) for number,e in decisions.items()):
        raise ValueError('late source must be rejected specifically as SessionError::replay')
    decision=decisions[target_message]
    if not target['origin_ns']<parity_ns<=decision['end_ns'] or parity_ns-target['origin_ns']>=250000000:
        raise ValueError('repair timing outside predeclared VM interval')
    newer=[r for r in receiver['rows'] if any(m['source_id']==r['id'] and m['message_number'] in (6,7,8) and m['envelope_sequence']>target['envelope_sequence'] for m in mapped) and r['observed_ns']<parity_ns]
    if not newer:raise ValueError('no newer same-row typed publication before repair parity')
    for key in ('transport_samples_unknown_age','transport_samples_stale'):
        if receiver['end']['bridge'][key]!=state[key]:raise ValueError('unexpected clock/stale receiver classification')
    return dict(selected_source=target,receiver_decision=decision,newer_observed_before_parity=[r['id'] for r in newer],parity_incoming_ns=parity_ns,callback_ingress_to_parity_VM_ns=parity_ns-target['origin_ns'],
                scope='direct replay classification before Session age evaluation; actual VM elapsed under250ms is not an evaluated conservative age bound or physical sensor age')


def diagnostic_correlation(run, sender, receiver, identity, addresses, losses=0, late_repair=False):
    trace=m3_sample_trace.summarize(run/'robot-bridge-0.log');joined=m3_sample_trace.correlate(trace)
    remote=m3_sample_trace.summarize(run/'operator-bridge-0.log')
    if joined['queued_without_observed_handoff'] or joined['sdk_errors']:
        raise ValueError('incomplete queued admission/handoff diagnostic')
    sources={(r['stamp_sec'],r['stamp_nanosec']):r for r in sender['rows']}
    if len(sources)!=19:raise ValueError('ambiguous source header timestamps')
    mapped=[];rejected=[]
    for pair in joined['joined']+[{"admission":e} for e in joined['rejected']]:
        a=pair['admission'];source=sources.get((a['stamp_sec'],a['stamp_nanosec']))
        if not source or a['begin_ns']<source['begin_ns'] or a['route']!=1:
            raise ValueError('ROS source/admission identity mismatch')
        if a['session']!=bytes(sender['begin']['bridge']['session_id']).hex() or a['owner_epoch']!=bytes(sender['begin']['bridge']['owner_epoch']).hex():
            raise ValueError('wrong trace owner/session')
        if 'handoff' in pair:
            mapped.append(dict(source_id=source['id'],origin_ns=a['origin_ns'],envelope_sequence=pair['handoff']['envelope_sequence'],message_number=pair['handoff']['message_number'],wire_sequence_candidate=pair['wire_sequence_candidate']))
        else:
            if a['result']!=1:raise ValueError('diagnostic rejected admission is not BUSY')
            rejected.append(source['id'])
    if sorted([m['source_id'] for m in mapped]+rejected)!=list(range(19)) or len(mapped)!=sender['end']['bridge']['sensor_sent'] or len(rejected)!=sender['end']['bridge']['samples_submit_busy']:
        raise ValueError('trace/source/counter reconciliation differs')
    observed=receiver['rows'];hashes={r['id']:r['payload_sha256'] for r in sender['rows']}
    selected,expected_ids=selected_sources(mapped,losses,late_repair)
    if [r['id'] for r in observed]!=expected_ids or any(r['payload_sha256']!=hashes[r['id']] for r in observed):
        raise ValueError('admitted/observed typed payloads differ')
    binding=identity['binding'];origin=identity['initial_sequence'];sdk=[e for e in trace['events'] if e['point']==2]
    if sorted(e['message_number'] for e in sdk)!=list(range(1,len(sdk)+1)) or len(joined['bindings'])!=1 or joined['bindings'][0]['message_number']!=1 or any(e['initial_sequence']!=origin for e in sdk):
        raise ValueError('SDK message/origin/binding identity differs')
    excluded={m['message_number'] for m in selected}
    expected=Counter([((origin+e['message_number']-1)&0x7fffffff,e['message_number'],binding['socket_id'],False) for e in sdk if e['kind']==5 and e['message_number'] not in excluded]+[((origin+i)&0x7fffffff,0,binding['socket_id'],False) for i in range(3,len(sdk),4)])
    captures={}
    for role,address in addresses.items():
        path=run/'measurement';status,pairs=captured(path/(role+'.mono'),address)
        actual=Counter(frame_key(r['prefix'],binding) for r,h in pairs if frame_key(r['prefix'],binding) is not None)
        total,pcaps=pcap_count(path/(role+'.pcap'),binding);footer=artifact_footer(path,role,total)
        if actual!=pcaps or actual!=expected or not footer['population_reconciled']:
            raise ValueError('SDK/native/PCAP source/parity identities differ')
        captures[role]=dict(status=status,footer=footer,source_records=len(mapped)-losses,parity_records=len(sdk)//4)
    late=None
    if late_repair:
        _,incoming=captured(run/'measurement/operator.mono',addresses['operator'])
        parity=((origin+7)&0x7fffffff,0,binding['socket_id'],False)
        times=[row['monotonic_ns'] for row,h in incoming if frame_key(row['prefix'],binding)==parity]
        if len(times)!=1:raise ValueError('late-row parity observation ambiguous')
        successor=((origin+5)&0x7fffffff,6,binding['socket_id'],False)
        first=[row['monotonic_ns'] for row,h in incoming if frame_key(row['prefix'],binding)==successor]
        if len(first)!=1:raise ValueError('first successor observation ambiguous')
        horizon=repair_horizon(first[0],times[0])
        late=verify_late_receiver(mapped,remote,receiver,bytes(sender['begin']['bridge']['owner_epoch']).hex(),selected,times[0])
        late.update(first_successor_incoming_ns=first[0],successor_to_parity_native_ns=horizon)
    return dict(late_repair=late,sender_trace=trace,receiver_trace=remote,mapped=mapped,busy_source_ids=sorted(rejected),selected_sources=selected,expected_observed_ids=expected_ids,captures=captures,
                selected_source_delivery='reconstructed source explicitly rejected as replay after newer publications' if late_repair else 'all selected IDs observed after absent wire source' if losses==1 else 'selected IDs absent at finite cutoff' if losses==2 else 'no injected loss',
                qualification=False,scope='finite traced ROS case; actual SDK identity to selected source and typed publication, with independent BUSY retained; not replacement baseline, physical delivery or full N3/M3 acceptance')


def capture_start(lab,path,backend='tcpdump'):
    if backend not in ('tcpdump','packet-socket'):raise ValueError('unknown capture backend')
    path.mkdir();lab.run=path;inside='/workspace/'+str(path.relative_to(ROOT));result=[]
    try:
        if backend=='packet-socket':start(path,inside,lab,result)
        for role,name in lab.containers.items():
            log=(path/(role+'-capture.log')).open('w')
            argv=pcap_options()+['-w',inside+'/'+role+'.pcap',PCAP_FILTER] if backend=='tcpdump' else [
                'python3','tools/m3_packet_capture.py','--output',inside+'/'+role+'.pcap',
                '--ready',inside+'/'+role+'-packet-ready.json','--stop',inside+'/'+role+'-packet-stop',
                '--status',inside+'/'+role+'-packet-status.json','--filter',PCAP_FILTER]
            result.append((subprocess.Popen(['docker','exec',name]+argv,stdout=log,stderr=subprocess.STDOUT),log))
        if backend=='tcpdump':start(path,inside,lab,result)
        deadline=time.monotonic()+5
        def ready():
            return all((path/(r+'-packet-ready.json')).exists() for r in lab.containers) if backend=='packet-socket' else all('listening on eth0' in (path/(r+'-capture.log')).read_text() for r in lab.containers)
        while not ready():
            if any(p.poll() is not None for p,_ in result) or time.monotonic()>deadline:raise ValueError('capture readiness failed')
            time.sleep(.05)
        return result
    except Exception:
        # Startup failures also retain handles for bounded owned cleanup.
        for role in lab.containers:(path/(role+'-packet-stop')).touch()
        try:stop_captures(lab)
        except Exception:pass
        for p,log in result:
            try:p.wait(timeout=6)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
            log.close()
        raise


def capture_stop(lab,processes):
    packet=all((lab.run/(r+'-packet-ready.json')).exists() for r in lab.containers)
    errors=[]
    if packet:
        for role in lab.containers:(lab.run/(role+'-packet-stop')).touch()
        # Packet mode starts the two native observers first. Keep them attached
        # until both PCAP sockets have closed, preserving coverage of that phase.
        for p,log in processes[2:]:
            try:
                if p.wait(timeout=7)!=0:errors.append('packet recorder failed')
            except subprocess.TimeoutExpired:errors.append('packet recorder stop timeout')
    try:stop_captures(lab,drain_check=not packet and not (lab.run/'capture-drain.json').exists())
    except Exception as error:errors.append(str(error))
    for p,log in processes:
        try:
            if p.wait(timeout=5)!=0:errors.append('capture exited unsuccessfully')
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5);errors.append('capture exit timeout')
        if not log.closed:log.close()
    if errors:raise ValueError('; '.join(errors))


def wait_files(run,names,peers):
    end=time.monotonic()+45
    while not all((run/n).exists() for n in names):
        if any(p.poll() is not None for p,_ in peers) or time.monotonic()>end:
            raise ValueError('ROS phase barrier failed: '+','.join(names))
        time.sleep(.05)


def run_case(run,image,losses,trace_diagnostic=False,trace_loss=False,capture_backend='tcpdump',late_repair=False,sample_period_ms=50):
    if sample_period_ms not in (5,50):raise ValueError('unsupported finite source period')
    traced=trace_diagnostic or trace_loss or late_repair
    run.mkdir(); inside='/workspace/'+str(run.relative_to(ROOT));lab=NetworkLab(ROOT,run,image,monotonic_capture=True)
    captures=[];peers=[];fault=None;key=run/'passphrase';key.touch(mode=0o600);key.write_text(secrets.token_urlsafe(32))
    result=dict(status='running',losses=losses,trace_diagnostic=trace_diagnostic,trace_loss=trace_loss,late_repair=late_repair,sample_period_ms=sample_period_ms,capture_backend=capture_backend,pcap_filter=PCAP_FILTER,qualification=False,scope='finite IMU at requested'+str(1000/sample_period_ms)+'Hz, explicit permanent-neighbor fixture, two separate closed capture phases; not full200/50Hz N3 matrix or CONTROL/M3 acceptance')
    try:
        lab.start(key);result['clock_proof']={r:lab.inside(r,r+'-clock-proof',['sh','-c','cat /proc/sys/kernel/random/boot_id; cat /proc/self/timens_offsets']) for r in lab.containers};common_clock(result['clock_proof'])
        configure(lab,'permanent');lab.apply('N0',1701);result['features_before']=feature_snapshot(lab,'features-before')
        captures=capture_start(lab,run/'identity',capture_backend)
        for role,name in lab.containers.items():
            log=(run/(role+'-scenario.log')).open('w')
            command='source /opt/ros/jazzy/setup.bash; source install/m3-ros/setup.bash; exec python3 ros2/robotweax_srt_bridge_demo/scripts/m3_ros_sensor_scenario.py --role '+role+' --run '+inside+' --peer '+lab.addresses['operator']+(' --sample-diagnostics' if traced else '')+' --sample-period-ms '+str(sample_period_ms)
            peers.append((subprocess.Popen(['docker','exec',name,'bash','-c',command],stdout=log,stderr=subprocess.STDOUT),log))
        wait_files(run,[r+'-finite-ready.json' for r in lab.containers],peers)
        capture_stop(lab,captures);captures=[]
        identity=identity_capture(run/'identity',lab.addresses);result['identity']=identity
        result['identity_captures']=validate_capture_populations(run/'identity',lab.addresses,identity,0,'identity')
        captures=capture_start(lab,run/'measurement',capture_backend)
        if losses:
            binding=identity['binding']; selection=Selection(identity['initial_sequence'],1,(0,) if late_repair else (3,) if losses==1 else (2,3),(5,) if late_repair else (8,) if losses==1 else (7,8),binding['socket_id'],binding['source_port'],binding['destination_port'])
            result['selection']=asdict(selection);fault=install(lab,selection);result['fault']=fault
        (run/'armed').touch()
        wait_files(run,[r+'-finite-result.json' for r in lab.containers],peers)
        if fault:
            result['final_counters']=counters(readback(lab,'sensor-fault-final'),losses)
            if any(c['drops']!=1 for c in result['final_counters']):
                raise ValueError('exact selected drop count differs')
            remove(lab,fault)
        sender=json.loads((run/'robot-finite-result.json').read_text());receiver=json.loads((run/'operator-finite-result.json').read_text())
        result['outcome']=dict(diagnostic_window=diagnostic_window(sender,receiver,losses,late_repair)) if traced else outcomes(sender,receiver,losses)
        capture_stop(lab,captures);captures=[]
        if not traced:result['measurement_captures']=validate_capture_populations(run/'measurement',lab.addresses,identity,losses,'measurement')
        result['features_after']=feature_snapshot(lab,'features-after')
        if result['features_after']!=result['features_before']:
            raise ValueError('interface features changed')
        (run/'release').touch()
        for p,log in peers:
            if p.wait(timeout=8)!=0:
                raise ValueError('ROS scenario exit failed')
            log.close()
        if traced:result['sample_correlation']=diagnostic_correlation(run,sender,receiver,identity,lab.addresses,losses,late_repair)
        result['status']='passed'
    except Exception as error:
        result.update(status='failed',error=str(error));raise
    finally:
        if fault and not fault['restored']:
            try:remove(lab,fault)
            except Exception as error:result['cleanup_error']=str(error)
        if captures:
            try:capture_stop(lab,captures)
            except Exception as error:result['capture_stop_error']=str(error)
        (run/'release').touch()
        if result['status']!='passed':(run/'abort').touch()
        for p,log in peers:
            try:p.wait(timeout=8)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
            if not log.closed:log.close()
        lab.run=run;lab.cleanup();key.unlink(missing_ok=True);write(run/'result.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);modes=p.add_mutually_exclusive_group();modes.add_argument('--trace-diagnostic',action='store_true',help='one observer validation with explicit BUSY accounting; no injected-loss cohort');modes.add_argument('--trace-losses',action='store_true',help='one/two finite row faults using actual SDK source identities; independent BUSY retained');modes.add_argument('--trace-late-repair',action='store_true',help='one first-position source loss; require explicit receiver replay rejection after newer publication');p.add_argument('--capture-backend',choices=('tcpdump','packet-socket'),default='tcpdump');p.add_argument('--trace-loss-count',type=int,choices=(1,2),help='explicit separately planned traced fault only');p.add_argument('--sample-period-ms',type=int,choices=(5,50),default=50);a=p.parse_args();
    if a.trace_late_repair and a.sample_period_ms!=5:p.error('late repair requires --sample-period-ms 5; observed parity must also fit the pinned20ms gap horizon')
    if a.trace_loss_count is not None and not a.trace_losses:p.error('--trace-loss-count requires --trace-losses')
    run=a.out.resolve();run.mkdir(parents=True,exist_ok=False)
    image=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64','ros2-srt-m3:20261105'],text=True))[0]['RepoDigests'][0];result=dict(status='running',image=image,cases=[])
    try:
        for losses in ((0,) if a.trace_diagnostic else (1,) if a.trace_late_repair else (a.trace_loss_count,) if a.trace_loss_count is not None else (1,2) if a.trace_losses else (0,1,2)):result['cases'].append(run_case(run/str(losses),image,losses,a.trace_diagnostic,a.trace_losses,a.capture_backend,a.trace_late_repair,a.sample_period_ms))
        result['status']='passed'
    except Exception as error:result.update(status='failed',error=str(error));raise
    finally:write(run/'result.json',result)
