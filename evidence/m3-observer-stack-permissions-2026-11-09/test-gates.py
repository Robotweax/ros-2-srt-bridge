"""Offline final gates; no Linux permission calls or live target."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('permission_run',Path(__file__).with_name('run.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class GateTests(unittest.TestCase):
    def test_same_fixture_requires_real_stacks_and_capability_scope(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);cap0=dict(CapEff='0',CapPrm='0',CapInh='0',CapAmb='0',NoNewPrivs='1');cap1=dict(cap0,CapEff='200000',CapPrm='200000')
            child=dict(pid=10,passed=True,forced_kill=False,signal_begin_ns=1_000_000_000,signal_end_ns=1_000_000_001,end_ns=4_000_000_000,stack_observer=dict(complete=True),stack_observer_armed=True)
            (p/'result.json').write_text(json.dumps(dict(status='passed',shutdown=dict(children=[child]))));(p/'permission-proof.json').write_text(json.dumps(dict(supervisor_before_signal=cap0,target_before_signal=cap0,observer_before_signal=cap1)));(p/'supervisor-final-permissions.json').write_text(json.dumps(cap0))
            points=['fixture_ready','fixture_sigint_observed','fixture_blocked_begin','fixture_blocked_end','fixture_exit'];times=[1,1_000_000_002,1_000_000_003,3_990_000_000,3_999_000_000]
            (p/'stages.jsonl').write_text('\n'.join(json.dumps(dict(point=point,monotonic_ns=ns,pid=10,sequence=i+1,dropped_before=0)) for i,(point,ns) in enumerate(zip(points,times))))
            rows=[dict(kind='begin',observer_independent=True,root=dict(pid=10),pid=20,mode='procfs',boot_id=dict(status='ok'),time_namespace_offsets=dict(status='ok',text='monotonic 0 0\nboottime 0 0'))]
            for ns in (2_000_000_000,2_500_000_000):rows.append(dict(kind='sample',begin_ns=ns,end_ns=ns+10,process_limit_hit=False,processes=[dict(status='sampled',identity_still_matches=True,threads_truncated=False,identity=dict(pid=10),threads=[dict(tid=tid,kernel_stack=dict(status='ok',text='futex_wait',truncated=False),wchan=dict(text='futex_wait')) for tid in (10,11)])]))
            (p/'blocked-target-shutdown-stacks.ready.json').write_text(json.dumps(dict(ready_ns=500_000_000)))
            def save():(p/'blocked-target-shutdown-stacks.jsonl').write_text('\n'.join(json.dumps(r) for r in rows))
            save();self.assertEqual(m.assess(p)['status'],'passed')
            for sample in rows[1:]:
                for thread in sample['processes'][0]['threads']:thread['kernel_stack']=dict(status='unavailable',error='PermissionError',errno=13)
            save()
            with self.assertRaisesRegex(ValueError,'kernel stacks unavailable'):m.assess(p)
if __name__=='__main__':unittest.main()
