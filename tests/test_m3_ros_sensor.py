import copy
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_ros_sensor import outcomes, identity_capture


def results(losses):
    fields='sensor_ingress_pending sensor_outbound_pending sensor_receive_pending samples_ingress sensor_submitted invalid_samples oversize_samples stale_samples context_drops sensor_ingress_replaced sensor_ingress_flushed sensor_inputs sensor_input_rejected sensor_outbound_replaced sensor_outbound_expired sensor_outbound_flushed sensor_sent transport_samples_received transport_samples_rejected sensor_receive_replaced sensor_receive_flushed sensor_polled sensor_poll_expired samples_published'.split()
    state=dict.fromkeys(fields,0);state.update(owner_epoch=[1]*16,session_id=[2]*16,ready=True,clock_qualified=True,sensor_qos_verified=True,imu_age_upper_max_ns=0,joint_age_upper_max_ns=0,imu_age_upper_histogram_ms=[0]*251,joint_age_upper_histogram_ms=[0]*251)
    sent=dict(begin=dict(bridge=copy.deepcopy(state)),end=dict(bridge=copy.deepcopy(state)),start_ns=1,stop_ns=1000000001,bad=[],direct=0,rows=[dict(id=i,payload_sha256=str(i)) for i in range(19)])
    received=copy.deepcopy(sent);received['rows']=[r for r in received['rows'] if losses!=2 or r['id'] not in (5,6)]
    sent['end']['bridge'].update(samples_ingress=19,sensor_submitted=19,sensor_inputs=19,sensor_sent=19)
    n=len(received['rows']);received['end']['bridge'].update(transport_samples_received=n,sensor_polled=n,samples_published=n,imu_age_upper_max_ns=10000000)
    received['end']['bridge']['imu_age_upper_histogram_ms'][10]=n
    return sent,received


class RosSensorTests(unittest.TestCase):
    def test_balanced_repair_and_missing_population(self):
        for losses,count in ((0,19),(1,19),(2,17)):
            v=outcomes(*results(losses),losses)
            self.assertEqual(v['window']['published'],count)
            self.assertTrue(all(x==0 for x in v['window']['balances'].values()))

    def test_wrong_payload_order_age_session_or_stage_loss_rejects(self):
        for kind in ('hash','order','age','session','clock','replacement'):
            a,b=results(1)
            if kind=='hash':b['rows'][0]['payload_sha256']='wrong'
            elif kind=='order':b['rows'][1],b['rows'][2]=b['rows'][2],b['rows'][1]
            elif kind=='age':b['end']['bridge']['imu_age_upper_max_ns']=250000001
            elif kind=='session':b['end']['bridge']['session_id']=[3]*16
            elif kind=='clock':b['begin']['bridge']['clock_qualified']=False
            else:b['end']['bridge']['sensor_receive_replaced']=1
            with self.subTest(kind=kind),self.assertRaises(ValueError):outcomes(a,b,1)

    def test_identity_requires_single_binding_and_matching_handshake(self):
        flow=dict(direction='out',source='10.0.0.1',destination='10.0.0.2',source_port=41234,destination_port=10081,sequence=123,message_number=1,socket_id=456,retransmitted=False,control=False,monotonic_ns=100)
        frame=bytearray(106);struct.pack_into('!I',frame,42,0x80000000);struct.pack_into('!I',frame,66,123)
        hs=dict(flow,control=True)
        def capture(path,address):
            if path.stem=='operator':return {},[({},dict(flow,direction='in'))]
            return dict(stop_before_ns=200),[({'prefix':frame},hs),({},flow)]
        with patch('m3_ros_sensor.captured',side_effect=capture):
            self.assertEqual(identity_capture(Path('/tmp'),{'robot':'10.0.0.1','operator':'10.0.0.2'})['initial_sequence'],123)
            struct.pack_into('!I',frame,66,124)
            with self.assertRaises(ValueError):identity_capture(Path('/tmp'),{'robot':'10.0.0.1','operator':'10.0.0.2'})
            flow['message_number']=2
            with self.assertRaises(ValueError):identity_capture(Path('/tmp'),{'robot':'10.0.0.1','operator':'10.0.0.2'})

class TraceDiagnosticWindowTests(unittest.TestCase):
    def test_busy_is_accounted_in_separate_observer_validation(self):
        from m3_ros_sensor import diagnostic_window
        a,b=results(0)
        a['end']['bridge']['samples_submit_busy']=1
        a['begin']['bridge']['samples_submit_busy']=0
        a['end']['bridge'].update(context_drops=1,sensor_submitted=18,sensor_inputs=18,sensor_sent=18)
        b['rows']=[r for r in b['rows'] if r['id']!=7]
        b['end']['bridge'].update(transport_samples_received=18,sensor_polled=18,samples_published=18)
        b['end']['bridge']['imu_age_upper_histogram_ms'][10]=18
        result=diagnostic_window(a,b)
        self.assertEqual(result['losses']['admission'],1)
        with self.assertRaises(ValueError):outcomes(a,b,0)
        a['end']['bridge']['samples_submit_busy']=0
        with self.assertRaises(ValueError):diagnostic_window(a,b)

