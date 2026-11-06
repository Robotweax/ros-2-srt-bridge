"""Offline development probe: match generated CDR fingerprints, not a general RTPS decoder."""
import collections,hashlib,json,struct,sys
from pathlib import Path
from rclpy.serialization import deserialize_message,serialize_message
from robotweax_srt_bridge_msgs.msg import DdsCommandFrame as Frame
sys.path.insert(0,'tools')
import m3_monotonic_capture as mono
from m3_dds_result_timeline import read_journal
run=Path(sys.argv[1]);report=json.loads((run/'run.json').read_text());peers={role:bytes(report['results']['final_command_'+side]['process_epoch']) for role,side in [('operator','sender'),('robot','receiver')]}
journals={role:read_journal(run/(role+'.sqlite'),side)['entries'] for role,side in [('operator',1),('robot',2)]}
rows=[];counts=collections.Counter()
for role in peers:
 native=collections.defaultdict(list)
 for r in mono.records(run/(role+'.mono')):native[(r['length'],r['prefix'])].append(r['monotonic_ns'])
 for p in sorted(run.glob(role+'.pcap*')):
  with p.open('rb') as file:
   h=file.read(24);assert h[:4]==b'\xd4\xc3\xb2\xa1' and struct.unpack_from('<I',h,20)[0]==1
   while rh:=file.read(16):
    sec,us,n,original=struct.unpack('<IIII',rh);b=file.read(n);assert n==original and len(b)==n
    if len(b)<42 or b[12:14]!=b'\x08\x00' or b[23]!=17:continue
    ip=b[14:];ihl=(ip[0]&15)*4
    if struct.unpack_from('!H',ip,6)[0]&0x3fff:counts['skipped_ip_fragments']+=1;continue
    udp=ip[ihl:];size=struct.unpack_from('!H',udp,4)[0];payload=udp[8:size]
    if not payload.startswith(b'RTPS'):continue
    for owner,epoch in peers.items():
     for kind in range(2,7):
      sample=Frame();sample.kind=kind;sample.process_epoch=list(epoch);prefix=serialize_message(sample)[:21]
      start=0
      while (at:=payload.find(prefix,start))>=0:
       start=at+len(prefix);counts['fingerprint_candidates']+=1
       try:message=deserialize_message(payload[at:],Frame);encoded=serialize_message(message)
       except Exception:counts['decode_rejected']+=1;continue
       if message.protocol_version!=2 or message.route_id!=100 or not any(message.request_id):counts['validation_rejected']+=1;continue
       id=bytes(message.request_id).hex();entry=journals[owner].get(id)
       if not entry or len(encoded)>len(payload)-at:raise ValueError('unmatched/truncated decoded candidate')
       if kind in (2,4,6) and bytes(message.payload_hash).hex()!=entry['payload_hash']:raise ValueError('payload hash mismatch')
       if kind==4:
        status=message.status
        if not status.found or bytes(status.request_id)!=bytes(message.request_id) or status.route_id!=100 or status.new_generation!=int.from_bytes(bytes.fromhex(id),'little'):raise ValueError('status identity/generation mismatch')
        if (status.state,status.revision) not in ((2,1),(3,2),(4,3)):raise ValueError('unexpected historical status')
       if kind==2 and (message.origin_monotonic_ns!=entry['source_ns'] or message.deadline_ns!=entry['deadline_ns']):raise ValueError('command context mismatch')
       stamps=native.get((len(b),b[:128]),[])
       rows.append(dict(capture_role=role,owner=owner,kind=kind,sequence=message.sequence,reply_to_sequence=message.reply_to_sequence,request_id=bytes(message.request_id).hex(),sent_monotonic_ns=message.sent_monotonic_ns,status_state=message.status.state,status_revision=message.status.revision,native_match_count=len(stamps),capture_monotonic_ns=stamps[0] if len(stamps)==1 else None,pcap_realtime_ns=sec*10**9+us*1000,serialized_sha256=hashlib.sha256(payload[at:at+len(encoded)]).hexdigest(),serialized_bytes=len(encoded),roundtrip_differences=[i for i,(x,y) in enumerate(zip(encoded,payload[at:at+len(encoded)])) if x!=y]))
       counts['decoded']+=1
out=dict(run=str(run),counts=counts,rows=rows,scope='validated generated CDR fingerprints in unfragmented captured RTPS UDP payloads; generated decoder plus command-journal identity/hash/context checks; roundtrip differing byte offsets retained (padding not assumed); no RTPS reassembly, middleware delivery/acceptance or physical delivery inferred; native timestamp only for unique full-length/128-byte-prefix match')
print(json.dumps(out,indent=2))
