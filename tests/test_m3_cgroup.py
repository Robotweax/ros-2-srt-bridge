#!/usr/bin/env python3
import copy
import os
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'ros2/robotweax_srt_bridge_demo/scripts'))
from endpoint_measurement import parse_keyed_counters,sample_cgroup
from m3_window_measurement import summarize_cgroup


def samples():
    return [dict(begin_ns=i*250000000,end_ns=i*250000000+1000,
        cgroup=dict(available=True,identity=dict(inode=1,namespace='cg1'),limits=dict(cpu_max='max 100000',memory_max='max'),
            cpu=dict(usage_usec=i*20000,user_usec=i*15000,system_usec=i*5000,nr_throttled=0),memory_events=dict(oom=0,oom_kill=0),memory_current_bytes=4096+i*10)) for i in range(17)]


class CgroupTests(unittest.TestCase):
    def test_keyed_counters_are_order_independent_and_fail_closed(self):
        self.assertEqual(parse_keyed_counters('system_usec 2\nusage_usec 3\nuser_usec 1\n'),dict(system_usec=2,usage_usec=3,user_usec=1))
        for raw in ('a 1\na 2','a -1','a x','a 1 2',''):
            with self.assertRaises(ValueError):parse_keyed_counters(raw)

    def test_cgroup_reader_checks_membership_and_hierarchy_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'cg';proc=Path(tmp)/'proc';root.mkdir();(proc/'ns').mkdir(parents=True);(proc/'ns/cgroup').symlink_to('cgroup:[42]')
            (proc/'cgroup').write_text('0::/\n')
            for name,value in {'cgroup.procs':str(os.getpid()),'cgroup.controllers':'cpu memory','cgroup.type':'domain','cpu.stat':'usage_usec 3\nuser_usec 2\nsystem_usec 1','memory.events':'oom 0\noom_kill 0','memory.current':'4096','cpu.max':'max 100000','memory.max':'max'}.items():(root/name).write_text(value)
            r=sample_cgroup(root,proc);self.assertTrue(r['available']);self.assertEqual(r['memory_current_bytes'],4096)
            (root/'cgroup.procs').write_text('0');self.assertFalse(sample_cgroup(root,proc)['available'])
            (root/'cgroup.procs').write_text(str(os.getpid()));(proc/'cgroup').write_text('0::/other');self.assertFalse(sample_cgroup(root,proc)['available'])

    def test_observed_deltas_and_charged_memory_without_interpolation(self):
        r=summarize_cgroup(samples(),1000000000,3000000000);self.assertTrue(r['qualified'])
        self.assertEqual(r['inner_cpu_seconds'],.14);self.assertEqual(r['outer_cpu_seconds'],.18)
        self.assertEqual(r['maximum_observed_memory_current_bytes'],4206)
        self.assertEqual(r['inner_cpu_deltas']['system_usec'],35000)
        self.assertIn('capture',r['scope']);self.assertIn('not RSS',r['memory_scope'])

    def test_unavailable_churn_limits_regression_and_gaps_reject(self):
        for field in ('unavailable','identity','limits','reset','events','memory','gap','keys'):
            rows=copy.deepcopy(samples());g=rows[7]['cgroup']
            if field=='unavailable':g['available']=False
            if field=='identity':g['identity']['inode']=2
            if field=='limits':g['limits']['cpu_max']='10000 100000'
            if field=='reset':g['cpu']['usage_usec']=0
            if field=='events':g['memory_events']['oom']=1
            if field=='memory':g['memory_current_bytes']=-1
            if field=='gap':rows=rows[:5]+rows[11:]
            if field=='keys':g['cpu']['new_key']=0
            self.assertFalse(summarize_cgroup(rows,1000000000,3000000000)['qualified'],field)

    def test_legacy_samples_and_missing_brackets_are_unqualified(self):
        self.assertFalse(summarize_cgroup([dict(begin_ns=0,end_ns=1)],10,20)['qualified'])
        rows=samples()
        for row in rows:row.pop('cgroup')
        self.assertFalse(summarize_cgroup(rows,1000000000,3000000000)['qualified'])

    def test_throttle_and_memory_events_are_retained_as_observed_deltas(self):
        rows=samples()
        for i,row in enumerate(rows):row['cgroup']['cpu']['nr_throttled']=i;row['cgroup']['memory_events']['oom']=int(i>=7)
        r=summarize_cgroup(rows,1000000000,3000000000)
        self.assertTrue(r['qualified']);self.assertEqual(r['outer_memory_event_deltas']['oom'],1)
        self.assertEqual(r['inner_cpu_deltas']['nr_throttled'],7)


if __name__=='__main__':unittest.main()
