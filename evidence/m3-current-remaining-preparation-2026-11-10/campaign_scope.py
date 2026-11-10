"""Fresh exact-grant activation and per-case output/parameters; no resume/retry."""
import hashlib
import json
from pathlib import Path
from plan import authorize
from cases import cases
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
_active=None
def select(case_id):
    matches=[s for s in cases() if s['id']==case_id]
    if len(matches)!=1:raise ValueError('case not in exact remaining seven')
    return matches[0]
def activate(grant_path,freeze,case_id):
    global _active
    _active=None;slot=select(case_id);actual=json.loads((HERE/'freeze.json').read_text())
    if freeze!=actual or freeze['execution_enabled'] is not False or freeze['authorization_supplied'] is not False or freeze['cases']!=cases():raise ValueError('campaign freeze/context differs')
    authorize(json.loads(Path(grant_path).read_text()),hashlib.sha256((HERE/'freeze.json').read_bytes()).hexdigest())
    from integrity import verify_files
    verify_files(freeze);_active=(freeze,slot)
def guard(output,bundle,prefix,*,parameters=None):
    if _active is None:raise ValueError('remaining campaign inactive; no execution grant')
    freeze,slot=_active;expected=ROOT/freeze['output_relative']/slot['id']
    if Path(output).resolve()!=expected.resolve() or Path(bundle).resolve()!=(ROOT/freeze['bundle_relative']).resolve() or prefix!=freeze['prefix']+'-'+slot['id'].lower():raise ValueError('campaign case output/bundle/prefix differs')
    if parameters is not None and parameters!=(slot['profile'],slot['seed'],slot['source_seconds']):raise ValueError('campaign case parameters differ')
