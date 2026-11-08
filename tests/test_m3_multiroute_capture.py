import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_multiroute_capture import expected_wire,verify_populations,verify_recovery
from test_m3_multiroute_accounting import setup


def fixture():
    source,sender,receiver,local,remote=setup()
    pair=next(e for e in local['events'] if e['point']==2 and e['message_number']==8)
    src=next(e for e in source['events'] if (e['route'],e['stamp_sec'],e['stamp_nanosec'])==(pair['route'],pair['stamp_sec'],pair['stamp_nanosec']))
    typed=next(e for e in receiver['rows'] if (e['route'],e['counter'])==(src['route'],src['counter']))
    typed['observed_ns']=pair['end_ns']+10
    identity=dict(initial_sequence=123,binding=dict(socket_id=99))
    return source,local,remote,receiver,identity,pair['end_ns']-1,pair['begin_ns']-1,pair['end_ns']+20


class MultirouteCaptureTests(unittest.TestCase):
    def test_dynamic_source_and_parity_populations_include_binding_offset(self):
        source,sender,receiver,local,remote=setup();identity=dict(initial_sequence=123,binding=dict(socket_id=99))
        keys=expected_wire(local['events'],identity)
        self.assertEqual(sum(n for k,n in keys.items() if k[1]),2500)
        self.assertEqual(sum(n for k,n in keys.items() if not k[1]),625)
        self.assertNotIn((123,1,99,False),keys)
        one=expected_wire(local['events'],identity,(8,))
        self.assertNotIn((130,8,99,False),one);self.assertIn((130,0,99,False),one)
        self.assertEqual(sum(keys.values())-sum(one.values()),1)

    def test_origin_wrap_and_invalid_sdk_population(self):
        _,_,_,local,_=setup();identity=dict(initial_sequence=0x7ffffffc,binding=dict(socket_id=99))
        for e in local['events']:
            if e['point']==2:e['initial_sequence']=identity['initial_sequence']
        keys=expected_wire(local['events'],identity)
        self.assertIn((0,5,99,False),keys)
        for fault in ('missing','binding','origin','exclude'):
            events=copy.deepcopy(local['events']);excluded=()
            if fault=='missing':events.pop(2)
            if fault=='binding':events[0]['kind']=5
            if fault=='origin':events[0]['initial_sequence']=0
            if fault=='exclude':excluded=(99999,)
            with self.assertRaises(ValueError):expected_wire(events,identity,excluded)

    def test_no_capture_mismatch_or_unreconciled_footer_is_rescued(self):
        expected={(1,2,3,False):1}
        verify_populations(expected,expected,expected,dict(population_reconciled=True))
        for a,b,f in (({},expected,True),(expected,{},True),(expected,expected,False)):
            with self.assertRaises(ValueError):verify_populations(expected,a,b,dict(population_reconciled=f))

    def test_mixed_route_repair_requires_accepted_hash_and_active_classifier(self):
        result=verify_recovery(*fixture())
        self.assertEqual(result['source_route'],2);self.assertEqual(result['message_number'],8)
        self.assertEqual({e['route'] for e in result['row_messages']},{1,2})
        for fault in ('route','decision','hash','parity','remove','install'):
            args=list(fixture());source,local,remote,receiver,identity,parity,installed,removed=args
            if fault=='route':
                for e in local['events']:e['route']=1
            if fault=='decision':
                for e in remote['events']:
                    if e['message_number']==8:e['result']=12
            if fault=='hash':
                for e in receiver['rows']:
                    if e['route']==2 and e['counter']==2:e['payload_sha256']='cd'*32
            if fault=='parity':args[5]=removed
            if fault=='remove':args[7]=parity
            if fault=='install':args[6]=removed
            with self.assertRaises(ValueError):verify_recovery(*args)
