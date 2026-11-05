#!/usr/bin/env python3
"""Install, relocate, and consume the bridge without source/build-tree target exports."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--srt-prefix', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    original = destination / 'original-prefix'
    relocated = destination / 'relocated-prefix'
    commands = []

    def run(argv, cwd=ROOT):
        commands.append(argv)
        subprocess.run(argv, cwd=cwd, check=True)

    report = {'status': 'running', 'commands': commands}
    try:
        run(['cmake', '--install', str(args.build.resolve()), '--prefix', str(original)])
        original.rename(relocated)
        for file in relocated.rglob('*.cmake'):
            if str(ROOT) in file.read_text():
                raise RuntimeError(f'Installed CMake metadata retained a workspace path: {file.name}')
        build = destination / 'consumer-build'
        run(['cmake', '-S', str(ROOT / 'tests/installed'), '-B', str(build), '-G', 'Ninja',
             '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
             '-DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF', '-DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF',
             f'-DCMAKE_PREFIX_PATH={relocated};{args.srt_prefix.resolve()}',
             f'-DEXPECTED_PREFIX={relocated}'])
        run(['cmake', '--build', str(build), '--parallel', '2'])
        for command in json.loads((build / 'compile_commands.json').read_text()):
            if f'-I{ROOT}/src' in command['command'] or f'-I{ROOT}/build' in command['command']:
                raise RuntimeError('Consumer used a bridge source/build include directory')
        dependencies = subprocess.check_output(['ldd', str(build / 'installed_bridge_consumer')], text=True)
        print(dependencies, flush=True)
        if any(name in dependencies for name in ('/opt/ros/', 'librcl', 'librmw', 'libsrt.so')):
            raise RuntimeError('Installed consumer linked ROS or a second SRT provider')
        report['runtime_dependencies'] = dependencies
        negative = ['cmake', '-S', str(ROOT / 'tests/installed/missing-component'),
                    '-B', str(destination / 'missing-component-build'), '-G', 'Ninja',
                    '-DCMAKE_FIND_USE_PACKAGE_REGISTRY=OFF', '-DCMAKE_FIND_USE_SYSTEM_PACKAGE_REGISTRY=OFF',
                    f'-DCMAKE_PREFIX_PATH={relocated};{args.srt_prefix.resolve()}']
        commands.append(negative)
        rejected = subprocess.run(negative, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        print(rejected.stdout, flush=True)
        if rejected.returncode == 0 or 'RobotweaxBridge_FOUND' not in rejected.stdout:
            raise RuntimeError('Missing required package component was not rejected correctly')
        report['missing_component_rejected'] = True
        runtime = destination / 'runtime'
        runtime.mkdir()
        run([str(build / 'installed_bridge_consumer')], cwd=runtime)
        report['files_sha256'] = {str(p.relative_to(relocated)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in sorted(relocated.rglob('*')) if p.is_file()}
        report['status'] = 'passed'
    finally:
        args.manifest.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
