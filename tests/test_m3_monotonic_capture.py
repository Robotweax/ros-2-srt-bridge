#!/usr/bin/env python3
import copy
import json
from pathlib import Path
import socket
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_monotonic_capture import HEADER,RECORD,records,decode,summarize
from m3_capture import summarize as pcap_summary


def frame(payload=b'RTPS'+bytes(200),fragment=0):
    ip=bytearray(20);ip[0]=0x45;ip[9]=17;struct.pack_into('!HH',ip,2,28+len(payload),0);struct.pack_into('!H',ip,6,fragment)
    ip[12:16]=socket.inet_aton('10.0.0.1');ip[16:20]=socket.inet_aton('10.0.0.2')
    return bytes(12)+b'\x08\x00'+ip+struct.pack('!HHHH',7400,7410,8+len(payload),0)+payload


def record(frame,ns=10,index=2,kind=4):return RECORD.pack(ns,len(frame),min(len(frame),128),kind,index,frame[:128].ljust(128,b'\0'))

def status(n):return dict(complete=True,clock='kernel_monotonic',time_namespace_zero=True,ifindex=2,records=n,seen=n,submitted=n,reserve_failed=0,copy_failed=0,ready_ns=1,stop_before_ns=30)


class MonotonicCaptureTests(unittest.TestCase):
    def test_prefix_totals_equal_whole_pcap_summary(self):
        frames=[frame(),frame(struct.pack('!IIII',1,0,0,0)+bytes(1200))]
        # Second datagram uses sensor port for FEC classification.
        frames[1]=frames[1][:36]+struct.pack('!H',10081)+frames[1][38:]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'capture.mono';path.write_bytes(HEADER.pack(0x314d5253,1,152,1)+b''.join(record(f) for f in frames))
            mono=summarize(path,status(2),'10.0.0.1',[5,20])
            pcap=Path(tmp)/'capture.pcap';pcap.write_bytes(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1)+b''.join(struct.pack('<IIII',1,0,len(f),len(f))+f for f in frames))
            self.assertEqual(mono['classes'],pcap_summary([pcap],'10.0.0.1')['classes'])
            self.assertEqual(mono['classes']['out/sensor_fec_parity']['packets'],1)

    def test_window_is_half_open_and_independent_of_record_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'c';p.write_bytes(HEADER.pack(0x314d5253,1,152,1)+b''.join(record(frame(),ns=n) for n in (20,9,10)))
            result=summarize(p,status(3),'10.0.0.1',[10,20]);self.assertEqual(result['inside_records'],1)

    def test_loss_counter_mismatch_clock_and_coverage_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'c';p.write_bytes(HEADER.pack(0x314d5253,1,152,1)+record(frame()))
            for key,value in [('complete',False),('seen',2),('submitted',2),('reserve_failed',1),('copy_failed',1),('time_namespace_zero',False),('clock','realtime'),('ready_ns',12),('stop_before_ns',15),('ifindex',3)]:
                s=status(1);s[key]=value
                with self.assertRaises(ValueError,msg=key):summarize(p,s,'10.0.0.1',[5,20])

    def test_invalid_binary_header_record_fields_and_padding_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'c';head=HEADER.pack(0x314d5253,1,152,1)
            for value in [b'x',head+record(frame())[:-1],head+record(frame(),kind=9),head+record(frame(),index=0),head+record(frame(),ns=0),head+record(frame(b'x'))[:-1]+b'x']:
                p.write_bytes(value)
                with self.assertRaises(ValueError):list(records(p))

    def test_fragments_are_explicit_and_have_no_udp_payload_total(self):
        f=frame(bytes(16),fragment=0x2000);row=dict(prefix=f,length=len(f),packet_type=4)
        with self.assertRaises(ValueError):decode(row,'10.0.0.1')
        self.assertEqual(decode(row,'10.0.0.1',True),('out/ipv4_udp_fragment',None))

    def test_known_non_udp_ignored_but_ipv6_udp_and_extensions_reject(self):
        ipv6=bytearray(54);ipv6[12:14]=b'\x86\xdd';ipv6[14]=0x60;ipv6[20]=58
        self.assertIsNone(decode(dict(prefix=ipv6,length=54,packet_type=0),'10.0.0.1'))
        hop=bytearray(ipv6)+bytes(8);hop[20]=0;struct.pack_into('!H',hop,18,8);hop[54]=58
        self.assertIsNone(decode(dict(prefix=hop,length=62,packet_type=0),'10.0.0.1'))
        hop[54]=17
        with self.assertRaises(ValueError):decode(dict(prefix=hop,length=62,packet_type=0),'10.0.0.1')
        for protocol in (17,0,44):
            ipv6[20]=protocol
            with self.assertRaises(ValueError):decode(dict(prefix=ipv6,length=54,packet_type=0),'10.0.0.1')

    def test_corrupt_lengths_and_direction_reject(self):
        for offset,value in [(16,65535),(38,65535)]:
            f=bytearray(frame());struct.pack_into('!H',f,offset,value)
            with self.assertRaises(ValueError):decode(dict(prefix=f[:128],length=len(f),packet_type=4),'10.0.0.1')
        with self.assertRaises(ValueError):decode(dict(prefix=frame()[:128],length=len(frame()),packet_type=0),'10.0.0.1')


if __name__=='__main__':unittest.main()
