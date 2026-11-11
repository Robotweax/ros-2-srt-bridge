"""Per-launch trace planning/catalogs; no process creation or native policy changes."""
from pathlib import Path
from launch_readiness import atomic


def plan_launch(launch,positive_ordinal):
    role=launch['role'];negative=launch['name']=='wrong-hash'
    if negative:
        if role!='robot':raise ValueError('unexpected negative launch')
        purpose='negative_type_hash'
    else:
        purposes={'operator':('measurement',),'robot':('warmup','measurement')}
        if not 1<=positive_ordinal<=len(purposes[role]):raise ValueError('unplanned bridge launch')
        purpose=purposes[role][positive_ordinal-1]
    stem=role+'-'+launch['name']+'-'+launch['token']
    prefix=Path('launch-readiness')
    return dict(context=launch,purpose=purpose,readiness_path=str(prefix/(stem+'.json')),identity_path=None if negative else str(prefix/(stem+'.identity.json')),trace_path=None if negative else str(prefix/(stem+'.shutdown.jsonl')),requires_trace=not negative,registration=None,attested=False,pid=None,returncode=None)


def save_launches(run,role,entries):
    rows=[dict(entry,returncode=child.returncode) for child,entry in entries.items()]
    atomic(Path(run)/(role+'-bridge-launches.json'),dict(schema_version=1,role=role,launches=rows))
