"""Read-only native bundle description for a separately authorized future freeze."""
import hashlib
from pathlib import Path
from task_assessment import COLLECTOR_SHA
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sources():
    files={name:HERE/name for name in ('observer_entry.py','observer-seccomp.json','observer-architecture.json','shutdown_observer.py','collector-binding.json')}
    files['m3_observer_filtering.py']=ROOT/'tools/m3_observer_filtering.py'
    if hashlib.sha256(files['shutdown_observer.py'].read_bytes()).hexdigest()!=COLLECTOR_SHA:raise ValueError('bundle collector differs')
    return files
def binding():
    return dict(schema_version=1,task_visibility=True,candidate_sha256={name:hashlib.sha256((HERE/name).read_bytes()).hexdigest() for name in ('task_assessment.py','lifecycle.py')},module_manifest_sha256=hashlib.sha256((HERE/'bindings.json').read_bytes()).hexdigest(),native_bundle={name:dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for name,path in sources().items()})
