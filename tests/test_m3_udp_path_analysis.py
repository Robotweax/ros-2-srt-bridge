from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_udp_path_analysis import arp_kind,selected_windows,stable_identity,analyze
from m3_arp_gap_observations import parse_arp
import test_m3_arp_gap_observations as arp_tests

LOCAL='10.0.0.1';PEER='10.0.0.2';LM='02:00:00:00:00:01';PM='02:00:00:00:00:02'


def arp(**kw):
    d=dict(operation=1,ethernet_source_mac=LM,ethernet_destination_mac='ff:ff:ff:ff:ff:ff',sender_mac=LM,target_mac='00:00:00:00:00:00',sender_ipv4=LOCAL,target_ipv4=PEER,outgoing=True);d.update(kw);return d


class UdpPathTests(unittest.TestCase):
    def test_reflected_local_copy_is_not_a_peer_reply(self):
        self.assertEqual(arp_kind(arp(),LOCAL,PEER,LM,PM),'outgoing_local_request')
        self.assertEqual(arp_kind(arp(outgoing=False),LOCAL,PEER,LM,PM),'reflected_local_request')
        peer=arp(operation=2,ethernet_source_mac=PM,ethernet_destination_mac=LM,sender_mac=PM,target_mac=LM,sender_ipv4=PEER,target_ipv4=LOCAL,outgoing=False)
        self.assertEqual(arp_kind(peer,LOCAL,PEER,LM,PM),'incoming_peer_reply')
        for key,value in [('sender_mac',LM),('target_mac',PM),('ethernet_destination_mac',PM)]:
            self.assertNotEqual(arp_kind(peer|{key:value},LOCAL,PEER,LM,PM),'incoming_peer_reply')
    def test_mac_fields_are_extracted_from_distinct_header_offsets(self):
        r=arp_tests.row();f=bytearray(r['prefix']);f[:6]=bytes.fromhex(PM.replace(':',''));f[6:12]=bytes.fromhex(LM.replace(':',''));f[22:28]=f[6:12];f[32:38]=f[:6];r['prefix']=bytes(f)
        a=parse_arp(r);self.assertEqual(a['sender_mac'],LM);self.assertEqual(a['target_mac'],PM)
        self.assertEqual(a['ethernet_destination_mac'],PM);self.assertEqual(a['ethernet_source_mac'],LM)
    def test_loss_without_later_source_packet_is_still_selected(self):
        g=dict(window_ns=[10,20],flow=dict(source=LOCAL),classification='mapping_withheld',why='session changed')
        selected=selected_windows(dict(gaps=[],loss_windows=[g]),dict(operator=LOCAL,robot=PEER))
        self.assertEqual(selected[0]['family'],'loss_window');self.assertEqual(selected[0]['sender'],'operator')
        with self.assertRaises(ValueError):selected_windows(dict(gaps=[g|dict(window_ns=[20,10])],loss_windows=[]),dict(operator=LOCAL))
        with self.assertRaises(ValueError):selected_windows(dict(gaps=[g],loss_windows=[]),dict(robot=PEER))
    def test_unavailable_or_new_socket_withholds_identity(self):
        r=dict(begin_ns=11,end_ns=12,available=1,owner_epoch='x',generation=1,socket=7)
        identity=['x',1,7]
        self.assertTrue(stable_identity({'operator-a':dict(records=[r])},'operator',[10,20],identity))
        for change in [dict(available=0),dict(socket=8),dict(generation=2)]:
            self.assertFalse(stable_identity({'operator-a':dict(records=[r|change])},'operator',[10,20],identity))
        self.assertFalse(stable_identity({},'operator',[10,20],identity))
    def test_changed_raw_metadata_is_rejected_before_primary_analysis(self):
        # Raw report and link snapshots are authority inputs too, not just .mono files.
        import m3_udp_path_analysis as module
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();run=root/'run';run.mkdir();(run/'run.json').write_text('{}')
            with patch.object(module,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'hash mismatch'):analyze(run,{},True)
