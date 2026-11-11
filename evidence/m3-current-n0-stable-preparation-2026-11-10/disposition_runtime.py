"""Evidence-local matched build selection; preserves the entire old runtime chain."""
import json
from pathlib import Path
from m3_source_preflight import sha
from m3_runtime_layout import matched as old_matched
HERE=Path(__file__).resolve().parent

def matched(root,name):
    if name!='socket-disposition':raise ValueError('only socket-disposition layout allowed')
    root=Path(root);old=old_matched(root,'shutdown-tracing');data=json.loads((HERE/'binary-verification.json').read_text())
    if data['preserved_shutdown_trace']!=old:raise ValueError('preserved shutdown build drift')
    paths=[p.replace('install/m3-shutdown-trace-calibration-ros/','install/m3-socket-disposition-ros/').replace('install/bridge-shutdown-trace-calibration/','install/bridge-socket-disposition/') for p in old['runtime_paths']]
    files=data['new_matched_build_binaries'];required=set(paths[:-1])|{str(p.relative_to(root)) for p in (root/'install/bridge-socket-disposition/lib').glob('lib*.a')}
    if not required<=set(files) or not files:raise ValueError('incomplete disposition build')
    if any(sha(root/p)!=h for p,h in files.items()):raise ValueError('disposition binary drift')
    if not (root/'install/m3-socket-disposition-ros/setup.bash').exists():raise ValueError('new ROS setup absent')
    return dict(name=name,sdk='install/bridge-socket-disposition',ros='install/m3-socket-disposition-ros',runtime_paths=paths,matched_build_sha256=files,preserved_shutdown_trace=old,calibration=str((HERE/'binary-verification.json').relative_to(root)),calibration_sha256=sha(HERE/'binary-verification.json'))
