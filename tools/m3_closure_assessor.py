#!/usr/bin/env python3
"""Strict closed-case assessor and stop controller; no live runner/dispatcher."""
import argparse
import json
from pathlib import Path
from m3_source_preflight import IMAGE,write
from m3_multiroute_window import verify_window
from m3_multiroute_accounting import assess as assess_multiroute
from m3_multiroute_capture import verify_captures,verify_recovery,verify_two_loss
from m3_ros_sensor import identity_capture,validate_capture_populations
from m3_n5_sensor_audit import assess_publications
from m3_n5_progress import command_progress
from m3_dds_result_timeline import common_clock,read_journal
from m3_n4 import check_outcome,DIRECTIONS
from m3_n4_ros import check_crash
from m3_n4_sensor_check import assess as assess_freshness
from m3_source_trace import summarize as source_trace
from m3_sample_trace import summarize as sample_trace


def require(value,message):
    if not value:raise ValueError(message)


def cleanup(run):
    data=json.loads((run/'network.json').read_text())
    for label in ('operator-remove','robot-remove','network-remove'):
        rows=[r for r in data['commands'] if r['label']==label]
        require(len(rows)==1 and rows[0]['exit_code']==0,'owned cleanup incomplete: '+label)
    require(not (run/'passphrase').exists(),'fixture credential retained')


def provenance(record,freeze):
    require(freeze.get('schema_version')==1,'missing assessor freeze schema')
    layout=record.get('runtime_layout');require(layout==freeze['runtime_layout'],'case runtime differs from frozen candidate')
    require(layout.get('name')=='sender-reconcile','closure requires sender-reconcile candidate')
    require(layout.get('matched_build_sha256') and layout.get('calibration_sha256')==freeze['candidate_manifest_sha256'],'incomplete candidate binding')
    require(record.get('image_reference',record.get('image'))==IMAGE,'case image differs')
    actual=record.get('source_sha256',{});expected=freeze.get('source_sha256',{})
    require(expected and actual,'missing frozen source evidence')
    require(all(actual.get(p)==h for p,h in expected.items()),'source bytes differ from freeze')


def assess_n3_result(result,slot):
    require(result['status']=='passed','N3 inner harness failed')
    require(result['seconds']==slot['source_seconds'] and result['base_seed']==slot['seed'] and result['losses']==slot['losses'],'N3 slot differs')
    a=result['assessment'];verify_window(a,slot['source_seconds'],slot['losses'])
    require(a['passed'] and all(r['cadence_pass'] for r in a['cadence']['routes'].values()),'source cadence failed')
    require(not any(a['window']['balances'].values()),'unbalanced N3 counters')
    require(set(a['window']['age_upper_histograms'])=={'imu','joint'},'missing route histogram')
    for route in a['window']['age_upper_histograms'].values():require(route['count']>0 and 0<=route['maximum_ms']<=250,'missing/stale N3 publications')
    for key in ('source_trace_status','sender_trace_status','receiver_trace_status'):
        s=a[key];require(not s.get('dropped',0) and not s.get('exhausted',0),'N3 trace dropped/exhausted')
        require(s['attempted']>0,'N3 trace unavailable')
    source=a['source_trace_status'];require(source.get('complete') is True and source['attempted']==source['recorded']==source['printed'],'N3 source footer incomplete')
    for phase in ('identity_captures','measurement_captures'):
        require(set(result[phase])=={'operator','robot'},'missing capture peer')
        for capture in result[phase].values():
            s=capture['status'];f=capture['footer']
            require(s['complete'] and s['records']==s['seen']==s['submitted'] and not s['reserve_failed'] and not s['copy_failed'],'native capture incomplete')
            require(f['population_reconciled'] and f['file_integrity_valid'] and not f['kernel_drops'] and f['captured_records']==f['filtered_records'],'PCAP population incomplete')
    require(set(result['child_shutdown'])=={'operator','robot'} and all(r['passed'] for r in result['child_shutdown'].values()),'N3 child shutdown incomplete')
    if slot['losses']:
        require(result['fault']['restored'] and len(result['final_counters'])==slot['losses'] and all(c['drops']==1 and c['packets']==1 for c in result['final_counters']),'N3 fault/restoration evidence incomplete')
        if slot['losses']==1:require(result.get('recovery',{}).get('message_number')==8,'one-loss repair proof missing')
        else:require({s['message_number'] for s in result.get('two_loss',{}).get('selected_sources',[])}=={7,8},'two-loss source proof missing')
    return dict(gate='N3_strict_window_and_recorded_capture',window=a['window'])


