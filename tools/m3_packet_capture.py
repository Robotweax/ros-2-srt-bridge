#!/usr/bin/env python3
"""Opt-in finite Linux/amd64 recorder: attach final BPF before protocol bind."""
import argparse
import ctypes as C
import ctypes.util
import hashlib
import json
from pathlib import Path
import select
import socket
import struct
import sys
import time

SOL_PACKET=263
PACKET_STATISTICS=6
SO_ATTACH_FILTER=26
SO_TIMESTAMPNS=35
MAX_BYTES=128<<20
MAX_RECORDS=75000


class Insn(C.Structure):
    _fields_=[('code',C.c_ushort),('jt',C.c_ubyte),('jf',C.c_ubyte),('k',C.c_uint32)]


class Program(C.Structure):
    _fields_=[('length',C.c_uint),('instructions',C.POINTER(Insn))]


class SockProgram(C.Structure):
    _fields_=[('length',C.c_ushort),('instructions',C.POINTER(Insn))]


def library():
    p=C.CDLL(ctypes.util.find_library('pcap') or 'libpcap.so.0.8')
    p.pcap_open_dead.argtypes=[C.c_int,C.c_int];p.pcap_open_dead.restype=C.c_void_p
    p.pcap_compile.argtypes=[C.c_void_p,C.POINTER(Program),C.c_char_p,C.c_int,C.c_uint32];p.pcap_compile.restype=C.c_int
    p.pcap_freecode.argtypes=[C.POINTER(Program)]
    p.pcap_close.argtypes=[C.c_void_p]
    p.pcap_geterr.argtypes=[C.c_void_p];p.pcap_geterr.restype=C.c_char_p
    p.pcap_lib_version.restype=C.c_char_p
    return p


def compile_filter(expression):
    p=library();dead=p.pcap_open_dead(1,65535)
    if not dead:raise RuntimeError('pcap_open_dead failed')
    program=Program()
    try:
        if p.pcap_compile(dead,C.byref(program),expression.encode(),1,0xffffffff):
            raise ValueError(p.pcap_geterr(dead).decode())
        if not 1<=program.length<=4096:raise ValueError('unbounded BPF program')
        instructions=[(x.code,x.jt,x.jf,x.k) for x in program.instructions[:program.length]]
        return instructions,p.pcap_lib_version().decode()
    finally:
        if program.instructions:p.pcap_freecode(C.byref(program))
        p.pcap_close(dead)


def attach(sock,instructions):
    array=(Insn*len(instructions))(*(Insn(*x) for x in instructions))
    program=SockProgram(len(instructions),array)
    libc=C.CDLL(None,use_errno=True)
    libc.setsockopt.argtypes=[C.c_int,C.c_int,C.c_int,C.c_void_p,C.c_uint];libc.setsockopt.restype=C.c_int
    if libc.setsockopt(sock.fileno(),socket.SOL_SOCKET,SO_ATTACH_FILTER,C.byref(program),C.sizeof(program)):
        raise OSError(C.get_errno(),'SO_ATTACH_FILTER failed')


