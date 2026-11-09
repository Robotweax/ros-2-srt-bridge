"""Default-off, bounded passive source ARP lifecycle diagnostic integration."""
import json,subprocess,time
from m3_source_preflight import ROOT,sha
from m3_arp_packet_trace import BINARY
from m3_arp_packet_analysis import last_json,lifecycles,reply_header
from m3_monotonic_capture import records


def prepare():
    if not (ROOT/BINARY).is_file():raise ValueError('build the separate ARP tracer before live capture')
    return dict(binary_sha256=sha(ROOT/BINARY),source_sha256=sha(ROOT/'tools/arp_packet_trace/main.cpp'),extra_capability='PERFMON on owned endpoints; BPF already enabled',format_version=1,readiness_version=2,limit_seconds=600,ring_bytes=4194304,max_pending=4096,max_events=1000000,scope='passive source TX lifecycle, no verdict or tuning; exact owned Ethernet+ARP reply/netns/interface')


def start(lab,run,inside,macs,processes):
    for role,name in lab.containers.items():
        peer='robot' if role=='operator' else 'operator';lab.inside(role,role+'-arp-trace-btf',[BINARY,'--inspect'])
        log=(run/(role+'-arp-trace.log')).open('w');argv=['docker','exec',name,BINARY,'eth0',lab.addresses[role],lab.addresses[peer],macs[role],macs[peer],inside+'/'+role+'-arp-trace.jsonl',inside+'/'+role+'-arp-trace-ready.json','600']
        processes.append((role,subprocess.Popen(argv,stdout=log,stderr=subprocess.STDOUT),log))
    end=time.monotonic()+10
    while not all((run/(r+'-arp-trace-ready.json')).exists() for r in lab.containers):
        if any(p.poll() is not None for _,p,_ in processes) or time.monotonic()>end:raise ValueError('ARP trace readiness failed')
        time.sleep(.01)


def stop(lab,processes):
    errors=[]
    for role,_,_ in processes:
        try:lab.inside(role,role+'-arp-trace-stop',['python3','-c','import pathlib,os,signal\nfor p in pathlib.Path("/proc").glob("[0-9]*/comm"):\n try:\n  if p.read_text().strip()=="m3_arp_trace":os.kill(int(p.parent.name),signal.SIGTERM)\n except (FileNotFoundError,ProcessLookupError):pass\n'])
        except Exception as e:errors.append(str(e))
    for role,p,log in processes:
        try:
            if p.wait(timeout=5):errors.append(role+' trace failed')
        except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5);errors.append(role+' trace forced termination')
        finally:log.close()
    if errors:raise ValueError('; '.join(errors))


def summarize(run,addresses,macs):
    result={}
    for role in ('operator','robot'):
        peer='robot' if role=='operator' else 'operator';status=last_json(run/(role+'-arp-trace.log'));ready=json.loads((run/(role+'-arp-trace-ready.json')).read_text());events=[json.loads(line) for line in (run/(role+'-arp-trace.jsonl')).read_text().splitlines()]
        reasons=json.loads((run/(role+'-arp-trace-btf.log')).read_text())['drop_reasons'];rows=lifecycles(events,status,ready,reasons)
        # Canonical helper calls its reply source robot; remap roles explicitly.
        header=reply_header(dict(robot=addresses[role],operator=addresses[peer]),dict(robot=macs[role],operator=macs[peer]));counts={}
        for observer in (role,peer):
            s=last_json(run/(observer+'-monotonic-capture.log'))
            if not s.get('complete') or s.get('artifact_version')!=2 or not s.get('time_namespace_zero') or s.get('clock')!='kernel_monotonic' or not s['ready_ns']<=ready['ready_ns']<status['detach_before_ns']<=s['stop_before_ns']:raise ValueError('trace native coverage')
            selected=[]
            for raw in records(run/(observer+'.mono')):
                if raw['prefix'][:42]!=header or not ready['ready_ns']<=raw['monotonic_ns']<=status['detach_before_ns']:continue
                if raw['ifindex']!=s['ifindex'] or raw['packet_type']!=(4 if observer==role else 0) or raw['gso_size'] or raw['gso_segs'] not in (0,1) or raw['vlan_present']:raise ValueError('trace native framing/direction')
                selected.append(raw['monotonic_ns'])
            counts[observer]=len(selected)
        driver=sum(r['outcome']=='driver_start' for r in rows)
        if any(n!=driver for n in counts.values()):raise ValueError('trace driver/source/peer reply population mismatch')
        if any(r['ambiguities'] or r['outcome'] in ('other_free','consumed_before_driver') for r in rows):raise ValueError('trace lifecycle branch unavailable/ambiguous')
        result[role]=dict(complete=True,status=status,ready=ready,native_reply_counts=counts,counts={k:sum(r['outcome']==k for r in rows) for k in ('driver_start','qdisc_drop','other_free','consumed_before_driver')},lifetimes=rows,scope='Exact source lifecycle IDs; native peer count cross-check only, no individual peer mapping or physical wire proof')
    return result
