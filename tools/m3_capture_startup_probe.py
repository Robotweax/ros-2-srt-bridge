#!/usr/bin/env python3
"""Known finite packets across libpcap filter change and pre-bind BPF recorder."""
import argparse
from collections import Counter
import ctypes as C
import json
from pathlib import Path
import select
import secrets
import socket
import struct
import subprocess
import time
from m3_packet_capture import library,Program,validate_status
from m3_network import NetworkLab
from m3_neighbor_diagnostics import configure
from m3_monotonic_capture import start,records,feature_snapshot
from m3_capture import stop_captures

ROOT=Path(__file__).resolve().parents[1]
POSITIVE=39781
NEGATIVE=39782
MAGIC=b'CAPSTART'
FINAL='udp port 39781'
BROAD='udp and (port 39781 or port 39782)'


def write(p,value):
    path=Path(p);temp=path.with_name(path.name+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)


def identity(frame):
    if len(frame)<58 or frame[12:14]!=b'\x08\x00' or frame[14]!=0x45 or frame[23]!=17:return None
    payload=frame[42:]
    if payload[:8]!=MAGIC:return None
    return struct.unpack_from('!II',payload,8)


def pcaps(path):
    result=[];count=0
    with path.open('rb') as f:
        h=f.read(24)
        if len(h)!=24 or h[:4]!=b'\xd4\xc3\xb2\xa1':raise ValueError('unsupported probe PCAP')
        while True:
            row=f.read(16)
            if not row:break
            if len(row)!=16:raise ValueError('short PCAP record')
            _,_,n,original=struct.unpack('<IIII',row);data=f.read(n)
            if len(data)!=n or n!=original:raise ValueError('truncated PCAP')
            count+=1;result.append(identity(data))
    return count,Counter(x for x in result if x is not None)


def receive(a):
    sockets=[socket.socket(socket.AF_INET,socket.SOCK_DGRAM) for _ in range(2)];rows=[]
    try:
        for sock,port in zip(sockets,(POSITIVE,NEGATIVE)):sock.bind(('0.0.0.0',port))
        Path(a.ready).touch();deadline=time.monotonic()+45
        while not Path(a.stop).exists():
            if time.monotonic()>deadline:raise RuntimeError('probe receiver timeout')
            for sock in select.select(sockets,[],[],.05)[0]:
                data,_=sock.recvfrom(4096)
                if data[:8]!=MAGIC:raise ValueError('unexpected probe data')
                case,index=struct.unpack_from('!II',data,8);rows.append((case,index));write(a.out,rows)
    finally:
        for sock in sockets:sock.close()
        write(a.out,rows)


def send(a):
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        for i in range(a.count):
            payload=MAGIC+struct.pack('!II',a.case,i)+bytes(64)
            if sock.sendto(payload,(a.peer,a.port))!=len(payload):raise ValueError('short probe send')
            time.sleep(.01)


class Stats(C.Structure):
    _fields_=[('received',C.c_uint),('dropped',C.c_uint),('ifdrop',C.c_uint)]


class Header(C.Structure):
    _fields_=[('sec',C.c_long),('usec',C.c_long),('caplen',C.c_uint),('length',C.c_uint)]


