from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_retirement_order import RetirementOrder


def data(seq,socket=7,message=1):
    return struct.pack('!IIII',seq,(3<<30)|(1<<27)|message,0,socket)+b'opaque'


def retire(first,last=None,socket=7,message=0):
    return struct.pack('!IIIIII',0x80070000,message,0,socket,first,first if last is None else last)


class RetirementOrderTests(unittest.TestCase):
    def test_order_repetition_and_eventual_overlap_are_distinct(self):
        v=RetirementOrder();flow=('a','b',1,10081)
        for packet in [data(1),retire(1),retire(2),retire(2),data(2),data(2)]:v.observe(flow,packet)
        g=v.summary()[0]
        self.assertEqual(g['data_packets'],3);self.assertEqual(g['unique_data_sequences'],2)
        self.assertEqual(g['retirement_controls'],3);self.assertEqual(g['repeated_retirement_controls'],1)
        self.assertEqual(g['data_packets_after_prior_same_sequence_retirement'],2)
        self.assertEqual(g['unique_data_sequences_after_prior_retirement'],1)
        self.assertEqual(g['data_sequences_eventually_named_by_retirement'],2)
        self.assertEqual(g['encryption_key_flags'],{1:3})

    def test_flow_and_socket_incarnations_do_not_cross_match(self):
        v=RetirementOrder();a=('a','b',1,10081);b=('a','b',2,10081)
        v.observe(a,retire(9));v.observe(a,data(9,socket=8));v.observe(b,data(9))
        self.assertEqual(len(v.summary()),3)
        self.assertEqual(sum(g['data_packets_after_prior_same_sequence_retirement'] for g in v.summary()),0)

    def test_ranges_invalid_sequences_message_retirements_and_short_headers(self):
        v=RetirementOrder();flow=('a','b',1,10081)
        for packet in [retire(1,2),retire(0x80000001),retire(3,message=1),retire(4)[:-1]]:v.observe(flow,packet)
        for seq in [1,2,3,4]:v.observe(flow,data(seq))
        g=v.summary()[0];self.assertEqual(g['unsupported_controls'],4);self.assertEqual(g['retirement_controls'],0)
        self.assertEqual(g['data_packets_after_prior_same_sequence_retirement'],0)
        with self.assertRaisesRegex(ValueError,'short SRT'):v.observe(flow,b'short')

    def test_wrap_uses_exact_sequence_and_parity_is_excluded(self):
        v=RetirementOrder();flow=('a','b',1,10081)
        for packet in [retire(0x7fffffff),data(0),data(0x7fffffff,message=0),data(0x7fffffff)]:v.observe(flow,packet)
        g=v.summary()[0];self.assertEqual(g['data_packets'],2)
        self.assertEqual(g['unique_data_sequences_after_prior_retirement'],1)
