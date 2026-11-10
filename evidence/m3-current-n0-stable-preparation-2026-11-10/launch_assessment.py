"""Closed-file N0 launch/stage binding; never select first child or splice traces."""
import json
from pathlib import Path
from m3_observer_filtering import require_role
from launch_readiness import PHASE,IDENTITY_HELPER_BINDING,IDENTITY_HELPER_PATH,stable
from launch_records import plan_launch
from stage_gate import trace_check

ROOT=Path(__file__).resolve().parents[2]
BINDING=dict(IDENTITY_HELPER_BINDING,path='/workspace/'+str(IDENTITY_HELPER_PATH.relative_to(ROOT)))
PLAN={'operator':(('operator-bridge-0','measurement'),),'robot':(('wrong-hash','negative_type_hash'),('robot-bridge-1','warmup'),('robot-bridge-2','measurement'))}


def require(value,message):
    if not value:raise ValueError(message)


def assess_launches(out,reports):
    out=Path(out);load=lambda path:json.loads((out/path).read_text())
    result={};tokens=set();trace_paths=set()
    for role,expected in PLAN.items():
        catalog=load(role+'-bridge-launches.json')
        require(catalog['schema_version']==1 and catalog['role']==role,'catalog schema/role mismatch')
        entries=catalog['launches'];require([(e['context']['name'],e['purpose']) for e in entries]==list(expected),'missing/extra/reordered launch')
        require(not (out/(role+'-shutdown-stages.jsonl')).exists(),'legacy role trace is not per-launch evidence')
        children=reports[role]['children'];require(reports[role]['passed'] and all(c['passed'] and not c['forced_kill'] and c['returncode']==0 for c in children),'role child shutdown failed')
        accepted={};ordinal=0;seen_children=set();identities=set()
        for entry in entries:
            context=entry['context'];token=context['token'];negative=entry['purpose']=='negative_type_hash'
            require(context['schema_version']==1 and context['role']==role and len(token)==32 and all(c in '0123456789abcdef' for c in token) and token not in tokens,'invalid/duplicate launch identity')
            tokens.add(token)
            if not negative:ordinal+=1
            expected_entry=plan_launch(context,max(ordinal,1))
            for key in ('purpose','readiness_path','identity_path','trace_path','requires_trace'):require(entry[key]==expected_entry[key],'launch path/purpose mismatch: '+key)
            require(Path(context['record']).name==Path(entry['readiness_path']).name,'readiness context filename differs')
            registration=entry['registration'];require(registration and entry['pid']==registration['pid'],'missing launch registration')
            key=(registration['pid'],registration['start_ticks']);require(key not in identities,'duplicate registered launch identity');identities.add(key)
            ready=load(entry['readiness_path']);require(ready['schema_version']==1 and ready['phase']==PHASE and ready['launch']==context,'foreign readiness record')
            require(ready['snapshot']['identity_helper']==BINDING,'identity helper binding differs')
            stable(ready['snapshot'],registration);require_role(ready['snapshot']['permissions'],0)
            if negative:
                require(entry['returncode']==1 and not entry['attested'],'negative startup outcome differs')
                require('ROS type hash mismatch' in (out/'wrong-hash.log').read_text() and load('robot-ready.json')['wrong_hash_rejected'] is True,'negative startup proof missing')
                continue
            require(entry['attested'] and entry['returncode']==0,'positive launch not attested or did not exit cleanly')
            info=load(entry['identity_path']);require(info['launch_token']==token and info['launch_name']==context['name'] and info['identity_helper']==BINDING,'foreign attested identity')
            require(all(info[k]==registration[k] for k in ('pid','start_ticks','ppid')),'attested process identity differs');require_role(info['permissions'],0)
            hits=[(i,c) for i,c in enumerate(children) if c.get('launch_token')==token]
            require(len(hits)==1,'missing/duplicate launch child outcome');index,child=hits[0];seen_children.add(index)
            require(child['name']==context['name'] and child['pid']==registration['pid'] and child['start_ticks']==registration['start_ticks'] and child['purpose']==entry['purpose'] and child['trace_path']==entry['trace_path'] and child['identity_path']==entry['identity_path'],'child outcome bound to another launch')
            require(0<child['signal_begin_ns']<=child['signal_end_ns']<=child['end_ns'],'missing/invalid SIGINT/reap bracket')
            stage=trace_check(out/entry['trace_path'],child['pid'])
            require(all(ready['snapshot']['end_ns']<=r['monotonic_ns']<=child['end_ns'] for r in stage['rows']),'trace outside launch lifetime')
            require(next(r['monotonic_ns'] for r in stage['rows'] if r['point']=='main_spin_end')>=child['signal_begin_ns'],'shutdown trace precedes this SIGINT')
            require(entry['trace_path'] not in trace_paths,'trace path reused');trace_paths.add(entry['trace_path'])
            accepted[entry['purpose']]=dict(entry=entry,child=child,identity=info,stages=stage)
        require({i for i,c in enumerate(children) if '-bridge-' in c['name']}==seen_children,'unbound bridge child outcome')
        final=accepted['measurement'];require(load(role+'-bridge-identity.json')==final['identity'],'observer-compatible identity is not final launch')
        if role=='robot':require(accepted['warmup']['child']['end_ns']<=load(final['entry']['readiness_path'])['snapshot']['begin_ns'],'warmup/final launch overlap')
        result[role]=accepted
    actual={str(p.relative_to(out)) for p in (out/'launch-readiness').glob('*.shutdown.jsonl')}
    require(actual==trace_paths,'missing/unlisted shutdown trace file')
    return result
