"""Explicit fixed install layouts; never replaces or rebuilds an installed baseline."""
import json
from pathlib import Path
from m3_source_preflight import sha
from m3_n5_progress import RUNTIMES

LAYOUTS={
    'baseline':dict(ros='install/m3-ros',sdk='install/bridge-m3'),
    'start-trace':dict(ros='install/m3-start-trace-ros',sdk='install/bridge-start-trace-qualified'),
    'sender-visibility':dict(ros='install/m3-sender-visibility-ros',sdk='install/bridge-sender-visibility'),
    'probe-tracing':dict(ros='install/m3-probe-tracing-ros',sdk='install/bridge-probe-tracing'),
}
CALIBRATION='evidence/m3-start-tracing-2026-11-09/binary-verification.json'
SENDER_CALIBRATION='evidence/m3-sender-visibility-2026-11-09/binary-verification.json'
PROBE_CALIBRATION='evidence/m3-probe-tracing-2026-11-09/binary-verification.json'


def paths(name):
    if name not in LAYOUTS:raise ValueError('unknown runtime layout')
    c=LAYOUTS[name]
    return [p.replace('install/m3-ros/',c['ros']+'/',1).replace('install/bridge-m3/',c['sdk']+'/',1) for p in RUNTIMES]


def matched(root,name):
    root=Path(root);runtime_paths=paths(name);c=dict(LAYOUTS[name]);c['name']=name;c['runtime_paths']=runtime_paths
    if name!='baseline':
        calibration=PROBE_CALIBRATION if name=='probe-tracing' else SENDER_CALIBRATION if name=='sender-visibility' else CALIBRATION
        manifest=root/calibration;data=json.loads(manifest.read_text());expected=data['new_matched_build_binaries']
        required=set(c['runtime_paths'][:-1])|{str(p.relative_to(root)) for p in (root/c['sdk']/'lib').glob('lib*.a')}
        if not expected or not required<=set(expected):raise ValueError('incomplete matched runtime manifest')
        for p,h in expected.items():
            if sha(root/p)!=h:raise ValueError('matched runtime changed: '+p)
        if not (root/c['ros']/'setup.bash').is_file():raise ValueError('matched ROS setup missing')
        baseline=data['installed_baseline']
        if not set(RUNTIMES)<=set(baseline):raise ValueError('incomplete preserved baseline manifest')
        for p,h in baseline.items():
            if sha(root/p)!=h:raise ValueError('preserved installed baseline changed: '+p)
        if name in ('sender-visibility','probe-tracing'):
            previous=matched(root,'start-trace')['matched_build_sha256']
            if data.get('preserved_start_trace')!=previous:raise ValueError('preserved start-trace manifest mismatch')
            c['preserved_start_trace_sha256']=previous
        if name=='probe-tracing':
            previous=matched(root,'sender-visibility')['matched_build_sha256']
            if data.get('preserved_sender_visibility')!=previous:raise ValueError('preserved sender-visibility manifest mismatch')
            c['preserved_sender_visibility_sha256']=previous
        c.update(calibration=calibration,calibration_sha256=sha(manifest),matched_build_sha256=dict(expected),preserved_baseline_sha256=dict(baseline))
    return c
