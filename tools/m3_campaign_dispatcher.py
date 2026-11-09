#!/usr/bin/env python3
"""Frozen sequential M3 dispatch. Preparation never launches a workload."""
import argparse
import json
from pathlib import Path
from m3_source_preflight import ROOT,IMAGE,sha,write,source_inventory
from m3_n4_fixture import native_layout
from m3_closure_assessor import assess_case,evaluate_sequence,require

PLAN='evidence/m3-closure-plan-2026-11-09/plan.json'
HELPERS=('build/m3-monotonic-capture/monotonic_capture','build/m3-netdev-features/netdev_features')
COMBINED_FLAGS=('--skip-build','--monotonic-capture','--command-diagnostics',
    '--provider-diagnostics','--sensor-provider-diagnostics','--start-diagnostics','--sender-diagnostics')


def slots(root=ROOT):
    # Use exactly the predeclared order/settings. Readiness annotations are historical.
    data=json.loads((Path(root)/PLAN).read_text())
    cases=data['proposed_future_cases']
    require(len(cases)==38 and [s['ordinal'] for s in cases]==list(range(1,39)),'invalid campaign order')
    require(len({s['id'] for s in cases})==38,'duplicate case identity')
    for s in cases:require(Path(s['id']).name==s['id'] and s['id'] not in ('.','..'),'unsafe case identity')
    return cases


def invocation(slot):
    """Typed single-case adapters only; never use legacy N4 batch entry points."""
    layout='sender-reconcile'
    if slot['stage']=='N3':
        return dict(adapter='n3',kwargs=dict(capture=True,losses=slot['losses'],seed=slot['seed'],seconds=slot['source_seconds'],runtime_layout=layout))
    if slot['stage'] in ('N0','LONG'):
        return dict(adapter='combined',argv=['--profile',slot['profile'],'--seed',str(slot['seed']),'--seconds',str(slot['source_seconds']),'--runtime-layout',layout,'--image-reference',IMAGE,*COMBINED_FLAGS])
    require(slot['stage']=='N4','unknown stage')
    if slot['id'].startswith('N4-ROS-'):
        return dict(adapter='ros_n4',kwargs=dict(mode=slot.get('direction',slot.get('phase')),runtime_layout=layout))
    require(slot['hold_seconds']==2,'only predeclared bounded two-second N4 cases')
    return dict(adapter='native_n4',kwargs=dict(phase=slot['phase'],direction=slot['direction'],hold_seconds=2,runtime_layout=layout))


def prepare(root=ROOT):
    root=Path(root);selected=native_layout(root,'sender-reconcile');cases=slots(root)
    return dict(schema_version=1,execution_authorized=False,automatic_start=False,
        plan=PLAN,plan_sha256=sha(root/PLAN),case_ids=[s['id'] for s in cases],
        runtime_layout=selected['layout'],candidate_manifest_sha256=selected['layout']['calibration_sha256'],
        source_sha256=source_inventory(root),native_fixture_binding=selected['binding'],
        helper_sha256={p:sha(root/p) for p in HELPERS},image_reference=IMAGE,
        invocations=[dict(id=s['id'],**invocation(s)) for s in cases],
        scope='build/source readiness only; no runtime qualification or execution authorization')


def verify_freeze(freeze,root=ROOT):
    require(freeze==prepare(root),'campaign freeze drift; no launch/advance')


def authorize(authorization,freeze_path,freeze,out,root=ROOT):
    # A separately supplied future grant is required. The prepared freeze is always disabled.
    require(authorization.get('schema_version')==1 and authorization.get('execution_authorized') is True,'campaign execution not authorized')
    require(authorization.get('freeze_sha256')==sha(freeze_path),'authorization belongs to another freeze')
    require(authorization.get('case_ids')==freeze['case_ids'],'authorization case order/scope differs')
    relative=str(Path(out).resolve().relative_to(Path(root).resolve()))
    require(relative.startswith('.local/') and authorization.get('output_relative')==relative,'authorization output differs or is outside .local')
    require(not Path(out).exists(),'campaign output already exists; no resume/retry')


def dispatch_slot(slot,out,root=ROOT):
    """Live adapters; called only behind the explicit execute/authorization gate."""
    spec=invocation(slot)
    if spec['adapter']=='combined':
        from run_m3 import main
        main([*spec['argv'],'--output',str(out)])
    else:
        if spec['adapter']=='n3':from m3_ros_multiroute import run as runner
        elif spec['adapter']=='native_n4':from m3_n4 import run_case as runner
        else:from m3_n4_ros import run_case as runner
        runner(out,**spec['kwargs'])
    path=out/('run.json' if spec['adapter']=='combined' else 'result.json')
    return dict(run=str(out.relative_to(root)),inner_status=json.loads(path.read_text())['status'])


def execute(freeze_path,authorization,out,root=ROOT):
    root=Path(root).resolve();out=Path(out).resolve();freeze=json.loads(Path(freeze_path).read_text())
    authorize(authorization,freeze_path,freeze,out,root)
    verify_freeze(freeze,root)
    out.mkdir(parents=True,exist_ok=False)
    write(out/'freeze.json',freeze);write(out/'authorization.json',authorization)
    cases=slots(root)
    def produce(slot):
        verify_freeze(freeze,root)
        target=out/slot['id']
        require(not target.exists(),'case output already exists')
        write(out/'active-case.json',dict(id=slot['id'],run=str(target.relative_to(root)),status='dispatching'))
        return dispatch_slot(slot,target,root)
    def assess(slot,produced):
        # Both pre/post drift and independent outcome/cleanup checks precede advancement.
        verify_freeze(freeze,root)
        proof=assess_case(root/produced['run'],slot,freeze)
        verify_freeze(freeze,root)
        write(out/(slot['id']+'-assessment.json'),proof)
        return proof
    return evaluate_sequence(cases,produce,assess,lambda report:write(out/'campaign.json',report))


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--freeze',required=True,type=Path)
    p.add_argument('--execute',action='store_true')
    p.add_argument('--authorization',type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args(argv)
    if not a.execute:
        if a.authorization or a.output:p.error('preparation accepts --freeze only')
        if a.freeze.exists():p.error('freeze already exists')
        write(a.freeze,prepare());return 0
    if not a.authorization or not a.output:p.error('execution requires a separate authorization file and fresh output')
    result=execute(a.freeze,json.loads(a.authorization.read_text()),a.output.resolve())
    return int(result['status']!='passed')


if __name__=='__main__':raise SystemExit(main())
