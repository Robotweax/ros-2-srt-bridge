"""Private imports of exact reviewed candidate bytes; generic caches are untouched."""
import builtins
import hashlib
from pathlib import Path
import types
HERE=Path(__file__).resolve().parent
ORIGINAL=HERE.parent/'m3-task-metadata-assessment-2026-11-10'
def bound(name,assessment=None):
    path=HERE/(name+'.py');source=path.read_bytes()
    if hashlib.sha256(source).hexdigest()!=hashlib.sha256((ORIGINAL/path.name).read_bytes()).hexdigest():raise ValueError('assessment candidate differs: '+name)
    m=types.ModuleType('_robotweax_post_sigint_'+name);m.__file__=str(path)
    if assessment is not None:
        def imported(name,*args,**kwargs):
            if name=='task_assessment':return assessment
            return builtins.__import__(name,*args,**kwargs)
        m.__dict__['__builtins__']=dict(vars(builtins),__import__=imported)
    exec(compile(source,str(path),'exec'),m.__dict__);return m
metadata=bound('task_assessment');lifecycle=bound('lifecycle',metadata)
