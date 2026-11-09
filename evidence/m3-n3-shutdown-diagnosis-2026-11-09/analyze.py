"""Retained-file/source diagnosis only. No process, fixture or campaign launch."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write
from m3_campaign_dispatcher import verify_freeze
from m3_monotonic_capture import records
from m3_dds_result_timeline import common_clock

out=Path(__file__).resolve().parent
cohort=ROOT/'evidence/m3-n3-frozen-cohort-2026-11-09'
manifest=json.loads((cohort/'local-artifact-hashes.json').read_text())
assert len(manifest)==913 and all(sha(ROOT/p)==r['sha256'] for p,r in manifest.items())
freeze=ROOT/'evidence/m3-dispatcher-fixture-validation-2026-11-09/campaign-freeze.json'
verify_freeze(json.loads(freeze.read_text()))
base=ROOT/json.loads((cohort/'preflight.json').read_text())['output_relative']
campaign=json.loads((base/'campaign.json').read_text());assert campaign['all_later_stages_disabled'] and len(campaign['disabled_case_ids'])==29
rows=[];inputs={}
def load(p):
    inputs[str(p.relative_to(ROOT))]=sha(p)
    return json.loads(p.read_text())
for case in campaign['rows']:
    slot=case['slot'];run=base/slot['id'];result=load(run/'result.json');common_clock(result['clock_proof'])
    child=load(run/'operator-child-shutdown.json')['children'][0];signal=child['signal_begin_ns']
    log=run/'operator-bridge-0.log';inputs[str(log.relative_to(ROOT))]=sha(log)
    lines=log.read_text().splitlines()
    samples=[json.loads(line[len('SAMPLE_TRACE '):]) for line in lines if line.startswith('SAMPLE_TRACE ')]
    footers=[json.loads(line[len('SAMPLE_TRACE_STATUS '):]) for line in lines if line.startswith('SAMPLE_TRACE_STATUS ')]
    assert [r['sequence'] for r in samples]==list(range(1,len(samples)+1))
    ep_path=run/'operator-endpoint-samples.jsonl';inputs[str(ep_path.relative_to(ROOT))]=sha(ep_path)
    ep=[json.loads(line) for line in ep_path.read_text().splitlines()]
    assert all(r['end_ns']<signal for r in ep)
    metrics=load(run/'operator-multiroute-result.json')['end']
    captured=[]
    for role in ('operator','robot'):
        path=run/'measurement'/(role+'.mono');inputs[str(path.relative_to(ROOT))]=sha(path)
        packets=list(records(path));latest=max(r['monotonic_ns'] for r in packets)
        assert latest<signal
        status_path=run/'measurement'/(role+'-monotonic-capture.log');inputs[str(status_path.relative_to(ROOT))]=sha(status_path)
        status=json.loads(status_path.read_text());assert status['complete'] and status['records']==len(packets)
        captured.append(dict(role=role,records=len(packets),last_packet_ns=latest,signal_minus_last_packet_ns=signal-latest,stop_before_ns=status['stop_before_ns']))
    row=dict(case=slot['id'],strict_status=case['status'],operator_child=child,
        signal_to_reap_ns=child['end_ns']-signal,
        observed_sample_records=len(samples),last_sample_event_ns=samples[-1]['end_ns'],signal_minus_last_sample_event_ns=signal-samples[-1]['end_ns'],sample_footer=footers,
        last_process_sample_end_ns=ep[-1]['end_ns'],signal_minus_last_process_sample_ns=signal-ep[-1]['end_ns'],process_samples_during_shutdown=0,
        last_process_sample=ep[-1],end_metrics=dict(monotonic_ns=metrics['monotonic_ns'],bridge={k:metrics['bridge'][k] for k in ('ready','clock_qualified','fault','worker_fault','commands_sent','sensor_ingress_pending','sensor_outbound_pending','sensor_receive_pending')}),measurement_captures=captured,
        command_trace_lines=sum(line.startswith('COMMAND_TRACE ') for line in lines))
    if case['status']=='passed':assert child['passed'] and len(footers)==1 and footers[0]['attempted']==len(samples) and footers[0]['dropped']==0
    else:assert slot['id']=='N3-two-loss-4211' and child['forced_kill'] and child['returncode']==-9 and not footers
    rows.append(row)
failed=rows[-1];b=failed['end_metrics']['bridge'];assert b['ready'] and b['clock_qualified'] and b['fault']==b['worker_fault']==b['commands_sent']==0
assert all(b[k]==0 for k in ('sensor_ingress_pending','sensor_outbound_pending','sensor_receive_pending'))
clean=[r['signal_to_reap_ns'] for r in rows[:-1]]
sources={}
for name,needles in {
 'ros2/robotweax_srt_bridge/src/bridge_node.cpp':['~BridgeNode()','int main(','worker.executable=worker_path','const auto key=credential'],
 'ros2/robotweax_srt_bridge_demo/scripts/scenario_processes.py':['def stop_children','process.wait(timeout=wait_seconds)','process.kill()'],
 'ros2/robotweax_srt_bridge_demo/scripts/m3_scenario.py':['def spin(','self.endpoint_sampler.tick(roots)'],
 'ros2/robotweax_srt_bridge_demo/scripts/m3_ros_multiroute_scenario.py':['def cleanup(','report=stop_children'],
 'tools/m3_ros_multiroute.py':['capture_stop(lab,captures);','if p.wait(timeout=25)!=0'],
 'src/robotweax_srt_bridge_transport/endpoint.cpp':['void run()noexcept','if(worker){worker->request_stop()','transport.join();','void CommandEndpoint::join()'],
 'src/robotweax_srt_bridge_core/src/worker/supervisor.cpp':['void stop()noexcept','bool join()','const auto kill_at=','JournalWorker::~JournalWorker'],
 'src/robotweax_srt_bridge_core/src/transport/transport.cpp':['~Provider()','Provider provider;','void close_fd(','shutting_down=true;','void TransportOwner::join()'],
}.items():
    p=ROOT/name;lines=p.read_text().splitlines();sources[name]=dict(sha256=sha(p),anchors={needle:[i for i,line in enumerate(lines,1) if needle in line] for needle in needles})
    assert all(sources[name]['anchors'].values()),name
write(out/'assessment.json',dict(status='diagnosed_to_observation_limit',root_cause='undetermined',
    proven_failure='operator bridge did not reap during existing5s SIGINT wait; parent forced kill/-9',
    current_cohort_status='failed_8_strict_passes_1_child_shutdown_failure',
    candidate_manifest_sha256='929d1f7c7727b6c9ba363762074557873d0ffeb6ed6a2b4ab75957d341ee0fc7',
    clean_operator_shutdown_ns=dict(minimum=min(clean),maximum=max(clean)),failed_signal_to_reap_ns=failed['signal_to_reap_ns'],
    observation_gap=dict(process_sampler='scenario-spin driven; stops before synchronous stop_children, not an independent teardown sampler',packets='all native records precede operator SIGINT; recorders stopped before release',lifecycle_trace='command diagnostics disabled; no handler/spin/destructor/join stage markers or thread stacks'),
    failure_path=dict(operator_worker='plain SDK journal worker, not ROS rate worker',footer='absent; normally emitted after endpoint join and trace drain, before member destruction',localization='no proof SIGINT handler/destructor entered; cannot select ROS executor, worker join, transport join/socket-close/provider cleanup or trace drain from retained data'),
    unsupported_causes=['ROS rate backend shutdown on operator','selected two-source loss as causal proof','source-rate/queue/buffer/clock tuning needed','post-signal CPU starvation/OOM exclusion from pre-signal counters','provider global cleanup proven cause','native worker4s join as unconditional total bridge shutdown bound'],
    no_runtime_changes=True,no_tuning=True,no_retry=True,new_experiments=0,remaining_stage_cases_disabled=29,M3_complete=False,rows=rows))
write(out/'input-hashes.json',dict(original_local_manifest_sha256=sha(cohort/'local-artifact-hashes.json'),original_local_files_verified=len(manifest),frozen_campaign_sha256=sha(freeze),selected_inputs=inputs,source_anchors=sources))
print('Retained913 raw files and original freeze verified; shutdown cause cannot be uniquely located without post-signal stage/stack evidence.')
