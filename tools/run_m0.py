#!/usr/bin/env python3
"""Build and qualify pinned SRT/ROS inputs; keep every attempt in .local/m0.

No host network configuration or real hardware is used. Images are resolved to
immutable repository digests before execution. Dependency sources are a separate clone.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def capture(args):
    return subprocess.check_output(args, cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--srt-source', type=Path, default=ROOT.parent,
                        help='local SRT repository to clone without changing it')
    parser.add_argument('--build-image', action='store_true')
    args = parser.parse_args()
    baseline = json.loads((ROOT / 'baselines/dependencies.json').read_text())
    run = ROOT / '.local/m0' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True)
    report = {'status': 'running', 'commands': [], 'baseline_sha256':
              hashlib.sha256((ROOT / 'baselines/dependencies.json').read_bytes()).hexdigest()}

    def save():
        (run / 'run.json').write_text(json.dumps(report, indent=2) + '\n')

    def logged(name, command):
        report['commands'].append({'log': name + '.log', 'argv': command})
        save()
        print(name, flush=True)
        with (run / (name + '.log')).open('w') as out:
            result = subprocess.run(command, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
        report['commands'][-1]['exit_code'] = result.returncode
        save()
        if result.returncode:
            raise RuntimeError(f'{name} failed; see {run / (name + ".log")}')

    try:
        dep = ROOT / '.deps/srt'
        if not dep.exists():
            dep.parent.mkdir(exist_ok=True)
            logged('clone', ['git', 'clone', '--no-checkout', str(args.srt_source.resolve()), str(dep)])
            logged('checkout', ['git', '-C', str(dep), 'checkout', '--detach', baseline['srt']['candidate_sha']])
        actual = capture(['git', '-C', str(dep), 'rev-parse', 'HEAD'])
        dirty = capture(['git', '-C', str(dep), 'status', '--porcelain', '--untracked-files=all'])
        if actual != baseline['srt']['candidate_sha'] or dirty:
            raise RuntimeError('SRT source must be clean and match candidate SHA')
        report['srt_sha'] = actual
        report['srt_source_dirty'] = False
        if args.build_image:
            logged('image-build', ['docker', 'build', '--platform', 'linux/amd64', '-f',
                   'containers/m0.Dockerfile', '-t', 'ros2-srt-m0:20261104', '.'])
        dev_ref = 'ros2-srt-m0:20261104' if args.build_image else baseline['environment']['development_image_reference']
        dev = json.loads(capture(['docker', 'image', 'inspect', '--platform', 'linux/amd64', dev_ref]))[0]
        ros_ref = baseline['ros']['image_reference']
        ros = json.loads(capture(['docker', 'image', 'inspect', '--platform', 'linux/amd64', ros_ref]))[0]
        for image in (dev, ros):
            if image['Os'] != 'linux' or image['Architecture'] != 'amd64':
                raise RuntimeError('Image platform mismatch')
        report['development_image_id'] = dev['Id']
        report['ros_image_id'] = ros['Id']
        dev_run_ref = dev['RepoDigests'][0]
        report['development_image_reference'] = dev_run_ref
        report['ros_image_reference'] = ros_ref
        mount = ['-v', f'{ROOT}:/workspace', '-w', '/workspace']

        def docker(image, *command, ros_env=False):
            env = ['-e', 'RMW_IMPLEMENTATION=rmw_fastrtps_cpp'] if ros_env else []
            return ['docker', 'run', '--rm', '--pull=never', '--platform', 'linux/amd64',
                    '--network', 'none', *env, *mount, image, *command]

        logged('development-packages', docker(dev_run_ref, 'dpkg-query', '-W'))
        logged('ros-packages', docker(ros_ref, 'dpkg-query', '-W'))
        logged('build', docker(dev_run_ref, 'sh', 'tools/build_m0.sh'))
        inside_run = '/workspace/' + str(run.relative_to(ROOT))
        logged('transport-tests', docker(dev_run_ref, 'sh', 'tools/test_m0.sh', inside_run))
        logged('ros-build', docker(ros_ref, 'bash', '-c',
            'source /opt/ros/jazzy/setup.bash && '
            'cmake -S tests/ros_types -B build/ros-types -DCMAKE_BUILD_TYPE=Release && '
            'cmake --build build/ros-types --parallel 2', ros_env=True))
        # Keep stdout as parseable JSON. Any unexpected output or failure is a gate failure.
        probe_command = docker(ros_ref, 'bash', '-c',
            'source /opt/ros/jazzy/setup.bash && build/ros-types/ros_type_probe', ros_env=True)
        report['commands'].append({'log': 'ros-type-output.json', 'argv': probe_command})
        save()
        result = subprocess.run(probe_command, cwd=ROOT, capture_output=True, text=True)
        report['commands'][-1]['exit_code'] = result.returncode
        (run / 'ros-type-output.json').write_text(result.stdout)
        (run / 'ros-type-stderr.log').write_text(result.stderr)
        if result.returncode:
            raise RuntimeError('ROS type probe failed')
        report['ros_types'] = json.loads(result.stdout)
        libraries = list((ROOT / 'install/srt-m0').glob('lib*/**/librobotweax-srt.a'))
        if len(libraries) != 1:
            raise RuntimeError('Expected exactly one installed SRT archive')
        report['installed_library_sha256'] = hashlib.sha256(libraries[0].read_bytes()).hexdigest()
        report['status'] = 'passed'
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = str(error)
        raise
    finally:
        save()
        print('Evidence:', run, flush=True)


if __name__ == '__main__':
    main()
