#!/usr/bin/env python3
"""Closed-run CONTROL counter/tap correlation; never historical-cause authority."""
import argparse
import json
from pathlib import Path
from m3_control_liveness import digest,parse_control,FLOW_FIELDS
from m3_control_fault_analysis import baseline,connection,inside_deltas,ARCHIVE
from m3_command_trace import summarize_run as summarize_commands
from m3_provider_stats import summarize_run
from m3_dds_result_timeline import common_clock
from m3_monotonic_capture import records


def same_flow(row,flow):return all(row[k]==flow[k] for k in FLOW_FIELDS if k!='direction')


def correlate(flow,before,after,sender,peer,stats,captured):
    result=dict(flow=flow,window_ns=[before,after],classification='mapping_withheld')
    try:
        selected={}
        for role in (sender,peer):
            name,row=baseline({k:v for k,v in stats.items() if k.startswith(role+'-')},before)
            selected[role]=(name,row)
        a=selected[sender][1];b=selected[peer][1]
        if b['socket']!=flow['destination_socket_id']:raise ValueError('receiver socket mismatch')
        if a['session']!=b['session'] or a['session']=='00'*16:raise ValueError('session association unavailable')
        reverse=[r for r in captured[sender] if before-2000000000<=r['monotonic_ns']<=before and r['direction']=='in'
                 and r['source']==flow['destination'] and r['destination']==flow['source']
                 and r['source_port']==flow['destination_port'] and r['destination_port']==flow['source_port']
                 and r['destination_socket_id']==a['socket']]
        if not reverse:raise ValueError('reverse tuple/socket association unavailable')
        deltas=inside_deltas(stats[selected[sender][0]]['records'],connection(a),before+1,after)
        outgoing=sum(same_flow(r,flow) and before<r['monotonic_ns']<after for r in captured[sender])
        incoming=sum(same_flow(r,flow) and before<r['monotonic_ns']<after for r in captured[peer])
        increased=any(deltas['totals'][k]>0 for k in ('data_sent','ack_sent','nak_sent'))
        if not deltas['adjacent_pairs']:category='insufficient_available_provider_pairs'
        elif outgoing:category='old_flow_egress_present_in_interval'
        elif increased:category='selected_send_counters_increased_without_old_flow_egress_observation'
        else:category='selected_send_counters_flat_not_udp_absence_proof'
        result.update(classification=category,sender_process=selected[sender][0],sender_identity=list(connection(a)),
                      receiver_process=selected[peer][0],receiver_identity=list(connection(b)),
                      provider=deltas,source_old_flow_observations=outgoing,peer_old_flow_observations=incoming)
    except ValueError as error:result['why']=str(error)
    return result


def analyze(run,threshold_ns=1000000000):
    if threshold_ns<=0:raise ValueError('invalid gap threshold')
    report=json.loads((run/'run.json').read_text())
    if report['status']=='running':raise ValueError('run not closed')
    if report.get('srt_archive_sha256')!=ARCHIVE:raise ValueError('unverified provider handle/wire-ID contract')
    proof=common_clock(report['clock_namespace_proof']);stats=summarize_run(run);commands=summarize_commands(run)
    interval=report['results']['publication_interval'];start=interval['resume_monotonic_ns'];end=interval['pause_monotonic_ns']
    window=[start-6000000000,end+2000000000]
    addresses=json.loads((run/'network.json').read_text())['addresses'];captured={};hashes={}
    for role in ('operator','robot'):
        status=report['monotonic_captures']['statuses'][role]
        if status.get('complete') is not True or status.get('artifact_version')!=2 or status.get('clock')!='kernel_monotonic' or status.get('time_namespace_zero') is not True:
            raise ValueError('unqualified native v2 capture')
        if not status['ready_ns']<=window[0]<window[1]<=status['stop_before_ns'] or status['reserve_failed'] or status['copy_failed']:raise ValueError('native coverage/loss')
        path=run/(role+'.mono');sha=digest(path);rows=[];count=0
        for row in records(path):
            count+=1
            if row['artifact_version']!=2 or row['ifindex']!=status['ifindex']:raise ValueError('native identity changed')
            if window[0]<=row['monotonic_ns']<window[1]:
                value=parse_control(row,addresses[role],status['mtu'])
                if value:rows.append(value)
        if count!=status['records'] or count!=status['seen'] or count!=status['submitted'] or digest(path)!=sha:raise ValueError('native count/hash mismatch')
        captured[role]=sorted(rows,key=lambda row:row['monotonic_ns']);hashes[role]=sha
    gaps=[];events=[];loss_windows=[]
    for role in ('operator','robot'):
        peer='robot' if role=='operator' else 'operator';previous={}
        for row in captured[role]:
            if row['direction']!='out' or not row['destination_socket_id'] or not start<=row['monotonic_ns']<end:continue
            key=tuple(row[k] for k in FLOW_FIELDS);old=previous.get(key);previous[key]=row
            if old and row['monotonic_ns']-old['monotonic_ns']>=threshold_ns:
                value=correlate({k:row[k] for k in FLOW_FIELDS},old['monotonic_ns'],row['monotonic_ns'],role,peer,stats,captured)
                value.update(sender_role=role,gap_ns=row['monotonic_ns']-old['monotonic_ns'],kind='fully_observed_adjacent_source_gap');gaps.append(value)
    for name,trace in commands.items():
        role=name.split('-')[0];peer='robot' if role=='operator' else 'operator'
        for event in trace['events']:
            if not start<=event['monotonic_ns']<end:continue
            if event['point']==30 and event['detail']&1:events.append(dict(process=name,**event))
            if event['point']!=31 or event['detail']!=0:continue
            events.append(dict(process=name,**event))
            candidates=[r for r in stats[name]['records'] if r['available'] and r['owner_epoch']==event['owner_epoch'] and r['generation']==event['control_generation'] and r['end_ns']<=event['monotonic_ns']]
            if not candidates:
                loss_windows.append(dict(process=name,event_ns=event['monotonic_ns'],classification='mapping_withheld',why='no same-generation available provider baseline'));continue
            local=max(candidates,key=lambda r:r['end_ns'])
            incoming=[r for r in captured[role] if r['direction']=='in' and r['destination_socket_id']==local['socket'] and r['monotonic_ns']<event['monotonic_ns']]
            if not incoming:
                loss_windows.append(dict(process=name,event_ns=event['monotonic_ns'],classification='mapping_withheld',why='incoming history censored'));continue
            last=incoming[-1];flow={k:last[k] for k in FLOW_FIELDS};flow['direction']='out'
            value=correlate(flow,last['monotonic_ns'],event['monotonic_ns'],peer,role,stats,captured)
            value.update(process=name,event_ns=event['monotonic_ns'],quiet_ns=event['monotonic_ns']-last['monotonic_ns'],kind='receiver_last_observation_to_loss');loss_windows.append(value)
    return dict(active_ns=[start,end],capture_analysis_ns=window,threshold_ns=threshold_ns,clock_proof=proof,native_sha256=hashes,
                gaps=gaps,active_control_events=events,loss_windows=loss_windows,
                scope='selected counters exclude some UDP types; read brackets/availability/identity preserved; all qualifying adjacent source gaps retained, boundaries censored; routing mapping is not authentication; no unique cause, physical delivery, nonexecution or performance inference')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();args.out.write_text(json.dumps(analyze(args.run),indent=2)+'\n')
