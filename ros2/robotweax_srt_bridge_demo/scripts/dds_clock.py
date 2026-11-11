"""Bracket realtime with monotonic reads so scheduling is uncertainty, not drift."""
import time


def clock_sample():
    before=time.monotonic_ns();wall=time.time_ns();after=time.monotonic_ns()
    return wall,(wall-after,wall-before)


def interval_distance(first,second):
    if first[0]>first[1] or second[0]>second[1]:raise ValueError('invalid clock interval')
    return max(0,first[0]-second[1],second[0]-first[1])


class ClockMonitor:
    def __init__(self,reference,limit_ns=1000000):
        if reference[1]-reference[0]>limit_ns:raise ValueError('clock reference too wide')
        self.reference=self.previous=reference
        self.limit_ns=limit_ns;self.max_step_ns=self.max_deviation_ns=self.max_width_ns=0
        self.steps=[]

    @property
    def qualified(self):
        return self.max_step_ns<=self.limit_ns

    def observe(self,wall,interval):
        step=interval_distance(interval,self.previous)
        self.max_step_ns=max(self.max_step_ns,step)
        self.max_deviation_ns=max(self.max_deviation_ns,interval_distance(interval,self.reference))
        width=interval[1]-interval[0];self.max_width_ns=max(self.max_width_ns,width)
        if step>self.limit_ns and len(self.steps)<16:
            self.steps.append(dict(realtime_ns=wall,previous_interval=list(self.previous),interval=list(interval),minimum_step_ns=step))
        self.previous=interval
        return self.qualified and width<=self.limit_ns
