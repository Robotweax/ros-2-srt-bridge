"""Offline source/closed-evidence audit; no subprocess, network or workload calls."""
from collections import Counter
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,source_inventory,write
from m3_runtime_layout import matched
OUT=Path(__file__).resolve().parent
CASE='evidence/m3-bridge-shutdown-lifecycle-2026-11-10'
CASES=['m3-shutdown-live-calibration-2026-11-09','m3-bridge-shutdown-diagnostic-2026-11-10','m3-bridge-shutdown-capability-fix-2026-11-10','m3-bridge-shutdown-lifecycle-2026-11-10']
CONDITIONAL={'socket_epoll_remove_begin','socket_close_begin','socket_close_end'}


def main():
    inputs={}
    def read(path):
        p=ROOT/path;inputs[path]=sha(p);return json.loads(p.read_text())
    def lines(path):
        p=ROOT/path;inputs[path]=sha(p);return [json.loads(x) for x in p.read_text().splitlines()]
    freeze=read(CASE+'/freeze.json');run=freeze['output_relative']
    assert source_inventory()==freeze['source_sha256'];assert matched(ROOT,'shutdown-tracing')==freeze['runtime_layout']
    assert all(sha(ROOT/p)==h for p,h in freeze['inputs_sha256'].items())
    indexes=dict(freeze['retained_indexes']);indexes[CASE+'/local-artifact-hashes.json']=sha(ROOT/CASE/'local-artifact-hashes.json')
    checked={}
    for index,digest in indexes.items():
        assert sha(ROOT/index)==digest
        records=read(index)
        assert all(sha(ROOT/p)==v['sha256'] and (ROOT/p).stat().st_size==v['bytes'] for p,v in records.items())
        checked[index]=len(records)
    src='src/robotweax_srt_bridge_core/src/transport/transport.cpp';text=(ROOT/src).read_text();inputs[src]=sha(ROOT/src)
    assert sha(ROOT/src)==freeze['source_sha256'][src]
    original=read('evidence/m3-shutdown-live-calibration-2026-11-09/freeze.json');assert original['source_sha256'][src]==sha(ROOT/src)
    assert 'if(fd!=SRT_INVALID_SOCK)' in text and 'if(stopping.load()||shutting_down)shutdown_stage(config.shutdown_trace,"socket_close_begin",fd);' in text
    table=[];base=None
    for case in CASES:
        for role in ('operator','robot'):
            path='evidence/'+case+'/'+role+'-shutdown-stages.jsonl';rows=lines(path)
            assert sorted(r['sequence'] for r in rows)==list(range(1,len(rows)+1)) and len({r['pid'] for r in rows})==1 and not any(r['dropped_before'] for r in rows)
            common=Counter(r['point'] for r in rows if r['point'] not in CONDITIONAL)
            if base is None:base=common
            assert common==base and sum(common.values())==39
            counts=Counter(r['point'] for r in rows);n=counts['socket_close_begin']
            assert all(counts[p]==n for p in CONDITIONAL) and len(rows)==39+3*n
            table.append(dict(case=case,role=role,records=len(rows),common_records=39,conditional_close_triplets=n,sequence_complete=True,reported_drops=0,closed_fd_details=[r['detail'] for r in rows if r['point']=='socket_close_end']))
    robot=lines(CASE+'/robot-shutdown-stages.jsonl');operator=lines(CASE+'/operator-shutdown-stages.jsonl')
    children={role:read(run+'/'+role+'-child-shutdown.json') for role in ('operator','robot')}
    op=children['operator']['children'][0];rb=next(c for c in children['robot']['children'] if '-bridge-' in c['name']);source=next(c for c in children['robot']['children'] if c['name']=='robot-source')
    op_last=max(r['monotonic_ns'] for r in operator if r['point']=='socket_close_end')
    times=dict(operator_sigint_begin_ns=op['signal_begin_ns'],operator_last_socket_close_end_ns=op_last,robot_source_signal_begin_ns=source['signal_begin_ns'],robot_source_reap_ns=source['end_ns'],robot_bridge_sigint_begin_ns=rb['signal_begin_ns'],robot_transport_shutdown_begin_ns=next(r['monotonic_ns'] for r in robot if r['point']=='transport_shutdown_begin'),robot_control_close_begin_ns=next(r['monotonic_ns'] for r in robot if r['point']=='control_close_begin'),robot_sensor_close_end_ns=next(r['monotonic_ns'] for r in robot if r['point']=='sensor_close_end'))
    assert times['operator_last_socket_close_end_ns']<times['robot_source_reap_ns']<=times['robot_bridge_sigint_begin_ns']<times['robot_transport_shutdown_begin_ns']
    result=read(run+'/result.json');barrier=read(run+'/robot-multiroute-result.json');assert barrier['end']['bridge']['ready'] and barrier['end']['bridge']['control_generation']==barrier['end']['bridge']['sensor_generation']==1
    last_sdk=0;sockets=set()
    log=ROOT/run/'robot-bridge-0.log';inputs[str(log.relative_to(ROOT))]=sha(log)
    for line in log.read_text().splitlines():
        if line.startswith('SAMPLE_TRACE '):
            row=json.loads(line[len('SAMPLE_TRACE '):]);last_sdk=max(last_sdk,row['end_ns'])
            if row['socket']>=0:sockets.add(row['socket'])
    boundaries=dict(last_robot_sample_trace_end_ns=last_sdk,last_robot_ready_barrier_ns=barrier['end']['monotonic_ns'],last_robot_endpoint_sample_end_ns=lines(run+'/robot-endpoint-samples.jsonl')[-1]['end_ns'],measurement_capture_stop_before_ns={role:result['measurement_captures'][role]['status']['stop_before_ns'] for role in ('operator','robot')},sender_sensor_socket_ids=sorted(sockets))
    assert all(v<op['signal_begin_ns'] for v in boundaries['measurement_capture_stop_before_ns'].values())
    assert boundaries['last_robot_endpoint_sample_end_ns']<op['signal_begin_ns']
    for p in ('src/robotweax_srt_bridge_core/src/session.cpp','src/robotweax_srt_bridge_core/include/robotweax/srt_bridge/shutdown_trace.hpp','ros2/robotweax_srt_bridge_demo/scripts/scenario_processes.py','evidence/m3-shutdown-live-calibration-2026-11-09/calibrate.py'):
        inputs[p]=sha(ROOT/p)
    report=dict(status='retained_diagnosis_complete_to_observation_limit',comparison=table,timing=times,peer_last_close_to_robot_sigint_ns=rb['signal_begin_ns']-op_last,observation_boundaries=boundaries,established='Marker gate is unconditional but actual socket-close markers require valid fd AND local stopping/shutting_down. Latest robot executes complete unconditional cleanup with no conditional triplets.',source_supported_inference='Robot caller handles are already invalid when final close_fd runs; caller listener handles were never created. Link slots observed active earlier were invalidated before locally traced shutdown; close_fd is the source path clearing a valid slot after an srt_close attempt. Return values and every handle lifetime are not logged.',not_established=['exact earlier close timestamp and reason','which peer-loss/provider/timer path triggered closure','successful srt_close return/kernel descriptor release','socket leak or original two-loss hang cause'],likely_mechanism='Peer-first shutdown with source-first robot child cleanup gives robot an untraced pre-stop link-loss cleanup interval; timing supports but does not independently prove exact trigger.',historical_failed_gate_preserved=True,new_experiments=0,tuning_changes=0,tests_or_native_builds_run=0,remaining_campaign_cases_disabled=29,retry_two_loss_4211=False,M3_complete=False)
    write(OUT/'report.json',report);write(OUT/'inputs-sha256.json',inputs);write(OUT/'postflight.json',dict(source_and_frozen_inputs_unchanged=True,matched_entries=13,preserved_build_chain_unchanged=True,retained_raw_files_verified=checked,new_experiments=0,remaining_campaign_cases_disabled=29))
    print(json.dumps(dict(analysis='complete',traces_compared=len(table),peer_close_to_robot_sigint_ns=report['peer_last_close_to_robot_sigint_ns'],runtime_changes=0)))

if __name__=='__main__':main()
