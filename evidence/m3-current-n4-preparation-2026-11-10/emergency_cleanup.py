"""Failure-only bounded cleanup of recorded owned N4 lab objects; never retries cases."""
import json
from m3_source_preflight import write


def cleanup(target,command):
    if not target.exists():return
    (target/'release').touch();(target/'resume').touch();(target/'restored').touch();(target/'settle').touch()
    path=target/'network.json';rows=[]
    if path.exists():
        data=json.loads(path.read_text());network=data['network']
        if not network.startswith('ros2-srt-m3-') or set(data['containers'])!={'operator','robot'} or any(name!=network+'-'+role for role,name in data['containers'].items()):raise ValueError('cannot verify N4 cleanup ownership')
        for argv in [*(['docker','rm','-f',name] for name in data['containers'].values()),['docker','network','rm',network]]:
            try:
                value=command(argv,capture_output=True,text=True,timeout=15);rows.append(dict(argv=argv,exit_code=value.returncode,stdout=value.stdout,stderr=value.stderr))
            except BaseException as error:rows.append(dict(argv=argv,error=str(error)))
    (target/'passphrase').unlink(missing_ok=True)
    write(target/'emergency-cleanup.json',dict(scope='owned failure cleanup only; case stays failed',commands=rows))
