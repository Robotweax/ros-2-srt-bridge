"""One predeclared three-slot calibration. No campaign dispatcher or N3 fault case."""
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
sys.path.insert(1,str(ROOT/'ros2/robotweax_srt_bridge_demo/scripts'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from m3_runtime_layout import matched
from m3_ros_multiroute import run as run_sensor
from m3_closure_assessor import require,cleanup,assess_n3_result,validate_n3_artifacts,evaluate_sequence
from scenario_processes import stop_children

OUT=Path(__file__).resolve().parent
FIXTURE='build/m3-shutdown-observer-calibration/blocked_fixture'
PLAN=[dict(id='default-off-N0',kind='sensor',diagnostics=False),dict(id='enabled-procfs-N0',kind='sensor',diagnostics=True),dict(id='independent-blocked-procfs',kind='blocked')]


def trace_check(path,pid,fixture=False):
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    require(rows and sorted(r['sequence'] for r in rows)==list(range(1,len(rows)+1)),'stage sequence gap/duplicate')
    require(all(r['pid']==pid and r['tid']>0 and r['monotonic_ns']>0 and r['dropped_before']==0 for r in rows),'stage identity/drop failure')
    required=['fixture_ready','fixture_sigint_observed','fixture_blocked_begin','fixture_blocked_end','fixture_exit'] if fixture else ['main_spin_begin','main_spin_end','ros_context_shutdown_callback','node_destructor_begin','node_endpoint_stop_begin','node_endpoint_stop_end','node_endpoint_join_begin','node_endpoint_join_end','worker_stop_begin','worker_stop_end','worker_join_begin','worker_join_end','endpoint_transport_join_begin','endpoint_transport_join_end','socket_close_begin','socket_close_end','epoll_release_begin','epoll_release_end','provider_release_begin','provider_release_locked','provider_cleanup_begin','provider_cleanup_end','provider_release_end','node_trace_drain_begin','node_trace_drain_end','main_node_reset_begin','main_node_reset_end','main_context_shutdown_begin','main_context_shutdown_end']
    points={r['point'] for r in rows};require(set(required)<=points,'missing shutdown stage: '+str(set(required)-points))
    pairs=[('fixture_blocked_begin','fixture_blocked_end')] if fixture else [('main_spin_begin','main_spin_end'),('node_endpoint_join_begin','node_endpoint_join_end'),('worker_join_begin','worker_join_end'),('endpoint_transport_join_begin','endpoint_transport_join_end'),('provider_cleanup_begin','provider_cleanup_end'),('main_node_reset_begin','main_node_reset_end'),('node_trace_drain_begin','node_trace_drain_end')]
    for begin,end in pairs:
        a=next(r for r in rows if r['point']==begin);b=next(r for r in rows if r['point']==end)
        require(a['tid']==b['tid'] and a['monotonic_ns']<=b['monotonic_ns'],'stage pair clock/thread mismatch')
    return dict(records=len(rows),points=sorted(points),rows=rows)


def observer_check(run,child,require_blocked=False):
    control=child.get('stack_observer',{});require(control.get('complete') and child.get('stack_observer_armed'),'observer control incomplete')
    path=Path(control['path']);path=ROOT/str(path).removeprefix('/workspace/') if str(path).startswith('/workspace/') else path
    rows=[json.loads(line) for line in path.read_text().splitlines()]
    ready=json.loads(path.with_suffix('.ready.json').read_text());require(ready['ready_ns']<=child['signal_begin_ns'],'observer not ready before SIGINT')
    begin=rows[0];require(begin['observer_independent'] and begin['pid']!=child['pid'] and begin['root']['pid']==child['pid'],'observer/root identity mismatch')
    require(begin['boot_id']['status']=='ok' and begin['time_namespace_offsets']['status']=='ok','observer clock namespace proof unavailable')
    offsets=begin['time_namespace_offsets']['text'].splitlines()
    require(offsets and all(len(line.split())==3 and all(int(v)==0 for v in line.split()[1:]) for line in offsets),'observer nonzero time namespace')
    require(begin['mode']=='procfs' and not any(r['kind']=='userspace_stack' for r in rows),'unplanned GDB attach')
    samples=[r for r in rows if r['kind']=='sample'];post=[r for r in samples if child['signal_end_ns']<=r['begin_ns']<=r['end_ns']<=child['end_ns']]
    require(all(not s['process_limit_hit'] and all(not p.get('threads_truncated',False) and p.get('identity_still_matches',True) for p in s['processes']) for s in samples),'observer identity/budget incomplete')
    threads=[t for s in post for p in s['processes'] if p.get('status')=='sampled' for t in p['threads']]
    available=[t for t in threads if t['kernel_stack']['status']=='ok' and t['kernel_stack'].get('text','').strip()]
    unavailable=[t['kernel_stack'] for t in threads if t['kernel_stack']['status']!='ok']
    proof=dict(control=control,post_signal_samples=len(post),post_signal_thread_reads=len(threads),nonempty_post_signal_kernel_stacks=len(available),unavailable_post_signal_kernel_stacks=len(unavailable),kernel_errors=unavailable[:4],rows_sha256=sha(path),intrusive=False)
    if require_blocked:
        require(len(post)>=2,'independent observer did not cover blocked parent wait')
        write(run/'observer-coverage.json',proof)
        require(available,'post-signal kernel stack unavailable; independent sampling is not stack calibration')
    return proof


def blocked(run,freeze):
    run.mkdir();inside='/workspace/'+str(run.relative_to(ROOT))
    argv=['docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none','-v',str(ROOT)+':/workspace','-w','/workspace',IMAGE,'python3',str(OUT.relative_to(ROOT)/'calibrate.py'),'--inside-blocked',inside]
    with (run/'container.log').open('w') as log:code=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=25).returncode
    require(code==0,'blocked fixture container failed; inspect retained log')
    return dict(run=str(run.relative_to(ROOT)),inner_status=json.loads((run/'result.json').read_text())['status'])


def inside_blocked(run):
    log=(run/'target.log').open('w');target=subprocess.Popen([str(ROOT/FIXTURE),str(run/'stages.jsonl'),str(run/'target-ready')],stdout=log,stderr=subprocess.STDOUT)
    until=time.monotonic()+5
    while not (run/'target-ready').exists() and target.poll() is None and time.monotonic()<until:time.sleep(.01)
    report=None
    try:
        require((run/'target-ready').exists(),'controlled target not ready')
        report=stop_children([(target,'blocked-target',log)],observer_directory=run,stack_mode='procfs')
        require(report['passed'],'controlled target exceeded unchanged5s child wait')
        write(run/'result.json',dict(status='passed',shutdown=report,fixture_hold_seconds=3))
    finally:
        if target.poll() is None:target.kill();target.wait(timeout=2)
        if not log.closed:log.close()
        if report is not None:write(run/'child-shutdown.json',report)


def execute():
    freeze=json.loads((OUT/'freeze.json').read_text());run=ROOT/freeze['output_relative']
    require(not run.exists(),'calibration output exists; no retry')
    def verify():
        require(matched(ROOT,'shutdown-tracing')==freeze['runtime_layout'],'matched build drift')
        require(source_inventory()==freeze['source_sha256'],'source drift')
        require(all(sha(ROOT/p)==h for p,h in freeze['driver_and_fixture_sha256'].items()),'driver/fixture drift')
    verify();run.mkdir();write(run/'freeze.json',freeze)
    def produce(slot):
        verify();target=run/slot['id'];print('START '+slot['id'],flush=True)
        if slot['kind']=='sensor':
            result=run_sensor(target,capture=True,losses=0,seed=1701,seconds=10,runtime_layout='shutdown-tracing',shutdown_diagnostics=slot['diagnostics'],shutdown_stacks=slot['diagnostics'],shutdown_stack_mode='procfs')
            return dict(run=str(target.relative_to(ROOT)),inner_status=result['status'])
        return blocked(target,freeze)
    def assess(slot,produced):
        verify();target=ROOT/produced['run'];result=json.loads((target/'result.json').read_text());require(result['status']=='passed','inner fixture failed: '+str(result.get('error')))
        proofs={}
        if slot['kind']=='sensor':
            fake=dict(source_seconds=10,seed=1701,losses=0);proofs['sensor']=assess_n3_result(result,fake);validate_n3_artifacts(target,result,fake);cleanup(target)
            for role in ('operator','robot'):
                bridge=next(c for c in result['child_shutdown'][role]['children'] if '-bridge-' in c['name'])
                if slot['diagnostics']:
                    proofs[role]=dict(stages=trace_check(target/(role+'-shutdown-stages.jsonl'),bridge['pid']),observer=observer_check(target,bridge))
                else:
                    require(not list(target.glob('*shutdown-stages*')) and not list(target.glob('*shutdown-stacks*')),'default-off emitted diagnostics')
                    require(all('stack_observer' not in c for c in result['child_shutdown'][role]['children']),'default-off observer launched')
        else:
            child=result['shutdown']['children'][0]
            proofs['stages']=trace_check(target/'stages.jsonl',child['pid'],fixture=True)
            elapsed=child['end_ns']-child['signal_end_ns'];require(2_500_000_000<=elapsed<=5_000_000_000 and not child['forced_kill'],'controlled blocked wait outside declared window')
            proofs['observer']=observer_check(target,child,require_blocked=True)
        verify();write(target/'calibration-assessment.json',dict(status='passed',proofs=proofs));print('PASS '+slot['id'],flush=True);return dict(status='passed',proofs=proofs)
    def record(report):
        report.update(all_campaign_stages_disabled=True,retry_two_loss_4211=False,remaining_campaign_cases_disabled=29,scope='bounded shutdown visibility calibration only',no_tuning=True)
        write(run/'calibration.json',report)
        if report['rows'][-1]['status']=='failed':print('STOP '+report['rows'][-1]['slot']['id']+': '+report['rows'][-1]['error'],flush=True)
    result=evaluate_sequence(PLAN,produce,assess,record);print('FINAL '+result['status'],flush=True);return result


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--inside-blocked':inside_blocked(Path(sys.argv[2]))
    elif len(sys.argv)==1:raise SystemExit(execute()['status']!='passed')
    else:raise SystemExit('no alternative slot order or retry entry point')
