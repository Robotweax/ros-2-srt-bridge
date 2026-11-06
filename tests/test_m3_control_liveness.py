from pathlib import Path
import socket,struct,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_control_liveness import parse_control,summarize_flows


def row(ns,socket_id=7,kind=2):
    payload=struct.pack('!IIII',0x80000000|(kind<<16),0,0,socket_id)
    ip=bytearray(20);ip[0]=0x45;ip[9]=17;struct.pack_into('!H',ip,2,28+len(payload))
    ip[12:16]=socket.inet_aton('10.0.0.1');ip[16:20]=socket.inet_aton('10.0.0.2')
    frame=bytes(12)+b'\x08\x00'+ip+struct.pack('!HHHH',10080,40000,8+len(payload),0)+payload
    return dict(monotonic_ns=ns,prefix=frame,length=len(frame),packet_type=4,artifact_version=2,gso_segs=1,gso_size=0,vlan_present=0)


class LivenessTests(unittest.TestCase):
    def parse(self,r):return parse_control(r,'10.0.0.1',1500)

    def test_outer_header_and_shutdown_without_payload_decryption(self):
        p=self.parse(row(10,kind=5));self.assertEqual(p['kind'],'shutdown');self.assertEqual(p['destination_socket_id'],7)
        self.assertEqual(p['source_port'],10080);self.assertEqual(p['direction'],'out')

    def test_reconnect_socket_ids_never_make_a_cross_connection_gap(self):
        rows=[self.parse(row(1,7)),self.parse(row(90,8))]
        result=summarize_flows(rows,0,100,50)
        self.assertEqual(len(result),2);self.assertTrue(all(r['largest_gap'] is None for r in result))
        self.assertEqual(result[0]['observed_quiet_to_event_ns'],49)
        self.assertIsNone(result[1]['observed_quiet_to_event_ns'])
        self.assertIsNone(result[0]['first_at_or_after_event_ns'])

    def test_zero_destination_handshake_does_not_claim_connection_quiet(self):
        result=summarize_flows([self.parse(row(1,0,0)),self.parse(row(90,0,0))],0,100,50)[0]
        self.assertFalse(result['nonzero_destination_socket_id'])
        self.assertIsNone(result['observed_quiet_to_event_ns'])

    def test_gap_sorting_duplicate_observations_and_window_censoring(self):
        rows=[self.parse(row(t)) for t in (40,0,20,20,30,100)]
        result=summarize_flows(rows,10,50)[0]
        self.assertEqual(result['observations'],4)
        self.assertEqual(result['largest_gap']['gap_ns'],10)
        self.assertEqual(result['first_ns'],20);self.assertEqual(result['last_ns'],40)
        with self.assertRaises(ValueError):summarize_flows(rows,50,10)

    def test_segmented_vlan_and_short_control_are_not_silently_accepted(self):
        for change in (dict(gso_segs=2),dict(gso_size=1000),dict(vlan_present=1),dict(artifact_version=1)):
            with self.assertRaises(ValueError):self.parse(row(1)|change)
        r=row(1);r['prefix']=r['prefix'][:-4]
        with self.assertRaises(ValueError):self.parse(r)
