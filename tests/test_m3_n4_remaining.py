import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_sample_trace import summarize
from m3_n4_sensor_check import assess
from m3_n4 import check_outcome
from test_m3_n4 import fixture
from test_m3_multiroute_accounting import setup
from test_m3_sample_trace import event
from test_m3_multiroute_accounting import remove_first
from m3_multiroute_accounting import assess as ordinary_assess


class RemainingN4Tests(unittest.TestCase):
    def test_inactive_admission_is_explicit_opt_in_and_never_queued_or_sdk_success(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'trace'
            for point,result in ((1,4),(1,2),(1,0),(2,0)):
                e=event(point,result);e['session']='00'*16
                path.write_text('SAMPLE_TRACE '+json.dumps(e)+'\nSAMPLE_TRACE_STATUS '+json.dumps(dict(schema_version=2,attempted=1,dropped=0,exhausted=0,limit=75000))+'\n')
                with self.assertRaises(ValueError):summarize(path)
                if point==1 and result in (2,4):self.assertTrue(summarize(path,allow_inactive_admissions=True)['complete'])
                else:
                    with self.assertRaises(ValueError):summarize(path,allow_inactive_admissions=True)

    def test_overrun_can_expire_or_safely_reject_context_but_never_apply_effect(self):
        for phase,state in (('admission',6),('dispatch',6),('started',7)):
            args=fixture(phase,state)
            for journal in args[3:5]:
                journal['entries']['01'+'00'*15]['finished_ns']=7_000_000_000
                if state==7:journal['entries']['01'+'00'*15]['reason']=3
            args[6]['begin_ns']=6_000_000_000
            r=check_outcome(*args);self.assertEqual(r['effects'],0)
        args=fixture('started',4);args[6]['begin_ns']=6_000_000_000
        with self.assertRaises(ValueError):check_outcome(*args)

    def test_obsolete_is_enum4_and_not_stopped_enum2(self):
        args=setup();remove_first(args,'busy');args[3]['events'][1]['result']=4
        args[1]['end']['bridge']['samples_submit_busy']=0;args[1]['end']['bridge']['samples_submit_obsolete']=1
        self.assertEqual(ordinary_assess(*args)['window']['losses']['admission'],1)
        args[3]['events'][1]['result']=2
        with self.assertRaises(ValueError):ordinary_assess(*args)

    def test_sensor_acceptance_age_blackout_and_context_joins(self):
        # Source cadence has its own independent tests; here isolate receiver,
        # metadata and accounting gates with a validated-cadence stand-in.
        for fault in (None,'age','blackout','message','progress'):
            source,sender,receiver,local,remote=setup();sender['contexts']=receiver['contexts']=[]
            for row in receiver['rows']:row['observed_ns']=row['stamp_sec']*10**9+row['stamp_nanosec']+50_000_000
            local['status']['attempted']=5001
            direction='to-robot';restored=4e9
            if fault=='age':receiver['rows'][0]['observed_ns']+=300_000_000
            if fault=='blackout':direction='both'
            if fault=='message':remote['events'][0]['message_number']+=1
            if fault=='progress':restored=20e9
            with patch('m3_n4_sensor_check.qualify',return_value=dict(passed=True,duration_ns=15e9)):
                if fault is None:self.assertTrue(assess(source,sender,receiver,local,remote,[2e9,4e9],restored,direction)['passed'])
                else:
                    with self.assertRaises(ValueError):assess(source,sender,receiver,local,remote,[2e9,4e9],restored,direction)

    def test_sensor_checker_rejects_insufficient_source_duration(self):
        source,sender,receiver,local,remote=setup()
        sender['contexts']=receiver['contexts']=[]
        with self.assertRaisesRegex(ValueError,'duration'):assess(source,sender,receiver,local,remote,[2e9,4e9],4e9,'both')

class JournalInspectionTests(unittest.TestCase):
    def test_live_read_closes_connection_even_when_an_external_reference_survives(self):
        import sqlite3
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ros2/robotweax_srt_bridge_demo/scripts'))
        from scenario_journal import visible_entries
        original=sqlite3.connect
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'journal.sqlite'
            db=original(path);db.execute('CREATE TABLE entries(id BLOB,state INTEGER)');db.execute('INSERT INTO entries VALUES(?,?)',(bytes([1])*16,13));db.commit();db.close()
            kept=[]
            def connect(*args,**kwargs):
                db=original(*args,**kwargs);kept.append(db);return db
            with patch('scenario_journal.sqlite3.connect',side_effect=connect):
                self.assertEqual(visible_entries(path),[dict(id='01'*16,state=3)])
            with self.assertRaises(sqlite3.ProgrammingError):kept[0].execute('SELECT 1')
