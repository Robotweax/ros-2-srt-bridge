"""Read-only audit of closed, completed study journals; no reopening through bridge API."""
import hashlib
import json
from pathlib import Path
import sqlite3


def audit(run):
    run=Path(run);manifest=json.loads((run/'run.json').read_text());expected=manifest['command_summary']['attempts'];sides={}
    for role,side in [('robot',2),('operator',1)]:
        path=run/(role+'.sqlite')
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
            db.execute('PRAGMA query_only=ON')
            assert db.execute('PRAGMA quick_check').fetchall()==[('ok',)]
            assert db.execute('PRAGMA application_id').fetchone()[0]==0x52574a31
            assert db.execute('PRAGMA user_version').fetchone()[0]==1
            identity=db.execute('SELECT local,remote,side FROM identity').fetchall();assert len(identity)==1 and identity[0][2]==side
            entries={}
            for id,route,state,blob in db.execute('SELECT id,route,state,record FROM entries ORDER BY id'):
                integer=lambda at,n:int.from_bytes(blob[at:at+n],'big')
                assert len(blob)==512 and blob[:4]==b'RWJ1' and integer(4,2)==1 and state==10+blob[6] and route==integer(8,4)
                entries[id.hex()]=dict(route=route,state=blob[6],reason=blob[7],hash=blob[72:104].hex(),rate=integer(104,4),expected_generation=integer(112,8),generation=integer(120,8),revision=integer(176,8),result_valid=bool(blob[164]),result_rate=integer(160,4),result_generation=integer(168,8),dispatched_ns=integer(136,8))
        assert before==hashlib.sha256(path.read_bytes()).hexdigest()
        sides[role]=dict(quick_check='ok',identity=identity[0],sha256=before,entries=entries)
    robot=sides['robot']['entries'];operator=sides['operator']['entries'];assert set(robot)==set(operator)
    common=('route','state','reason','hash','rate','expected_generation','generation','revision','result_valid','result_rate','result_generation')
    assert all(all(robot[k][field]==operator[k][field] for field in common) for k in robot)
    all_succeeded=len(robot)==expected and all(e['state']==4 and e['reason']==0 and e['revision']==3 and e['result_valid'] and e['result_rate']==e['rate']==200 and e['result_generation']==e['generation'] and e['expected_generation']+1==e['generation'] for e in robot.values())
    if all_succeeded:
        assert sorted(e['result_generation'] for e in robot.values())==list(range(1,expected+1))
        assert all(e['dispatched_ns']>0 for e in robot.values())
    return dict(run=str(run),matching_entries=len(robot),expected_attempts=expected,all_succeeded_revision3=all_succeeded,sides=sides,scope='SQLite quick_check and common command/hash/result field audit of closed records; main database hashes unchanged; not additional crash/durability fault testing')


if __name__=='__main__':
    import sys
    print(json.dumps(audit(sys.argv[1]),indent=2))