class TracedFaultPopulationTests(unittest.TestCase):
    def test_fault_identity_shifts_with_independent_busy_source(self):
        from m3_ros_sensor import selected_sources
        # Source ID2 never admitted. SDK message IDs remain consecutive, beginning
        # at2 after the binding; the targeted message8 now belongs to source ID7.
        admitted=[i for i in range(19) if i!=2]
        mapped=[dict(source_id=i,message_number=j+2) for j,i in enumerate(admitted)]
        selected,observed=selected_sources(mapped,1)
        self.assertEqual([m['source_id'] for m in selected],[7])
        self.assertEqual(observed,admitted)
        selected,observed=selected_sources(mapped,2)
        self.assertEqual([m['source_id'] for m in selected],[6,7])
        self.assertEqual(observed,[i for i in admitted if i not in (6,7)])

    def test_missing_duplicate_or_unaccepted_target_rejects(self):
        from m3_ros_sensor import selected_sources
        for mapped in ([],[dict(source_id=1,message_number=7)],
                       [dict(source_id=1,message_number=7),dict(source_id=1,message_number=8)],
                       [dict(source_id=1,message_number=7),dict(source_id=2,message_number=7),dict(source_id=3,message_number=8)]):
            with self.assertRaises(ValueError):selected_sources(mapped,2)

    def test_two_loss_gap_and_busy_are_separate_conservation_terms(self):
        from m3_ros_sensor import diagnostic_window
        a,b=results(2)
        a['begin']['bridge']['samples_submit_busy']=0
        a['end']['bridge'].update(samples_submit_busy=1,context_drops=1,sensor_submitted=18,sensor_inputs=18,sensor_sent=18)
        b['rows']=[r for r in b['rows'] if r['id']!=10]
        b['end']['bridge'].update(transport_samples_received=16,sensor_polled=16,samples_published=16)
        b['end']['bridge']['imu_age_upper_histogram_ms'][10]=16
        result=diagnostic_window(a,b,2)
        self.assertEqual(result['losses']['admission'],1)
        self.assertEqual(result['losses']['srt_accept_to_receiver_gap'],2)
        with self.assertRaises(ValueError):diagnostic_window(a,b,1)

class LateReceiverTests(unittest.TestCase):
    def fixture(self):
        from m3_ros_sensor import selected_sources
        mapped=[dict(source_id=i,message_number=i+2,origin_ns=100+i,envelope_sequence=i+1) for i in range(3,9)]
        selected,_=selected_sources(mapped,1,True)
        state=dict(session_id=[2]*16,owner_epoch=[3]*16,control_generation=1,sensor_generation=1,transport_samples_unknown_age=0,transport_samples_stale=0)
        rows=[dict(id=i,observed_ns=(100000000 if i in (4,5) else 210000000)) for i in range(4,9)]
        receiver=dict(begin=dict(bridge=copy.deepcopy(state)),end=dict(bridge=copy.deepcopy(state)),rows=rows)
        events=[dict(point=4,message_number=m['message_number'],origin_ns=m['origin_ns'],envelope_sequence=m['envelope_sequence'],route=1,source_epoch='01'*16,owner_epoch='03'*16,session='02'*16,control_generation=1,sensor_generation=1,result=12 if m['message_number']==5 else 0,end_ns=200000100) for m in mapped]
        return mapped,dict(events=events),receiver,'01'*16,selected,200000000

    def test_direct_replay_after_newer_publication(self):
        from m3_ros_sensor import verify_late_receiver
        result=verify_late_receiver(*self.fixture())
        self.assertEqual(result['receiver_decision']['result'],12)
        self.assertEqual(result['newer_observed_before_parity'],[4,5])

    def test_stale_unknown_missing_wrong_origin_or_early_repair_not_accepted(self):
        from m3_ros_sensor import verify_late_receiver
        for kind in ('stale','accepted','epoch','missing','duplicate','no-newer','timing','clock'):
            args=list(self.fixture());events=args[1]['events'];receiver=args[2]
            if kind=='stale':events[0]['result']=25
            elif kind=='accepted':events[0]['result']=0
            elif kind=='epoch':events[0]['source_epoch']='04'*16
            elif kind=='missing':events.pop()
            elif kind=='duplicate':events.append(copy.deepcopy(events[0]))
            elif kind=='no-newer':
                for row in receiver['rows']:row['observed_ns']=300000000
            elif kind=='timing':args[-1]=300000000
            else:receiver['end']['bridge']['transport_samples_unknown_age']=1
            with self.subTest(kind=kind),self.assertRaises(ValueError):verify_late_receiver(*args)

    def test_repaired_but_rejected_is_receiver_loss_not_transport_gap(self):
        from m3_ros_sensor import diagnostic_window
        a,b=results(0);a['begin']['bridge']['samples_submit_busy']=0;a['end']['bridge']['samples_submit_busy']=0
        b['rows']=[r for r in b['rows'] if r['id']!=3]
        b['end']['bridge'].update(transport_samples_rejected=1,sensor_polled=18,samples_published=18)
        b['end']['bridge']['imu_age_upper_histogram_ms'][10]=18
        value=diagnostic_window(a,b,1,True)
        self.assertEqual(value['losses']['receiver_rejected'],1)
        self.assertEqual(value['losses']['srt_accept_to_receiver_gap'],0)
        with self.assertRaises(ValueError):diagnostic_window(a,b,1)

class RepairHorizonTests(unittest.TestCase):
    def test_native_gap_interval_strictly_below_pinned20ms(self):
        from m3_ros_sensor import repair_horizon
        self.assertEqual(repair_horizon(100,19999999),19999899)
        for first,parity in ((0,1),(100,99),(100,20000100),(100,100000100)):
            with self.assertRaises(ValueError):repair_horizon(first,parity)
