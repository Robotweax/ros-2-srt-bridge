"""Launch-bound pre-exec readiness; no workload, privilege change or process creation."""
import hashlib
import json
import types
import os
from pathlib import Path
import secrets
import time
from m3_observer_filtering import status,require_role
# Load the intended frozen helper by exact source bytes, independent of
# sys.path, sys.modules and timestamp-based bytecode caches. Never fall back.
IDENTITY_HELPER_PATH=Path(__file__).resolve().parents[2]/'evidence/m3-current-n0-preparation-2026-11-10/shutdown_observer.py'
IDENTITY_HELPER_SHA256='f4b2d9ed4f31bded2772d61081b7a9de8ac88ebfabc7ef690f24f149515868d3'
_identity_source=IDENTITY_HELPER_PATH.read_bytes()
if hashlib.sha256(_identity_source).hexdigest()!=IDENTITY_HELPER_SHA256:raise RuntimeError('bound identity helper source hash differs; no fallback')
_identity_module=types.ModuleType('_robotweax_n0_launch_identity_v1')
_identity_module.__file__=str(IDENTITY_HELPER_PATH)
exec(compile(_identity_source,str(IDENTITY_HELPER_PATH),'exec'),_identity_module.__dict__)
identity=_identity_module.identity
IDENTITY_HELPER_BINDING=dict(path=str(IDENTITY_HELPER_PATH),sha256=IDENTITY_HELPER_SHA256,module=identity.__module__,required_fields=['pid','start_ticks','ppid','state','name'])

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
    result=dict(pid=pid,begin_ns=time.monotonic_ns(),identity_helper=dict(IDENTITY_HELPER_BINDING))
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
        if record['snapshot'].get('identity_helper')!=IDENTITY_HELPER_BINDING:raise ValueError('foreign identity helper binding')
        stable(record['snapshot'],expected);require_role(record['snapshot']['permissions'],0)
        stable(current,expected)
        if child.poll() is not None:raise ValueError('child exited before attestation')
        require_role(current['permissions'],0)
        return dict(**current['identity_after'],permissions=current['permissions'],monotonic_ns=current['end_ns'],launch_token=launch['token'],launch_name=launch['name'],readiness_phase=PHASE,execed_bridge_attested=False,identity_helper=current['identity_helper'])
    except (OSError,ValueError,KeyError,TypeError) as error:
        failure(launch,'parent',error,current,phase='attestation',record=record,expected_identity=registration['identity'])
        raise ValueError('launch capability attestation failed; exact snapshot retained') from error


def unavailable(child,registration,reason,proc=Path('/proc')):
    failure(registration['launch'],'parent',reason,snapshot(child.pid,proc),phase='waiting_for_preexec')
    raise ValueError(reason+'; launch snapshot retained')
