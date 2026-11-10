#!/usr/bin/env python3
"""Opt-in independent Linux shutdown observer. Procfs is read-only; GDB is intrusive."""
import argparse
import json
import os
from pathlib import Path
import signal
import stat as stat_module
import subprocess
import sys
import time

MAX_PROCESSES=8
MAX_THREADS=64
MAX_READ=16384
MAX_SAMPLES=48
PERIOD=.25


def read_limited(path,limit=MAX_READ):
    try:
        with Path(path).open('rb') as f:data=f.read(limit+1)
        return dict(status='ok',text=data[:limit].decode(errors='replace'),truncated=len(data)>limit)
    except OSError as error:return dict(status='unavailable',error=type(error).__name__,errno=error.errno)


def identity(proc,pid):
    value=(proc/str(pid)/'stat').read_text();fields=value[value.rfind(')')+2:].split()
    return dict(pid=pid,start_ticks=int(fields[19]),state=fields[0],ppid=int(fields[1]),name=value[value.find('(')+1:value.rfind(')')])


def same_identity(proc,expected):
    try:return identity(proc,expected['pid'])['start_ticks']==expected['start_ticks']
    except (OSError,ValueError,IndexError):return False


def identity_state(proc,expected):
    try:
        current=identity(proc,expected['pid'])
        return dict(status='matching' if current['start_ticks']==expected['start_ticks'] else 'pid_reused',observed=current,checked_ns=time.monotonic_ns())
    except FileNotFoundError as error:
        return dict(status='process_missing',errno=error.errno,checked_ns=time.monotonic_ns())
    except (OSError,ValueError,IndexError) as error:
        return dict(status='identity_unavailable',error=type(error).__name__,errno=getattr(error,'errno',None),checked_ns=time.monotonic_ns())


def collect(proc,known):
    """Only the registered process and discovered descendants; never scan global /proc."""
    pending=list(known.values());seen=set();rows=[];limited=False
    while pending and len(rows)<MAX_PROCESSES:
        expected=pending.pop(0);pid=expected['pid']
        if pid in seen:continue
        seen.add(pid)
        check=identity_state(proc,expected)
        if check['status']!='matching':
            rows.append(dict(identity=expected,status=check['status'],identity_check=check));continue
        task=proc/str(pid)/'task'
        try:tasks=sorted(task.iterdir(),key=lambda p:int(p.name))
        except OSError as error:rows.append(dict(identity=expected,status='unavailable',error=type(error).__name__));continue
        threads=[]
        for thread in tasks[:MAX_THREADS]:
            threads.append(dict(tid=int(thread.name),stat=read_limited(thread/'stat'),wchan=read_limited(thread/'wchan'),syscall=read_limited(thread/'syscall'),kernel_stack=read_limited(thread/'stack')))
            children=read_limited(thread/'children')
            for child in children.get('text','').split():
                try:
                    child_id=identity(proc,int(child));key=(child_id['pid'],child_id['start_ticks'])
                    if key not in known:
                        if len(known)>=MAX_PROCESSES:limited=True;continue
                        known[key]=child_id;pending.append(child_id)
                except (OSError,ValueError,IndexError):continue
        after=identity_state(proc,expected)
        rows.append(dict(identity=expected,status='sampled',threads=threads,threads_truncated=len(tasks)>MAX_THREADS,identity_still_matches=after['status']=='matching',identity_check=after))
    return dict(processes=rows,process_limit_hit=limited or bool(pending))


def timed_read(path):
    begin=time.monotonic_ns();result=read_limited(path)
    return dict(begin_ns=begin,end_ns=time.monotonic_ns(),result=result)


def task_identity(record,tid):
    """A stat file binds a TID incarnation, never just a task directory name."""
    if record['status']!='ok':
        if record.get('error')=='FileNotFoundError' and record.get('errno')==2:return dict(status='missing',errno=2)
        return dict(status='unavailable',error=record.get('error'),errno=record.get('errno'))
    if record['truncated']:return dict(status='unavailable',error='truncated_stat')
    try:
        text=record['text'];left=text.index('(');right=text.rindex(')');fields=text[right+2:].split()
        actual=int(text[:left].strip());start=int(fields[19]);name=text[left+1:right]
        if text[left-1]!=' ' or text[right+1]!=' ' or actual!=tid or not 0<tid<2**31 or not 0<start<2**64 or len(name)>64 or fields[0] not in ('R','S','D','Z','T','t','X','x','K','W','P','I'):raise ValueError('task identity fields')
        return dict(status='known',identity=dict(tid=tid,start_ticks=start,name=name,state=fields[0]))
    except (ValueError,IndexError,TypeError) as error:return dict(status='unavailable',error='invalid_stat',detail=str(error)[:128])


