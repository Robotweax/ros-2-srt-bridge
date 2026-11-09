import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_closure_assessor import assess_n3_result,provenance,cleanup,evaluate_sequence,assess_combined,assess_outage
from m3_source_preflight import IMAGE
import test_m3_n5_sensor_audit
from m3_accounting import summarize_window


def n3():
    status=dict(complete=True,records=2,seen=2,submitted=2,reserve_failed=0,copy_failed=0)
    footer=dict(population_reconciled=True,file_integrity_valid=True,kernel_drops=0,captured_records=2,filtered_records=2)
    captures={role:dict(status=copy.deepcopy(status),footer=copy.deepcopy(footer)) for role in ('operator','robot')}
    a=dict(passed=True,cadence=dict(duration_ns=30_050_000_000,routes={r:dict(cadence_pass=True,skipped_slots=0) for r in ('1','2')}),source_trace_status=dict(attempted=7510,recorded=7510,printed=7510,complete=True),sender_trace_status=dict(attempted=15000),receiver_trace_status=dict(attempted=7200),sdk_without_receiver_decision=[],window=dict(losses=dict(srt_accept_to_receiver_gap=0,receiver_rejected=0),balances=dict(total=0),age_upper_histograms={r:dict(count=1,maximum_ms=10) for r in ('imu','joint')}))
    return dict(status='passed',seconds=30,base_seed=1701,losses=0,assessment=a,identity_captures=captures,measurement_captures=copy.deepcopy(captures),child_shutdown={r:dict(passed=True) for r in ('operator','robot')})


