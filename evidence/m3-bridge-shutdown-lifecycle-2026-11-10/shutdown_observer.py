#!/usr/bin/env python3
"""Opt-in independent Linux shutdown observer. Procfs is read-only; GDB is intrusive."""
import argparse
import json
import os
from pathlib import Path
import signal
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


def observe(pid,start_ticks,output,ready,stop,mode,proc=Path('/proc')):
    known={(pid,start_ticks):dict(pid=pid,start_ticks=start_ticks)}
    if not same_identity(proc,known[(pid,start_ticks)]):raise ValueError('registered root identity unavailable')
    start=time.monotonic();samples=0;gdb_done=set();reason='sample_limit';kernel_ok=kernel_unavailable=0
    with output.open('x') as log:
        def emit(value):log.write(json.dumps(value)+'\n');log.flush()
        emit(dict(kind='begin',clock='monotonic',boot_id=read_limited(proc/'sys/kernel/random/boot_id'),time_namespace_offsets=read_limited(proc/'self/timens_offsets'),pid=os.getpid(),root=known[(pid,start_ticks)],mode=mode,observer_independent=True,kernel_stacks_only=mode=='procfs'))
        ready.write_text(json.dumps(dict(pid=os.getpid(),ready_ns=time.monotonic_ns()))+'\n')
        for _ in range(MAX_SAMPLES):
            if stop.exists():reason='parent_stop';break
            if time.monotonic()-start>=12:reason='time_limit';break
            begin=time.monotonic_ns();snapshot=collect(proc,known)
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
    p.add_argument('--mode',choices=('procfs','gdb'),default='procfs');a=p.parse_args()
    observe(a.pid,a.start_ticks,a.output,a.ready,a.stop,a.mode)


if __name__=='__main__':main()
