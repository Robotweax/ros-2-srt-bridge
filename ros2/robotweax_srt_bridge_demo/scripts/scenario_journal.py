"""WAL-aware read-only fixture inspection; release SQLite resources immediately."""
from contextlib import closing
from pathlib import Path
import sqlite3


def visible_entries(path):
    with closing(sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
        return [dict(id=identity.hex(),state=state-10) for identity,state in db.execute('SELECT id,state FROM entries').fetchall()]
