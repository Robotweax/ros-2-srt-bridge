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
