"""Freeze once after offline checks; does not start containers or measurements."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_source_preflight import sha,write,source_inventory,IMAGE
from m3_runtime_layout import matched
from m3_observer_filtering import architecture,profile
OUT=Path(__file__).resolve().parent
NATIVE='ros@sha256:8eed0a4669bbf43ee331878a4c39bd8ebddea8e3312a58b4fae8edb14526b617'


def main():
    if (OUT/'freeze.json').exists():raise ValueError('immutable freeze already exists')
    def query(args):return subprocess.check_output(args,text=True).strip()
    daemon=query(['docker','info','--format','{{.Architecture}}'])
    image=json.loads(query(['docker','image','inspect','--platform','linux/arm64',NATIVE]))[0]
    if architecture(daemon)!='arm64' or image['Architecture']!='arm64':raise ValueError('native ARM64 image/daemon required')
    if query(['docker','ps','--quiet']):raise ValueError('live containers present before calibration')
    layout=matched(ROOT,'shutdown-tracing')
    preserved={}
    for name in ('m3-n3-frozen-cohort-2026-11-09','m3-shutdown-live-calibration-2026-11-09','m3-observer-stack-permissions-2026-11-09'):
        index=ROOT/'evidence'/name/'local-artifact-hashes.json';entries=json.loads(index.read_text())
        for path,item in entries.items():
            if sha(ROOT/path)!=item['sha256'] or (ROOT/path).stat().st_size!=item['bytes']:raise ValueError('retained evidence drift: '+path)
        preserved[name]=dict(index_sha256=sha(index),files=len(entries),bytes=sum(x['bytes'] for x in entries.values()))
    write(OUT/'observer-seccomp.json',profile(daemon,image['Architecture']))
    write(OUT/'observer-architecture.json',dict(native='arm64',daemon=daemon,profile_sha256=sha(OUT/'observer-seccomp.json')))
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    bundle=ROOT/'.local'/('observer-native-bundle-'+stamp);bundle.mkdir()
    files={'blocked_fixture':ROOT/'build/m3-shutdown-observer-calibration/blocked_fixture','shutdown_observer.py':ROOT/'ros2/robotweax_srt_bridge_demo/scripts/shutdown_observer.py','scenario_processes.py':ROOT/'ros2/robotweax_srt_bridge_demo/scripts/scenario_processes.py','m3_observer_filtering.py':ROOT/'tools/m3_observer_filtering.py',**{p:OUT/p for p in ('observer_entry.py','target_entry.py','observer-seccomp.json','observer-architecture.json')}}
    for name,src in files.items():
        shutil.copyfile(src,bundle/name);(bundle/name).chmod(0o555 if name=='blocked_fixture' else 0o444)
    bundle.chmod(0o555)
    inputs=[*files.values(),*(bundle/p for p in files),*(OUT/p for p in ('PLAN.md','run.py','prepare.py'))]
    freeze=dict(schema_version=1,created_utc=stamp,source_commit=query(['git','rev-parse','HEAD']),runtime_layout=layout,source_sha256=source_inventory(),inputs_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},output_relative='.local/observer-native-filter-'+stamp,bundle_relative=str(bundle.relative_to(ROOT)),prefix='observer-native-'+stamp.lower(),observer_image=NATIVE,observer_image_inspect=image,target_image=IMAGE,daemon_architecture=daemon,docker_server=query(['docker','version','--format','{{.Server.Version}}']),preserved_evidence=preserved,readiness_checks=1,blocked_calibration_limit=1,remaining_campaign_cases_disabled=29,retry_two_loss_4211=False,no_tuning=True)
    write(OUT/'freeze.json',freeze)
    print(json.dumps(dict(freeze_sha256=sha(OUT/'freeze.json'),bundle=freeze['bundle_relative'],output=freeze['output_relative'],matched_binaries=len(layout['matched_build_sha256']),preserved_evidence=preserved)))

if __name__=='__main__':main()
