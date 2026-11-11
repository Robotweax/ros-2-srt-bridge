from pathlib import Path
import socket,struct,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_arp_gap_observations import parse_arp


def row(op=1,packet_type=4):
    frame=bytes(12)+b'\x08\x06'+struct.pack('!HHBBH',1,0x800,6,4,op)+bytes(6)+socket.inet_aton('10.0.0.1')+bytes(6)+socket.inet_aton('10.0.0.2')
    return dict(prefix=frame,length=len(frame),artifact_version=2,packet_type=packet_type,monotonic_ns=10,gso_size=0,gso_segs=1,vlan_present=0)


class ArpTests(unittest.TestCase):
    def test_ipv4_request_reply_fields_and_non_outgoing_duplicate(self):
        for op in (1,2):
            p=parse_arp(row(op));self.assertEqual(p['operation'],op);self.assertEqual(p['sender_ipv4'],'10.0.0.1');self.assertEqual(p['target_ipv4'],'10.0.0.2');self.assertTrue(p['outgoing'])
        self.assertFalse(parse_arp(row(packet_type=1))['outgoing'])
    def test_other_ethertype_is_not_arp(self):
        r=row();r['prefix']=r['prefix'][:12]+b'\x08\x00'+r['prefix'][14:];self.assertIsNone(parse_arp(r))
    def test_bad_shape_and_short_record_rejected(self):
        for change in ('short','shape','length'):
            r=row()
            if change=='short':r['prefix']=r['prefix'][:40]
            if change=='shape':r['prefix']=r['prefix'][:18]+b'\x04'+r['prefix'][19:]
            if change=='length':r['length']=40
            with self.assertRaises(ValueError):parse_arp(r)
    def test_unqualified_representation_rejected(self):
        for kw in (dict(artifact_version=1),dict(gso_size=1000),dict(gso_segs=2),dict(vlan_present=1)):
            with self.assertRaises(ValueError):parse_arp(row()|kw)
