"""Exact installed SDK binding for the new isolated peer; read-only, never builds."""
import json
from pathlib import Path
from m3_source_preflight import sha
from m3_n4_fixture import create_binding
from disposition_runtime import matched
PEER='build/m3-n4-socket-disposition-peer/m3_n4_peer'


def native_layout(root,name):
    if name!='socket-disposition':raise ValueError('only frozen current SDK permitted')
    root=Path(root);layout=matched(root,name);path=root/Path(PEER).parent/'fixture-binding.json'
    binding=json.loads(path.read_text())
    expected=create_binding(root,root/layout['sdk'],root/PEER,root/layout['sdk']/'bin/robotweax-journal-worker',root/'install/srt-m0/lib/librobotweax-srt.a')
    if binding!=expected:raise ValueError('stale or mismatched N4 fixture binding')
    return dict(layout=layout,peer=PEER,worker=binding['worker'],runtime_sha256=dict(binding['files']),binding=binding)
