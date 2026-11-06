#!/usr/bin/env python3
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_observer_study import compare_pairs,plan,extract
from m3_capture import pcap_configuration


def rows():
    result=[]
    for slot in plan()[:8]:
        on=slot['observer'];g=dict(qualified=True,limits=dict(cpu_max='max 100000',memory_max='max'),inner_cpu_core_percent=5 if on else 10,outer_cpu_core_percent=6 if on else 11,maximum_observed_memory_current_bytes=8192 if on else 4096)
        result.append(dict(slot=slot,status='passed',metrics=dict(measurement_scope=dict(pcap_mode='immediate',pcap_config=pcap_configuration(),boot_id='same-boot',native_artifact_version=2 if on else None),image='same',configured_seconds=45,profile='N0',seed=1701,
            windows=dict(source_enabled=dict(cgroups={role:copy.deepcopy(g) for role in ('robot','operator')})),
            command_summary=dict(attempts=23,not_admitted=0,unresolved=0,by_state_reason={'4/0':dict(count=23,p95=200 if on else 100)}),effects=23)))
    return result


class StudyTests(unittest.TestCase):
    def test_negative_observed_differences_are_retained_without_overhead_claim(self):
        r=compare_pairs(rows());pair=r['srt']['pairs'][0]
        self.assertEqual(pair['roles']['robot']['observed_on_minus_off_core_percent'],[-6,-4])
        self.assertEqual(pair['roles']['robot']['sampled_charged_memory_max_difference_bytes'],4096)
        self.assertIn('not physical CPU bounds',r['srt']['scope'])

    def test_same_counts_ignore_latency_histograms_but_effect_difference_is_flagged(self):
        data=rows();self.assertTrue(compare_pairs(data)['srt']['pairs'][0]['same_command_counts_and_effects'])
        data[1]['metrics']['effects']=22
        self.assertFalse(compare_pairs(data)['srt']['pairs'][0]['same_command_counts_and_effects'])

    def test_incompatible_images_durations_limits_and_unqualified_counters_reject(self):
        for mutation in ('image','duration','limit','unqualified','mode','boot','artifact','buffer'):
            data=rows();m=data[1]['metrics']
            if mutation=='buffer':m['measurement_scope']['pcap_config']['buffer_kib']=4096
            if mutation=='mode':m['measurement_scope']['pcap_mode']='buffered'
            if mutation=='boot':m['measurement_scope']['boot_id']='other-boot'
            if mutation=='artifact':m['measurement_scope']['native_artifact_version']=1
            if mutation=='image':m['image']='other'
            if mutation=='duration':m['configured_seconds']=60
            if mutation=='limit':m['windows']['source_enabled']['cgroups']['robot']['limits']['cpu_max']='10000 100000'
            if mutation=='unqualified':m['windows']['source_enabled']['cgroups']['robot']['qualified']=False
            with self.assertRaises(ValueError,msg=mutation):compare_pairs(data)

    def test_partial_failed_and_missing_contrast_blocks_reject(self):
        with self.assertRaises(ValueError):compare_pairs(rows()[:-1])
        data=rows();data[0]['status']='failed'
        with self.assertRaises(ValueError):compare_pairs(data)
        data=rows();data[1]['slot']['observer']=False
        with self.assertRaises(ValueError):compare_pairs(data)


    def test_new_study_refuses_legacy_buffered_reports(self):
        report=dict(status='passed',profile='N0',seed=1701,seconds=45,pcap_dispatch_mode='buffered')
        with self.assertRaisesRegex(ValueError,'immediate'):extract(report,dict(profile='N0',seed=1701,seconds=45,observer=False,group='srt'))


if __name__=='__main__':unittest.main()
