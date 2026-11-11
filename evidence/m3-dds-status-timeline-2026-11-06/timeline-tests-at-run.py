#!/usr/bin/env python3
import copy
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_dds_result_timeline import correlate,read_journal,common_clock


def fixture():
    command=dict(number=1,new_generation=1,terminal=4,submitted_monotonic_ns=10,result_observed_monotonic_ns=200,status_observations=2)
    sender=dict(route=100,payload_hash='hash',source_epoch='epoch',owner_epoch='epoch',session='session',source_ns=20,admitted_ns=30,dispatched_ns=0,finished_ns=190,deadline_ns=5000,state=4,revision=3,result_valid=True,result_generation=1)
    receiver=dict(sender,owner_epoch='receiver',admitted_ns=40,dispatched_ns=50,finished_ns=60)
    id=(1).to_bytes(16,'little').hex()
    return command,{id:sender},{id:receiver},id


class TimelineTests(unittest.TestCase):
    def test_missing_mixed_boot_and_nonzero_offset_proofs_reject(self):
        proof='eec6bb52-6781-4e81-8f80-7b87d00379da\nmonotonic 0 0\nboottime 0 0\n'
        self.assertEqual(common_clock(dict(robot=proof,operator=proof)),proof)
        for other in ('',proof.replace('eec6','fec6'),proof.replace('monotonic 0','monotonic 1')):
            with self.assertRaises(ValueError):common_clock(dict(robot=proof,operator=other))
        shifted=proof.replace('monotonic 0','monotonic 1')
        with self.assertRaisesRegex(ValueError,'zero'):common_clock(dict(robot=shifted,operator=shifted))

    def test_separates_prompt_receiver_finish_from_late_sender_result(self):
        command,a,b,id=fixture();r=correlate([command],a,b)[0]
        self.assertTrue(r['qualified'])
        self.assertEqual(r['deltas_ms']['receiver_finish_to_sender_observation'],130/1e6)
        self.assertAlmostEqual(sum(r['deltas_ms'].values()),r['total_ms'])
        self.assertIsNone(r['status_history']) # old evidence remains explicitly absent

    def test_missing_unknown_and_restarted_owner_withhold_decomposition(self):
        command,a,b,id=fixture()
        for variant in ('missing','unknown','owner'):
            aa=copy.deepcopy(a);bb=copy.deepcopy(b)
            if variant=='missing':bb.clear()
            if variant=='unknown':aa[id]['state']=8;aa[id]['result_valid']=False
            if variant=='owner':aa[id]['owner_epoch']='restarted'
            r=correlate([command],aa,bb)[0]
            self.assertFalse(r['qualified']);self.assertNotIn('deltas_ms',r)

    def test_context_mismatch_clock_regression_and_dispatch_deadline_are_errors(self):
        command,a,b,id=fixture()
        for variant in ('context','clock','deadline'):
            bb=copy.deepcopy(b);aa=copy.deepcopy(a)
            if variant=='context':bb[id]['source_epoch']='other'
            if variant=='clock':bb[id]['finished_ns']=191
            if variant=='deadline':aa[id]['deadline_ns']=bb[id]['deadline_ns']=50
            with self.assertRaises(ValueError):correlate([command],aa,bb)
        with self.assertRaisesRegex(ValueError,'duplicate'):correlate([command,command],a,b)

    def test_nonempty_wal_is_rejected_before_opening_database(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'journal.sqlite';path.write_bytes(b'not a DB')
            Path(str(path)+'-wal').write_bytes(b'live')
            with self.assertRaisesRegex(ValueError,'closed'):read_journal(path,1)
            self.assertEqual(path.read_bytes(),b'not a DB')


if __name__=='__main__':unittest.main()
