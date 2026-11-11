import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_probe_trace_analysis import validate,summarize


def event(point,role='operator',time=10):
    return dict(point=point,probe_trace_version=1,monotonic_ns=time+1,evaluated_ns=time,reason=0,detail=9,value=0,
        owner_epoch=('01' if role=='operator' else '02')*16,entry_owner_epoch=('01' if role=='operator' else '02')*16,
        session='03'*16,control_generation=1,sensor_generation=1,request='00'*16,route=0,request_sequence=1,origin_ns=10,
        probe_t1=10,probe_t2=0,probe_t3=0,probe_pending_before=0,probe_pending_after=10,probe_end_ns=0,
        probe_fields_available=True,probe_mapper_submitted=False,probe_message_bytes=0,probe_sdk_bytes=0,
        clock_error=1,clock_deadline_ns=0,clock_observed=False,probe_anchor_ns=0,offset_lower_ns=0,offset_upper_ns=0)


def exchange(initiator='operator',base=10):
    peer='robot' if initiator=='operator' else 'operator';a=event(50,initiator,base);a.update(origin_ns=base,probe_t1=base,probe_pending_after=base)
    q=dict(a,point=51,evaluated_ns=base+1,monotonic_ns=base+2)
    sdk=dict(q,point=52,evaluated_ns=base+2,monotonic_ns=base+4,probe_fields_available=False,probe_t1=0,probe_end_ns=base+3,probe_message_bytes=103,probe_sdk_bytes=103)
    receive=dict(a,point=53,owner_epoch=event(50,peer)['owner_epoch'],evaluated_ns=base+5,monotonic_ns=base+6)
    reply=dict(receive,point=51,detail=10,entry_owner_epoch=receive['owner_epoch'],origin_ns=base+5,probe_t2=base+5,probe_t3=base+5,evaluated_ns=base+6,monotonic_ns=base+7)
    rsdk=dict(reply,point=52,probe_fields_available=False,probe_t1=0,probe_t2=0,probe_t3=0,evaluated_ns=base+7,probe_end_ns=base+8,monotonic_ns=base+9,probe_message_bytes=117,probe_sdk_bytes=117)
    admission=dict(reply,point=53,owner_epoch=a['owner_epoch'],probe_pending_before=base,probe_pending_after=0,probe_mapper_submitted=True,clock_error=0,clock_observed=True,probe_anchor_ns=base+10,evaluated_ns=base+10,monotonic_ns=base+11)
    return {initiator:[a,q,sdk,admission],peer:[receive,reply,rsdk]}


class ProbeTraceTests(unittest.TestCase):
    def test_availability_and_actual_mapper_call_are_required(self):
        e=event(53);e.update(detail=10,probe_t2=11,probe_t3=11,probe_pending_before=10,probe_pending_after=0,probe_mapper_submitted=True,clock_error=0,clock_observed=True,evaluated_ns=20,monotonic_ns=21,probe_anchor_ns=20);validate(e)
        for key,value in [('probe_fields_available',False),('probe_pending_before',9),('probe_anchor_ns',19),('evaluated_ns',2000000010),('probe_trace_version',True)]:
            with self.subTest(key=key),self.assertRaises(ValueError):validate(dict(e,**{key:value}))
        e.update(probe_mapper_submitted=False,value=15,probe_pending_after=10,probe_pending_before=10);validate(e)
        busy=event(50);busy.update(value=16,probe_fields_available=False,probe_t1=0,probe_pending_before=10);validate(busy)
        busy['probe_pending_after']=0
        with self.assertRaisesRegex(ValueError,'busy'):validate(busy)
    def test_sdk_brackets_and_full_byte_results(self):
        e=exchange()['operator'][2];validate(e)
        for k,v in [('probe_end_ns',e['evaluated_ns']-1),('probe_sdk_bytes',1),('probe_t1',10)]:
            with self.subTest(key=k),self.assertRaises(ValueError):validate(dict(e,**{k:v}))
        e.update(value=6001,probe_sdk_bytes=-1);validate(e)
    def traces(self):
        merged={'operator':[],'robot':[]}
        for family in (exchange(),exchange('robot',100)):
            for role,rows in family.items():merged[role]+=rows
        return {r+'-bridge-0.log':dict(complete=True,events=rows) for r,rows in merged.items()}
    def test_correlates_both_epochs_and_exact_echo_times(self):
        t=self.traces();result=summarize(t);self.assertEqual(len(result['lifecycles']),2)
        self.assertEqual(sum(x['qualified_mapper_admissions'] for x in result['lifecycles']),2)
        for row in t['operator-bridge-0.log']['events']:
            if row['point']==53 and row['detail']==10:row['probe_t2']+=1;row['probe_t3']+=1
        with self.assertRaisesRegex(ValueError,'echo correlation'):summarize(t)
    def test_no_silent_missing_or_misjoined_sdk_records(self):
        t=self.traces();bad=copy.deepcopy(t)
        next(e for e in bad['operator-bridge-0.log']['events'] if e['point']==52)['origin_ns']+=1
        with self.assertRaisesRegex(ValueError,'SDK/queue'):summarize(bad)
        t['operator-bridge-0.log']['complete']=False
        with self.assertRaisesRegex(ValueError,'incomplete'):summarize(t)
        with self.assertRaisesRegex(ValueError,'missing'):summarize({'operator':dict(complete=True,events=[])})


if __name__=='__main__':unittest.main()
