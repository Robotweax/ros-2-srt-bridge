import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(0,str(ROOT/'ros2/robotweax_srt_bridge_demo/scripts'))
from scenario_timeline import Timeline
from m3_n5_progress import timeline,command_progress


def state(**values):
    return dict(ready=False,failed=False,control_publishers=0,control_subscribers=0,hello_publishers=0,hello_subscribers=0,hellos_received=0,**values)


class TimelineTests(unittest.TestCase):
    def test_bounded_history_refuses_reuse_and_exhaustion_without_replacing_records(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'timeline';t=Timeline(p,limit=2)
            t.observe('ready',state(),{},now=1)
            t.observe('ready',state(),{},now=2)  # throttled, same phase/readiness
            t.observe('next',state(),{},now=3)
            with self.assertRaisesRegex(ValueError,'budget'):t.observe('third',state(),{},now=4)
            t.close()
            with self.assertRaisesRegex(ValueError,'exhausted'):timeline(p)
            self.assertEqual(len(p.read_text().splitlines()),3)
            original=p.read_bytes()
            with self.assertRaises(FileExistsError):Timeline(p)
            self.assertEqual(p.read_bytes(),original)

    def test_missing_diagnostics_match_hello_and_readiness_are_distinct(self):
        cases=[(None,'no_command_diagnostics'),(state(),'no_complete_endpoint_match_observed')]
        matched=state();matched.update(control_publishers=1,control_subscribers=1,hello_publishers=1,hello_subscribers=1)
        cases.append((matched,'no_received_hello_observed'))
        hello=dict(matched,hellos_received=4);cases.append((hello,'hello_received_but_not_ready'))
        cases.append((dict(hello,ready=True),'ready_observed'))
        for s,expected in cases:
            with self.subTest(expected=expected),tempfile.TemporaryDirectory() as d:
                p=Path(d)/'timeline';t=Timeline(p);t.observe('wait',s,{'imu':12},now=1);t.close()
                self.assertEqual(timeline(p)['classification'],expected)

    def test_truncated_population_and_regressed_clock_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'timeline';t=Timeline(p);t.observe('wait',None,{},now=20)
            with self.assertRaisesRegex(ValueError,'regressed'):t.observe('wait',None,{},now=19)
            with self.assertRaisesRegex(ValueError,'footer'):timeline(p)
            t.close();lines=p.read_text().splitlines();footer=json.loads(lines[-1]);footer['recorded']+=1
            p.write_text(lines[0]+'\n'+json.dumps(footer)+'\n')
            with self.assertRaisesRegex(ValueError,'population'):timeline(p)


class ProgressTests(unittest.TestCase):
    def setup_report(self):
        row=dict(number=1,expected_generation=0,new_generation=1,submitted_monotonic_ns=1,result_observed_monotonic_ns=200,terminal=4,result_valid=True,result_rate_hz=200,result_generation=1)
        proof='00000000-0000-0000-0000-000000000001\nmonotonic 0 0\nboottime 0 0\n'
        report=dict(dds_transport_profile='system',clock_namespace_proof=dict(robot=proof,operator=proof),results=dict(commands=[row],checkpoints=dict(begin=dict(device=dict(effects=0,generation=0))),final_device=dict(effects=1,generation=1),command_data_cutoff_monotonic_ns=1000,skipped_command_slots=2))
        entry=dict(state=4,reason=0,revision=3,route=100,payload_hash='hash',source_epoch='owner',source_ns=2,session='session',result_valid=True,result_generation=1,deadline_ns=5000000002,dispatched_ns=100)
        return report,entry

    def run_report(self,report,a,b):
        id=(1).to_bytes(16,'little').hex()
        with patch('m3_n5_progress.read_journal',side_effect=[dict(entries={id:a}),dict(entries={id:b})]):return command_progress(report,Path('/unused'))

    def test_success_requires_durable_identity_budget_and_effect_proof(self):
        report,a=self.setup_report();b=copy.deepcopy(a);b['deadline_ns']-=100
        result=self.run_report(report,a,b)
        self.assertTrue(result['no_unresolved_attempts']);self.assertEqual(result['skipped_slots'],2)
        for key,value in [('deadline_ns',a['deadline_ns']+1),('payload_hash','other'),('dispatched_ns',b['deadline_ns'])]:
            bad=dict(b,**{key:value})
            with self.subTest(key=key),self.assertRaises(ValueError):self.run_report(report,a,bad)
        report['results']['final_device']['effects']=2
        with self.assertRaises(ValueError):self.run_report(report,a,b)

    def test_unknown_not_found_and_elapsed_budget_never_become_success(self):
        report,a=self.setup_report();r=report['results']['commands'][0]
        r.update(terminal=8,result_valid=False,result_observed_monotonic_ns=6000000000,last_status_observation=dict(local_error=2,budget_elapsed=True),observed_after_data_cutoff=True)
        result=self.run_report(report,a,None)
        self.assertFalse(result['no_unresolved_attempts']);self.assertEqual(result['audit']['unknown'],1)
        self.assertIsNone(result['entries'][0]['receiver'])

    def test_late_results_cannot_be_silently_reclassified_into_window(self):
        report,a=self.setup_report();report['results']['commands'][0]['result_observed_monotonic_ns']=1500
        with self.assertRaisesRegex(ValueError,'phase'):self.run_report(report,a,a)
