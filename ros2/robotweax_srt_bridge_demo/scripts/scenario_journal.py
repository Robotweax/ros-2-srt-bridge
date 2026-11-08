"""WAL-aware read-only fixture inspection; release SQLite resources immediately."""
from contextlib import closing
from pathlib import Path
import sqlite3
import shutil


def visible_entries(path):
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
        return [dict(id=identity.hex(),state=state-10) for identity,state in db.execute('SELECT id,state FROM entries').fetchall()]


def copied_entries(path,destination):
    """Caller must hold its sole owned writer stopped; inspect only a private copy."""
    path=Path(path);destination=Path(destination);destination.mkdir(mode=0o700)
    target=destination/path.name
    shutil.copyfile(path,target)
    wal=Path(str(path)+'-wal')
    if wal.exists():shutil.copyfile(wal,Path(str(target)+'-wal'))
    # SQLite may recover its WAL in this private copy. Never invoke the bridge's
    # application recovery API or change the original writer's journal files.
    with closing(sqlite3.connect(target)) as db:
        return [dict(id=identity.hex(),state=state-10) for identity,state in db.execute('SELECT id,state FROM entries').fetchall()]
