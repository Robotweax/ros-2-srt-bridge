"""Private exact-source campaign graph; never borrow generic cached helpers."""
import builtins
import hashlib
import json
from pathlib import Path
import types
HERE=Path(__file__).resolve().parent
PINNED={'shutdown_observer':'6deab3c5e83e48b7c33dbbb4613c361469d9b62aa1bea86db0c1a8012cfae72e','task_assessment':'409a8812042b496354e28e7b0d940c81d9624f833d3bb1fb49ecbbd850b7c6ae','lifecycle':'4fafc85e3d4d8626b5e85db88ac8c704e5ff3c226570232febb8268446cf2068'}
_cache={}
def load(name):
    manifest=json.loads((HERE/'bindings.json').read_text());files=manifest['modules']
    if name not in files or not name.isidentifier():raise ValueError('unregistered campaign module')
    path=HERE/(name+'.py');source=path.read_bytes();digest=hashlib.sha256(source).hexdigest()
    if digest!=files[name] or name in PINNED and digest!=PINNED[name]:raise ValueError('bound campaign source differs: '+name)
    if name in _cache:return _cache[name]
    def imported(target,*args,**kwargs):
        if target in files:return load(target)
        return builtins.__import__(target,*args,**kwargs)
    module=types.ModuleType('_robotweax_campaign_task_'+name);module.__file__=str(path);module.__dict__['__builtins__']=dict(vars(builtins),__import__=imported);_cache[name]=module
    try:exec(compile(source,str(path),'exec'),module.__dict__)
    except BaseException:_cache.pop(name,None);raise
    return module
