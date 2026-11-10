"""Temporary overlay: retained workload gates + modeled launch/observer timeline.
Not a new campaign result. Original files and decisions are never written.
"""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from unittest.mock import patch
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'tools')]
from campaign_binding import load

def read(path):return json.loads(path.read_text())
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value)+'\n')
def lines(path):return [json.loads(x) for x in path.read_text().splitlines()]
def jsonl(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(''.join(json.dumps(x)+'\n' for x in value))
def overlay(out):
    public=ROOT/'evidence/m3-current-long-execution-2026-11-10/cases/N1-combined-1701';raw=ROOT/'.local/current-long-cohort-20261110T152312809927Z/N1-combined-1701'
    shutil.copytree(public,out,dirs_exist_ok=True)
    for path in [*raw.glob('*.sqlite'),*raw.glob('*-bridge-*.log')]:shutil.copyfile(path,out/path.name)
    shutil.rmtree(out/'launch-readiness')
    source=ROOT/'evidence/m3-current-n0-lifecycle-stabilization-2026-11-10/validation/test_lifecycle.py'
    spec=importlib.util.spec_from_file_location('campaign_launch_model',source);module=importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules,{name:load(name) for name in ('launch_readiness','launch_records','launch_assessment')}):spec.loader.exec_module(module)
    fixture=module.Fixture(out)
    entry=fixture.entries['operator','measurement'];catalog=read(out/'operator-bridge-launches.json');registration=catalog['launches'][0]['registration'];registration.update(pid=7,start_ticks=769);catalog['launches'][0]['pid']=7;write(out/'operator-bridge-launches.json',catalog)
    info=read(out/entry['identity_path']);info.update(pid=7,start_ticks=769);info['permissions']['Pid']='7'
    calibration=ROOT/'evidence/m3-task-post-sigint-calibration-execution-2026-11-10/run/data'
    rows=lines(calibration/'blocked-target-shutdown-stacks.jsonl');calchild=read(calibration/'result.json')['shutdown']['children'][0]
    info['boot_id']=rows[0]['boot_id']['text'].strip();write(out/entry['identity_path'],info);write(out/'operator-bridge-identity.json',info)
    ready=read(out/entry['readiness_path']);ready['snapshot']['identity_before'].update(pid=7,start_ticks=769);ready['snapshot']['identity_after'].update(pid=7,start_ticks=769);ready['snapshot']['permissions']['Pid']='7';write(out/entry['readiness_path'],ready)
    child=fixture.reports['operator']['children'][0];child.update(pid=7,start_ticks=769)
    for role,report in fixture.reports.items():write(out/(role+'-child-shutdown.json'),report)
    stages=lines(out/entry['trace_path'])
    for stage in stages:stage['pid']=7
    jsonl(out/entry['trace_path'],stages)
    room=child['end_ns']-child['signal_end_ns']
    scale=max(10,(calchild['end_ns']-calchild['signal_end_ns'])*2//room+1)
    def retime(value):
        if isinstance(value,dict):return {k:child['signal_end_ns']+(v-calchild['signal_end_ns'])//scale if k.endswith('_ns') and type(v) is int else retime(v) for k,v in value.items()}
        if isinstance(value,list):return [retime(v) for v in value]
        return value
    jsonl(out/'native-observer/blocked-target-shutdown-stacks.jsonl',retime(rows))
    events=retime(lines(calibration/'observer-exec.jsonl'));jsonl(out/'operator-observer-exec.jsonl',events);jsonl(out/'native-observer/observer-exec.jsonl',events)
    write(out/'operator-observer-ready.json',retime(read(calibration/'blocked-target-shutdown-stacks.ready.json')))
    return read(raw/'run.json'),load('cases').cases()[0],fixture
