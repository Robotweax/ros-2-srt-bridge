"""Temporary modeled campaign launch/SDK captures; no real case qualification."""
import importlib.util
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
from campaign_binding import load

def read(path):return json.loads(path.read_text())
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value)+'\n')
def lines(path):return [json.loads(x) for x in path.read_text().splitlines()]
def jsonl(path,rows):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(''.join(json.dumps(x)+'\n' for x in rows))
def overlay(out,slot):
    path=ROOT/'evidence/m3-sdkros-task-calibration-preparation-2026-11-10/validation/model.py';spec=importlib.util.spec_from_file_location('prior_SDK_overlay',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);result,_,fixture=m.overlay(out)
    from m3_network import PROFILES
    profile=PROFILES[slot['profile']];network=read(out/'network.json');network['commands']=[c for c in network['commands'] if not c['label'].startswith('profile-')]
    for role in ('operator','robot'):
        seed=slot['seed']+(role=='operator')
        for i,argv in enumerate(profile.commands(seed)):network['commands'].append(dict(label=f'profile-{role}-{i}',exit_code=0,argv=['docker','exec',network['containers'][role],*argv]))
        q=dict(kind='netem',handle='1:',root=True,options=dict(seed=seed,limit=profile.queue_packets,delay=dict(delay=profile.delay_ms/1000,jitter=profile.jitter_ms/1000),**{'loss-random':dict(loss=profile.loss_percent/100)}));state=[q]
        if slot['profile']=='N5':q.pop('root');q.update(handle='10:',parent='1:1');state.insert(0,dict(kind='tbf',handle='1:',root=True,options=dict(rate=64000,burst=4096)))
        write(out/(f'profile-{role}-readback.log'),state)
    write(out/'network.json',network);return result,fixture
