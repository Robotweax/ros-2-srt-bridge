#!/usr/bin/env python3
"""Build installed SDK + Jazzy adapters and run a private two-container M2 scenario."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import shlex
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'ros2-srt-m2@sha256:8073dba4247e6957ced6b3def0d6100e0bc7d983ba22f309b1c04e8d55e46c21'
IMAGE_ID = 'sha256:bab4ed00856d8bbe557e404e1c5bf88a5978628ab55bfea058ac1d4e6012cb86'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-image', action='store_true', help='build and qualify a new image from the pinned ROS base')
    parser.add_argument('--skip-build', action='store_true', help='development rerun; not qualification evidence')
    args = parser.parse_args()
    if args.build_image and args.skip_build:
        parser.error('--build-image requires a full qualification build')
    baseline_path = ROOT / 'baselines/m2-acceptance.json'
    accepted = json.loads(baseline_path.read_text()) if baseline_path.exists() else {}
    image_reference = accepted.get('image_reference', IMAGE)
    expected_image_id = accepted.get('image_platform_id', IMAGE_ID)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run = ROOT / '.local/m2' / stamp
    run.mkdir(parents=True)
    inside = '/workspace/' + str(run.relative_to(ROOT))
    report = {'status': 'running', 'qualification_build': not args.skip_build, 'commands': [],
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                for base in ['src', 'ros2', 'proto', 'cmake', 'containers']
                for p in sorted((ROOT/base).rglob('*')) if p.is_file() and '__pycache__' not in str(p)},
              'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    containers = []
    network = 'srt-m2-' + stamp.lower()
    credential = run / 'passphrase'
    credential.touch(mode=0o600)
    credential.write_text(secrets.token_urlsafe(32) + '\n')
    procs = []

    def save():
        (run/'run.json').write_text(json.dumps(report, indent=2)+'\n')

    def execute(name, argv):
        print(name, flush=True)
        item = {'name': name, 'argv': argv}
        report['commands'].append(item)
        save()
        with (run/(name+'.log')).open('w') as log:
            result = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        item['exit_code'] = result.returncode
        save()
        if result.returncode:
            raise RuntimeError(name + ' failed; see ' + str(run/(name+'.log')))

    def docker(command):
        return ['docker', 'run', '--rm', '--pull=never', '--platform', 'linux/amd64', '--network', 'none',
                '-v', str(ROOT)+':/workspace', '-w', '/workspace', image_reference, 'bash', '-c', command]

    try:
        if args.build_image:
            execute('image-build', ['docker', 'build', '--platform', 'linux/amd64', '--pull=false',
                    '-f', 'containers/m2.Dockerfile', '-t', 'ros2-srt-m2:20261105', '.'])
            image_reference = 'ros2-srt-m2:20261105'
        info = json.loads(subprocess.check_output(['docker', 'image', 'inspect', '--platform', 'linux/amd64', image_reference], text=True))[0]
        assert info['Architecture'] == 'amd64' and info['Os'] == 'linux'
        if not args.build_image:
            assert info['Id'] == expected_image_id
        image_reference = info['RepoDigests'][0]
        report['image_id'] = info['Id']
        report['image_reference'] = image_reference
        report['new_environment_qualification'] = args.build_image
        if not args.skip_build:
            execute('build', docker('set -e; '
                'cmake -S . -B build/m2-sdk -G Ninja -DCMAKE_BUILD_TYPE=Release '
                '-DCMAKE_PREFIX_PATH=/workspace/install/srt-m0 -DBUILD_MANAGEMENT_CODEC=ON '
                '-DBUILD_SRT_TRANSPORT=ON -DBUILD_TESTING=ON -DBUILD_SHARED_LIBS=OFF; '
                'cmake --build build/m2-sdk --parallel 3; '
                'cmake --install build/m2-sdk --prefix /workspace/install/bridge-m2; '
                'source /opt/ros/jazzy/setup.bash; '
                'colcon --log-base '+inside+'/colcon-build build --cmake-clean-first --base-paths ros2 '
                '--build-base build/m2-ros --install-base install/m2-ros '
                '--cmake-args -DCMAKE_BUILD_TYPE=Release '
                '-DCMAKE_PREFIX_PATH="/workspace/install/bridge-m2;/workspace/install/srt-m0"'))
            execute('ros-tests', docker('set -e; source /opt/ros/jazzy/setup.bash; '
                'source install/m2-ros/setup.bash; '
                'colcon --log-base '+inside+'/colcon-test test --base-paths ros2 --build-base build/m2-ros '
                '--install-base install/m2-ros --return-code-on-test-failure; '
                'colcon test-result --test-result-base build/m2-ros --verbose'))
        execute('versions', docker('dpkg-query -W ros-jazzy-rclcpp ros-jazzy-rclpy ros-jazzy-sensor-msgs '
                  'ros-jazzy-rmw-fastrtps-cpp libprotobuf-dev libssl-dev libsqlite3-dev ninja-build'))
        execute('network', ['docker', 'network', 'create', '--internal', network])
        for role, domain in [('operator', 42), ('robot', 41)]:
            name = network+'-'+role
            execute(role+'-container', ['docker', 'run', '-d', '--pull=never', '--platform', 'linux/amd64',
                '--network', network, '--name', name, '-e', 'ROS_DOMAIN_ID='+str(domain),
                '-e', 'ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST', '-e', 'RMW_IMPLEMENTATION=rmw_fastrtps_cpp',
                '-v', str(ROOT)+':/workspace', '-v', str(credential)+':/run/bridge/passphrase:ro',
                '-w', '/workspace', image_reference, 'sleep', 'infinity'])
            containers.append(name)
        peers = {}
        for role, name in zip(('operator', 'robot'), containers):
            info = json.loads(subprocess.check_output(['docker', 'inspect', name], text=True))[0]
            peers[role] = info['NetworkSettings']['Networks'][network]['IPAddress']
            assert not peers[role].startswith('127.') and not info['HostConfig']['PortBindings']
        report['isolation'] = {'network': network, 'internal': True, 'addresses': peers,
                               'ros_domains': {'robot': 41, 'operator': 42}, 'dds_discovery': 'LOCALHOST'}
        save()
        for role, name in zip(('operator', 'robot'), containers):
            command = ('source /opt/ros/jazzy/setup.bash; source install/m2-ros/setup.bash; '
                       'exec python3 ros2/robotweax_srt_bridge_demo/scripts/m2_scenario.py '+
                       shlex.join(['--role', role, '--run', inside, '--peer', peers['operator']]))
            log = (run/(role+'-scenario.log')).open('w')
            proc = subprocess.Popen(['docker', 'exec', name, 'bash', '-c', command], cwd=ROOT,
                                    stdout=log, stderr=subprocess.STDOUT)
            procs.append((proc, log, role))
        end = time.monotonic()+180
        while time.monotonic() < end:
            if any(p.poll() not in (None, 0) for p, _, _ in procs):
                raise RuntimeError('scenario failed: '+str(run))
            if all(p.poll() is not None for p, _, _ in procs):
                break
            time.sleep(.5)
        else:
            raise RuntimeError('scenario deadline exceeded')
        result = json.loads((run/'operator-result.json').read_text())
        assert result['status'] == 'passed'
        report['results'] = result
        report['status'] = 'passed'
    except BaseException as error:
        report['status'] = 'failed'
        report['error'] = str(error)
        raise
    finally:
        for name in reversed(containers):
            subprocess.run(['docker', 'rm', '-f', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for proc, log, _ in procs:
            proc.wait(timeout=10)
            log.close()
        subprocess.run(['docker', 'network', 'rm', network], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        credential.unlink(missing_ok=True)
        save()
        print(run, flush=True)


if __name__ == '__main__':
    main()
