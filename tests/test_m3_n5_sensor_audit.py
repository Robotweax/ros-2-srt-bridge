from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_n5_sensor_audit import assess_publications,provider_gauges
from m3_provider_stats import SENSOR_GAUGES
import test_m3_tools


def fixture():
    begin,end,interval=test_m3_tools.WindowTests().fixture()
    for phase in (begin,end):
        for role in ('sender','receiver'):
            phase[role].update(ready=True,clock_qualified=True,sensor_qos_verified=True,fault=0,worker_fault=0,session_id=[2]*16,control_generation=1,sensor_generation=1,transport_samples_unknown_age=0,transport_samples_stale=0,imu_age_upper_max_ns=0,joint_age_upper_max_ns=0)
    end['receiver']['imu_age_upper_max_ns']=10000000
    return begin,end,interval


class SensorAuditTests(unittest.TestCase):
    def test_all_publications_accounted_and_missing_source_retained(self):
        r=assess_publications(*fixture())
        self.assertEqual(r['populations']['source'],10);self.assertEqual(r['populations']['published'],7)
        self.assertEqual(r['populations']['unobserved_source'],3)
        self.assertEqual(r['publication_age']['imu']['histogram']['count'],7)
        self.assertIsNone(r['observed_bridge_queue_high_water'])
        self.assertEqual(r['publication_age']['joint']['freshness_gate'],'unavailable_no_publications')

    def test_unknown_age_rejection_is_not_a_published_percentile_or_transport_loss(self):
        a,b,t=fixture();b['receiver']['transport_samples_received']=8;b['receiver']['transport_samples_rejected']=1;b['receiver']['transport_samples_unknown_age']=1;b['sender']['sensor_sent']=8;b['sender']['sensor_outbound_replaced']=2
        r=assess_publications(a,b,t);self.assertEqual(r['populations']['unknown_age_rejected'],1);self.assertEqual(r['publication_age']['imu']['histogram']['count'],7)
        b['receiver']['transport_samples_unknown_age']=2
        with self.assertRaisesRegex(ValueError,'subsets'):assess_publications(a,b,t)

    def test_diagnostic_tail_or_missing_histogram_cannot_cover_window_publications(self):
        a,b,t=fixture();b['receiver']['imu_age_upper_histogram_ms'][10]-=1
        with self.assertRaisesRegex(ValueError,'histogram population'):assess_publications(a,b,t)
        a,b,t=fixture();b['receiver']['imu_age_upper_max_ns']=250000001
        with self.assertRaisesRegex(ValueError,'over-budget'):assess_publications(a,b,t)

    def test_unchanged_cumulative_maximum_is_not_a_window_maximum(self):
        a,b,t=fixture();a['receiver']['imu_age_upper_max_ns']=20000000;b['receiver']['imu_age_upper_max_ns']=20000000
        r=assess_publications(a,b,t);self.assertIsNone(r['publication_age']['imu']['exact_window_max_ns']);self.assertEqual(r['publication_age']['imu']['histogram']['maximum_ms'],10)

    def test_unqualified_changed_context_and_pending_checkpoints_are_refused(self):
        for fault in ('clock','context','pending'):
            a,b,t=fixture()
            if fault=='clock':b['receiver']['clock_qualified']=False
            elif fault=='context':b['receiver']['control_generation']=2
            else:b['receiver']['sensor_receive_pending']=1
            with self.subTest(fault=fault),self.assertRaises(ValueError):assess_publications(a,b,t)

    def test_provider_old_owner_and_absence_are_not_zero_peaks_or_merged(self):
        row=dict.fromkeys(SENSOR_GAUGES,0);row.update(begin_ns=10,end_ns=11,available=1,owner_epoch='old',generation=1,socket=5)
        current=dict(row,begin_ns=20,end_ns=21,owner_epoch='new',send_buffer_packets=4)
        stats={'warmup':dict(complete=True,status={},records=[row]),'active':dict(complete=True,status={},records=[row,current])}
        r=provider_gauges(stats,15,30);self.assertEqual(r['warmup']['connections'],{})
        self.assertFalse(r['warmup']['hard_peak_qualified']);self.assertEqual(len(r['active']['connections']),1)
        self.assertEqual(next(iter(r['active']['connections'].values()))['gauges']['send_buffer_packets']['maximum'],4)
        stats['active']['complete']=False
        with self.assertRaisesRegex(ValueError,'incomplete'):provider_gauges(stats,15,30)


if __name__=='__main__':unittest.main()
