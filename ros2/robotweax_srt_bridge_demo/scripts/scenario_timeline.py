"""Bounded development timeline; snapshots are observations, not wire evidence."""
import json
import time


class Timeline:
    def __init__(self,path,limit=2048):
        if type(limit) is not int or limit<1:raise ValueError('invalid timeline limit')
        self.file=path.open('x');self.limit=limit;self.count=0;self.last_ns=None;self.key=None;self.closed=False;self.exhausted=False

    def observe(self,phase,state,counts,now=None):
        if self.closed:raise ValueError('timeline already closed')
        now=time.monotonic_ns() if now is None else now
        if self.last_ns is not None and now<self.last_ns:raise ValueError('timeline clock regressed')
        key=(phase,None if state is None else state['ready'],None if state is None else state['failed'])
        if key==self.key and self.last_ns is not None and now-self.last_ns<1000000000:return
        if self.count>=self.limit:
            self.exhausted=True
            raise ValueError('timeline budget exhausted')
        self.file.write(json.dumps(dict(kind='snapshot',monotonic_ns=now,phase=phase,command=state,typed_counts=counts))+'\n');self.file.flush()
        self.last_ns=now;self.key=key;self.count+=1

    def close(self):
        if not self.closed:
            self.file.write(json.dumps(dict(kind='status',recorded=self.count,limit=self.limit,exhausted=self.exhausted))+'\n');self.file.close();self.closed=True
