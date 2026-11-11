from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_multiroute_capture import verify_two_loss,expected_wire
from m3_multiroute_accounting import assess
from test_m3_multiroute_accounting import setup


def fixture():
    source,sender,receiver,local,remote=setup();selected=set()
    for h in local['events']:
        if h['point']==2 and h['message_number'] in (7,8):
            src=next(e for e in source['events'] if (e['route'],e['stamp_sec'],e['stamp_nanosec'])==(h['route'],h['stamp_sec'],h['stamp_nanosec']))
            selected.add((src['route'],src['counter']))
    for row in receiver['rows']:
        row['observed_ns']=row['stamp_sec']*10**9+row['stamp_nanosec']+10
    receiver['rows']=[r for r in receiver['rows'] if (r['route'],r['counter']) not in selected]
    remote['events']=[e for e in remote['events'] if e['message_number'] not in (7,8)]
    for k in ('transport_samples_received','sensor_polled','samples_published'):receiver['end']['bridge'][k]-=2
    for name in ('imu','joint'):receiver['end']['bridge'][name+'_age_upper_histogram_ms'][1]-=1
    receiver['end']['monotonic_ns']=sender['pause']['monotonic_ns']
    identity=dict(initial_sequence=123,binding=dict(socket_id=99))
    return source,sender,receiver,local,remote,identity,1_020_000_100,999_999_990,11_000_000_100


def check(args):
    source,sender,receiver,local,remote,identity,parity,installed,removed=args
    return verify_two_loss(source,local,remote,receiver,identity,parity,installed,removed)


class MixedRouteTwoLossTests(unittest.TestCase):
    def test_two_distinct_route_sources_absent_with_subsequent_progress(self):
        args=fixture();r=check(args)
        self.assertEqual({s['source_route'] for s in r['selected_sources']},{1,2})
        self.assertEqual([s['message_number'] for s in r['selected_sources']],[7,8])
        self.assertTrue(all(s['subsequent_observations'] for s in r['selected_sources']))
        source,sender,receiver,local,remote,*_=args
        accounting=assess(source,sender,receiver,local,remote)
        self.assertEqual(accounting['sdk_without_receiver_decision'],[7,8])
        self.assertEqual(accounting['window']['losses']['srt_accept_to_receiver_gap'],2)
        self.assertFalse(any(accounting['window']['balances'].values()))

    def test_exclusions_remove_only_selected_sources_not_shared_sequence_parity(self):
        source,sender,receiver,local,remote,identity,*_=fixture();keys=expected_wire(local['events'],identity,(7,8))
        self.assertNotIn((129,7,99,False),keys);self.assertNotIn((130,8,99,False),keys)
        self.assertIn((130,0,99,False),keys)
        self.assertEqual(sum(n for k,n in keys.items() if k[1]),2498)

    def test_extra_gap_rejection_or_selected_receiver_event_fails(self):
        for fault in ('extra','rejection','selected'):
            args=list(fixture());remote=args[4]
            if fault=='extra':remote['events'].pop()
            if fault=='rejection':remote['events'][0]['result']=12
            if fault=='selected':remote['events'].append(dict(remote['events'][0],message_number=7))
            with self.assertRaises(ValueError):check(args)

    def test_typed_selected_absence_and_progress_are_required(self):
        for fault in ('observed','progress','route','origin'):
            args=list(fixture());source,sender,receiver,local,remote,identity,*_=args
            if fault=='observed':receiver['rows'].append(dict(route=2,counter=2))
            if fault=='progress':receiver['rows']=[r for r in receiver['rows'] if r['route']!=2]
            if fault=='route':
                for e in local['events']:
                    if e['point']==1 and e['route']==2:e['route']=3
                    if e['point']==2 and e['route']==2:e['route']=3
            if fault=='origin':identity['initial_sequence']+=1
            with self.assertRaises(ValueError):check(args)

    def test_parity_cutoff_and_classifier_brackets_fail_closed(self):
        for fault in ('parity','install','remove','cutoff'):
            args=list(fixture())
            if fault=='parity':args[6]=args[8]+1
            if fault=='install':args[7]=args[6]+1
            if fault=='remove':args[8]=args[2]['end']['monotonic_ns']-1
            if fault=='cutoff':args[2]['end']['monotonic_ns']=args[6]-1
            with self.assertRaises(ValueError):check(args)
