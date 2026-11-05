"""Atomic laboratory phase files; never a command or journal-result transport."""
import json


def write(path,value):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value,indent=2)+'\n')
    temporary.replace(path)


def read(path):
    # exists()+open() is a TOCTOU race on a shared container bind mount.
    # Missing means no new phase yet; malformed JSON still fails explicitly.
    try:return json.loads(path.read_text())
    except FileNotFoundError:return {}
