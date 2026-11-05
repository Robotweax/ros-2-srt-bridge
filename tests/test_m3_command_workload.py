#!/usr/bin/env python3
import copy
from pathlib import Path
import sys
import unittest
import tempfile
import json
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ros2/robotweax_srt_bridge_demo/scripts'))
from command_workload import Cadence,audit_commands,record_status_observation
from scenario_files import read,write


class StatusObservationTests(unittest.TestCase):
    def status(self,**values):
        return dict(found=True,state=1,reason=0,local_error=2,revision=0,query_queued=False,**values)

    def test_not_found_after_budget_does_not_invent_terminal_or_nonexecution(self):
        row=dict(number=1,submitted_monotonic_ns=10)
        record_status_observation(row,self.status(),5000000010)
        self.assertTrue(row['last_status_observation']['budget_elapsed'])
        self.assertEqual(row['not_found_status_observations'],1)
        self.assertEqual(row['last_status_observation']['state'],1)
        self.assertNotIn('terminal',row);self.assertNotIn('result_valid',row)
        self.assertNotIn('result_observed_monotonic_ns',row)

    def test_observation_retains_latest_fields_without_clearing_prior_error_count(self):
        row=dict(submitted_monotonic_ns=10)
        record_status_observation(row,self.status(),11)
        status=self.status();status.update(state=4,local_error=0,revision=3)
        record_status_observation(row,status,12)
        self.assertEqual(row['status_observations'],2)
        self.assertEqual(row['not_found_status_observations'],1)
        self.assertEqual(row['last_status_observation']['state'],4)
        self.assertFalse(row['last_status_observation']['budget_elapsed'])
        self.assertNotIn('terminal',row) # transport adapter validates/records terminal results
        with self.assertRaisesRegex(ValueError,'predates'):record_status_observation(row,status,9)


class PhaseFileTests(unittest.TestCase):
    def test_disappearing_phase_file_is_absent_not_a_failed_workload(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'control.json';write(path,dict(sequence=1))
            self.assertTrue(path.exists())
            with patch.object(Path,'read_text',side_effect=FileNotFoundError):self.assertEqual(read(path),{})
            self.assertEqual(read(path),dict(sequence=1))

    def test_atomic_roundtrip_and_corrupt_phase_is_not_silenced(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'control.json';self.assertEqual(read(path),{})
            write(path,dict(sequence=7,action='ready'));self.assertEqual(read(path)['sequence'],7)
            self.assertFalse(path.with_suffix('.tmp').exists())
            path.write_text('{')
            with self.assertRaises(json.JSONDecodeError):read(path)


class CadenceTests(unittest.TestCase):
    def test_fixed_phase_skips_busy_slots_without_bursts(self):
        clock=Cadence(10)
        self.assertTrue(clock.due(10,True))
        self.assertFalse(clock.due(11,True))
        self.assertFalse(clock.due(12.1,False))
        self.assertTrue(clock.due(18.1,True))
        self.assertEqual(clock.next,20)
        self.assertEqual(clock.skipped,3)
        self.assertFalse(clock.due(18.2,True))

    def test_300_second_window_has_150_slots(self):
        clock=Cadence(0);times=[]
        for n in range(30000):
            if clock.due(n/100,True):times.append(n/100)
        self.assertEqual(len(times),150);self.assertEqual(times[-1],298)
        with self.assertRaises(ValueError):Cadence(0,0)


class OutcomeTests(unittest.TestCase):
    def fixture(self):
        return [dict(number=1,expected_generation=0,new_generation=1,terminal=4,result_valid=True,result_rate_hz=200,result_generation=1)],dict(effects=0,generation=0),dict(effects=1,generation=1)

    def test_confirmed_result_requires_matching_effect_population(self):
        rows,begin,end=self.fixture();self.assertTrue(audit_commands(rows,begin,end)['all_succeeded'])
        with self.assertRaisesRegex(ValueError,'population'):audit_commands(rows,begin,begin)
        rows[0]['result_generation']=2
        with self.assertRaisesRegex(ValueError,'confirmed'):audit_commands(rows,begin,end)

    def test_authoritative_expiry_allows_new_id_without_generation_advance(self):
        expired=dict(number=1,expected_generation=0,new_generation=1,terminal=7,reason=3,result_valid=False)
        before=dict(effects=0,generation=0)
        report=audit_commands([expired],before,before)
        self.assertEqual(report['confirmed_successes'],0);self.assertEqual(report['unresolved'],0)
        self.assertEqual(report['unknown'],0);self.assertFalse(report['all_succeeded'])
        success=dict(number=2,expected_generation=0,new_generation=1,terminal=4,result_valid=True,result_rate_hz=200,result_generation=1)
        report=audit_commands([expired,success],before,dict(effects=1,generation=1))
        self.assertEqual(report['confirmed_successes'],1);self.assertEqual(report['effects'],1)
        self.assertEqual(report['attempts'],2)

    def test_unknown_and_unresolved_can_have_effects_without_success_claim(self):
        rows,begin,end=self.fixture();rows[0].update(terminal=8,result_valid=False)
        report=audit_commands(rows,begin,end);self.assertEqual(report['unknown'],1);self.assertFalse(report['all_succeeded'])
        del rows[0]['terminal'];report=audit_commands(rows,begin,end)
        self.assertEqual(report['unresolved'],1);self.assertFalse(report['all_succeeded'])

    def test_duplicate_ids_extra_effects_and_non_admission_are_rejected(self):
        rows,begin,end=self.fixture()
        with self.assertRaisesRegex(ValueError,'duplicate'):audit_commands(rows+copy.deepcopy(rows),begin,end)
        with self.assertRaisesRegex(ValueError,'population'):audit_commands(rows,begin,dict(effects=2,generation=2))
        rows[0]['terminal']='not_admitted'
        with self.assertRaisesRegex(ValueError,'population'):audit_commands(rows,begin,end)

    def test_cutoff_and_drain_censoring_are_enforced(self):
        rows,begin,end=self.fixture();rows[0].update(submitted_monotonic_ns=1,result_observed_monotonic_ns=11,observed_after_data_cutoff=True)
        self.assertTrue(audit_commands(rows,begin,end,cutoff_ns=10)['all_succeeded'])
        rows[0]['submitted_monotonic_ns']=11
        with self.assertRaisesRegex(ValueError,'submitted'):audit_commands(rows,begin,end,cutoff_ns=10)
        rows[0]['submitted_monotonic_ns']=1;rows[0]['result_observed_monotonic_ns']=8000000011
        with self.assertRaisesRegex(ValueError,'drain'):audit_commands(rows,begin,end,cutoff_ns=10)
        rows[0]['result_observed_monotonic_ns']=9
        with self.assertRaisesRegex(ValueError,'phase'):audit_commands(rows,begin,end,cutoff_ns=10)

    def test_unknown_result_and_generation_drift_are_rejected(self):
        rows,begin,end=self.fixture();rows[0]['terminal']=8
        with self.assertRaisesRegex(ValueError,'UNKNOWN'):audit_commands(rows,begin,end)
        rows[0]['result_valid']=False;rows[0]['new_generation']=3
        with self.assertRaisesRegex(ValueError,'generation'):audit_commands(rows,begin,end)
        rows[0]['new_generation']=1
        with self.assertRaisesRegex(ValueError,'population'):audit_commands(rows,begin,dict(effects=1,generation=2))


if __name__=='__main__':unittest.main()
