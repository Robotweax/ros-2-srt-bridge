"""Linux endpoint process/clock samples, independent of ROS and transport."""
import json
import os
from pathlib import Path
import time


def parse_stat(raw,page_size):
    fields=raw[raw.rfind(')')+2:].split()
    return dict(start_ticks=int(fields[19]),cpu_ticks=int(fields[11])+int(fields[12]),waited_child_cpu_ticks=int(fields[13])+int(fields[14]),rss_bytes=int(fields[21])*page_size)


def parse_keyed_counters(raw):
    result={}
    for line in raw.splitlines():
        key,value=line.split()
        if key in result:raise ValueError('duplicate counter')
        result[key]=int(value)
        if result[key]<0:raise ValueError('negative counter')
    if not result:raise ValueError('empty counter file')
    return result


def sample_cgroup(root=Path('/sys/fs/cgroup'),proc=Path('/proc/self')):
    """Read namespace-root cgroup v2; never changes limits or membership."""
    try:
        if (proc/'cgroup').read_text().strip()!='0::/':raise ValueError('process not at cgroup namespace root')
        if str(os.getpid()) not in (root/'cgroup.procs').read_text().split():raise ValueError('process absent from sampled cgroup')
        if not (root/'cgroup.controllers').is_file() or (root/'cgroup.type').read_text().strip()!='domain':raise ValueError('unsupported cgroup hierarchy')
        stat=root.stat();namespace=os.readlink(proc/'ns/cgroup')
        cpu=parse_keyed_counters((root/'cpu.stat').read_text())
        if not {'usage_usec','user_usec','system_usec'}<=cpu.keys():raise ValueError('missing CPU counters')
        events=parse_keyed_counters((root/'memory.events').read_text())
        if not {'oom','oom_kill'}<=events.keys():raise ValueError('missing memory event counters')
        memory=int((root/'memory.current').read_text())
        if memory<0:raise ValueError('negative cgroup memory')
        return dict(available=True,identity=dict(device=stat.st_dev,inode=stat.st_ino,namespace=namespace),
            cpu=cpu,memory_current_bytes=memory,memory_events=events,
            limits=dict(cpu_max=(root/'cpu.max').read_text().strip(),memory_max=(root/'memory.max').read_text().strip()))
    except (OSError,ValueError) as error:return dict(available=False,error=str(error))


class EndpointSampler:
    def __init__(self,path):
        self.file=Path(path).open('w');self.previous=0
        clock_name=Path(path).name.replace('-endpoint-samples','-clock-samples')
        if clock_name==Path(path).name:clock_name+='.clock.jsonl'
        self.clock_file=Path(path).with_name(clock_name).open('w');self.previous_clock=0
        self.hz=os.sysconf('SC_CLK_TCK');self.page_size=os.sysconf('SC_PAGE_SIZE')

    def tick(self,roots):
        now=time.monotonic_ns()
        if now-self.previous_clock>=25000000:
            self.previous_clock=now
            begin=time.monotonic_ns();wall=time.time_ns();end=time.monotonic_ns()
            self.clock_file.write(json.dumps(dict(begin_ns=begin,end_ns=end,wall_ns=wall,offset_min_ns=wall-end,offset_max_ns=wall-begin))+'\n')
            self.clock_file.flush()
        if now-self.previous<250000000:return
        self.previous=now;begin=time.monotonic_ns();wall=time.time_ns();clock_end=time.monotonic_ns()
        pending=list(roots);seen=set();rows=[];errors=[]
        while pending:
            label,pid=pending.pop()
            if pid in seen:continue
            seen.add(pid)
            try:
                proc=Path('/proc')/str(pid)
                stat=parse_stat((proc/'stat').read_text(),self.page_size)
                rows.append(dict(label=label,pid=pid,comm=(proc/'comm').read_text().strip(),**stat))
                for task in (proc/'task').iterdir():
                    pending.extend((label,int(child)) for child in (task/'children').read_text().split())
            except (FileNotFoundError,ProcessLookupError,PermissionError) as error:
                errors.append(dict(pid=pid,error=type(error).__name__))
        cgroup=sample_cgroup()
        self.file.write(json.dumps(dict(begin_ns=begin,end_ns=time.monotonic_ns(),wall_ns=wall,
            offset_min_ns=wall-clock_end,offset_max_ns=wall-begin,hz=self.hz,page_size_bytes=self.page_size,processes=rows,errors=errors,cgroup=cgroup))+'\n')
        self.file.flush()

    def close(self):self.file.close();self.clock_file.close()
