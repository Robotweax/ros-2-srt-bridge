"""Read-only frozen input/build/index checks shared by driver and workload entry."""
import hashlib
import json
from pathlib import Path
from m3_source_preflight import source_inventory
from disposition_runtime import matched
from observer_bundle import binding
ROOT=Path(__file__).resolve().parents[2]
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def verify_files(freeze):
    if source_inventory()!=freeze['source_sha256'] or matched(ROOT,'socket-disposition')!=freeze['runtime_layout']:raise ValueError('source/matched build drift')
    if binding()!=freeze['task_assessment_binding']:raise ValueError('task assessment/bundle binding differs')
    for path,digest in {**freeze['inputs_sha256'],**freeze['reused_native_inputs_sha256']}.items():
        if sha(ROOT/path)!=digest:raise ValueError('frozen input drift: '+path)
    for path,digest in freeze['retained_indexes'].items():
        if sha(ROOT/path)!=digest:raise ValueError('retained index drift: '+path)
        for name,item in json.loads((ROOT/path).read_text()).items():
            if sha(ROOT/name)!=item['sha256']:raise ValueError('retained artifact drift: '+name)
