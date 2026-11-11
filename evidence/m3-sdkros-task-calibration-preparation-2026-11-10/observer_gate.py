"""Closed-file calibrated collector/exec/launch/clock binding; no live calls."""
import hashlib
import json
from pathlib import Path
from m3_observer_filtering import require_role
from task_assessment import COLLECTOR_SHA,require,offsets
HERE=Path(__file__).resolve().parent

def check_observer(out,rows,child,info,ready):
    load=lambda name:[json.loads(line) for line in (out/name).read_text().splitlines()]
    events=load('operator-observer-exec.jsonl');final=load('native-observer/observer-exec.jsonl')
    require(events==final and [e['kind'] for e in events]==['entry','preexec_verified','exec_begin'],'observer bootstrap population/binding differs')
    begin=rows[0];require(begin['pid']==events[0]['pid']==ready['pid'] and ready['ready_ns']<=child['signal_begin_ns'],'observer launch/readiness differs')
    require_role(events[1]['permissions'],1<<21)
    require(all(e.get('collector_sha256')==COLLECTOR_SHA and e.get('task_visibility') is True for e in events[1:]),'observer collector activation binding differs')
    require(events[2]['target']==dict(pid=info['pid'],start_ticks=info['start_ticks'])==begin['root'],'observer exec target differs')
    profile=hashlib.sha256((HERE/'observer-seccomp.json').read_bytes()).hexdigest()
    require(events[1]['profile_sha256']==profile,'observer profile source differs')
    require(begin['boot_id']['text'].strip()==info['boot_id']==events[1]['boot_id'],'observer boot differs')
    for text in (info['time_namespace_offsets'],events[1]['time_namespace_offsets']):offsets(dict(status='ok',text=text,truncated=False))
    return dict(collector_sha256=COLLECTOR_SHA,task_visibility=True,exec_target=events[2]['target'],profile_sha256=profile,scope='closed-file launch/exec/clock binding, not a live permission attestation')
