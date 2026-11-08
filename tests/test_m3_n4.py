import copy
import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_n4 import check_outcome,ID
from m3_failure_detection import record_count


def fixture(phase='admission',state=4):
    record=dict(route=100,payload_hash=hashlib.sha256(struct.pack('!IIIIQQ',0x52574331,100,100,5000,0,1)).hexdigest(),owner_epoch='01'*16,source_epoch='01'*16,source_ns=100,deadline_ns=5_000_000_100,session='02'*16,state=state,reason=0 if state==4 else 1,revision=3 if state==4 else 2,result_valid=state==4,result_generation=1 if state==4 else 0,dispatched_ns=1000,finished_ns=2000)
    a=dict(entries={ID:copy.deepcopy(record)});b=copy.deepcopy(a);b['entries'][ID]['owner_epoch']='03'*16
    sender=dict(commands_sent=1,fault=0,worker_fault=0)
    receiver=dict(fault=0,worker_fault=0,effects=int(state==4),generation=int(state==4),rate_hz=100 if state==4 else 200)
    barrier=dict(ns=3000,effects=0);resumed=dict(begin_ns=500)
    visible=None if phase=='admission' else dict(state=3,result_valid=False,finished_ns=0) if phase=='started' else dict(state=4,result_valid=True,finished_ns=2000)
    initial={'operator':dict(owner='01'*16,snapshot=dict(session='02'*16)),'robot':dict(owner='03'*16,snapshot=dict(session='02'*16))}
    submitted=dict(origin_ns=100,deadline_ns=5_000_000_100)
    return [phase,sender,receiver,a,b,barrier,resumed,visible,initial,submitted]


class N4OutcomeTests(unittest.TestCase):
    def test_durable_success_or_safe_decline_and_commit_recovery(self):
        for phase,state in (('admission',4),('admission',6),('started',4),('started',6),('committed',4)):
            result=check_outcome(*fixture(phase,state));self.assertEqual(result['state'],state)

    def test_replay_deadline_changed_proof_or_false_success_fails(self):
        for fault in ('replay','deadline','proof','effects','rate'):
            a=fixture()
            if fault=='replay':a[1]['commands_sent']=2
            if fault=='deadline':
                for journal in a[3:5]:journal['entries'][ID]['deadline_ns']+=1
            if fault=='proof':a[4]['entries'][ID]['payload_hash']='cd'*32
            if fault=='effects':a[2]['effects']=2
            if fault=='rate':a[2]['rate_hz']=200
            with self.assertRaises(ValueError):check_outcome(*a)

    def test_phase_placement_uncertainty_and_stale_start_fail(self):
        for fault in ('admitted','committed','unknown','stale','started'):
            a=fixture('committed' if fault=='committed' else 'started' if fault=='started' else 'admission')
            if fault=='admitted':a[7]=dict(state=2)
            if fault=='committed':a[7]['state']=3
            if fault=='unknown':
                for journal in a[3:5]:journal['entries'][ID]['state']=8
            if fault=='stale':a[6]['begin_ns']=6_000_000_000
            if fault=='started':a[5]['effects']=1
            with self.assertRaises(ValueError):check_outcome(*a)

    def test_owner_ingress_and_payload_provenance_are_not_rebound(self):
        for fault in ('owner','session','origin','payload'):
            a=fixture()
            if fault=='owner':a[8]['robot']['owner']='ff'*16
            if fault=='session':a[8]['operator']['snapshot']['session']='ff'*16
            if fault=='origin':a[9]['origin_ns']+=1
            if fault=='payload':
                for journal in a[3:5]:journal['entries'][ID]['payload_hash']='ff'*32
            with self.assertRaises(ValueError):check_outcome(*a)

    def test_decline_cannot_hide_effect_or_lost_committed_result(self):
        a=fixture('admission',6);a[2]['effects']=1
        with self.assertRaises(ValueError):check_outcome(*a)
        with self.assertRaises(ValueError):check_outcome(*fixture('committed',6))


class FailureArtifactTests(unittest.TestCase):
    def test_real_record_counter_rejects_truncated_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'capture'
            header=struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1)
            packet=struct.pack('<IIII',0,0,14,14)+bytes(14);path.write_bytes(header+packet)
            self.assertEqual(record_count(path),1)
            for bad in (b'',header+packet[:-1],header+b'123'):
                path.write_bytes(bad)
                with self.assertRaises(ValueError):record_count(path)