def validate_n3_artifacts(run,result,slot):
    """Reuse the original raw source/SDK/packet/fault validators after peers close."""
    common_clock(result['clock_proof'])
    load=lambda name:json.loads((run/name).read_text())
    sender=load('robot-multiroute-result.json');receiver=load('operator-multiroute-result.json')
    source=source_trace(run/'robot-source.log');local=sample_trace(run/'robot-bridge-0.log');remote=sample_trace(run/'operator-bridge-0.log')
    computed=assess_multiroute(source,sender,receiver,local,remote)
    require({k:v for k,v in computed.items() if k!='scope'}=={k:v for k,v in result['assessment'].items() if k!='scope'},'N3 raw accounting differs')
    addresses=load('network.json')['addresses'];identity=identity_capture(run/'identity',addresses)
    require(identity==result['identity'],'N3 handshake identity differs')
    require(validate_capture_populations(run/'identity',addresses,identity,0,'identity')==result['identity_captures'],'N3 identity capture differs')
    selected=() if slot['losses']==0 else (8,) if slot['losses']==1 else (7,8)
    capture=verify_captures(run/'measurement',addresses,identity,local['events'],sender['resume']['monotonic_ns'],sender['pause']['monotonic_ns'],selected)
    require(capture==result['measurement_captures'],'N3 measurement capture differs')
    if selected:
        install=max(x['end_ns'] for x in result['fault']['install']);remove=result['fault']['remove']['begin_ns'];parity=capture['operator']['selected_parity_ns']
        check=verify_recovery if slot['losses']==1 else verify_two_loss
        proof=check(source,local,remote,receiver,identity,parity,install,remove)
        require(proof==result['recovery' if slot['losses']==1 else 'two_loss'],'N3 selected-source outcome differs')


def assess_combined(report,run,slot):
    require(report['status']=='passed','combined inner harness failed')
    require(report['profile']==slot['profile'] and report['seed']==slot['seed'] and report['seconds']==slot['source_seconds'],'combined slot differs')
    require('dds_transport_profile' not in report,'DDS is not an SRT candidate case')
    require(report.get('pcap_population_reconciled') is True and set(report['captures'])=={'operator','robot'},'combined capture incomplete')
    for c in report['captures'].values():require(c['tcpdump_population_reconciled'] and c['tcpdump_file_integrity_valid'] and not c['tcpdump_kernel_drops'],'combined PCAP gate failed')
    require(report.get('monotonic_captures') and set(report['monotonic_captures']['statuses'])=={'operator','robot'},'native captures missing')
    for s in report['monotonic_captures']['statuses'].values():require(s['complete'] and s['artifact_version']==2 and s['clock']=='kernel_monotonic' and s['time_namespace_zero'] and s['records']==s['seen']==s['submitted'] and not s['reserve_failed'] and not s['copy_failed'],'combined native capture gate failed')
    result=report['results'];require(not result['typed_errors'] and result['direct_dds_samples']==0,'typed/isolation error')
    common_clock(report['clock_namespace_proof'])
    sensor=assess_publications(result['checkpoints']['begin'],result['checkpoints']['end'],result['publication_interval'])
    require(sensor['window']==report['measurement_window'],'recomputed SENSOR window differs')
    require(all(r['nonempty'] for r in sensor['publication_age'].values()),'empty sensor population')
    for route,target in (('imu',200),('joints',50)):require(abs(sensor['window']['source_actual_hz'][route]/target-1)<=.01,'combined source cadence failed')
    for key in ('provider_diagnostics','sensor_provider_diagnostics'):
        rows=report.get(key,{})
        require(rows and all(s['complete'] and not s['status']['dropped'] and not s['status']['exhausted'] for s in rows.values()),'provider observer incomplete')
    require(slot['source_seconds']<=sensor['window']['source_enabled_seconds']<=slot['source_seconds']+1,'combined source duration differs')
    interval=result['publication_interval'];bounds=[interval['resume_monotonic_ns'],interval['pause_monotonic_ns']]
    windows=report['monotonic_captures']['windows']['source_enabled']
    require(set(windows)=={'operator','robot'},'combined source capture peer missing')
    for role,window in windows.items():
        status=report['monotonic_captures']['statuses'][role]
        require(status['ready_ns']<=bounds[0]<bounds[1]<=status['stop_before_ns'] and window['qualified'] and window['window_monotonic_ns']==bounds and window['frame_interpretation']['qualified'],'combined source capture window unqualified')
    progress=command_progress(report,run)
    require(progress['entries'] and progress['no_unresolved_attempts'],'strict command progress failed; inner safety PASS cannot advance')
    child_reports=[result['shutdowns'],json.loads((Path(run)/'robot-final.json').read_text())['shutdowns']]
    require(len(child_reports[0])>=1 and len(child_reports[1])>=2 and all(s['exit_code']==0 and 0<=s['seconds']<=5 for group in child_reports for s in group),'combined child shutdown incomplete')
    if slot['profile']=='N5':require(report['competitor_check']['target_bitrate']==128000 and report['competitor_check']['alive_poll_checks']>0,'N5 competing load missing')
    return dict(gate='combined_strict_success',progress=progress,sensor=sensor)