class StrictAssessorTests(unittest.TestCase):
    def test_rate_pass_does_not_hide_source_skip(self):
        d=n3();slot=dict(source_seconds=30,seed=1701,losses=0);assess_n3_result(d,slot)
        d['assessment']['cadence']['routes']['1']['skipped_slots']=3
        with self.assertRaisesRegex(ValueError,'source scheduling'):assess_n3_result(d,slot)
    def test_native_pcap_footer_histogram_and_child_failures_refuse(self):
        for kind in ('native','pcap','source_footer','histogram','child'):
            d=n3()
            if kind=='native':d['measurement_captures']['operator']['status']['seen']=3
            elif kind=='pcap':d['identity_captures']['robot']['footer']['kernel_drops']=1
            elif kind=='source_footer':d['assessment']['source_trace_status']['printed']=0
            elif kind=='histogram':d['assessment']['window']['age_upper_histograms']['imu']['count']=0
            else:d['child_shutdown']['robot']['passed']=False
            with self.subTest(kind=kind),self.assertRaises(ValueError):assess_n3_result(d,dict(source_seconds=30,seed=1701,losses=0))
    def test_outage_requires_kernel_direction_hold_and_drop_evidence(self):
        event=lambda begin,end,loss:dict(bracket=dict(begin_ns=begin,end_ns=end),qdisc=dict(kind='netem',options=dict(seed=1702,**{'loss-random':dict(loss=loss)})))
        data=dict(outage_install={'operator':event(1,2,1)},outage_restore={'operator':event(3_000_000_003,3_000_000_004,0)},hold=dict(begin_ns=3,end_ns=2_000_000_003),guaranteed_outage_ns=[2,3_000_000_003],outage_final={'operator':[dict(kind='netem',drops=1)]})
        assess_outage(data,'to-robot','guaranteed_outage_ns','outage_final')
        for kind in ('direction','interval','hold','drops','loss'):
            d=copy.deepcopy(data)
            if kind=='direction':d['outage_restore']={}
            elif kind=='interval':d['guaranteed_outage_ns'][0]=3
            elif kind=='hold':d['hold']['begin_ns']=1
            elif kind=='drops':d['outage_final']['operator'][0]['drops']=0
            else:d['outage_install']['operator']['qdisc']['options']['loss-random']['loss']=0
            with self.subTest(kind=kind),self.assertRaises(ValueError):assess_outage(d,'to-robot','guaranteed_outage_ns','outage_final')

    def test_runtime_and_source_freeze_are_mandatory(self):
        layout=dict(name='sender-reconcile',calibration_sha256='hash',matched_build_sha256={'worker':'x'})
        freeze=dict(schema_version=1,runtime_layout=layout,candidate_manifest_sha256='hash',source_sha256={'tool':'sha'})
        record=dict(image=IMAGE,runtime_layout=layout,source_sha256={'tool':'sha'});provenance(record,freeze)
        for key,value in [('image','other'),('runtime_layout',dict(layout,name='baseline')),('source_sha256',{}),('source_sha256',{'tool':'changed'})]:
            with self.subTest(key=key),self.assertRaises(ValueError):provenance(dict(record,**{key:value}),freeze)
    def test_assessment_precedes_next_case_and_failed_harness_pass_stops_all_stages(self):
        events=[];slots=[dict(id=n,stage=s) for n,s in ((1,'N3'),(2,'N0'),(3,'N4'))]
        def produce(slot):events.append(('produce',slot['id']));return dict(status='passed')
        def assess(slot,report):
            events.append(('assess',slot['id']))
            if slot['id']==2:raise ValueError('strict progress unresolved')
            return dict(status='passed')
        result=evaluate_sequence(slots,produce,assess,lambda value:None)
        self.assertEqual(events,[('produce',1),('assess',1),('produce',2),('assess',2)])
        self.assertEqual([r['status'] for r in result['rows']],['passed','failed','not_executed']);self.assertFalse(result['complete_M3_acceptance'])
        self.assertEqual(result['rows'][1]['produced']['status'],'passed')
    def test_cleanup_failure_stops_after_producer_exception_or_assessor_refusal(self):
        for outcome in ('producer','cleanup','refused'):
            calls=[]
            def produce(slot):
                calls.append(slot)
                if outcome=='producer':raise ValueError('producer failed')
                return 'closed'
            def assess(slot,value):
                if outcome=='cleanup':raise ValueError('cleanup failed')
                return dict(status='failed')
            r=evaluate_sequence([1,2],produce,assess,lambda value:None)
            self.assertEqual(calls,[1]);self.assertEqual(r['rows'][1]['status'],'not_executed')
    def test_owned_cleanup_and_credential_absence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rows=[dict(label=n,exit_code=0) for n in ('operator-remove','robot-remove','network-remove')]
            (root/'network.json').write_text(json.dumps(dict(commands=rows)));cleanup(root)
            (root/'passphrase').write_text('synthetic')
            with self.assertRaisesRegex(ValueError,'credential'):cleanup(root)
            (root/'passphrase').unlink();rows[-1]['exit_code']=1;(root/'network.json').write_text(json.dumps(dict(commands=rows)))
            with self.assertRaisesRegex(ValueError,'cleanup'):cleanup(root)
    def test_combined_harness_pass_does_not_hide_unresolved_command(self):
        a,b,t=test_m3_n5_sensor_audit.fixture();b['receiver']['joint_age_upper_histogram_ms'][10]=1;b['receiver']['samples_published']+=1;b['receiver']['sensor_polled']+=1;b['receiver']['transport_samples_received']+=1;b['sender']['sensor_sent']+=1;b['sender']['sensor_inputs']+=1;b['sender']['sensor_submitted']+=1;b['sender']['samples_ingress']+=1;b['device']['joints_published']=1;b['observer']['joints']=1;b['receiver']['joint_age_upper_max_ns']=10000000
        window=summarize_window(a,b,t);window['source_actual_hz'] # Rates are verified separately below.
        # Use a short synthetic fixture; mock only the already unit-tested publication reader.
        sensor=dict(window=dict(window,source_enabled_seconds=300,source_actual_hz=dict(imu=200,joints=50)),publication_age={r:dict(nonempty=True) for r in ('imu','joint')})
        state=dict(complete=True,artifact_version=2,clock='kernel_monotonic',time_namespace_zero=True,records=1,seen=1,submitted=1,reserve_failed=0,copy_failed=0)
        report=dict(status='passed',profile='N0',seed=1701,seconds=300,pcap_population_reconciled=True,captures={r:dict(tcpdump_population_reconciled=True,tcpdump_file_integrity_valid=True,tcpdump_kernel_drops=0) for r in ('operator','robot')},monotonic_captures=dict(statuses={r:state for r in ('operator','robot')}),results=dict(typed_errors=[],direct_dds_samples=0,checkpoints=dict(begin=a,end=b),publication_interval=t,shutdowns=[dict(exit_code=0,seconds=.1)]),clock_namespace_proof={},measurement_window=sensor['window'],provider_diagnostics={'op':dict(complete=True,status=dict(dropped=0,exhausted=0))},sensor_provider_diagnostics={'op':dict(complete=True,status=dict(dropped=0,exhausted=0))})
        report['results']['publication_interval']=dict(resume_monotonic_ns=10,pause_monotonic_ns=20)
        state.update(ready_ns=1,stop_before_ns=30)
        report['monotonic_captures']['windows']=dict(source_enabled={r:dict(qualified=True,window_monotonic_ns=[10,20],frame_interpretation=dict(qualified=True)) for r in ('operator','robot')})
        with patch('m3_closure_assessor.common_clock'),patch('m3_closure_assessor.assess_publications',return_value=sensor),patch('m3_closure_assessor.command_progress',return_value=dict(entries=[{}],no_unresolved_attempts=False)),self.assertRaisesRegex(ValueError,'strict command progress'):
            assess_combined(report,Path('/synthetic'),dict(profile='N0',seed=1701,source_seconds=300))


if __name__=='__main__':unittest.main()
