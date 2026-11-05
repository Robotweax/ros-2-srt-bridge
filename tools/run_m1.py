#!/usr/bin/env python3
"""Run current core contracts in the qualified Linux image; retain every attempt."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native', action='store_true', help='also run full root/installed-SRT tests after M0')
    args = parser.parse_args()
    baseline = json.loads((ROOT / 'baselines/dependencies.json').read_text())
    image = baseline['environment']['development_image_reference']
    run = ROOT / '.local/m1' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True)
    sources = sorted(set(ROOT.glob('src/**/*.cpp')) | set(ROOT.glob('src/**/*.hpp')) |
                     set(ROOT.glob('tests/protocol/*')) | set(ROOT.glob('tests/native/*')) | set(ROOT.glob('proto/*')) |
                     set(ROOT.glob('src/**/CMakeLists.txt')) | set(ROOT.glob('cmake/**/*')) |
                     set(ROOT.glob('tests/installed/**/*')) | {ROOT / 'tools/run_m1.py', ROOT / 'tools/check_install.py', ROOT / 'CMakeLists.txt'})
    report = {'status': 'running', 'image_reference': image, 'commands': [],
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sources if p.is_file()}}

    def save():
        (run / 'run.json').write_text(json.dumps(report, indent=2) + '\n')

    def execute(name, command):
        report['commands'].append({'log': name + '.log', 'argv': command})
        save()
        print(name, flush=True)
        with (run / (name + '.log')).open('w') as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        report['commands'][-1]['exit_code'] = result.returncode
        save()
        if result.returncode:
            raise RuntimeError(f'{name} failed; see {run / (name + ".log")}')

    try:
        info = json.loads(subprocess.check_output(['docker', 'image', 'inspect', '--platform',
                          'linux/amd64', image], text=True))[0]
        if info['Os'] != 'linux' or info['Architecture'] != 'amd64':
            raise RuntimeError('M1 image must be Linux amd64')
        report['image_platform_id'] = info['Id']
        for mode in ('debug', 'asan-ubsan'):
            build = f'build/m1-{mode}'
            flags = ' -DCMAKE_CXX_FLAGS= -DCMAKE_EXE_LINKER_FLAGS=' if mode == 'debug' else (
                ' -DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer"'
                ' -DCMAKE_EXE_LINKER_FLAGS="-fsanitize=address,undefined"')
            inside = '/workspace/' + str(run.relative_to(ROOT))
            command = (f'cmake -S src/robotweax_srt_bridge_core -B {build} -G Ninja '
                       f'-DCMAKE_BUILD_TYPE=Debug -DBUILD_TESTING=ON -DBUILD_SHARED_LIBS=OFF '
                       f'-DBUILD_MANAGEMENT_CODEC=ON{flags} && '
                       f'cmake --build {build} --parallel 3 && '
                       f'ctest --test-dir {build} --show-only=json-v1 > {inside}/{mode}-inventory.json && '
                       f'ctest --test-dir {build} --no-tests=error --output-on-failure '
                       f'--test-output-size-passed 1048576 --output-junit {inside}/{mode}.xml')
            execute(mode, ['docker', 'run', '--rm', '--pull=never', '--platform', 'linux/amd64',
                    '--network', 'none', '-v', f'{ROOT}:/workspace', '-w', '/workspace', image,
                    'sh', '-c', command])
            inventory = json.loads((run / f'{mode}-inventory.json').read_text())
            expected = {'clock_contract', 'wire_contract', 'management_contract', 'routes_contract', 'session_contract', 'queues_contract', 'bandwidth_contract', 'reconnect_contract', 'command_contract', 'journal_contract', 'journal_crash_contract', 'journal_quota_contract', 'worker_contract', 'execution_contract', 'error_contract'}
            if {t['name'] for t in inventory['tests']} != expected:
                raise RuntimeError('M1 test inventory changed; review expected gates')
            cases = ET.parse(run / f'{mode}.xml').getroot().findall('testcase')
            if len(cases) != len(expected) or any(t.find('failure') is not None or
                    t.find('skipped') is not None or 'PASS ' not in (t.findtext('system-out') or '') for t in cases):
                raise RuntimeError('Incomplete M1 contract results')
        if args.native:
            archives = list((ROOT / 'install/srt-m0').glob('lib*/**/librobotweax-srt.a'))
            if len(archives) != 1 or hashlib.sha256(archives[0].read_bytes()).hexdigest() != baseline['srt']['installed_library_sha256']:
                raise RuntimeError('Native tests require the M0-qualified installed SRT archive')
            report['srt_archive_sha256'] = baseline['srt']['installed_library_sha256']
            build = 'build/m1-native'
            inside = '/workspace/' + str(run.relative_to(ROOT))
            command = (f'cmake -S . -B {build} -G Ninja -DCMAKE_BUILD_TYPE=Release '
                       '-DCMAKE_PREFIX_PATH=/workspace/install/srt-m0 -DBUILD_MANAGEMENT_CODEC=ON '
                       '-DBUILD_PROFILE_PROBE=ON -DBUILD_TESTING=ON -DBUILD_SHARED_LIBS=OFF '
                       '-DCMAKE_CXX_FLAGS= -DCMAKE_EXE_LINKER_FLAGS= && '
                       f'cmake --build {build} --parallel 3 && '
                       f'ctest --test-dir {build} --no-tests=error --output-on-failure '
                       f'--test-output-size-passed 1048576 --output-junit {inside}/native.xml')
            execute('native', ['docker', 'run', '--rm', '--pull=never', '--platform', 'linux/amd64',
                    '--network', 'none', '-v', f'{ROOT}:/workspace', '-w', '/workspace', image,
                    'sh', '-c', command])
            cases = ET.parse(run / 'native.xml').getroot().findall('testcase')
            if len(cases) != 67 or not {'session_sockets_ipv4', 'session_sockets_ipv6', 'transport_owner_ipv4', 'transport_owner_ipv6', 'worker_transport_ipv4', 'worker_transport_ipv6', 'command_endpoint_ipv4', 'command_endpoint_ipv6', 'execution_start_ipv4', 'execution_start_ipv6', 'wire_errors_ipv4', 'wire_errors_ipv6'} <= {c.attrib['name'] for c in cases} or any(
                    c.find('failure') is not None or c.find('skipped') is not None for c in cases):
                raise RuntimeError('Incomplete native regression results')
            install_command = (f'python3 tools/check_install.py --build {build} '
                               f'--destination {inside}/installed-smoke --srt-prefix install/srt-m0 '
                               f'--manifest {inside}/installed-manifest.json')
            execute('installed-consumer', ['docker', 'run', '--rm', '--pull=never', '--platform', 'linux/amd64',
                    '--network', 'none', '-v', f'{ROOT}:/workspace', '-w', '/workspace', image,
                    'sh', '-c', install_command])
            if json.loads((run / 'installed-manifest.json').read_text()).get('status') != 'passed':
                raise RuntimeError('Installed bridge consumer failed')
            build = 'build/m1-transport-sanitized'
            command = (f'cmake -S . -B {build} -G Ninja -DCMAKE_BUILD_TYPE=Debug '
                       '-DCMAKE_PREFIX_PATH=/workspace/install/srt-m0 -DBUILD_MANAGEMENT_CODEC=ON '
                       '-DBUILD_SRT_TRANSPORT=ON -DBUILD_PROFILE_PROBE=ON -DBUILD_TESTING=ON '
                       '-DBUILD_SHARED_LIBS=OFF '
                       '-DCMAKE_CXX_FLAGS="-fsanitize=address,undefined -fno-omit-frame-pointer" '
                       '-DCMAKE_EXE_LINKER_FLAGS="-fsanitize=address,undefined" && '
                       f'cmake --build {build} --target transport_tests worker_transport_tests endpoint_tests execution_start_tests error_transport_tests --parallel 3 && '
                       f'ctest --test-dir {build} -R "transport_owner|worker_transport|command_endpoint|execution_start|wire_errors" --no-tests=error --output-on-failure '
                       f'--test-output-size-passed 1048576 --output-junit {inside}/transport-sanitized.xml')
            execute('transport-sanitized', ['docker', 'run', '--rm', '--pull=never', '--platform', 'linux/amd64',
                    '--network', 'none', '-v', f'{ROOT}:/workspace', '-w', '/workspace', image,
                    'sh', '-c', command])
            cases = ET.parse(run / 'transport-sanitized.xml').getroot().findall('testcase')
            if {c.attrib['name'] for c in cases} != {'transport_owner_ipv4', 'transport_owner_ipv6', 'worker_transport_ipv4', 'worker_transport_ipv6', 'command_endpoint_ipv4', 'command_endpoint_ipv6', 'execution_start_ipv4', 'execution_start_ipv6', 'wire_errors_ipv4', 'wire_errors_ipv6'} or any(
                    c.find('failure') is not None or c.find('skipped') is not None or
                    'PASS ' not in (c.findtext('system-out') or '') for c in cases):
                raise RuntimeError('Incomplete sanitized transport results')
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
