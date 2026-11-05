#!/bin/sh
set -eu
cd /workspace
results=${1:?usage: test_m0.sh RESULT_DIRECTORY}
mkdir -p "$results"
ctest --test-dir build/srt-m0 --show-only=json-v1 > "$results/upstream-inventory.json"
python3 - "$results/upstream-inventory.json" <<'PY'
import json, sys
inventory = json.load(open(sys.argv[1]))['tests']
selected = [t for t in inventory if any(p['name'] == 'LABELS' and 'profile' in p['value'] for p in t['properties'])]
if len(selected) != 4:
    raise SystemExit(f'Expected four pinned upstream profile partitions, found {len(selected)}')
print('Upstream profile inventory:', ', '.join(t['name'] for t in selected))
PY
ctest --test-dir build/srt-m0 -L profile --no-tests=error --output-on-failure --test-output-size-passed 1048576 \
  --output-junit "$results/upstream-profile.xml"
ctest --test-dir build/srt-m0 -R '^robotweax_srt_session_auth_admission_tests$' \
  --no-tests=error --output-on-failure --test-output-size-passed 1048576 --output-junit "$results/upstream-admission.xml"
timeout 60s build/srt-m0/robotweax_srt_tests --include session_authentication > "$results/session-auth-native.log" 2>&1
cat "$results/session-auth-native.log"
python3 - "$results/session-auth-native.log" <<'PY_CHECK'
import sys
text = open(sys.argv[1]).read()
if '15/15 tests passed' not in text or '[SKIP]' in text:
    raise SystemExit('Pinned SESSIONAUTH subset must execute all 15 cases without skips')
PY_CHECK
ctest --test-dir build/m0 --show-only=json-v1 > "$results/probe-inventory.json"
ctest --test-dir build/m0 -L m0 --no-tests=error --output-on-failure --test-output-size-passed 1048576 \
  --output-junit "$results/profile-probe.xml"
python3 - "$results" <<'PY_CHECK'
from pathlib import Path
import sys
import re
import xml.etree.ElementTree as ET
root = Path(sys.argv[1])
for filename, count in [('upstream-profile.xml', 4), ('upstream-admission.xml', 1), ('profile-probe.xml', 40)]:
    suite = ET.parse(root / filename).getroot()
    cases = suite.findall('testcase')
    if len(cases) != count or any(t.find('failure') is not None or t.find('skipped') is not None for t in cases):
        raise SystemExit(f'Invalid qualification result: {filename}')
    if filename.startswith('upstream-'):
        for case in cases:
            summary = re.search(r'(\d+)/(\d+) tests passed', case.findtext('system-out') or '')
            if not summary or summary[1] != summary[2] or int(summary[1]) == 0:
                raise SystemExit(f'Incomplete native output: {filename}')
    if '[SKIP]' in (root / filename).read_text():
        raise SystemExit(f'Native case skipped inside partition: {filename}')
PY_CHECK