def libpcap_recorder(a):
    p=library();p.pcap_create.argtypes=[C.c_char_p,C.c_char_p];p.pcap_create.restype=C.c_void_p
    p.pcap_activate.argtypes=[C.c_void_p];p.pcap_activate.restype=C.c_int
    for name in ('pcap_set_snaplen','pcap_set_buffer_size','pcap_set_immediate_mode','pcap_set_timeout'):
        getattr(p,name).argtypes=[C.c_void_p,C.c_int];getattr(p,name).restype=C.c_int
    p.pcap_setfilter.argtypes=[C.c_void_p,C.POINTER(Program)];p.pcap_setfilter.restype=C.c_int
    p.pcap_stats.argtypes=[C.c_void_p,C.POINTER(Stats)];p.pcap_stats.restype=C.c_int
    p.pcap_setnonblock.argtypes=[C.c_void_p,C.c_int,C.c_char_p];p.pcap_setnonblock.restype=C.c_int
    p.pcap_dump_open.argtypes=[C.c_void_p,C.c_char_p];p.pcap_dump_open.restype=C.c_void_p
    p.pcap_dump.argtypes=[C.c_void_p,C.POINTER(Header),C.POINTER(C.c_ubyte)]
    p.pcap_dump_flush.argtypes=[C.c_void_p];p.pcap_dump_flush.restype=C.c_int
    p.pcap_dump_close.argtypes=[C.c_void_p]
    callback_type=C.CFUNCTYPE(None,C.c_void_p,C.POINTER(Header),C.POINTER(C.c_ubyte))
    p.pcap_dispatch.argtypes=[C.c_void_p,C.c_int,callback_type,C.c_void_p];p.pcap_dispatch.restype=C.c_int
    error=C.create_string_buffer(256);handle=p.pcap_create(b'eth0',error);dump=None;report=dict(status='running',mode=a.case_name,stats=[],records=0,known_ids=[],libpcap_version=p.pcap_lib_version().decode())
    if not handle:raise RuntimeError(error.value.decode())
    def check(rc):
        if rc<0:raise RuntimeError(p.pcap_geterr(handle).decode())
    def apply(expression):
        code=Program();check(p.pcap_compile(handle,C.byref(code),expression.encode(),1,0xffffffff))
        try:check(p.pcap_setfilter(handle,C.byref(code)))
        finally:p.pcap_freecode(C.byref(code))
    def stats(label):
        value=Stats();check(p.pcap_stats(handle,C.byref(value)))
        row=dict(label=label,received=value.received,dropped=value.dropped,ifdrop=value.ifdrop,records=report['records'],vm_ns=time.monotonic_ns());report['stats'].append(row);return row
    try:
        for name,n in (('pcap_set_snaplen',65535),('pcap_set_buffer_size',32<<20),('pcap_set_immediate_mode',1),('pcap_set_timeout',100)):check(getattr(p,name)(handle,n))
        check(p.pcap_activate(handle));apply(BROAD if a.case_name=='carry' else FINAL);check(p.pcap_setnonblock(handle,1,error))
        initial=stats('initial')
        if initial['received'] or initial['dropped']:raise ValueError('probe startup already contaminated')
        dump=p.pcap_dump_open(handle,str(a.out).encode())
        if not dump:raise RuntimeError('pcap dump open')
        Path(a.ready).touch();deadline=time.monotonic()+15
        while not Path(a.change).exists():
            if time.monotonic()>deadline:raise RuntimeError('filter-change barrier timeout')
            time.sleep(.01)
        before=stats('before_final_filter')
        expected=2 if a.case_name=='carry' else 0
        if before['received']!=expected or before['dropped']:raise ValueError('negative population not controlled')
        apply(FINAL);stats('after_final_filter');Path(a.final).touch()
        errors=[]
        @callback_type
        def callback(user,h,packet):
            try:
                frame=C.string_at(packet,h.contents.caplen)
                p.pcap_dump(dump,h,packet);report['records']+=1;report['known_ids'].append(identity(frame))
            except Exception as e:errors.append(str(e))
        previous=None;deadline=time.monotonic()+20
        while True:
            check(p.pcap_dispatch(handle,64,callback,None))
            if errors:raise ValueError(errors[0])
            if Path(a.stop).exists():
                row=stats('drain');current=(row['received'],row['dropped'],row['records'])
                if current==previous:break
                previous=current;time.sleep(.2)
            else:time.sleep(.01)
            if time.monotonic()>deadline:raise RuntimeError('libpcap probe deadline')
        check(p.pcap_dump_flush(dump));report['status']='passed'
    except Exception as e:report.update(status='failed',error=str(e));raise
    finally:
        if dump:p.pcap_dump_close(dump)
        p.pcap_close(handle);write(a.status,report)


def wait(predicate,peers,seconds=10):
    deadline=time.monotonic()+seconds
    while not predicate():
        if any(p.poll() is not None for p,log in peers) or time.monotonic()>deadline:raise RuntimeError('startup probe phase failed')
        time.sleep(.02)


