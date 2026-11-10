"""Launch-bound pre-exec readiness; no workload, privilege change or process creation."""
import json
import os
from pathlib import Path
import secrets
import time
from m3_observer_filtering import status,require_role
from shutdown_observer import identity

PHASE='capabilities_reduced_preexec'


def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.tmp')
    with temporary.open('x') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')
    os.replace(temporary,path)


def new_launch(run,role,name,binary):
    if role not in ('operator','robot') or not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in name):raise ValueError('unsafe launch name')
    token=secrets.token_hex(16)
    return dict(schema_version=1,token=token,role=role,name=name,binary=str(binary),record=str(Path(run)/'launch-readiness'/(role+'-'+name+'-'+token+'.json')))


def snapshot(pid,proc=Path('/proc')):
    result=dict(pid=pid,begin_ns=time.monotonic_ns())
    # Keep the exact one status read used by the validator, bracketed by identity.
    for key,read in (('identity_before',lambda:identity(proc,pid)),('permissions',lambda:status(pid,proc)),('identity_after',lambda:identity(proc,pid))):
        try:result[key]=read()
        except (OSError,ValueError,IndexError) as error:result[key+'_error']=dict(type=type(error).__name__,errno=getattr(error,'errno',None),message=str(error))
    result['end_ns']=time.monotonic_ns();return result


def stable(value,expected):
    for key in ('identity_before','identity_after'):
        row=value[key]
        if any(row[k]!=expected[k] for k in ('pid','start_ticks','ppid')) or row['state'] in ('Z','X'):raise ValueError('child identity changed, exited or unavailable')
    if int(value['permissions']['Pid'])!=expected['pid'] or int(value['permissions']['PPid'])!=expected['ppid']:raise ValueError('status belongs to another child')


def failure(launch,side,error,current,**extra):
    path=Path(launch['record']).with_suffix('.'+side+'-failure.json')
    if not path.exists():atomic(path,dict(schema_version=1,status='failed',launch=launch,side=side,error=str(error),snapshot=current,**extra))
    return path


def register(child,launch,proc=Path('/proc')):
    current=snapshot(child.pid,proc)
    try:
        expected=current['identity_before'];stable(current,expected)
        if child.poll() is not None:raise ValueError('child exited before launch registration')
    except (KeyError,ValueError) as error:
        failure(launch,'parent',error,current,phase='registration');raise ValueError('launch registration failed; snapshot retained') from error
    return dict(launch=launch,identity=expected)


def publish(launch,pid,proc=Path('/proc')):
    current=snapshot(pid,proc)
    try:
        stable(current,current['identity_before']);require_role(current['permissions'],0)
        if Path(launch['record']).exists():raise ValueError('launch record already exists')
        atomic(launch['record'],dict(schema_version=1,phase=PHASE,launch=launch,snapshot=current))
    except (KeyError,ValueError,OSError) as error:
        failure(launch,'wrapper',error,current,phase=PHASE);raise


def check(child,registration,proc=Path('/proc')):
    launch=registration['launch'];path=Path(launch['record'])
    if not path.exists():return None
    current=snapshot(child.pid,proc);record=None
    try:
        record=json.loads(path.read_text())
        if record['schema_version']!=1 or record['phase']!=PHASE or record['launch']!=launch:raise ValueError('foreign launch or wrong readiness phase')
        expected=registration['identity']
        stable(record['snapshot'],expected);require_role(record['snapshot']['permissions'],0)
        stable(current,expected)
        if child.poll() is not None:raise ValueError('child exited before attestation')
        require_role(current['permissions'],0)
        return dict(**current['identity_after'],permissions=current['permissions'],monotonic_ns=current['end_ns'],launch_token=launch['token'],launch_name=launch['name'],readiness_phase=PHASE,execed_bridge_attested=False)
    except (OSError,ValueError,KeyError,TypeError) as error:
        failure(launch,'parent',error,current,phase='attestation',record=record,expected_identity=registration['identity'])
        raise ValueError('launch capability attestation failed; exact snapshot retained') from error


def unavailable(child,registration,reason,proc=Path('/proc')):
    failure(registration['launch'],'parent',reason,snapshot(child.pid,proc),phase='waiting_for_preexec')
    raise ValueError(reason+'; launch snapshot retained')