def assess_outage(result,direction,interval_key,counters_key):
    roles=set(DIRECTIONS[direction])
    for key in ('outage_install','outage_restore',counters_key):
        require(set(result[key])==roles,'N4 outage direction evidence differs')
    for key,loss in (('outage_install',1),('outage_restore',0)):
        for role,event in result[key].items():
            q=event['qdisc'];b=event['bracket']
            require(0<b['begin_ns']<=b['end_ns'],'N4 invalid change bracket')
            require(q['kind']=='netem' and q['options']['seed']==(1702 if role=='operator' else 1701) and q['options'].get('loss-random',{}).get('loss',0)==loss,'N4 kernel loss/seed differs')
    interval=[max(v['bracket']['end_ns'] for v in result['outage_install'].values()),min(v['bracket']['begin_ns'] for v in result['outage_restore'].values())]
    require(result[interval_key]==interval and interval[1]-interval[0]>=2_000_000_000,'N4 outage interval differs/short')
    h=result['hold'];require(interval[0]<=h['begin_ns']<=h['end_ns']<=interval[1] and h['end_ns']-h['begin_ns']>=2_000_000_000,'N4 hold outside guaranteed outage')
    for qs in result[counters_key].values():
        netem=[q for q in qs if q['kind']=='netem']
        require(len(netem)==1 and netem[0]['drops']>0,'N4 outage matched no traffic')


def assess_native_n4(result,run,slot,record,freeze):
    require(result['status']=='passed' and result['phase']==slot['phase'] and result['direction']==slot['direction'] and result['hold_seconds']==slot['hold_seconds']==2,'native N4 slot/hold differs')
    binding=record.get('fixture_binding')
    require(binding and binding.get('schema_version')==1 and binding==freeze.get('native_fixture_binding'),'native fixture build binding missing or differs from freeze')
    require(binding['sdk']==record['runtime_layout']['sdk'] and binding['worker']==binding['sdk']+'/bin/robotweax-journal-worker','fixture worker prefix differs')
    require(all(binding['files'].get(p)==h for p,h in record['runtime_layout']['matched_build_sha256'].items() if p.startswith(binding['sdk']+'/')),'fixture linked SDK differs from candidate')
    assess_outage(result,slot['direction'],'guaranteed_outage_ns','outage_final')
    a=read_journal(run/'operator.sqlite',1);b=read_journal(run/'robot.sqlite',2)
    load=lambda name:json.loads((run/name).read_text())
    sender=load('operator-result.json');receiver=load('robot-result.json')
    proof=check_outcome('committed' if slot['phase']=='query' else slot['phase'],sender,receiver,a,b,result['barrier']['snapshot'],load('resumed.json'),result['barrier']['visible_journal'],{r:load(r+'-ready.json') for r in ('operator','robot')},load('submitted.json'))
    require(proof==result['outcome'],'native N4 durable outcome differs')
    require(result['guaranteed_outage_ns'][1]-result['guaranteed_outage_ns'][0]>=2_000_000_000,'N4 outage short')
    for role,stopped in result['stopped'].items():
        require(role in ('operator','robot') and not stopped['dropped'] and stopped['trace_records']==stopped['trace_attempted'] and 0<stopped['stop_end_ns']-stopped['stop_begin_ns']<5_000_000_000 and not stopped['snapshot']['running'] and not stopped['snapshot']['transport_running'],'native N4 shutdown incomplete')
    require(set(result['stopped'])=={'operator','robot'},'missing native stopped peer')
    if slot['phase']=='query':require(sender['queries_sent']>0 and proof['state']==4,'QUERY retrieval not established')
    return dict(gate='N4_phase_specific_not_all_success',outcome=proof)


