"""Explicit two-second owned N5 child-netem loss burst; root/classifier retained."""
import json
from m3_control_fault import bracket


def command(loss,seed):return ['tc','qdisc','change','dev','eth0','parent','1:1','handle','10:','netem','limit','16','loss','random',str(loss)+'%','seed',str(seed)]


def readback(lab,role,label,seed,loss):
    rows=json.loads(lab.inside(role,label,['tc','-j','-s','qdisc','show','dev','eth0']))
    roots=[r for r in rows if r.get('root')];children=[r for r in rows if r.get('kind')=='netem' and r.get('handle')=='10:' and r.get('parent')=='1:1']
    if len(roots)!=1 or roots[0]['kind']!='tbf' or roots[0]['handle']!='1:' or roots[0]['options']['rate']!=64000 or len(children)!=1:raise ValueError('requires owned N5 hierarchy')
    child=children[0]
    if child['options']['limit']!=16 or child['options'].get('seed')!=seed or child['options'].get('loss-random',{}).get('loss',0)!=loss:raise ValueError('child loss readback mismatch')
    return dict(root_config={k:roots[0][k] for k in ('kind','handle','options')},child=child)


def start(lab,role,seed):
    if role not in lab.containers:raise ValueError('not an owned endpoint')
    actual=seed+(role=='operator');before=readback(lab,role,'root-burst-before',actual,0)
    installed=bracket(lab,role,'root-burst-install',command(100,actual))
    try:
        active=readback(lab,role,'root-burst-active',actual,1)
        if active['root_config']!=before['root_config']:raise ValueError('root configuration changed')
    except Exception:
        bracket(lab,role,'root-burst-abort-restore',command(0,actual));raise
    return dict(role=role,seed=actual,install=installed,before=before,active=active,restored=False,scope='known whole-endpoint child loss, not command-phase/N4 qualification; root/classifier identity retained')


def stop(lab,fault):
    role=fault['role']
    try:fault['final_active']=readback(lab,role,'root-burst-final-active',fault['seed'],1)
    finally:
        fault['remove']=bracket(lab,role,'root-burst-restore',command(0,fault['seed']))
        fault['after']=readback(lab,role,'root-burst-restored',fault['seed'],0)
        if fault['after']['root_config']!=fault['before']['root_config']:raise ValueError('restored root changed')
        fault['restored']=True;fault['guaranteed_active_ns']=[fault['install']['end_ns'],fault['remove']['begin_ns']]
    return fault