def write(path,value):
    temp=path.with_name(path.name+'.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)


def validate_status(status,records):
    if status.get('backend')!='filtered_packet_socket' or status.get('complete') is not True or status.get('status')!='passed':
        raise ValueError('packet recorder did not complete')
    lifecycle=[status.get(k) for k in ('attach_begin_ns','attach_end_ns','bind_begin_ns','bind_end_ns','ready_ns','stop_before_ns')]
    if any(type(v) is not int or v<=0 for v in lifecycle) or lifecycle!=sorted(lifecycle):
        raise ValueError('packet filter/bind/stop ordering unqualified')
    if status.get('filter_before_bind') is not True or status.get('protocol_before_bind')!=0 or status.get('protocol_after_bind')!=3 or status.get('initial_kernel_packets')!=0:
        raise ValueError('packet filter/bind lifecycle unqualified')
    if status.get('records')!=records or status.get('kernel_packets')!=records or status.get('kernel_drops')!=0 or status.get('truncated') or status.get('budget_exhausted'):
        raise ValueError('packet file/dispatch/kernel population mismatch')
    samples=status.get('drain_snapshots',[])
    if len(samples)<2 or samples[-1]!=samples[-2] or samples[-1]!=dict(records=records,kernel_packets=records,kernel_drops=0):
        raise ValueError('packet drain not stable/equal')
    return dict(capture_backend='filtered_packet_socket',captured_records=records,filtered_records=status['kernel_packets'],kernel_drops=0,file_integrity_valid=True,population_reconciled=True)


def artifact_footer(run,role,records):
    run=Path(run);status_path=run/(role+'-packet-status.json')
    if (run/(role+'-packet-ready.json')).exists():
        status=json.loads(status_path.read_text());result=validate_status(status,records)
        path=run/(role+'.pcap')
        if records<=0 or status.get('file_bytes')!=path.stat().st_size or status.get('file_sha256')!=hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('packet capture file changed or empty')
        return result
    from m3_capture import validate_tcpdump_footer
    result=validate_tcpdump_footer((run/(role+'-capture.log')).read_text(),records)
    return dict(result,capture_backend='tcpdump',population_reconciled=result['tcpdump_population_reconciled'])


def capture(args):
    if sys.platform!='linux' or struct.calcsize('l')!=8:raise ValueError('requires pinned Linux64 fixture')
    paths=[Path(getattr(args,k)) for k in ('output','ready','stop','status')]
    if any(p.exists() for p in paths):raise FileExistsError('recorder artifacts already exist')
    output,ready,stop,status_path=paths
    instructions,version=compile_filter(args.filter)
    report=dict(status='running',backend='filtered_packet_socket',complete=False,filter=args.filter,libpcap_compile_version=version,
        filter_program=instructions,records=0,kernel_packets=0,kernel_drops=0,truncated=0,budget_exhausted=False,drain_snapshots=[],
        timestamp='kernel SO_TIMESTAMPNS realtime, rounded down to PCAP microseconds; not monotonic age authority',
        scope='owned fixed Linux/amd64 Ethernet fixture; final filter attached while protocol0 before eth0 ETH_P_ALL bind; no prefilter counter subtraction')
    sock=None;file=None
    try:
        sock=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,0)
        report['protocol_before_bind']=sock.getsockname()[1]
        if report['protocol_before_bind']!=0:raise ValueError('socket already receives a protocol')
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF,32<<20)
        report['receive_buffer_requested']=32<<20;report['receive_buffer_actual']=sock.getsockopt(socket.SOL_SOCKET,socket.SO_RCVBUF)
        sock.setsockopt(socket.SOL_SOCKET,SO_TIMESTAMPNS,1)
        report['attach_begin_ns']=time.monotonic_ns();attach(sock,instructions);report['attach_end_ns']=time.monotonic_ns();report['filter_before_bind']=True
        first=struct.unpack('II',sock.getsockopt(SOL_PACKET,PACKET_STATISTICS,8))
        report['initial_kernel_packets']=first[0]
        if first!=(0,0):raise ValueError('nonzero disabled-socket statistics')
        file=output.open('xb');file.write(struct.pack('<IHHIIII',0xa1b2c3d4,2,4,0,0,65535,1));file.flush()
        sock.setblocking(False)
        report['bind_begin_ns']=time.monotonic_ns();sock.bind((args.interface,3));report['bind_end_ns']=time.monotonic_ns()
        report['protocol_after_bind']=sock.getsockname()[1]
        if report['protocol_after_bind']!=3:raise ValueError('ETH_P_ALL bind not retained')
        report['ready_ns']=time.monotonic_ns();write(ready,{k:report[k] for k in ('backend','filter_before_bind','protocol_before_bind','protocol_after_bind','initial_kernel_packets','attach_begin_ns','attach_end_ns','bind_begin_ns','bind_end_ns','ready_ns')})
        total_bytes=24;deadline=time.monotonic()+120;drain_end=None;previous=None
        def receive():
            nonlocal total_bytes
            for _ in range(1024):
                try:data,ancillary,flags,_=sock.recvmsg(65535,128)
                except BlockingIOError:break
                if flags&(socket.MSG_TRUNC|socket.MSG_CTRUNC):report['truncated']+=1;raise ValueError('truncated recorder packet or metadata')
                stamps=[struct.unpack('qq',v[:16]) for level,kind,v in ancillary if level==socket.SOL_SOCKET and kind==SO_TIMESTAMPNS and len(v)>=16]
                if len(stamps)!=1 or not 0<=stamps[0][1]<1000000000:raise ValueError('missing/invalid kernel timestamp')
                if len(data)<14 or report['records']>=MAX_RECORDS or total_bytes+16+len(data)>MAX_BYTES:
                    report['budget_exhausted']=True;raise ValueError('packet recorder budget/framing exceeded')
                sec,ns=stamps[0];file.write(struct.pack('<IIII',sec,ns//1000,len(data),len(data)));file.write(data)
                report['records']+=1;total_bytes+=16+len(data)
        def stats():
            n,d=struct.unpack('II',sock.getsockopt(SOL_PACKET,PACKET_STATISTICS,8));report['kernel_packets']+=n;report['kernel_drops']+=d
            if report['kernel_drops']:raise ValueError('packet socket kernel drops')
            return dict(records=report['records'],kernel_packets=report['kernel_packets'],kernel_drops=report['kernel_drops'])
        while True:
            if time.monotonic()>deadline:raise RuntimeError('packet recorder deadline')
            receive()
            if stop.exists():
                if drain_end is None:drain_end=time.monotonic()+5
                sample=stats();report['drain_snapshots'].append(sample)
                if sample==previous and sample['records']==sample['kernel_packets']:
                    report['stop_before_ns']=time.monotonic_ns();break
                if time.monotonic()>drain_end:raise ValueError('packet recorder drain timeout')
                previous=sample;time.sleep(.2)
            else:select.select([sock],[],[],.05)
        # Stop the sole socket, then assert no accepted packet remains unread.
        receive();final=stats()
        if final!=previous:raise ValueError('packet population changed at close boundary')
        sock.close();sock=None;file.flush();file.close();file=None
        report['file_bytes']=output.stat().st_size;report['file_sha256']=hashlib.sha256(output.read_bytes()).hexdigest()
        report.update(status='passed',complete=True);validate_status(report,report['records'])
    except Exception as error:
        report.update(status='failed',error=str(error));raise
    finally:
        if sock is not None:sock.close()
        if file is not None:file.close()
        write(status_path,report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--interface',choices=['eth0'],default='eth0')
    for key in ('output','ready','stop','status','filter'):p.add_argument('--'+key,required=True)
    capture(p.parse_args())
