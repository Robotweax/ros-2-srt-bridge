"""Best-effort cleanup of this case only after an unexpected host exception."""
import json
from m3_source_preflight import write


def cleanup(target,prefix,command):
    if not target.exists():return
    log=[]
    def call(args):
        try:
            result=command(args,capture_output=True,text=True,timeout=15)
            log.append(dict(argv=args,exit_code=result.returncode,stdout=result.stdout,stderr=result.stderr))
            return result
        except BaseException as error:log.append(dict(argv=args,error=str(error)));return None
        finally:write(target/'emergency-cleanup.json',dict(scope='unexpected exception cleanup only; case remains failed',commands=log))
    observer=prefix+'-observer';state=call(['docker','inspect',observer])
    if state is not None and state.returncode==0:
        call(['docker','kill',observer]);destination=target/'emergency-observer';destination.mkdir(exist_ok=True)
        call(['docker','cp',observer+':/out/.',str(destination)]);call(['docker','rm','-f',observer])
    call(['docker','volume','rm',prefix+'-observer-output'])
    path=target/'network.json'
    if path.exists():
        data=json.loads(path.read_text());network=data['network']
        if not network.startswith('ros2-srt-m3-') or any(role not in ('operator','robot') or name!=network+'-'+role for role,name in data['containers'].items()):raise ValueError('cannot verify emergency lab ownership')
        for name in data['containers'].values():call(['docker','rm','-f',name])
        call(['docker','network','rm',network])
    (target/'passphrase').unlink(missing_ok=True)