def run_case(run,image,mode):
    run.mkdir();inside='/workspace/'+str(run.relative_to(ROOT));lab=NetworkLab(ROOT,run,image,monotonic_capture=True)
    peers=[];captures=[];key=run/'passphrase';key.touch(mode=0o600);key.write_text(secrets.token_urlsafe(32));result=dict(status='running',mode=mode,qualification=False)
    try:
        lab.start(key);configure(lab,'permanent');lab.apply('N0',1701);result['features_before']=feature_snapshot(lab,'features-before')
        start(run,inside,lab,captures)
        def launch(role,label,argv):
            log=(run/(label+'.log')).open('w');item=(subprocess.Popen(['docker','exec',lab.containers[role]]+argv,stdout=log,stderr=subprocess.STDOUT),log);peers.append(item);return item[0]
        receiver=launch('robot','receiver',['python3','tools/m3_capture_startup_probe.py','receive','--out',inside+'/received.json','--ready',inside+'/receiver-ready','--stop',inside+'/receiver-stop'])
        wait(lambda:(run/'receiver-ready').exists(),peers)
        if mode=='prebind':
            recorder=launch('robot','recorder',['python3','tools/m3_packet_capture.py','--output',inside+'/capture.pcap','--ready',inside+'/ready','--stop',inside+'/stop','--status',inside+'/recorder-status.json','--filter',FINAL])
        else:
            recorder=launch('robot','recorder',['python3','tools/m3_capture_startup_probe.py','libpcap','--case-name',mode,'--out',inside+'/capture.pcap','--ready',inside+'/ready','--change',inside+'/change','--final',inside+'/final','--stop',inside+'/stop','--status',inside+'/recorder-status.json'])
        wait(lambda:(run/'ready').exists(),peers)
        for case,count,port in ((1,2,NEGATIVE),(2,16,POSITIVE)):
            lab.inside('operator','send-'+str(case),['python3','tools/m3_capture_startup_probe.py','send','--peer',lab.addresses['robot'],'--port',str(port),'--case',str(case),'--count',str(count)])
            wait(lambda:(run/'received.json').exists() and len(json.loads((run/'received.json').read_text()))==(2 if case==1 else 18),peers)
            if case==1 and mode!='prebind':
                (run/'change').touch();wait(lambda:(run/'final').exists(),peers)
        (run/'stop').touch()
        if recorder.wait(timeout=8)!=0:raise ValueError('probe recorder failed')
        (run/'receiver-stop').touch()
        if receiver.wait(timeout=5)!=0:raise ValueError('probe receiver failed')
        stop_captures(lab)
        for p,log in captures:
            if p.wait(timeout=5)!=0:raise ValueError('native capture failed')
            log.close()
        report=json.loads((run/'recorder-status.json').read_text());n,ids=pcaps(run/'capture.pcap');expected=Counter((2,i) for i in range(16))
        if n!=16 or ids!=expected:raise ValueError('positive/negative PCAP identities differ')
        if mode=='prebind':result['counter_validation']=validate_status(report,n)
        else:
            final=report['stats'][-1];received=18 if mode=='carry' else 16
            if report['records']!=16 or final['received']!=received or final['dropped'] or Counter(tuple(x) for x in report['known_ids'])!=expected:raise ValueError('libpcap counter transition result differs')
        result['native']={}
        for role in lab.containers:
            status=json.loads((run/(role+'-monotonic-capture.log')).read_text().splitlines()[-1]);rows=list(records(run/(role+'.mono')))
            if not status['complete'] or not status['records']==status['seen']==status['submitted']==len(rows) or status['reserve_failed'] or status['copy_failed']:raise ValueError('native population incomplete')
            found=Counter(identity(r['prefix']) for r in rows if identity(r['prefix']) is not None)
            if found!=expected+Counter((1,i) for i in range(2)):raise ValueError('native finite populations differ')
            result['native'][role]=status
        if Counter(tuple(x) for x in json.loads((run/'received.json').read_text()))!=expected+Counter((1,i) for i in range(2)):raise ValueError('receiver population differs')
        result['features_after']=feature_snapshot(lab,'features-after')
        if result['features_before']!=result['features_after']:raise ValueError('features changed')
        result.update(status='passed',record_count=n,recorder=report,known_negative_packets=2,known_positive_packets=16,
                      capture_population_accepted=mode!='carry',interpretation='controlled broad-to-narrow transition carries two prior accepted packets into stats but not callbacks; known negative capture gate' if mode=='carry' else 'final-filter population16, file/dispatch/kernel16, negative identities excluded')
    except Exception as e:result.update(status='failed',error=str(e));raise
    finally:
        (run/'stop').touch();(run/'receiver-stop').touch()
        for p,log in peers:
            if p.poll() is None:p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
            log.close()
        if any(p.poll() is None for p,log in captures):
            try:stop_captures(lab)
            except Exception:pass
        for p,log in captures:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.terminate();p.wait(timeout=5)
            if not log.closed:log.close()
        lab.cleanup();key.unlink(missing_ok=True);write(run/'result.json',result)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    r=sub.add_parser('receive')
    for key in ('out','ready','stop'):r.add_argument('--'+key,required=True)
    s=sub.add_parser('send');s.add_argument('--peer',required=True)
    for key in ('case','count','port'):s.add_argument('--'+key,type=int,required=True)
    r=sub.add_parser('libpcap')
    for key in ('case-name','out','ready','change','final','stop','status'):r.add_argument('--'+key,required=True)
    r=sub.add_parser('run');r.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.mode=='receive':receive(a)
    elif a.mode=='send':send(a)
    elif a.mode=='libpcap':libpcap_recorder(a)
    else:
        run=a.out.resolve();run.mkdir(parents=True,exist_ok=False);image=json.loads(subprocess.check_output(['docker','image','inspect','--platform','linux/amd64','ros2-srt-m3:20261105'],text=True))[0]['RepoDigests'][0];report=dict(status='running',image=image,cases=[])
        try:
            for mode in ('carry','early','prebind'):report['cases'].append(run_case(run/mode,image,mode))
            report['status']='passed'
        except Exception as e:report.update(status='failed',error=str(e));raise
        finally:write(run/'result.json',report)
