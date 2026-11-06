"""Linux endpoint process/clock samples, independent of ROS and transport."""
import json
import os
from pathlib import Path
import time


def parse_stat(raw,page_size):
    fields=raw[raw.rfind(')')+2:].split()
    return dict(start_ticks=int(fields[19]),cpu_ticks=int(fields[11])+int(fields[12]),waited_child_cpu_ticks=int(fields[13])+int(fields[14]),rss_bytes=int(fields[21])*page_size)


class EndpointSampler:
    def __init__(self,path):
        self.file=Path(path).open('w');self.previous=0
        self.hz=os.sysconf('SC_CLK_TCK');self.page_size=os.sysconf('SC_PAGE_SIZE')

    def tick(self,roots):
        now=time.monotonic_ns()
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
        self.file.write(json.dumps(dict(begin_ns=begin,end_ns=time.monotonic_ns(),wall_ns=wall,
            offset_min_ns=wall-clock_end,offset_max_ns=wall-begin,hz=self.hz,page_size_bytes=self.page_size,processes=rows,errors=errors))+'\n')
        self.file.flush()

    def close(self):self.file.close()
