"""Temporary procfs models and deterministic in-read mutations only; no live target."""
import ast
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parents[1]
OLD=ROOT/'evidence/m3-current-long-preparation-2026-11-10/shutdown_observer.py'
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
observer=module('task_visibility_candidate',HERE/'shutdown_observer.py')
prior=module('unchanged_observer',OLD)

def stat_text(tid,start,name='owned (task)'):
    fields=['0']*30;fields[0]='S';fields[1]='1';fields[19]=str(start)
    return str(tid)+' ('+name+') '+' '.join(fields)

class TaskVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.proc=self.root/'proc';self.proc.mkdir();self.process(101,700)
        self.known={(101,700):dict(pid=101,start_ticks=700)};self.history={}
    def process(self,pid,start,children=''):
        path=self.proc/str(pid);path.mkdir(exist_ok=True);(path/'stat').write_text(stat_text(pid,start));self.task(pid,pid,start,children)
    def task(self,pid,tid,start,children=''):
        path=self.proc/str(pid)/'task'/str(tid);path.mkdir(parents=True,exist_ok=True)
        for name,text in dict(stat=stat_text(tid,start),wchan='futex_wait',syscall='98 0 0',stack='[<0>] futex_wait\n',children=children).items():(path/name).write_text(text)
        return path
    def collect(self):return observer.collect_with_task_visibility(self.proc,self.known,self.history)
    def thread(self,result,tid=101):return next(t for t in result['processes'][0]['threads'] if t['tid']==tid)
    def test_live_identity_brackets_all_reads_and_stack_once(self):
        calls=[];actual=observer.read_limited
        def read(path,*args):calls.append(Path(path));return actual(path,*args)
        with patch.object(observer,'read_limited',side_effect=read):r=self.collect()
        t=self.thread(r);e=t['task_evidence'];self.assertEqual(e['lifetime_status'],'matching');self.assertFalse(e['confirmed_exit'])
        self.assertEqual(e['identity_before']['identity']['start_ticks'],700);self.assertEqual(e['identity_before'],e['identity_after'])
        self.assertEqual(sum(p.name=='stack' for p in calls),1);self.assertEqual(sum(p.name=='stat' for p in calls),2)
        end=e['enumeration_end_ns']
        for key in ('stat','wchan','syscall','stack','children'):
            read=e['reads'][key];self.assertLessEqual(end,read['begin_ns']);self.assertLessEqual(read['begin_ns'],read['end_ns']);end=read['end_ns']
        self.assertLessEqual(end,e['final_stat']['begin_ns']);self.assertLessEqual(e['final_stat']['end_ns'],e['directory_presence']['begin_ns']);self.assertLessEqual(e['directory_presence']['end_ns'],e['parent_identity_check']['checked_ns'])
    def test_exit_after_enumeration_before_stat_no_current_identity(self):
        path=self.task(101,102,701);self.collect();actual=observer.bounded_tasks
        def enumerate(task):
            result=actual(task);shutil.rmtree(path);return result
        with patch.object(observer,'bounded_tasks',side_effect=enumerate):t=self.thread(self.collect(),102)
        e=t['task_evidence'];self.assertEqual(e['lifetime_status'],'absent_without_current_identity');self.assertEqual(e['prior_sample_identity_hint']['start_ticks'],701);self.assertFalse(e['confirmed_exit']);self.assertEqual(t['kernel_stack']['errno'],2)
        self.assertTrue(all(r['result']['status']=='unavailable' for r in e['reads'].values()))
    def test_exit_between_initial_stat_and_stack_retains_initial_identity(self):
        path=self.task(101,102,701);actual=observer.read_limited
        def read(file,*args):
            if Path(file)==path/'stack':shutil.rmtree(path)
            return actual(file,*args)
        with patch.object(observer,'read_limited',side_effect=read):t=self.thread(self.collect(),102)
        e=t['task_evidence'];self.assertEqual(e['lifetime_status'],'absent_after_identified_read');self.assertEqual(e['identity_before']['identity']['start_ticks'],701);self.assertEqual(e['identity_after']['status'],'missing');self.assertEqual(e['directory_presence']['result']['status'],'absent');self.assertEqual(t['kernel_stack']['status'],'unavailable')
    def test_exit_after_stack_stays_readable_but_presence_changed(self):
        path=self.task(101,102,701);actual=observer.read_limited
        def read(file,*args):
            result=actual(file,*args)
            if Path(file)==path/'stack':shutil.rmtree(path)
            return result
        with patch.object(observer,'read_limited',side_effect=read):t=self.thread(self.collect(),102)
        self.assertEqual(t['kernel_stack']['status'],'ok');self.assertEqual(t['task_evidence']['lifetime_status'],'absent_after_identified_read');self.assertFalse(t['task_evidence']['confirmed_exit'])
    def test_tid_reuse_between_stat_checks_is_explicit(self):
        path=self.task(101,102,701);actual=observer.read_limited
        def read(file,*args):
            result=actual(file,*args)
            if Path(file)==path/'stack':(path/'stat').write_text(stat_text(102,999))
            return result
        with patch.object(observer,'read_limited',side_effect=read):e=self.thread(self.collect(),102)['task_evidence']
        self.assertEqual(e['lifetime_status'],'tid_reused');self.assertEqual(e['identity_before']['identity']['start_ticks'],701);self.assertEqual(e['identity_after']['identity']['start_ticks'],999)
    def test_reuse_since_previous_sample_is_only_a_hint(self):
        path=self.task(101,102,701);self.collect();(path/'stat').write_text(stat_text(102,999));e=self.thread(self.collect(),102)['task_evidence'];self.assertTrue(e['changed_since_prior']);self.assertEqual(e['lifetime_status'],'matching');self.assertEqual(e['prior_sample_identity_hint']['start_ticks'],701);self.assertFalse(e['confirmed_exit'])
    def test_task_appears_after_missing_first_stat_not_confirmed_exit(self):
        path=self.task(101,102,701);actual=observer.read_limited;first=True
        def read(file,*args):
            nonlocal first
            if Path(file)==path/'stat' and first:
                first=False;return dict(status='unavailable',error='FileNotFoundError',errno=2)
            return actual(file,*args)
        with patch.object(observer,'read_limited',side_effect=read):e=self.thread(self.collect(),102)['task_evidence']
        self.assertEqual(e['lifetime_status'],'appeared_after_initial_absence');self.assertFalse(e['confirmed_exit'])
    def test_missing_stat_with_directory_present_is_ambiguous(self):
        path=self.task(101,102,701);(path/'stat').unlink();e=self.thread(self.collect(),102)['task_evidence'];self.assertEqual(e['lifetime_status'],'identity_or_presence_unavailable');self.assertEqual(e['directory_presence']['result']['status'],'present')
    def test_permission_errors_preserved_not_empty_success(self):
        actual=observer.read_limited
        for errno in (1,13,5):
            def read(file,*args):
                if Path(file).name=='stack':return dict(status='unavailable',error='PermissionError' if errno in (1,13) else 'OSError',errno=errno)
                return actual(file,*args)
            with self.subTest(errno=errno),patch.object(observer,'read_limited',side_effect=read):t=self.thread(self.collect())
            self.assertEqual(t['kernel_stack']['errno'],errno);self.assertEqual(t['task_evidence']['lifetime_status'],'matching');self.assertFalse(t['task_evidence']['confirmed_exit'])
    def test_malformed_mismatched_and_truncated_stat_never_bind_identity(self):
        for text in ('bad',stat_text(999,700),stat_text(101,0),stat_text(101,2**64),stat_text(101,700,'x'*65)):
            with self.subTest(text=text[:40]):self.assertEqual(observer.task_identity(dict(status='ok',text=text,truncated=False),101)['status'],'unavailable')
        self.assertEqual(observer.task_identity(dict(status='ok',text=stat_text(101,700),truncated=True),101)['error'],'truncated_stat')
    def test_task_name_with_parentheses_and_spaces_parses(self):
        value=observer.task_identity(dict(status='ok',text=stat_text(101,700),truncated=False),101);self.assertEqual(value['identity']['name'],'owned (task)')
    def test_stack_truncation_preserved(self):
        (self.proc/'101/task/101/stack').write_text('x'*(observer.MAX_READ+1));t=self.thread(self.collect());self.assertTrue(t['kernel_stack']['truncated']);self.assertFalse(t['task_evidence']['confirmed_exit'])
    def test_parent_reuse_invalidates_task_classification_and_cache(self):
        actual=observer.identity_state;calls=0
        def state(proc,expected):
            nonlocal calls
            calls+=1
            if calls==2:(self.proc/'101/stat').write_text(stat_text(101,999))
            return actual(proc,expected)
        with patch.object(observer,'identity_state',side_effect=state):r=self.collect()
        self.assertEqual(self.thread(r)['task_evidence']['lifetime_status'],'parent_identity_not_matching');self.assertFalse(r['processes'][0]['identity_still_matches']);self.assertFalse(self.history)
    def test_not_listed_prior_task_record_is_not_exit_proof(self):
        path=self.task(101,102,701);self.collect();shutil.rmtree(path);r=self.collect();hint=r['processes'][0]['prior_tasks_not_listed'][0];self.assertEqual(hint['status'],'not_in_complete_enumeration');self.assertFalse(hint['confirmed_exit']);self.assertNotIn(102,self.history[(101,700)])
    def test_history_is_bounded_and_pruned_over_many_turns(self):
        for tid in range(102,202):
            path=self.task(101,tid,tid+1000);self.collect();shutil.rmtree(path);self.assertLessEqual(sum(len(v) for v in self.history.values()),2)
        self.collect();self.assertEqual(set(self.history[(101,700)]),{101})
        with self.assertRaises(ValueError):observer.collect_with_task_visibility(self.proc,self.known,{(101,700):{i:{} for i in range(observer.MAX_THREADS+1)}})
    def test_scan_stops_after_one_over_budget_entry(self):
        class Entry:
            def __init__(self,name):self.name=str(name)
        class Scan:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def __iter__(self):return self
            def __next__(self):
                self.count+=1
                if self.count>observer.MAX_THREADS+1:raise AssertionError('unbounded scan')
                return Entry(self.count)
            count=0
        scan=Scan()
        with patch.object(observer.os,'scandir',return_value=scan):tasks,proof=observer.bounded_tasks(Path('/synthetic'))
        self.assertEqual(len(tasks),observer.MAX_THREADS);self.assertEqual(proof['entries_seen'],observer.MAX_THREADS+1);self.assertFalse(proof['complete'])
    def test_scope_only_registered_process_and_descendants(self):
        self.process(102,701);self.process(999,999);(self.proc/'101/task/101/children').write_text('102');r=self.collect();self.assertEqual({x['identity']['pid'] for x in r['processes']},{101,102});self.assertNotIn((999,999),self.history)
    def test_process_budget_explicit_and_history_bound(self):
        for pid in range(102,114):self.process(pid,pid+1000)
        (self.proc/'101/task/101/children').write_text(' '.join(str(i) for i in range(102,114)));r=self.collect();self.assertTrue(r['process_limit_hit']);self.assertEqual(len(r['processes']),observer.MAX_PROCESSES);self.assertLessEqual(len(self.history),observer.MAX_PROCESSES)
    def loop(self,enabled):
        output=self.root/('on.jsonl' if enabled else 'off.jsonl');stop=self.root/'stop';stop.unlink(missing_ok=True)
        with patch.object(observer.time,'sleep',side_effect=lambda _:stop.touch()):observer.observe(101,700,output,self.root/'ready',stop,'procfs',self.proc,task_visibility=enabled)
        return [json.loads(x) for x in output.read_text().splitlines()]
    def test_enabled_loop_marks_schema_and_keeps_unavailable_stack_counter(self):
        (self.proc/'101/task/101/stack').unlink();rows=self.loop(True);self.assertEqual(rows[0]['task_visibility_schema_version'],1);self.assertEqual(rows[-1]['kernel_stack_reads_unavailable'],1);self.assertEqual(rows[-1]['kernel_stack_reads_ok'],0);self.assertFalse(rows[-1]['userspace_stacks_requested'])
    def test_default_loop_never_invokes_task_collection(self):
        with patch.object(observer,'collect_with_task_visibility',side_effect=AssertionError('default off')):rows=self.loop(False)
        self.assertNotIn('task_visibility_schema_version',rows[0]);self.assertNotIn('task_evidence',rows[1]['processes'][0]['threads'][0])
    def test_original_helpers_constants_GDB_and_parent_class_unchanged(self):
        def nodes(path):return {n.name:ast.dump(n) for n in ast.parse(path.read_text()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        old,new=nodes(OLD),nodes(HERE/'shutdown_observer.py')
        for name in ('read_limited','identity','same_identity','identity_state','collect','gdb_stack','Observer'):self.assertEqual(old[name],new[name],name)
        for name in ('MAX_PROCESSES','MAX_THREADS','MAX_READ','MAX_SAMPLES','PERIOD'):self.assertEqual(getattr(observer,name),getattr(prior,name))
    def test_flag_cli_off_by_default_and_GDB_refused(self):
        argv=['observer','--pid','101','--start-ticks','700','--output','/unused/o','--ready','/unused/r','--stop','/unused/s']
        with patch.object(sys,'argv',argv),patch.object(observer,'observe') as run:observer.main();self.assertFalse(run.call_args.kwargs['task_visibility'])
        with patch.object(sys,'argv',argv+['--task-visibility']),patch.object(observer,'observe') as run:observer.main();self.assertTrue(run.call_args.kwargs['task_visibility'])
        with patch.object(sys,'argv',argv+['--task-visibility','--mode','gdb']),patch.object(observer,'observe') as run,self.assertRaises(SystemExit):observer.main()
        run.assert_not_called()
    def test_frozen_assessor_still_rejects_real_N1_2903(self):
        gate=module('old_frozen_gate',ROOT/'evidence/m3-current-long-preparation-2026-11-10/lifecycle.py')
        p=ROOT/'evidence/m3-current-long-execution-2026-11-10/cases/N1-combined-2903';s=json.loads((p/'strict-assessment.json').read_text());final=s['launches']['operator']['measurement'];rows=[json.loads(x) for x in (p/'native-observer/blocked-target-shutdown-stacks.jsonl').read_text().splitlines()]
        with self.assertRaisesRegex(ValueError,'live target kernel stack unavailable'):gate.coverage(rows,final['child'],final['stages']['rows'])
    def test_reappearance_with_new_final_identity_marks_prior_change(self):
        path=self.task(101,102,701);self.collect();(path/'stat').write_text(stat_text(102,999));actual=observer.read_limited;first=True
        def read(file,*args):
            nonlocal first
            if Path(file)==path/'stat' and first:first=False;return dict(status='unavailable',error='FileNotFoundError',errno=2)
            return actual(file,*args)
        with patch.object(observer,'read_limited',side_effect=read):e=self.thread(self.collect(),102)['task_evidence']
        self.assertEqual(e['identity_before']['status'],'missing');self.assertEqual(e['identity_after']['identity']['start_ticks'],999);self.assertTrue(e['changed_since_prior']);self.assertFalse(e['confirmed_exit'])
    def test_directory_read_errors_are_not_absence(self):
        for error in (PermissionError(13,'denied'),OSError(20,'not a directory'),OSError(5,'I/O')):
            with self.subTest(error=error),patch.object(Path,'stat',side_effect=error):p=observer.task_presence(Path('/synthetic'))
            self.assertEqual(p['result']['status'],'unavailable');self.assertEqual(p['result']['errno'],error.errno)
    def test_parent_disappearance_does_not_confirm_task_exit(self):
        actual=observer.identity_state;calls=0
        def state(proc,expected):
            nonlocal calls
            calls+=1
            if calls==2:(self.proc/'101/stat').unlink()
            return actual(proc,expected)
        with patch.object(observer,'identity_state',side_effect=state):r=self.collect()
        self.assertEqual(self.thread(r)['task_evidence']['lifetime_status'],'parent_identity_not_matching');self.assertEqual(r['processes'][0]['identity_check']['status'],'process_missing');self.assertFalse(self.history)
    def test_truncated_scan_keeps_thread_cap_and_avoids_absence_claim(self):
        self.collect()
        for tid in range(102,102+observer.MAX_THREADS):self.task(101,tid,tid+1000)
        r=self.collect();p=r['processes'][0];self.assertEqual(len(p['threads']),observer.MAX_THREADS);self.assertTrue(p['threads_truncated']);self.assertFalse(p['task_enumeration']['complete']);self.assertTrue(all(not h['confirmed_exit'] and h['status']=='not_in_bounded_scan' for h in p['prior_tasks_not_listed']))
    def test_enumeration_failure_is_timestamped_and_invalidates_history(self):
        self.collect()
        with patch.object(observer.os,'scandir',side_effect=PermissionError(13,'denied')):r=self.collect()
        p=r['processes'][0];self.assertEqual(p['status'],'unavailable');self.assertEqual(p['errno'],13);self.assertLessEqual(p['task_enumeration_error']['begin_ns'],p['task_enumeration_error']['end_ns']);self.assertFalse(self.history)

if __name__=='__main__':unittest.main()
