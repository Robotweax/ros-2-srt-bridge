import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from test_m3_source_trace import fixtures
from test_m3_sample_trace import event
from m3_multiroute_accounting import assess


def setup():
    source,r=fixtures();base={}
    for line in (Path(__file__).resolve().parents[1]/'ros2/robotweax_srt_bridge_msgs/msg/BridgeState.msg').read_text().splitlines():
        if not line or line.startswith('#'):continue
        kind,name=line.split();base[name]=[0]*int(kind.split('[')[1][:-1]) if '[' in kind else 0
    base.update(ready=True,clock_qualified=True,sensor_qos_verified=True,session_id=[2]*16,owner_epoch=[1]*16,control_generation=1,sensor_generation=1)
    sender=dict(begin=dict(bridge=copy.deepcopy(base)),end=dict(bridge=copy.deepcopy(base)),resume=r['resume'],pause=r['pause'],rows=[],bad=[],direct=0)
    base['owner_epoch']=[3]*16
    receiver=dict(begin=dict(bridge=copy.deepcopy(base)),end=dict(bridge=copy.deepcopy(base)),rows=r['observed'],bad=[],direct=0)
    sender['end']['bridge'].update(samples_ingress=2500,sensor_submitted=2500,sensor_inputs=2500,sensor_sent=2500,imu_ingress=2000,joint_ingress=500)
    receiver['end']['bridge'].update(transport_samples_received=2500,sensor_polled=2500,samples_published=2500)
    receiver['end']['bridge']['imu_age_upper_histogram_ms'][1]=2000;receiver['end']['bridge']['joint_age_upper_histogram_ms'][1]=500
    bind=event(2);bind.update(kind=4,message_number=1)
    local=dict(events=[bind],status=dict(attempted=5001));remote=dict(events=[],status=dict(attempted=2500))
    for i,src in enumerate(source['events']):
        a=event();a.update(sequence=2*i+2,route=src['route'],begin_ns=src['begin_ns']+1,end_ns=src['begin_ns']+3,origin_ns=src['begin_ns'],stamp_sec=src['stamp_sec'],stamp_nanosec=src['stamp_nanosec'])
        h=dict(a,point=2,sequence=2*i+3,begin_ns=a['begin_ns']+1,end_ns=a['end_ns']+1,bytes=a['bytes']+96,message_number=i+2,socket=99,initial_sequence=123,initial_sequence_available=True,envelope_sequence=i+1)
        local['events'] += [a,h]
        remote['events'].append(dict(h,point=4,sequence=i+1,source_epoch='01'*16,owner_epoch='03'*16))
    return source,sender,receiver,local,remote


def remove_first(args,mode):
    source,sender,receiver,local,remote=args
    if mode!='observer':
        remote['events'].pop(0)
        for k in ('transport_samples_received','sensor_polled','samples_published'):receiver['end']['bridge'][k]-=1
        receiver['end']['bridge']['imu_age_upper_histogram_ms'][1]-=1
    receiver['rows'].pop(0)
    if mode in ('busy','replacement'):
        local['events'].pop(2)
        for e in local['events']:
            if e['point']==2 and e['message_number']>2:e['message_number']-=1
        for e in remote['events']:e['message_number']-=1
        sender['end']['bridge']['sensor_inputs']-=1;sender['end']['bridge']['sensor_sent']-=1
        if mode=='busy':
            local['events'][1]['result']=1;sender['end']['bridge']['sensor_submitted']-=1;sender['end']['bridge']['samples_submit_busy']=1;sender['end']['bridge']['context_drops']=1
        else:sender['end']['bridge']['sensor_ingress_replaced']=1


class MultirouteAccountingTests(unittest.TestCase):
    def test_full_route_source_sdk_receiver_typed_join(self):
        result=assess(*setup());self.assertTrue(result['passed']);self.assertEqual(result['window']['source_produced'],2500);self.assertFalse(any(result['window']['losses'].values()))

    def test_busy_does_not_consume_sdk_index_or_become_transport_loss(self):
        args=setup();remove_first(args,'busy');r=assess(*args)
        self.assertEqual(r['rejected_admissions'],[dict(route=1,counter=1,result=1)])
        self.assertEqual(r['window']['losses']['admission'],1);self.assertEqual(r['window']['losses']['srt_accept_to_receiver_gap'],0)

    def test_mailbox_replacement_keeps_unmatched_queued_input(self):
        args=setup();remove_first(args,'replacement');r=assess(*args)
        self.assertEqual(len(r['queued_without_observed_handoff']),1);self.assertEqual(r['window']['losses']['ingress_replaced'],1)

    def test_sdk_gap_and_observer_dds_are_distinct(self):
        args=setup();remove_first(args,'gap');r=assess(*args)
        self.assertEqual(r['sdk_without_receiver_decision'],[2]);self.assertEqual(r['window']['losses']['srt_accept_to_receiver_gap'],1)
        args=setup();remove_first(args,'observer');r=assess(*args)
        self.assertEqual(r['accepted_without_typed_observation'],[[1,1]]);self.assertEqual(r['window']['losses']['observer_dds'],1)

    def test_context_trace_population_and_source_hash_errors_fail(self):
        for fault in ('context','population','receiver','hash','duplicate'):
            args=setup();source,sender,receiver,local,remote=args
            if fault=='context':local['events'][1]['owner_epoch']='ff'*16
            if fault=='population':sender['end']['bridge']['sensor_sent']-=1
            if fault=='receiver':remote['events'][0]['source_epoch']='ff'*16
            if fault=='hash':receiver['rows'][0]['payload_sha256']='cd'*32
            if fault=='duplicate':remote['events'].append(remote['events'][0])
            with self.assertRaises(ValueError):assess(*args)
