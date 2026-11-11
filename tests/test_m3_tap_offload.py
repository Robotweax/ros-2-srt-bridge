#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from m3_capture import validate_tcpdump_footer
from m3_monotonic_capture import HEADER,RECORD_V2,records,summarize,decode
from m3_tap_probe import classify_stage
from test_m3_monotonic_capture import frame,status


class OffloadTests(unittest.TestCase):
    def summary(self,*,segs=0,size=0,vlan=0,length=200,version=2):
        with tempfile.TemporaryDirectory() as tmp:
            f=frame(b'RTPS'+bytes(length-4));p=Path(tmp)/'p'
            p.write_bytes(HEADER.pack(0x314d5253,version,168,1)+RECORD_V2.pack(10,len(f),min(len(f),128),4,2,segs,size,vlan,0,f[:128].ljust(128,b'\0')))
            s=status(1)|dict(mtu=1500,artifact_version=2,record_bytes=168)
            return summarize(p,s,'10.0.0.1',[5,20])

    def test_plain_v2_observations_have_unsegmented_interpretation(self):
        r=self.summary();self.assertTrue(r['qualified']);self.assertTrue(r['frame_interpretation']['qualified'])
        self.assertEqual(r['byte_unit'],'observed_skb_length_bytes')

    def test_gso_vlan_and_over_mtu_keep_observations_without_physical_frame_claim(self):
        for args in (dict(segs=8,size=1200,length=9600),dict(vlan=1),dict(length=2000)):
            r=self.summary(**args);self.assertTrue(r['qualified']);self.assertFalse(r['frame_interpretation']['qualified'])
        self.assertEqual(self.summary(segs=8,size=1200,length=9600)['frame_interpretation']['gso_observations'],1)

    def test_corrupt_offload_fields_and_unknown_artifact_reject(self):
        for args in (dict(segs=70000),dict(size=70000),dict(vlan=2),dict(version=3)):
            with self.assertRaises(ValueError):self.summary(**args)

    def test_inline_vlan_is_not_silently_ignored(self):
        f=bytearray(frame());f[12:14]=b'\x81\x00'
        with self.assertRaises(ValueError):decode(dict(prefix=f[:128],length=len(f),packet_type=4),'10.0.0.1')


class DispatchTests(unittest.TestCase):
    def test_buffered_filtered_packet_is_incomplete_without_kernel_drop(self):
        mismatch=validate_tcpdump_footer('16 packets captured\n17 packets received by filter\n0 packets dropped by kernel',16)
        self.assertTrue(mismatch['tcpdump_file_integrity_valid']);self.assertFalse(mismatch['tcpdump_population_reconciled'])
        self.assertTrue(validate_tcpdump_footer('1 packet captured\n1 packet received by filter\n0 packets dropped by kernel',1)['tcpdump_population_reconciled'])
        good='17 packets captured\n17 packets received by filter\n0 packets dropped by kernel'
        self.assertTrue(validate_tcpdump_footer(good,17)['tcpdump_population_reconciled'])
        for text,count in [('17 packets captured\n0 packets dropped by kernel',17),(good,16),(good.replace('0 packets dropped','1 packets dropped'),17)]:
            with self.assertRaises(ValueError):validate_tcpdump_footer(text,count)

    def test_synthetic_drop_and_delay_stage_classification_requires_full_populations(self):
        self.assertIn('after tested qdisc',classify_stage('egress-drop',16,0,0,0,16,[]))
        self.assertIn('before tested ingress',classify_stage('ingress-drop',16,16,16,0,16,[]))
        self.assertIn('includes',classify_stage('egress-delay',16,16,16,16,0,[200000000]*16))
        for args in [('egress-drop',16,2,0,0,16,[]),('egress-drop',16,0,0,0,15,[]),('egress-delay',16,16,16,16,0,[90000000]*16),('gso-noqueue',8,1,1,7,0,[])]:
            with self.assertRaises(ValueError):classify_stage(*args)


if __name__=='__main__':unittest.main()
