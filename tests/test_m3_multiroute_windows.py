import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_multiroute_window import budget,verify_window
from m3_multiroute_cohort import short_cases,thirty_second_cases,execute


def assessment():
    return dict(cadence=dict(duration_ns=10_050_000_000),source_trace_status=dict(attempted=2513),sender_trace_status=dict(attempted=5001),sdk_without_receiver_decision=[],window=dict(losses=dict(srt_accept_to_receiver_gap=0,receiver_rejected=0)))


class WindowTests(unittest.TestCase):
    def test_budget_reserves_fence_margin_without_expanding_storage(self):
        self.assertEqual(budget(10)['source_record_allowance'],2750)
        self.assertEqual(budget(30)['source_record_allowance'],7750)
        self.assertEqual(budget(30)['sender_record_allowance'],15501)
        self.assertEqual(budget(30)['source_limit'],10000)
        for value in (True,10.,0,40,600):
            with self.assertRaises(ValueError):budget(value)

    def test_actual_duration_and_record_population_are_checked(self):
        self.assertEqual(verify_window(assessment(),10,0)['nominal_seconds'],10)
        a=assessment();a['cadence']['duration_ns']=30_050_000_000;a['source_trace_status']['attempted']=7513;a['sender_trace_status']['attempted']=15001
        verify_window(a,30,1)
        for fault in ('short','long','source','sender'):
            a=assessment()
            if fault=='short':a['cadence']['duration_ns']=9_999_999_999
            if fault=='long':a['cadence']['duration_ns']=11_000_000_001
            if fault=='source':a['source_trace_status']['attempted']=2751
            if fault=='sender':a['sender_trace_status']['attempted']=5502
            with self.assertRaises(ValueError):verify_window(a,10,0)

    def test_receiver_gap_and_rejection_cannot_become_successful_baseline_or_repair(self):
        a=assessment();a['sdk_without_receiver_decision']=[7,8];a['window']['losses']['srt_accept_to_receiver_gap']=2
        verify_window(a,10,2)
        for losses in (0,1):
            with self.assertRaises(ValueError):verify_window(a,10,losses)
        a=assessment();a['window']['losses']['receiver_rejected']=1
        with self.assertRaises(ValueError):verify_window(a,10,1)


class CohortTests(unittest.TestCase):
    def test_exact_case_order_and_early_failure_leave_rest_unexecuted(self):
        cases=short_cases();self.assertEqual([c['name'] for c in cases],['baseline-1701','baseline-2903','baseline-4211','one-loss-1701','one-loss-2903','one-loss-4211'])
        invoked=[];updates=[]
        def invoke(case):
            invoked.append(case['name']);return dict(status='failed' if len(invoked)==2 else 'passed',error='original failure' if len(invoked)==2 else None)
        result=execute(cases,invoke,lambda value:updates.append(copy.deepcopy(value)))
        self.assertEqual(invoked,['baseline-1701','baseline-2903']);self.assertEqual(result['status'],'failed')
        self.assertEqual([c['status'] for c in result['cases']],['passed','failed']+['not_executed']*4)
        self.assertEqual(result['cases'][1]['error'],'original failure');self.assertFalse(result['full_N3_qualification'])

    def test_thirty_second_matrix_is_fixed_and_stops_without_adapting(self):
        cases=thirty_second_cases()
        self.assertEqual([(c['seed'],c['losses'],c['seconds']) for c in cases],[(s,n,30) for s in (1701,2903,4211) for n in (0,1,2)])
        invoked=[]
        result=execute(cases,lambda c:invoked.append(c['name']) or dict(status='failed'),lambda value:None)
        self.assertEqual(invoked,['baseline-1701'])
        self.assertEqual([c['status'] for c in result['cases']],['failed']+['not_executed']*8)

    def test_exception_stops_cohort_and_all_success_completes_without_retry(self):
        def fail(case):raise ValueError('fixture exception')
        result=execute(short_cases(),fail,lambda value:None)
        self.assertEqual(result['cases'][0]['error'],'fixture exception');self.assertEqual(result['cases'][1]['status'],'not_executed')
        calls=[]
        result=execute(short_cases(),lambda case:calls.append(case['name']) or dict(status='passed'),lambda value:None)
        self.assertEqual(len(calls),6);self.assertEqual(result['status'],'passed')
