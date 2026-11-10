"""Offline retained JSON and temporary procfs only; no live target or subprocess."""
import ast
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import task_assessment as assessment
import lifecycle
observer=assessment._collector

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
old=module('frozen_lifecycle',ROOT/'evidence/m3-current-long-preparation-2026-11-10/lifecycle.py')
def load(path):return [json.loads(x) for x in path.read_text().splitlines()]
def stat(tid,start):return str(tid)+' (fixture (task)) '+' '.join(['S','1']+['0']*17+[str(start)]+['0']*10)

class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.proc=Path(self.tmp.name)
        self.known={(101,700):dict(pid=101,start_ticks=700)};self.history={};self.samples=[]
        (self.proc/'101').mkdir();(self.proc/'101/stat').write_text(stat(101,700));self.task(101,700)
    def task(self,tid,start):
        path=self.proc/'101/task'/str(tid);path.mkdir(parents=True,exist_ok=True)
        for name,text in dict(stat=stat(tid,start),wchan='futex_wait',syscall='98 0',stack='[<0>] futex_wait\n',children='').items():(path/name).write_text(text)
        return path
    def sample(self):
        begin=time.monotonic_ns();value=observer.collect_with_task_visibility(self.proc,self.known,self.history)
        r=dict(kind='sample',begin_ns=begin,end_ns=time.monotonic_ns(),**value);self.samples.append(r);return r
    def rows(self):
        ok=sum(t['kernel_stack']['status']=='ok' for s in self.samples for p in s['processes'] for t in p.get('threads',[]));total=sum(len(p.get('threads',[])) for s in self.samples for p in s['processes'])
        value=dict(status='ok',truncated=False,text='model-boot')
        first=dict(kind='begin',clock='monotonic',mode='procfs',observer_independent=True,kernel_stacks_only=True,pid=500,root=dict(pid=101,start_ticks=700),boot_id=value,time_namespace_offsets=dict(value,text='monotonic 0 0\nboottime 0 0\n'),task_visibility_schema_version=1,task_history_capacity=512)
        footer=dict(kind='status',completed=True,budget_exhausted=False,userspace_stacks_requested=False,samples=len(self.samples),sample_limit=48,kernel_stack_reads_ok=ok,kernel_stack_reads_unavailable=total-ok)
        return deepcopy([first,*self.samples,footer])
    def assess(self):return assessment.assess_metadata(self.rows())
    def disappearance(self,when='stack',after=False,prior=False):
        path=self.task(102,701)
        if prior:self.sample()
        actual=observer.read_limited
        def read(file,*args):
            if Path(file)==path/when and path.exists() and not after:shutil.rmtree(path)
            value=actual(file,*args)
            if Path(file)==path/when and path.exists() and after:shutil.rmtree(path)
            return value
        with patch.object(observer,'read_limited',side_effect=read):self.sample()
    def child(self,post=True,forced=False):
        signal=self.samples[0]['begin_ns']-100 if post else self.samples[-1]['end_ns']+100
        return dict(pid=101,start_ticks=700,signal_begin_ns=signal,signal_end_ns=signal+1,end_ns=self.samples[-1]['end_ns']+1000,forced_kill=forced)
    def stages(self):return [dict(pid=101,tid=101,sequence=1,dropped_before=0,point='shutdown_begin',monotonic_ns=self.samples[0]['begin_ns']-1)]
    def test_readable_model_and_json_roundtrip(self):
        self.sample();r=self.assess();self.assertEqual(r['readable_task_records'],1);self.assertEqual(r['observed_disappearances'],0);self.assertEqual(r,assessment.assess_metadata(json.loads(json.dumps(self.rows()))))
    def test_retained_native_calibration_only_metadata_consistency(self):
        rows=load(ROOT/'evidence/m3-task-visibility-calibration-execution-2026-11-10/run/data/blocked-target-shutdown-stacks.jsonl');result=assessment.assess_metadata(rows)
        self.assertEqual([result[k] for k in ('samples','readable_task_records','observed_disappearances','raw_stack_reads_ok','raw_stack_reads_unavailable','confirmed_task_exits')],[3,5,1,5,0,0])
        self.assertEqual(result['rows'][-1]['processes'][0]['disappearances'][0]['classification'],'not_enumerated_after_prior_identity')
    def test_identified_disappearance_preserves_missing_stack(self):
        self.disappearance();r=self.assess();self.assertEqual(r['raw_stack_reads_unavailable'],1);self.assertEqual(r['readable_task_records'],1);self.assertEqual(r['observed_disappearances'],1);self.assertEqual(r['confirmed_task_exits'],0)
    def test_after_stack_disappearance_is_not_counted_readable(self):
        self.disappearance(after=True);r=self.assess();self.assertEqual(r['raw_stack_reads_ok'],2);self.assertEqual(r['readable_task_records'],1);self.assertEqual(r['observed_disappearances'],1)
    def test_all_missing_requires_previous_identity(self):
        self.disappearance('stat',prior=True);r=self.assess();self.assertEqual(r['rows'][-1]['processes'][0]['disappearances'][0]['classification'],'observed_absence_after_prior_identity')
    def test_first_observation_all_missing_rejected(self):
        self.disappearance('stat')
        with self.assertRaisesRegex(ValueError,'lacks current or previous'):self.assess()
    def test_prior_enumeration_absence_and_expiring_cache(self):
        path=self.task(102,701);self.sample();shutil.rmtree(path);self.sample();self.sample();r=self.assess();self.assertEqual(r['observed_disappearances'],1);self.assertFalse(r['rows'][-1]['processes'][0]['disappearances'])
    def test_forged_prior_hint_rejected(self):
        self.sample();self.sample();rows=self.rows();rows[2]['processes'][0]['threads'][0]['task_evidence']['prior_sample_identity_hint']=dict(tid=101,start_ticks=999,name='forged',state='S')
        with self.assertRaisesRegex(ValueError,'prior hint'):assessment.assess_metadata(rows)
    def test_missing_enumeration_hint_rejected(self):
        path=self.task(102,701);self.sample();shutil.rmtree(path);self.sample();rows=self.rows();rows[2]['processes'][0]['prior_tasks_not_listed']=[]
        with self.assertRaisesRegex(ValueError,'enumeration hint'):assessment.assess_metadata(rows)
    def test_prior_hint_does_not_prove_unobserved_reuse(self):
        self.disappearance('stat',prior=True);self.assertFalse(self.assess()['rows'][-1]['processes'][0]['disappearances'][0]['confirmed_exit'])
    def test_reuse_since_prior_rejected(self):
        path=self.task(102,701);self.sample();(path/'stat').write_text(stat(102,999));self.sample()
        with self.assertRaisesRegex(ValueError,'incarnation changed'):self.assess()
    def test_reuse_between_checks_rejected(self):
        path=self.task(102,701);actual=observer.read_limited
        def read(file,*args):
            r=actual(file,*args)
            if Path(file)==path/'stack':(path/'stat').write_text(stat(102,999))
            return r
        with patch.object(observer,'read_limited',side_effect=read):self.sample()
        with self.assertRaisesRegex(ValueError,'incarnation changed'):self.assess()
    def test_read_errors_cannot_be_absence(self):
        for code in (1,13,5,20):
            self.samples=[];self.history={};actual=observer.read_limited
            def read(file,*args):
                if Path(file).name=='stack':return dict(status='unavailable',error='OSError',errno=code)
                return actual(file,*args)
            with self.subTest(errno=code),patch.object(observer,'read_limited',side_effect=read):
                self.sample()
                with self.assertRaisesRegex(ValueError,'not supported absence'):self.assess()
    def test_truncated_or_invalid_reads_rejected(self):
        for name,text in (('stack','x'*16385),('stat','bad')):
            with self.subTest(name=name):
                self.samples=[];self.history={};path=self.proc/'101/task/101'/name;original=path.read_text();path.write_text(text);self.sample();path.write_text(original)
                with self.assertRaises(ValueError):self.assess()
    def test_missing_stack_while_directory_present_rejected(self):
        (self.proc/'101/task/101/stack').unlink();self.sample()
        with self.assertRaises(ValueError):self.assess()
    def test_partial_enoent_followed_by_readable_files_rejected(self):
        actual=observer.read_limited
        def read(file,*args):
            if Path(file).name=='wchan':return dict(status='unavailable',error='FileNotFoundError',errno=2)
            return actual(file,*args)
        with patch.object(observer,'read_limited',side_effect=read):self.sample()
        with self.assertRaises(ValueError):self.assess()
    def test_parent_identity_mismatch_rejected(self):
        self.sample();rows=self.rows();rows[1]['processes'][0]['identity_check']['observed']['start_ticks']=999
        with self.assertRaises(ValueError):assessment.assess_metadata(rows)
    def test_raw_top_level_disagrees_rejected(self):
        self.sample();rows=self.rows();rows[1]['processes'][0]['threads'][0]['kernel_stack']=dict(status='ok',text='invented',truncated=False)
        with self.assertRaisesRegex(ValueError,'raw task result'):assessment.assess_metadata(rows)
    def test_metadata_label_cannot_waive_raw_error(self):
        self.sample();rows=self.rows();rows[1]['processes'][0]['threads'][0]['task_evidence']['lifetime_status']='absent_after_identified_read'
        with self.assertRaisesRegex(ValueError,'lifetime label'):assessment.assess_metadata(rows)
    def test_clock_bracket_overlap_rejected(self):
        self.sample();rows=self.rows();e=rows[1]['processes'][0]['threads'][0]['task_evidence'];e['reads']['stack']['begin_ns']=e['reads']['stat']['begin_ns']
        with self.assertRaisesRegex(ValueError,'bracket'):assessment.assess_metadata(rows)
    def test_different_clock_origin_rejected(self):
        self.sample();rows=self.rows();rows[0]['time_namespace_offsets']['text']='monotonic 1 0\nboottime 0 0\n'
        with self.assertRaisesRegex(ValueError,'namespace'):assessment.assess_metadata(rows)
    def test_budget_schema_footer_and_claim_mutations_rejected(self):
        self.sample()
        mutations=[lambda r:r[0].update(task_visibility_schema_version=2),lambda r:r[-1].update(budget_exhausted=True),lambda r:r[-1].update(kernel_stack_reads_ok=8),lambda r:r[1].update(process_limit_hit=True),lambda r:r[1]['processes'][0].update(threads_truncated=True),lambda r:r[1]['processes'][0]['task_enumeration'].update(complete=False),lambda r:r[1]['processes'][0]['threads'][0]['task_evidence'].update(confirmed_exit=True),lambda r:r[-1].update(userspace_stacks_requested=True)]
        for index,mutate in enumerate(mutations):
            with self.subTest(index=index):
                rows=self.rows();mutate(rows)
                with self.assertRaises(ValueError):assessment.assess_metadata(rows)
    def test_duplicate_or_omitted_process_rejected(self):
        self.sample();self.sample()
        for processes in ([],self.rows()[1]['processes']*2):
            rows=self.rows();rows[2]['processes']=processes
            with self.assertRaises(ValueError):assessment.assess_metadata(rows)
    def test_lifecycle_post_signal_absence_preserves_counts(self):
        self.disappearance();r=lifecycle.coverage(self.rows(),self.child(),self.stages());self.assertEqual(r['nonempty_kernel_stacks'],1);self.assertEqual(len(r['observed_task_disappearances']),1);self.assertEqual(r['raw_stack_reads_unavailable'],1);self.assertEqual(r['confirmed_task_exits'],0)
    def test_pre_signal_absence_not_accepted_for_shutdown(self):
        self.disappearance();self.assess()
        with self.assertRaisesRegex(ValueError,'outside post-signal'):lifecycle.coverage(self.rows(),self.child(False),self.stages())
    def test_forced_kill_still_requires_two_post_signal_samples(self):
        self.sample()
        with self.assertRaisesRegex(ValueError,'bounded post-signal'):lifecycle.coverage(self.rows(),self.child(forced=True),self.stages())
        self.sample();self.assertEqual(lifecycle.coverage(self.rows(),self.child(forced=True),self.stages())['post_signal_samples'],2)
    def test_no_readable_stack_still_fails_lifecycle(self):
        (self.proc/'101/task/101/stack').write_text('');self.sample()
        with self.assertRaisesRegex(ValueError,'no real bridge'):lifecycle.coverage(self.rows(),self.child(),self.stages())
    def test_root_missing_before_reap_still_rejected(self):
        self.sample();(self.proc/'101/stat').unlink();self.sample()
        with self.assertRaisesRegex(ValueError,'root disappearance'):lifecycle.coverage(self.rows(),self.child(),self.stages())
    def test_join_function_and_legacy_gates_retained(self):
        def join_ast(path):return ast.dump(next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='join_end'))
        self.assertEqual(join_ast(HERE/'lifecycle.py'),join_ast(ROOT/'evidence/m3-current-long-preparation-2026-11-10/lifecycle.py'))
        self.assertEqual(lifecycle.WORKER_NAMES,old.WORKER_NAMES)
    def test_legacy_N1_failure_remains_and_has_no_new_schema(self):
        path=ROOT/'evidence/m3-current-long-execution-2026-11-10/cases/N1-combined-2903';s=json.loads((path/'strict-assessment.json').read_text());launch=s['launches']['operator']['measurement'];rows=load(path/'native-observer/blocked-target-shutdown-stacks.jsonl')
        with self.assertRaisesRegex(ValueError,'schema1 required'):assessment.assess_metadata(rows)
        with self.assertRaisesRegex(ValueError,'live target kernel stack unavailable'):old.coverage(rows,launch['child'],launch['stages']['rows'])
    def worker_samples(self):
        pid=201;path=self.proc/str(pid);path.mkdir();(path/'stat').write_text(stat(pid,800).replace('fixture (task)','robotweax-journ').replace(' S 1 ',' S 101 ',1))
        task=path/'task'/str(pid);task.mkdir(parents=True)
        for name,text in dict(stat=stat(pid,800),wchan='wait',syscall='98',stack='[<0>] wait',children='').items():(task/name).write_text(text)
        (self.proc/'101/task/101/children').write_text(str(pid));self.sample();signal=time.monotonic_ns();joined=signal+1;shutil.rmtree(path);(self.proc/'101/task/101/children').write_text('');self.sample()
        child=dict(self.child(),signal_begin_ns=signal-1,signal_end_ns=signal)
        stages=[dict(pid=101,tid=101,sequence=i+1,dropped_before=0,point=point,monotonic_ns=t) for i,(point,t) in enumerate((('worker_join_begin',signal),('worker_join_end',joined)))]
        return child,stages
    def test_registered_worker_process_exit_still_requires_join(self):
        child,stages=self.worker_samples();r=lifecycle.coverage(self.rows(),child,stages);self.assertEqual(r['confirmed_worker_exits'],[dict(pid=201,start_ticks=800)]);self.assertEqual(r['confirmed_task_exits'],0)
        with self.assertRaisesRegex(ValueError,'worker disappearance not confirmed'):lifecycle.coverage(self.rows(),child,stages[:1])
    def test_dropped_or_wrong_thread_join_still_rejected(self):
        child,stages=self.worker_samples()
        for field,value in (('tid',999),('dropped_before',1)):
            changed=deepcopy(stages);changed[-1][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):lifecycle.coverage(self.rows(),child,changed)
    def test_process_pid_reuse_still_rejected(self):
        self.sample();(self.proc/'101/stat').write_text(stat(101,999));self.sample()
        with self.assertRaises(ValueError):lifecycle.coverage(self.rows(),self.child(),self.stages())
    def test_independent_task_reads_cannot_overlap(self):
        self.task(102,701);self.sample();rows=self.rows();first,second=rows[1]['processes'][0]['threads'];second['task_evidence']['reads']['stat']['begin_ns']=first['task_evidence']['reads']['stat']['begin_ns']
        with self.assertRaisesRegex(ValueError,'overlap'):assessment.assess_metadata(rows)
    def test_directory_permission_error_is_not_absence(self):
        self.disappearance();rows=self.rows();rows[1]['processes'][0]['threads'][1]['task_evidence']['directory_presence']['result']=dict(status='unavailable',error='PermissionError',errno=13)
        with self.assertRaises(ValueError):assessment.assess_metadata(rows)
    def test_hint_absence_also_requires_post_signal_window(self):
        path=self.task(102,701);self.sample();shutil.rmtree(path);self.sample()
        r=lifecycle.coverage(self.rows(),self.child(),self.stages());self.assertEqual(len(r['observed_task_disappearances']),1)
        with self.assertRaisesRegex(ValueError,'outside post-signal'):lifecycle.coverage(self.rows(),self.child(False),self.stages())
    def test_absence_read_errors_never_override_later_missing_identity(self):
        self.disappearance();rows=self.rows();t=rows[1]['processes'][0]['threads'][1];bad=dict(status='unavailable',error='PermissionError',errno=13);t['kernel_stack']=bad;t['task_evidence']['reads']['stack']['result']=bad
        with self.assertRaisesRegex(ValueError,'not supported absence'):assessment.assess_metadata(rows)
    def test_lifecycle_binds_registered_launch_start_ticks(self):
        self.sample();child=dict(self.child(),start_ticks=999)
        with self.assertRaisesRegex(ValueError,'registered root differs'):lifecycle.coverage(self.rows(),child,self.stages())
    def test_boolean_schema_and_population_not_valid_integers(self):
        self.sample()
        for mutate in (lambda r:r[0].update(task_visibility_schema_version=True),lambda r:r[1].update(task_visibility_schema_version=True),lambda r:r[1]['processes'][0]['task_enumeration'].update(entries_seen=True),lambda r:r[1]['processes'][0]['threads'][0]['task_evidence'].update(schema_version=True)):
            rows=self.rows();mutate(rows)
            with self.assertRaises(ValueError):assessment.assess_metadata(rows)
    def test_main_task_start_must_match_parent_incarnation(self):
        (self.proc/'101/task/101/stat').write_text(stat(101,999));self.sample()
        with self.assertRaisesRegex(ValueError,'root task incarnation'):self.assess()
    def test_private_binding_ignores_generic_import_collision(self):
        poisoned=types.ModuleType('shutdown_observer')
        with patch.dict(sys.modules,{'shutdown_observer':poisoned}):
            loaded=module('independent_assessment',HERE/'task_assessment.py');self.assertTrue(callable(loaded._collector.task_identity));self.assertIs(sys.modules['shutdown_observer'],poisoned)
    def test_private_binding_rejects_changed_collector(self):
        with patch.object(Path,'read_bytes',return_value=b'changed'),self.assertRaisesRegex(ValueError,'source binding'):module('bad_assessment',HERE/'task_assessment.py')

if __name__=='__main__':unittest.main()