def assess_case(run,slot,freeze):
    run=Path(run);combined=slot['stage'] in ('N0','LONG')
    report=json.loads((run/('run.json' if combined else 'result.json')).read_text())
    record=report if combined else json.loads((run/'provenance.json').read_text())
    provenance(record,freeze)
    if combined:proof=assess_combined(report,run,slot)
    elif slot['stage']=='N3':
        proof=assess_n3_result(report,slot)
        validate_n3_artifacts(run,report,slot)
    else:
        require(slot['stage']=='N4' and report['status']=='passed','N4 inner harness failed')
        common_clock(report['clock_proof'])
        if 'phase' in report:proof=assess_native_n4(report,run,slot,record,freeze)
        else:
            require(report['mode']==slot.get('direction',slot.get('phase')),'ROS N4 mode differs')
            require(set(report['shutdown'])=={'operator','robot'} and all(s['passed'] for s in report['shutdown'].values()),'ROS N4 shutdown incomplete')
            if slot['id'].startswith('N4-ROS-crash-'):proof=check_crash(run,slot['phase']);require(proof==report['crash'],'ROS crash audit differs')
            else:
                assess_outage(report,slot['direction'],'outage_ns','drop_readback')
                require(report['restored_ns']==max(v['bracket']['end_ns'] for v in report['outage_restore'].values()),'ROS restoration bound differs')
                load=lambda name:json.loads((run/name).read_text())
                proof=assess_freshness(source_trace(run/'robot-source.log'),load('robot-fresh-result.json'),load('operator-fresh-result.json'),sample_trace(run/'robot-bridge-0.log',allow_inactive_admissions=True),sample_trace(run/'operator-bridge-0.log'),report['outage_ns'],report['restored_ns'],slot['direction'])
                require(proof==report['freshness'],'ROS freshness audit differs')
    cleanup(run)
    return dict(status='passed',proof=proof,cleanup='recorded_owned_removal_complete')


def evaluate_sequence(slots,produce,assessor,record):
    """Caller-supplied callbacks only; no process launching or authorization here."""
    rows=[];failed=False
    for slot in slots:
        row=dict(slot=slot,status='not_executed')
        if failed:row['reason']='previous declared gate failed; no retry'
        else:
            try:
                produced=produce(slot);row['produced']=produced
                assessed=assessor(slot,produced)
                require(assessed['status']=='passed','strict assessor refused case')
                row.update(status='passed',assessment=assessed)
            except Exception as error:row.update(status='failed',error=str(error));failed=True
        rows.append(row);record(dict(status='failed' if failed else 'running',rows=rows,complete_M3_acceptance=False))
    result=dict(status='failed' if failed else 'passed',rows=rows,complete_M3_acceptance=False);record(result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True,type=Path);p.add_argument('--slot',required=True,type=Path);p.add_argument('--freeze',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    if a.out.exists():p.error('output already exists')
    result=assess_case(a.run,json.loads(a.slot.read_text()),json.loads(a.freeze.read_text()));write(a.out,result)


if __name__=='__main__':main()
