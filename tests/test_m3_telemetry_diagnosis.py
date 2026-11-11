from collections import Counter
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_telemetry_diagnosis import udp_records,packet_view,compare


def frame(message=1,seq=10,socket=7,retransmit=False,control=None):
    words=(seq,(3<<30)|(int(retransmit)<<26)|message,0,socket) if control is None else (0x80000000|(control<<16),0,0,socket)
    payload=struct.pack('!IIII',*words)+b'opaque payload'
    udp=struct.pack('!HHHH',10081,20000,8+len(payload),0)+payload
    ip=bytearray(20);ip[0]=0x45;ip[9]=17;ip[2:4]=struct.pack('!H',20+len(udp));ip[12:16]=bytes([172,19,0,2]);ip[16:20]=bytes([172,19,0,3])
    return b'\x00'*12+b'\x08\x00'+bytes(ip)+udp


def pcap(path,frames):
    path.write_bytes(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1)+b''.join(struct.pack('<IIII',1,0,len(f),len(f))+f for f in frames))


class TelemetryCaptureTests(unittest.TestCase):
    def test_rotations_retransmissions_sockets_and_parity_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Path(tmp)/'a';b=Path(tmp)/'b';pcap(a,[frame(),frame(retransmit=True),frame(message=0)]);pcap(b,[frame(socket=8),frame(control=7)])
            result=packet_view([a,b],'172.19.0.2');source=[g for g in result['sensor_connections'] if g['category']=='sensor_source_data']
            self.assertEqual(len(source),2);self.assertEqual(source[0]['packets'],2);self.assertEqual(source[0]['unique_sequences'],1);self.assertEqual(source[0]['unique_message_numbers'],1);self.assertEqual(source[0]['retransmitted_packets'],1)
            self.assertEqual(result['classes']['out/sensor_fec_parity'],1);self.assertEqual(result['control_types']['out/sensor_srt_control/drop_request'],1)
            self.assertEqual(sum(result['identities']['out'].values()),5)

    def test_multiset_preserves_duplicates_and_tuple_payload_mismatch(self):
        a=Counter({('flow','digest'):2});b=Counter({('flow','digest'):1})
        self.assertEqual(compare(a,b)['source_not_at_sink'],1);self.assertFalse(compare(a,b)['equal_multisets']);self.assertTrue(compare(a,a)['equal_multisets'])
        self.assertEqual(compare(a,Counter({('other','digest'):2}))['matched_records'],0)

    def test_corrupt_truncated_fragment_and_udp_lengths_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a';f=bytearray(frame());pcap(p,[f]);p.write_bytes(p.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError,'truncated'):list(udp_records([p]))
            f[20:22]=b'\x20\x00';pcap(p,[f])
            with self.assertRaisesRegex(ValueError,'fragment'):list(udp_records([p]))
            f=bytearray(frame());f[38:40]=b'\x00\x08';pcap(p,[f])
            with self.assertRaisesRegex(ValueError,'UDP'):list(udp_records([p]))

    def test_message_number_wrap_has_no_numeric_gap_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'a';pcap(p,[frame(message=1),frame(message=(1<<26)-1)])
            g=packet_view([p],'172.19.0.2')['sensor_connections'][0]
            self.assertIsNone(g['numeric_message_span']);self.assertIsNone(g['unobserved_numbers_inside_span'])
