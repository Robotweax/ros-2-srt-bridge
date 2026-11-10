"""Process-local scoped activation: no grant/freeze substitution or campaign scope."""
import hashlib
import json
from pathlib import Path
from plan import authorize
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
_active=None
def activate(grant_path,freeze):
    global _active
    _active=None
    actual=json.loads((HERE/'freeze.json').read_text())
    if freeze!=actual or freeze['execution_enabled'] is not False or freeze['authorization_supplied'] is not False:raise ValueError('calibration freeze/context differs')
    authorize(json.loads(Path(grant_path).read_text()),hashlib.sha256((HERE/'freeze.json').read_bytes()).hexdigest())
    from integrity import verify_files
    verify_files(freeze);_active=freeze

def guard(output,bundle,prefix):
    if _active is None:raise ValueError('SDKROS calibration inactive; no live authority')
    expected=ROOT/_active['output_relative']/'fixture'
    if Path(output).resolve()!=expected.resolve() or Path(bundle).resolve()!=(ROOT/_active['bundle_relative']).resolve() or prefix!=_active['prefix']+'-sdkros':raise ValueError('SDKROS calibration output/bundle/prefix differs')
