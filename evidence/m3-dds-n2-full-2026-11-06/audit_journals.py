"""Read-only closed-journal audit retaining uncertainty instead of equating it to failure/nonexecution."""
from pathlib import Path
import hashlib
import json
import sqlite3


def audit(run):
    run=Path(run);manifest=json.loads((run/'run.json').read_text());roles={}
    for role,side in (('operator',1),('robot',2)):
        p=run/(role+'.sqlite');before=hashlib.sha256(p.read_bytes()).hexdigest()
        with sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True) as db:
            db.execute('PRAGMA query_only=ON')
            assert db.execute('PRAGMA quick_check').fetchall()==[('ok',)]
            assert db.execute('PRAGMA application_id').fetchone()[0]==0x52574a31 and db.execute('PRAGMA user_version').fetchone()[0]==1
            identity=db.execute('SELECT local,remote,side FROM identity').fetchall();assert len(identity)==1 and identity[0][2]==side
            entries={}
            for id,route,state,b in db.execute('SELECT id,route,state,record FROM entries ORDER BY id'):
                get=lambda at,n:int.from_bytes(b[at:at+n],'big')
                assert len(b)==512 and b[:4]==b'RWJ1' and get(4,2)==1 and state==10+b[6] and route==get(8,4)
                entries[id.hex()]=dict(route=route,state=b[6],reason=b[7],hash=b[72:104].hex(),rate=get(104,4),expected_generation=get(112,8),new_generation=get(120,8),revision=get(176,8),result_valid=bool(b[164]),result_rate=get(160,4),result_generation=get(168,8),dispatched_ns=get(136,8))
        assert before==hashlib.sha256(p.read_bytes()).hexdigest();roles[role]=dict(quick_check='ok',sha256=before,identity=identity[0],entries=entries)
    sender=roles['operator']['entries'];receiver=roles['robot']['entries'];common=sender.keys()&receiver.keys();divergent=[]
    command_fields=('route','hash','rate','expected_generation','new_generation')
    status_fields=('state','reason','revision','result_valid','result_rate','result_generation')
    for id in common:
        assert all(sender[id][k]==receiver[id][k] for k in command_fields)
        if any(sender[id][k]!=receiver[id][k] for k in status_fields):divergent.append(id)
        if sender[id]['revision']>0 and receiver[id]['revision']>0 and sender[id]['state'] in (4,5,6,7) and receiver[id]['state'] in (4,5,6,7):assert id not in divergent
    succeeded=[e for e in receiver.values() if e['state']==4]
    for e in succeeded:assert e['revision']==3 and e['result_valid'] and e['result_generation']==e['new_generation'] and e['dispatched_ns']>0
    expired=[e for e in receiver.values() if e['state']==7]
    for e in expired:assert not e['result_valid']
    return dict(run=str(run),roles=roles,common_entries=len(common),sender_only=sorted(sender.keys()-receiver.keys()),receiver_only=sorted(receiver.keys()-sender.keys()),status_divergences=divergent,receiver_successes=len(succeeded),receiver_expiries=len(expired),receiver_expiries_without_dispatch=sum(e['dispatched_ns']==0 for e in expired),manifest_unresolved=manifest['command_summary']['unresolved'],
        scope='SQLite integrity/common immutable command fields and terminal agreement where both terminal; unknown/missing/divergent observations retained; no absence proof or new crash-fault qualification')
