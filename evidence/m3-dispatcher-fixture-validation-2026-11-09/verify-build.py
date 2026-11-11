"""Static build/link evidence audit only: never executes the peer or worker."""
import json
from pathlib import Path
import re
import struct
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from m3_n4_fixture import native_layout
from m3_source_preflight import sha,write

out=Path(__file__).resolve().parent
selected=native_layout(ROOT,'sender-reconcile')
build=ROOT/'build/m3-n4-sender-reconcile-peer'
cache=(build/'CMakeCache.txt').read_text()
assert 'RobotweaxBridge_DIR:PATH=/workspace/install/bridge-sender-reconcile/lib/cmake/RobotweaxBridge' in cache
assert 'RobotweaxSRT_DIR:PATH=/workspace/install/srt-m0/lib/cmake/RobotweaxSRT' in cache
commands=json.loads((build/'compile_commands.json').read_text())
assert len(commands)==1
compile_command=commands[0]['command']
assert 'N4_WORKER_EXECUTABLE=' in compile_command and '/workspace/install/bridge-sender-reconcile/bin/robotweax-journal-worker' in compile_command
assert '-Werror' in compile_command and '-std=gnu++20' in compile_command
linkmap=(build/'link.map').read_text()
archives=sorted(set(re.findall(r'^LOAD (/workspace/install/\S+\.a)$',linkmap,re.M)))
assert len(archives)==7
assert all(p.startswith('/workspace/install/bridge-sender-reconcile/lib/') or p=='/workspace/install/srt-m0/lib/librobotweax-srt.a' for p in archives)
assert '/workspace/install/bridge-sender-reconcile/lib/librobotweax_srt_bridge_endpoint.a(endpoint.cpp.o)' in linkmap
assert '/workspace/install/bridge-sender-reconcile/lib/librobotweax_srt_bridge_transport.a(transport.cpp.o)' in linkmap
assert '/workspace/install/srt-m0/lib/librobotweax-srt.a(srt_api.cpp.o)' in linkmap
binary=(build/'m3_n4_peer').read_bytes()
assert binary[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',binary,18)[0]==62
assert b'/workspace/install/bridge-sender-reconcile/bin/robotweax-journal-worker\x00' in binary
assert b'--worker-ipc-v3\x00' in binary
elf=(out/'validation/elf-inspection.log').read_text()
assert 'ELF64' in elf and 'Advanced Micro Devices X86-64' in elf
assert all(name in elf for name in ('libprotobuf.so','libcrypto.so.3'))
assert 'RPATH' not in elf and 'RUNPATH' not in elf
manifest=json.loads((ROOT/'evidence/m3-sender-reconciliation-2026-11-09/source-sha256.json').read_text())
native={p:h for p,h in manifest.items() if (p=='CMakeLists.txt' or p.startswith(('src/','ros2/','proto/','cmake/'))) and '/scripts/' not in p}
assert len(native)==86 and all(sha(ROOT/p)==h for p,h in native.items())
write(out/'fixture-binding.json',selected['binding'])
write(out/'link-proof.json',dict(status='passed',scope='compile/link/static-inspection only; no fixture/worker execution or dynamic-loader/runtime/IPC qualification',
    image_reference='ros2-srt-m3@sha256:379b2ed9b14c5d3166ba236e219a2068b88ff1f9bb52ee4451207369426eebab',
    peer=selected['peer'],worker=selected['worker'],fixture_bound_files=len(selected['binding']['files']),
    native_inputs_unchanged=86,matched_candidate_binary_entries=len(selected['layout']['matched_build_sha256']),
    ELF=dict(bits=64,little_endian=True,machine='x86_64',executed=False,needed=re.findall(r'Shared library: \[(.*?)\]',elf)),
    static_archives=archives,worker_cli_flag='--worker-ipc-v3',worker_frame_version=4,
    local_build_artifacts={str(p.relative_to(ROOT)):sha(p) for p in (build/'m3_n4_peer',build/'fixture-binding.json',build/'CMakeCache.txt',build/'compile_commands.json',build/'link.map')},
    preserved_build_log_sha256=sha(out/'validation/native-build.log'),preserved_ELF_log_sha256=sha(out/'validation/elf-inspection.log')))
print('Static fixture build/link proof passed; peer and worker were not executed.')
