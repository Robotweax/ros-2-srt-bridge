import copy
import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'evidence/m3-socket-disposition-2026-11-10/socket_gate.py'
s=importlib.util.spec_from_file_location('socket_disposition_gate',path);gate=importlib.util.module_from_spec(s);s.loader.exec_module(gate)

class SocketDispositionTests(unittest.TestCase):
    def records(self,values=(-1,-1,-1,-1)):
        rows=[]
        def add(point,detail=0):rows.append(dict(point=point,detail=detail,sequence=len(rows)+1,monotonic_ns=len(rows)+1,pid=7,tid=8,dropped_before=0))
        add('transport_shutdown_begin')
        for phase,offset in (('control',0),('sensor',2)):
            add(phase+'_close_begin')
            for slot,fd in zip(gate.SLOTS[offset:offset+2],values[offset:offset+2]):
                add(slot,fd)
                if fd>=0:
                    for point,detail in [('socket_epoll_remove_begin',fd),('socket_close_begin',fd),('socket_close_result',0),('socket_close_end',fd)]:add(point,detail)
            add(phase+'_close_end')
        return rows
    def renumber(self,rows):
        for i,r in enumerate(rows):r.update(sequence=i+1,monotonic_ns=i+1)
    def test_explicit_all_preclosed_caller_passes_without_close_markers(self):
        proof=gate.check(self.records());self.assertEqual(len(proof['slots']),4);self.assertEqual(proof['traced_successful_close_fds'],[])
    def test_valid_data_and_listener_slots_require_successful_close_pairs(self):
        proof=gate.check(self.records((10,11,12,13)));self.assertEqual(proof['traced_successful_close_fds'],[10,11,12,13])
    def test_missing_duplicate_and_unknown_dispositions_reject(self):
        for mode in ('missing','duplicate','invalid'):
            rows=self.records()
            if mode=='missing':rows.pop(2)
            elif mode=='duplicate':rows.insert(3,copy.deepcopy(rows[2]))
            else:rows[2]['detail']=-2
            self.renumber(rows)
            with self.subTest(mode=mode),self.assertRaises(ValueError):gate.check(rows)
    def test_close_errors_missing_result_and_fd_mismatch_reject(self):
        for mode in ('error','missing','fd'):
            rows=self.records((10,-1,-1,-1));result=next(i for i,r in enumerate(rows) if r['point']=='socket_close_result')
            if mode=='error':rows[result]['detail']=-1
            elif mode=='missing':rows.pop(result)
            else:rows[result+1]['detail']=20
            self.renumber(rows)
            with self.subTest(mode=mode),self.assertRaises(ValueError):gate.check(rows)
    def test_already_invalid_cannot_conceal_orphan_close(self):
        rows=self.records((10,-1,-1,-1));rows[2]['detail']=-1
        with self.assertRaises(ValueError):gate.check(rows)
    def test_wrong_thread_phase_loss_and_time_reversal_reject(self):
        for mode in ('thread','phase','drop','time'):
            rows=self.records((10,-1,-1,-1))
            if mode=='thread':rows[2]['tid']=9
            if mode=='phase':rows[1]['point']='unrelated'
            if mode=='drop':rows[-1]['dropped_before']=1
            if mode=='time':rows[4]['monotonic_ns']=99
            with self.subTest(mode=mode),self.assertRaises(ValueError):gate.check(rows)
    def test_concurrent_file_order_uses_sequence_identity_not_write_order(self):
        rows=self.records((10,-1,-1,-1));rows[2],rows[3]=rows[3],rows[2]
        self.assertEqual(gate.check(rows)['traced_successful_close_fds'],[10])
        spec=importlib.util.spec_from_file_location('socket_lifecycle_sequence',path.parent/'lifecycle.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        stages=[dict(pid=7,tid=8,sequence=i,point=p,monotonic_ns=t,dropped_before=0) for i,p,t in ((1,'worker_join_begin',10),(2,'worker_join_end',20))]
        self.assertEqual(module.join_end(list(reversed(stages)),7),20)

if __name__=='__main__':unittest.main()
