from pathlib import Path
from collections import Counter,defaultdict
import json,struct,sys
sys.path.insert(0,'tools')
import m3_monotonic_capture as mono
run=Path('.local/m3/20261106T161648299549Z');result={}
for role in ('robot','operator'):
 native=[r for r in mono.records(run/(role+'.mono')) if len(r['prefix'])>=34 and r['prefix'][12:14]==b'\x08\x00' and r['prefix'][23]==17]
 counts=Counter()
 for p in run.glob(role+'.pcap*'):
  with p.open('rb') as f:
   h=f.read(24);assert h[:4]==b'\xd4\xc3\xb2\xa1'
   while rh:=f.read(16):
    _,_,n,length=struct.unpack('<IIII',rh);b=f.read(n);assert n==length and len(b)==n;counts[(length,b[:128])]+=1
 expected=Counter((r['length'],r['prefix']) for r in native);extra=counts-expected;assert not extra
 missing=expected-counts;unique=[r for r in native if (r['length'],r['prefix']) in missing and expected[(r['length'],r['prefix'])]==1]
 groups=[]
 for ns in sorted(r['monotonic_ns'] for r in unique):
  if not groups or ns-groups[-1]['last_ns']>1000000000:groups.append(dict(first_ns=ns,last_ns=ns,records=1))
  else:groups[-1]['last_ns']=ns;groups[-1]['records']+=1
 samples=[json.loads(line) for line in (run/(role+'-endpoint-samples.jsonl')).read_text().splitlines() if line];gaps=sorted([dict(previous_end_ns=a['end_ns'],next_begin_ns=b['begin_ns'],gap_ns=b['begin_ns']-a['end_ns']) for a,b in zip(samples,samples[1:])],key=lambda x:x['gap_ns'],reverse=True)[:5]
 result[role]=dict(native_udp_records=len(native),pcap_records=sum(counts.values()),missing_records=sum(missing.values()),uniquely_identified_missing=len(unique),ambiguous_missing=sum(missing.values())-len(unique),missing_clusters=groups,sampler_largest_gaps=gaps)
Path('.local/srt-n5-v2-dev/capture-gap.json').write_text(json.dumps(dict(run=str(run),roles=result,scope='native IPv4 UDP length/prefix multiset versus PCAP; missing timestamps only for unique keys; sampling-gap correlation is not a scheduler/storage/root-cause proof'),indent=2)+'\n');print(json.dumps(result,indent=2))