def task_presence(path):
    begin=time.monotonic_ns()
    try:
        value=path.stat()
        result=dict(status='present' if stat_module.S_ISDIR(value.st_mode) else 'unexpected_file_type',inode=value.st_ino,device=value.st_dev)
    except FileNotFoundError as error:result=dict(status='absent',errno=error.errno)
    except OSError as error:result=dict(status='unavailable',error=type(error).__name__,errno=error.errno)
    return dict(begin_ns=begin,end_ns=time.monotonic_ns(),result=result)


def bounded_tasks(task):
    """At most MAX_THREADS+1 directory entries; overflow remains explicit."""
    begin=time.monotonic_ns();tasks=[];seen=0
    with os.scandir(task) as entries:
        for entry in entries:
            seen+=1
            if seen>MAX_THREADS:break
            tid=int(entry.name)
            if not 0<tid<2**31:raise ValueError('invalid task directory name')
            tasks.append(task/entry.name)
    tasks.sort(key=lambda path:int(path.name))
    return tasks,dict(begin_ns=begin,end_ns=time.monotonic_ns(),entries_seen=seen,complete=seen<=MAX_THREADS,selected_tids=[int(p.name) for p in tasks])


def task_lifetime(before,after,presence):
    """Descriptive evidence only; no gate waiver or confirmed-exit authority."""
    if before['status']=='known' and after['status']=='known':
        a,b=before['identity'],after['identity']
        if (a['tid'],a['start_ticks'])!=(b['tid'],b['start_ticks']):return 'tid_reused'
        return 'matching' if presence['status']=='present' else 'presence_changed_after_stat'
    if after['status']=='missing' and presence['status']=='absent' and presence.get('errno')==2:
        if before['status']=='known':return 'absent_after_identified_read'
        if before['status']=='missing':return 'absent_without_current_identity'
        return 'absent_with_invalid_initial_identity'
    if before['status']=='missing' and after['status']=='known':return 'appeared_after_initial_absence'
    return 'identity_or_presence_unavailable'


def collect_with_task_visibility(proc,known,history):
    """Fixed extra checks, one stack attempt, bounded one-sample identity hints."""
    if len(history)>MAX_PROCESSES or any(len(tasks)>MAX_THREADS for tasks in history.values()):raise ValueError('task history budget exceeded')
    for key in list(history):
        if key not in known:del history[key]
    pending=list(known.values());seen=set();rows=[];limited=False
    while pending and len(rows)<MAX_PROCESSES:
        expected=pending.pop(0);pid=expected['pid'];key=(pid,expected['start_ticks'])
        if pid in seen:continue
        seen.add(pid);before=identity_state(proc,expected)
        if before['status']!='matching':
            history.pop(key,None);rows.append(dict(identity=expected,status=before['status'],identity_check=before));continue
        task=proc/str(pid)/'task';enumeration_begin=time.monotonic_ns()
        try:tasks,enumeration=bounded_tasks(task)
        except (OSError,ValueError) as error:
            history.pop(key,None);rows.append(dict(identity=expected,status='unavailable',error=type(error).__name__,errno=getattr(error,'errno',None),task_enumeration_error=dict(begin_ns=enumeration_begin,end_ns=time.monotonic_ns())));continue
        prior=history.get(key,{});threads=[];current={}
        for thread in tasks:
            tid=int(thread.name);reads={name:timed_read(thread/name) for name in ('stat','wchan','syscall','stack','children')}
            final_stat=timed_read(thread/'stat');presence=task_presence(thread)
            first_id=task_identity(reads['stat']['result'],tid);last_id=task_identity(final_stat['result'],tid)
            lifetime=task_lifetime(first_id,last_id,presence['result'])
            prior_id=prior.get(tid)
            observed_id=first_id if first_id['status']=='known' else last_id
            changed_since_prior=bool(prior_id and observed_id['status']=='known' and prior_id['start_ticks']!=observed_id['identity']['start_ticks'])
            evidence=dict(schema_version=1,parent_identity=dict(pid=pid,start_ticks=expected['start_ticks']),enumeration_begin_ns=enumeration['begin_ns'],enumeration_end_ns=enumeration['end_ns'],reads=reads,final_stat=final_stat,directory_presence=presence,identity_before=first_id,identity_after=last_id,lifetime_status=lifetime,prior_sample_identity_hint=prior_id,changed_since_prior=changed_since_prior,confirmed_exit=False,scope='snapshot identity/absence only; no exit code, no-reuse, replay or gate authority')
            threads.append(dict(tid=tid,stat=reads['stat']['result'],wchan=reads['wchan']['result'],syscall=reads['syscall']['result'],kernel_stack=reads['stack']['result'],task_evidence=evidence))
            if last_id['status']=='known' and presence['result']['status']=='present':current[tid]=last_id['identity']
            for child in reads['children']['result'].get('text','').split():
                try:
                    child_id=identity(proc,int(child));child_key=(child_id['pid'],child_id['start_ticks'])
                    if child_key not in known:
                        if len(known)>=MAX_PROCESSES:limited=True;continue
                        known[child_key]=child_id;pending.append(child_id)
                except (OSError,ValueError,IndexError):continue
        after=identity_state(proc,expected)
        for thread in threads:
            thread['task_evidence']['parent_identity_check']=after
            if after['status']!='matching':thread['task_evidence']['lifetime_status']='parent_identity_not_matching'
        hints=[dict(identity=identity,status='not_in_complete_enumeration' if enumeration['complete'] else 'not_in_bounded_scan',confirmed_exit=False) for tid,identity in sorted(prior.items()) if tid not in enumeration['selected_tids']]
        if after['status']=='matching':history[key]=current
        else:history.pop(key,None)
        rows.append(dict(identity=expected,status='sampled',threads=threads,threads_truncated=not enumeration['complete'],identity_still_matches=after['status']=='matching',identity_before=before,identity_check=after,task_enumeration=enumeration,prior_tasks_not_listed=hints))
    if len(history)>MAX_PROCESSES or sum(len(tasks) for tasks in history.values())>MAX_PROCESSES*MAX_THREADS:raise ValueError('task history budget exceeded')
    return dict(processes=rows,process_limit_hit=limited or bool(pending),task_visibility_schema_version=1)


