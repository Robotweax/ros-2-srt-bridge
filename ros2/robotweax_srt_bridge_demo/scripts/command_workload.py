"""Pure workload policy shared by DDS driver tests; no transport or ROS calls."""
import math


class Cadence:
    def __init__(self,start,period=2):
        if not math.isfinite(start) or not math.isfinite(period) or period<=0:raise ValueError('invalid cadence')
        self.next=start;self.period=period;self.skipped=0

    def due(self,now,available):
        if now<self.next:return False
        slots=math.floor((now-self.next)/self.period)+1
        self.next+=slots*self.period
        self.skipped+=slots-(1 if available else 0)
        return available


def audit_commands(rows,begin_device,final_device,cutoff_ns=None):
    numbers=[r['number'] for r in rows]
    if len(set(numbers))!=len(numbers):raise ValueError('duplicate intent number')
    successes=0;unknown=0
    for row in rows:
        if cutoff_ns is not None:
            if row['submitted_monotonic_ns']>cutoff_ns:raise ValueError('intent submitted after cutoff')
            if 'result_observed_monotonic_ns' in row:
                observed=row['result_observed_monotonic_ns']
                if observed>cutoff_ns+8000000000:raise ValueError('result observed beyond drain')
                if row.get('observed_after_data_cutoff')!=(observed>=cutoff_ns):raise ValueError('incorrect result observation phase')
        if row['new_generation']!=row['expected_generation']+1:raise ValueError('invalid workload generation')
        if row.get('terminal')==4:
            if not row.get('result_valid') or row.get('result_rate_hz')!=200 or row.get('result_generation')!=row['new_generation']:raise ValueError('invalid confirmed result')
            successes+=1
        if row.get('terminal')==8:
            if row.get('result_valid'):raise ValueError('UNKNOWN result must be invalid')
            unknown+=1
    effects=final_device['effects']-begin_device['effects']
    generation=final_device['generation']-begin_device['generation']
    possible=sum(r.get('terminal')!='not_admitted' for r in rows)
    if effects<successes or effects>possible or generation!=effects:raise ValueError('effect/generation population mismatch')
    return dict(attempts=len(rows),confirmed_successes=successes,unknown=unknown,effects=effects,
        unresolved=sum('terminal' not in r for r in rows),not_admitted=sum(r.get('terminal')=='not_admitted' for r in rows),
        all_succeeded=bool(rows) and successes==len(rows) and effects==successes,
        scope='effect count bounded by distinct intents; UNKNOWN/unresolved may have effects; no nonexecution inferred')


def record_status_observation(row,status,observed_ns):
    """Local status snapshot only: errors/timeouts never manufacture a terminal result."""
    if observed_ns<row['submitted_monotonic_ns']:raise ValueError('status predates submission')
    if observed_ns<row.get('last_status_observation',{}).get('observed_monotonic_ns',0):raise ValueError('status observation time regressed')
    row['status_observations']=row.get('status_observations',0)+1
    row['last_status_observation']={key:status[key] for key in ('found','state','reason','local_error','revision','query_queued')}
    row['last_status_observation'].update(observed_monotonic_ns=observed_ns,
        budget_elapsed=observed_ns-row['submitted_monotonic_ns']>=5000000000)
    # Keep the first 32 and most recent 32 polls. Long reconciliation waits must
    # remain diagnosable without unbounded per-intent memory or invented results.
    history=row.setdefault('status_observation_history',[])
    history.append(dict(row['last_status_observation']))
    if len(history)>64:
        del history[32]
        row['status_observations_omitted']=row.get('status_observations_omitted',0)+1
    if status['local_error']==2:row['not_found_status_observations']=row.get('not_found_status_observations',0)+1
