from pathlib import Path
import subprocess,json
root=Path.cwd();source=root/'src/robotweax_srt_bridge_core/src/transport/transport.cpp';fixed=source.read_bytes()
image=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64','ros2-srt-m3:20261105'],text=True))[0]['RepoDigests'][0]
argv=['docker','run','--rm','--pull=never','--platform','linux/amd64','--network','none','-v',str(root)+':/workspace','-w','/workspace',image,'bash','-c','cmake --build build/m3-sdk --target worker_transport_tests --parallel 3 && build/m3-sdk/tests/native/worker_transport_tests ipv4']
try:
 source.write_bytes(subprocess.check_output(['git','show','381dfa8:src/robotweax_srt_bridge_core/src/transport/transport.cpp']))
 with (root/'.local/command-trace-dev/pre-fix-regression.log').open('w') as log:r=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=90)
 text=(root/'.local/command-trace-dev/pre-fix-regression.log').read_text()
 assert r.returncode!=0 and 'command was discarded instead of waiting for clock' in text,text[-2000:]
 print('Expected old-runtime regression failure verified',flush=True)
finally:source.write_bytes(fixed)