def gdb_stack(proc,expected):
    begin=time.monotonic_ns()
    if not same_identity(proc,expected):return dict(status='gone_or_reused',identity=expected,begin_ns=begin,end_ns=time.monotonic_ns(),intrusive=True)
    try:
        if len(list((proc/str(expected['pid'])/'task').iterdir()))>MAX_THREADS:return dict(status='thread_budget_exceeded',identity=expected,intrusive=False)
    except OSError:return dict(status='gone_or_unavailable',identity=expected,intrusive=False)
    argv=['gdb','--batch','--nx','--nh','-iex','set auto-load off','-iex','set debuginfod enabled off','-ex','set pagination off','-ex','set print thread-events off','-ex','set backtrace limit 32','-ex','set print frame-arguments none','-ex','thread apply all bt','-ex','detach','-p',str(expected['pid'])]
    try:
        # Output goes to a private temporary file, avoiding pipe backpressure and unbounded RAM.
        import tempfile
        with tempfile.TemporaryFile() as log:
            import resource
            def bound_output():resource.setrlimit(resource.RLIMIT_FSIZE,(65536,65536))
            child=subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,DEBUGINFOD_URLS=''),preexec_fn=bound_output)
            timed_out=False;forced=False
            try:child.wait(timeout=.75)
            except subprocess.TimeoutExpired:
                timed_out=True;child.send_signal(signal.SIGINT)
                try:child.wait(timeout=.25)
                except subprocess.TimeoutExpired:forced=True;child.kill();child.wait(timeout=.25)
            log.seek(0);data=log.read(65537)
        matches=same_identity(proc,expected)
        return dict(status='captured' if child.returncode==0 and not timed_out and matches and b'#0' in data else 'unavailable_or_incomplete',identity=expected,begin_ns=begin,end_ns=time.monotonic_ns(),intrusive=True,returncode=child.returncode,timed_out=timed_out,debugger_forced_kill=forced,identity_still_matches=matches,output=data[:65536].decode(errors='replace'),output_truncated=len(data)>65536,resume_verified=False)
    except OSError as error:return dict(status='unavailable',identity=expected,begin_ns=begin,end_ns=time.monotonic_ns(),intrusive=True,error=type(error).__name__,errno=error.errno)


