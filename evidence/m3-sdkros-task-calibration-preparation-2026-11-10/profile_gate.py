"""Closed-file proof of the original frozen impairments; no commands executed."""
import json
from m3_network import PROFILES
from cases import cases

def profile_gate(out,slot):
    if slot not in cases():raise ValueError('profile scope differs')
    network=json.loads((out/'network.json').read_text());profile=PROFILES[slot['profile']]
    for role in ('operator','robot'):
        seed=slot['seed']+(role=='operator')
        for i,argv in enumerate(profile.commands(seed)):
            entries=[c for c in network['commands'] if c['label']=='profile-'+role+'-'+str(i)]
            if len(entries)!=1 or entries[0]['exit_code']!=0 or entries[0]['argv']!=['docker','exec',network['containers'][role],*argv]:raise ValueError('profile install differs')
        state=json.loads((out/('profile-'+role+'-readback.log')).read_text())
        roots=[q for q in state if q.get('root')]
        netem=[q for q in state if q['kind']=='netem']
        if len(roots)!=1 or len(netem)!=1:raise ValueError('profile topology differs')
        q=netem[0];o=q['options']
        if o['seed']!=seed or o['limit']!=profile.queue_packets or o.get('loss-random',{}).get('loss',0)!=profile.loss_percent/100 or o.get('delay',{}).get('delay',0)!=profile.delay_ms/1000 or o.get('delay',{}).get('jitter',0)!=profile.jitter_ms/1000:raise ValueError('profile kernel settings differ')
        if slot['profile']=='N5':
            if roots[0]['kind']!='tbf' or roots[0]['handle']!='1:' or roots[0]['options']['rate']!=64000 or roots[0]['options']['burst']!=4096 or q.get('parent')!='1:1' or q['handle']!='10:':raise ValueError('N5 original rate/root/child differs')
        elif roots[0]!=q or q['handle']!='1:':raise ValueError('netem original root differs')
    return dict(profile=slot['profile'],seed=slot['seed'],original_commands_and_kernel_settings_verified=True)
