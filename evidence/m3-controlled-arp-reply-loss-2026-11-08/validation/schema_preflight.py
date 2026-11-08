from pathlib import Path
import json,secrets,sys
sys.path.insert(0,'tools')
from m3_network import NetworkLab
from m3_source_preflight import ROOT,IMAGE
from m3_neighbor_diagnostics import configure
from m3_arp_reply_observer import selector,counters,PREF
out=ROOT/'.local/m3-arp-reply-build/schema-preflight';out.mkdir(exist_ok=False);key=out/'passphrase';key.touch(mode=0o600);key.write_text(secrets.token_urlsafe(32));lab=NetworkLab(ROOT,out,IMAGE);r=dict(status='running',no_probe_sent=True)
try:
 lab.start(key);lab.apply('N0',2903);n=configure(lab,'dynamic');r['neighbors']=n
 assert all(not a for a in n['before'].values())
 lab.inside('robot','arp-hook',['tc','qdisc','add','dev','eth0','clsact'])
 args=(lab.addresses['robot'],lab.addresses['operator'],n['peer_macs']['robot'],n['peer_macs']['operator'],'drop')
 lab.inside('robot','reply-selector',selector(*args));raw=json.loads(lab.inside('robot','reply-readback',['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF]));r['raw_rule']=raw;r['counters']=counters(raw,*args)
 lab.inside('robot','reply-remove',['tc','filter','del','dev','eth0','egress','protocol','arp','pref',PREF]);assert json.loads(lab.inside('robot','reply-restored',['tc','-j','-s','filter','show','dev','eth0','egress','pref',PREF]))==[];r['status']='passed'
except Exception as e:r.update(status='failed',error=str(e))
finally:
 lab.cleanup();key.unlink(missing_ok=True);(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
print(r['status'],r.get('error'));raise SystemExit(r['status']!='passed')
