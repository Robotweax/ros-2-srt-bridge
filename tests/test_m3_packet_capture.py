import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_packet_capture import validate_status


def status():
    return dict(backend='filtered_packet_socket',status='passed',complete=True,filter_before_bind=True,protocol_before_bind=0,protocol_after_bind=3,initial_kernel_packets=0,records=16,kernel_packets=16,kernel_drops=0,truncated=0,budget_exhausted=False,drain_snapshots=[dict(records=16,kernel_packets=16,kernel_drops=0)]*2,
                attach_begin_ns=1,attach_end_ns=2,bind_begin_ns=3,bind_end_ns=4,ready_ns=5,stop_before_ns=10)


class PacketCaptureTests(unittest.TestCase):
    def test_final_equality_with_filter_before_enabled_protocol(self):
        result=validate_status(status(),16)
        self.assertTrue(result['population_reconciled'])
        self.assertEqual(result['capture_backend'],'filtered_packet_socket')

    def test_prefilter_offset_never_subtracted(self):
        s=status();s['initial_kernel_packets']=2;s['kernel_packets']=18
        with self.assertRaises(ValueError):validate_status(s,16)

    def test_drops_incomplete_or_budget_exhaustion_fail_closed(self):
        for key,value in [('complete',False),('kernel_drops',1),('kernel_packets',17),('records',15),('truncated',1),('budget_exhausted',True),('status','failed')]:
            s=status();s[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_status(s,16)

    def test_activation_before_filter_or_wrong_protocol_rejected(self):
        for key,value in [('filter_before_bind',False),('protocol_before_bind',3),('protocol_after_bind',0),('attach_end_ns',4),('bind_begin_ns',1),('ready_ns',0)]:
            s=status();s[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validate_status(s,16)

    def test_unstable_or_missing_drain_fails(self):
        for snapshots in ([],[dict(records=16,kernel_packets=16,kernel_drops=0)],[dict(records=15,kernel_packets=16,kernel_drops=0),dict(records=16,kernel_packets=16,kernel_drops=0)]):
            s=status();s['drain_snapshots']=snapshots
            with self.assertRaises(ValueError):validate_status(s,16)
