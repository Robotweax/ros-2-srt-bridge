import copy
from pathlib import Path
import subprocess
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_dds_loaded_confirmation import SLOTS,check,execute
from m3_source_preflight import IMAGE


class LoadedDdsTests(unittest.TestCase):
    def fixture(self):
        report=dict(status='passed',image_reference=IMAGE,dds_transport_profile='system',startup_mode='simultaneous',profile='N0',seconds=15,seed=1701,runtime_layout=dict(name='sender-reconcile'),pcap_population_reconciled=True,age_estimates_qualified=True,measurement_window=dict(routes={r:dict(actual_source_hz=h,accepted=20,invalid=0,clock_rejected=0) for r,h in [('imu',200),('joints',50)]}))
        progress=dict(no_unresolved_attempts=True,entries=[{}]*8,skipped_slots=0)
        return report,copy.deepcopy(SLOTS[0]),progress,{r:dict(classification='ready_observed') for r in ('operator','robot')},{str(n):dict(passed=True) for n in range(3)}

    def test_fixed_cases_and_failure_stop_have_no_retry(self):
        self.assertEqual([(s['profile'],s['seconds'],s['seed']) for s in SLOTS],[('N0',15,1701),('N5',60,1701)])
        calls=[];r=execute(SLOTS,lambda s:calls.append(s['label']) or dict(status='failed'),lambda r:None)
        self.assertEqual(calls,['dds-N0-control']);self.assertEqual([x['status'] for x in r['rows']],['failed','not_executed'])
        def fail(s):raise ValueError('original failure')
        r=execute(SLOTS,fail,lambda r:None);self.assertEqual(r['rows'][0]['error'],'original failure');self.assertEqual(r['rows'][1]['status'],'not_executed')

    def test_capture_clock_layout_and_default_startup_are_mandatory(self):
        args=self.fixture();check(*args)
        for key,value in [('pcap_population_reconciled',False),('age_estimates_qualified',False),('dds_transport_profile','paced-sensors'),('startup_mode','control-first'),('runtime_layout',{})]:
            a=list(self.fixture());a[0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):check(*a)

    def test_empty_unresolved_or_missing_source_progress_cannot_pass(self):
        for fault in ('empty','unresolved','cadence','invalid','clock','unready','shutdown'):
            a=list(self.fixture())
            if fault=='empty':a[2]['entries']=[]
            elif fault=='unresolved':a[2]['no_unresolved_attempts']=False
            elif fault in ('cadence','invalid','clock'):a[0]['measurement_window']['routes']['imu'][{'cadence':'actual_source_hz','invalid':'invalid','clock':'clock_rejected'}[fault]]={'cadence':197,'invalid':1,'clock':1}[fault]
            elif fault=='unready':a[3]['operator']['classification']='no_received_hello_observed'
            else:a[4].pop('0')
            with self.subTest(fault=fault),self.assertRaises(ValueError):check(*a)

    def test_loaded_gate_requires_actual_competitor_and_preserves_skipped_commands(self):
        a=list(self.fixture());a[1]=SLOTS[1];a[0].update(profile='N5',seconds=60);a[2]['skipped_slots']=8
        with self.assertRaisesRegex(ValueError,'competitor'):check(*a)
        a[0]['competitor_check']=dict(target_bitrate=128000,alive_poll_checks=20);check(*a)

    def test_nonbaseline_build_is_refused_before_any_docker_work(self):
        root=Path(__file__).resolve().parents[1]
        p=subprocess.run([sys.executable,'tools/run_m3_dds.py','--runtime-layout','sender-reconcile'],cwd=root,capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertIn('requires --skip-build',p.stderr)


if __name__=='__main__':unittest.main()