def observe(pid,start_ticks,output,ready,stop,mode,proc=Path('/proc'),*,task_visibility=False):
    if task_visibility and mode!='procfs':raise ValueError('task visibility requires procfs mode')
    known={(pid,start_ticks):dict(pid=pid,start_ticks=start_ticks)}
    if not same_identity(proc,known[(pid,start_ticks)]):raise ValueError('registered root identity unavailable')
    start=time.monotonic();samples=0;gdb_done=set();reason='sample_limit';kernel_ok=kernel_unavailable=0;task_history={}
    with output.open('x') as log:
        def emit(value):log.write(json.dumps(value)+'\n');log.flush()
        emit(dict(kind='begin',clock='monotonic',boot_id=read_limited(proc/'sys/kernel/random/boot_id'),time_namespace_offsets=read_limited(proc/'self/timens_offsets'),pid=os.getpid(),root=known[(pid,start_ticks)],mode=mode,observer_independent=True,kernel_stacks_only=mode=='procfs',**(dict(task_visibility_schema_version=1,task_history_capacity=MAX_PROCESSES*MAX_THREADS) if task_visibility else {})))
        ready.write_text(json.dumps(dict(pid=os.getpid(),ready_ns=time.monotonic_ns()))+'\n')
        for _ in range(MAX_SAMPLES):
            if stop.exists():reason='parent_stop';break
            if time.monotonic()-start>=12:reason='time_limit';break
            begin=time.monotonic_ns();snapshot=collect_with_task_visibility(proc,known,task_history) if task_visibility else collect(proc,known)
            emit(dict(kind='sample',begin_ns=begin,end_ns=time.monotonic_ns(),**snapshot));samples+=1
            for process in snapshot['processes']:
                for thread in process.get('threads',[]):
                    if thread['kernel_stack']['status']=='ok':kernel_ok+=1
                    else:kernel_unavailable+=1
            if mode=='gdb' and time.monotonic()-start>=2:
                for key,expected in list(known.items()):
                    if stop.exists():break
                    if key not in gdb_done and time.monotonic()-start<12:
                        gdb_done.add(key);emit(dict(kind='userspace_stack',**gdb_stack(proc,expected)))
            if not any(same_identity(proc,p) for p in known.values()):reason='all_owned_processes_gone';break
            time.sleep(PERIOD)
        emit(dict(kind='status',completed=True,reason=reason,samples=samples,sample_limit=MAX_SAMPLES,budget_exhausted=reason in ('sample_limit','time_limit'),kernel_stack_reads_ok=kernel_ok,kernel_stack_reads_unavailable=kernel_unavailable,userspace_stacks_requested=mode=='gdb',end_ns=time.monotonic_ns(),scope='kernel stacks may be denied; userspace GDB attaches pause target and do not qualify timing or prove resumption; no outcome/replay authority'))


class Observer:
    """A separate process, armed before SIGINT; parent wait never drives sampling."""
    def __init__(self,pid,prefix,mode='procfs'):
        if mode not in ('procfs','gdb'):raise ValueError('unsupported stack mode')
        self.prefix=Path(prefix);self.ready=self.prefix.with_suffix('.ready.json');self.stop=self.prefix.with_suffix('.stop');self.output=self.prefix.with_suffix('.jsonl')
        if any(p.exists() for p in (self.ready,self.stop,self.output)):raise ValueError('observer output exists')
        expected=identity(Path('/proc'),pid)
        self.log=self.prefix.with_suffix('.log').open('x')
        try:self.process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--pid',str(pid),'--start-ticks',str(expected['start_ticks']),'--output',str(self.output),'--ready',str(self.ready),'--stop',str(self.stop),'--mode',mode],stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True)
        except BaseException:self.log.close();raise
        until=time.monotonic()+1
        while not self.ready.exists() and self.process.poll() is None and time.monotonic()<until:time.sleep(.01)
        self.armed=self.ready.exists()
    def close(self):
        self.stop.touch();forced=False;group_signal=False
        try:self.process.wait(timeout=1.5)
        except subprocess.TimeoutExpired:
            forced=True
            try:os.killpg(self.process.pid,signal.SIGKILL);group_signal=True
            except ProcessLookupError:pass
            self.process.wait(timeout=1)
        finally:
            self.log.close()
            # The observer owns this isolated session; reap/stop any debugger left behind.
            try:os.killpg(self.process.pid,signal.SIGKILL);group_signal=True
            except ProcessLookupError:pass
        footer={}
        try:
            rows=[json.loads(line) for line in self.output.read_text().splitlines()];footer=rows[-1] if rows and rows[-1].get('kind')=='status' else {}
        except (OSError,ValueError):pass
        return dict(group_cleanup_signal_sent=group_signal,scope='observer lifecycle only; stack availability remains in sample/GDB records; intrusive GDB timing unqualified',footer=footer,armed=self.armed,returncode=self.process.returncode,forced_kill=forced,path=str(self.output),complete=self.armed and not forced and not group_signal and self.process.returncode==0 and footer.get('completed') is True and not footer.get('budget_exhausted',True))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pid',type=int,required=True);p.add_argument('--start-ticks',type=int,required=True)
    for key in ('output','ready','stop'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--mode',choices=('procfs','gdb'),default='procfs')
    p.add_argument('--task-visibility',action='store_true',help='bounded task identity/absence observations; extra work, requires separate calibration')
    a=p.parse_args()
    if a.task_visibility and a.mode!='procfs':p.error('task visibility requires procfs mode')
    observe(a.pid,a.start_ticks,a.output,a.ready,a.stop,a.mode,task_visibility=a.task_visibility)


if __name__=='__main__':main()
