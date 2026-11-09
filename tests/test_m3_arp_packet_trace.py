import copy
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_arp_packet_analysis import lifecycles,reply_header
from m3_arp_trace_stimulus import request_frame


class PacketTraceTests(unittest.TestCase):
    def setUp(self):
        self.ready=dict(version=2,ready_ns=10,hooks=6,clock='kernel_monotonic')
        self.status=dict(complete=True,deadline=False,time_namespace_zero=True,detached_hooks=6,reserve_failed=0,map_failed=0,read_failed=0,collision=0,pending=0,created=1,retired=1,records=4,emitted=4,ready_ns=10,detach_before_ns=100)
        self.rows=[dict(ns=20,cookie=1,kind=1,aux=0,handle=0,parent=0),dict(ns=30,cookie=1,kind=2,aux=0,handle=65536,parent=4294967295),dict(ns=80,cookie=1,kind=3,aux=1,handle=65536,parent=4294967295),dict(ns=90,cookie=1,kind=4,aux=0,handle=0,parent=0)]
        self.reasons={'77':'SKB_DROP_REASON_QDISC_DROP','2':'SKB_DROP_REASON_NOT_SPECIFIED'}
    def analyze(self,rows=None,status=None):
        return lifecycles(self.rows if rows is None else rows,self.status if status is None else status,self.ready,self.reasons)
    def test_exact_queue_residence(self):
        row=self.analyze()[0];self.assertEqual(row['outcome'],'driver_start');self.assertEqual(row['residence'][0]['residence_ns'],50)
    def test_drop_requires_exact_reason(self):
        self.rows[-1].update(kind=5,aux=77);self.assertEqual(self.analyze()[0]['outcome'],'qdisc_drop')
        self.rows[-1]['aux']=2;self.assertEqual(self.analyze()[0]['outcome'],'other_free')
        self.rows[-1]['aux']=999
        with self.assertRaisesRegex(ValueError,'unknown BTF'):self.analyze()
    def test_missing_loss_and_lifecycle_population(self):
        for field in ('reserve_failed','map_failed','read_failed','collision','pending'):
            status=dict(self.status);status[field]=1
            with self.assertRaises(ValueError):self.analyze(status=status)
        for field in ('emitted','records','created','retired'):
            status=dict(self.status);status[field]+=1
            with self.assertRaises(ValueError):self.analyze(status=status)
    def test_timestamp_and_terminal_guards(self):
        for index,changes in ((0,dict(ns=9)),(3,dict(ns=101)),(3,dict(ns=80)),(1,dict(kind=4,handle=0,parent=0))):
            rows=copy.deepcopy(self.rows);rows[index].update(changes)
            with self.assertRaises(ValueError):self.analyze(rows)
    def test_bulk_is_ambiguous(self):
        self.rows[2]['aux']=2;row=self.analyze()[0];self.assertIn('bulk_dequeue',row['ambiguities']);self.assertEqual(row['residence'],[])
    def test_missing_enqueue_is_censored(self):
        self.rows.pop(1);self.status.update(records=3,emitted=3);row=self.analyze()[0];self.assertIn('dequeue_without_enqueue',row['ambiguities']);self.assertEqual(row['residence'],[])
    def test_pointer_reuse_uses_distinct_ids(self):
        second=[dict(r,cookie=2,ns=r['ns']+100) for r in self.rows];self.status.update(created=2,retired=2,records=8,emitted=8,detach_before_ns=200);self.assertEqual([r['cookie'] for r in self.analyze(self.rows+second)],[1,2])
    def test_consume_is_not_delivery(self):
        self.rows[-1]['kind']=6;self.assertEqual(self.analyze()[0]['outcome'],'consumed_before_driver')
    def test_detach_callback_runs_after_drain_before_capture_close(self):
        from m3_capture import stop_captures
        order=[]
        class Lab:
            containers={'robot':'owned-robot','operator':'owned-operator'}
            run=Path('/unused')
            def inside(self,role,label,argv):order.append(label)
        with patch('time.sleep'),patch('m3_capture_drain.check',side_effect=lambda *a:order.append('drained')):
            stop_captures(Lab(),drain_check=True,before_close=lambda:order.append('detached'))
        self.assertLess(order.index('competitor-stop'),order.index('drained'));self.assertLess(order.index('drained'),order.index('detached'));self.assertLess(order.index('detached'),order.index('robot-capture-stop'))
    def test_detach_failure_still_closes_native_captures(self):
        from m3_capture import stop_captures
        order=[]
        class Lab:
            containers={'robot':'owned-robot','operator':'owned-operator'}
            def inside(self,role,label,argv):order.append(label)
        def fail():raise ValueError('detach failure')
        with patch('time.sleep'),self.assertRaisesRegex(RuntimeError,'detach failure'):stop_captures(Lab(),before_close=fail)
        self.assertIn('robot-capture-stop',order);self.assertIn('operator-capture-stop',order)
    def test_packet_windows_keep_queued_carry_out(self):
        from m3_arp_packet_windows import membership
        rows=self.analyze();window=membership(rows,25,50)
        self.assertEqual(window['carry_in_ids'],[1]);self.assertEqual(window['carry_out_ids'],[1]);self.assertEqual(window['created_counts']['qdisc_drop'],0);self.assertEqual(window['lifetimes'][0]['outcome'],'driver_start')
        self.assertEqual(membership(rows,11,19)['lifetimes'],[])
    def test_packet_window_terminal_drop_is_not_creation_count(self):
        from m3_arp_packet_windows import membership
        self.rows[-1].update(kind=5,aux=77);rows=self.analyze();window=membership(rows,50,95)
        self.assertTrue(window['lifetimes'][0]['terminal_inside']);self.assertFalse(window['lifetimes'][0]['created_inside']);self.assertEqual(window['created_counts']['qdisc_drop'],0)
        self.assertEqual(membership(rows,20,90)['created_counts']['qdisc_drop'],1)
        with self.assertRaises(ValueError):membership(rows,90,20)
    def test_old_readiness_schema_rejected(self):
        self.ready['version']=1
        with self.assertRaisesRegex(ValueError,'readiness'):self.analyze()
    def test_owned_request_and_reply_fields(self):
        addresses=dict(operator='192.0.2.1',robot='192.0.2.2');macs=dict(operator='02:00:00:00:00:01',robot='02:00:00:00:00:02')
        req=request_frame(addresses['operator'],addresses['robot'],macs['operator'],macs['robot']);rep=reply_header(addresses,macs)
        self.assertEqual(len(req),42);self.assertEqual(req[20:22],b'\0\1');self.assertEqual(len(rep),42);self.assertEqual(rep[20:22],b'\0\2');self.assertEqual(rep[:6],req[6:12]);self.assertEqual(rep[38:],req[28:32])
        with self.assertRaises(ValueError):request_frame('192.0.2.1','192.0.2.1',macs['operator'],macs['robot'])
        with self.assertRaises(ValueError):request_frame('192.0.2.1','192.0.2.2','ff:ff:ff:ff:ff:ff',macs['robot'])


if __name__=='__main__':unittest.main()
