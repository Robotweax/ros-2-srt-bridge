import json
from m3_closure_assessor import require
from socket_gate import check

def trace_check(path,pid,fixture=False):
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    require(rows and sorted(r['sequence'] for r in rows)==list(range(1,len(rows)+1)),'stage sequence gap/duplicate')
    require(all(r['pid']==pid and r['tid']>0 and r['monotonic_ns']>0 and r['dropped_before']==0 for r in rows),'stage identity/drop failure')
    required=['fixture_ready','fixture_sigint_observed','fixture_blocked_begin','fixture_blocked_end','fixture_exit'] if fixture else ['main_spin_begin','main_spin_end','ros_context_shutdown_callback','node_destructor_begin','node_endpoint_stop_begin','node_endpoint_stop_end','node_endpoint_join_begin','node_endpoint_join_end','worker_stop_begin','worker_stop_end','worker_join_begin','worker_join_end','endpoint_transport_join_begin','endpoint_transport_join_end','epoll_release_begin','epoll_release_end','provider_release_begin','provider_release_locked','provider_cleanup_begin','provider_cleanup_end','provider_release_end','node_trace_drain_begin','node_trace_drain_end','main_node_reset_begin','main_node_reset_end','main_context_shutdown_begin','main_context_shutdown_end']
    points={r['point'] for r in rows};require(set(required)<=points,'missing shutdown stage: '+str(set(required)-points))
    pairs=[('fixture_blocked_begin','fixture_blocked_end')] if fixture else [('main_spin_begin','main_spin_end'),('node_endpoint_join_begin','node_endpoint_join_end'),('worker_join_begin','worker_join_end'),('endpoint_transport_join_begin','endpoint_transport_join_end'),('provider_cleanup_begin','provider_cleanup_end'),('main_node_reset_begin','main_node_reset_end'),('node_trace_drain_begin','node_trace_drain_end')]
    for begin,end in pairs:
        a=next(r for r in rows if r['point']==begin);b=next(r for r in rows if r['point']==end)
        require(a['tid']==b['tid'] and a['monotonic_ns']<=b['monotonic_ns'],'stage pair clock/thread mismatch')
    return dict(records=len(rows),points=sorted(points),rows=rows,sockets=check(rows))

