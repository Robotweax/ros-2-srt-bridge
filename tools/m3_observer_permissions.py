"""Explicit isolated-calibration observer permissions; never enabled by a bridge/lab default."""
import ctypes
import errno
from pathlib import Path
import platform
import sys

SYS_ADMIN=1<<21
AUDIT_ARCH_X86_64=0xc000003e
ALLOW=0x7fff0000
KILL=0x80000000
DENY=0x00050000|errno.EPERM
# Native x86_64 only. An additive filter stacks with Docker's unchanged default.
# Deny namespace/mount/admin/inspection/network/child-creation uses of the capability.
DENIED_SYSCALLS={41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,101,103,
    155,159,163,164,165,166,167,168,169,170,171,172,173,175,176,179,227,246,
    248,249,250,272,288,298,300,303,304,305,308,310,311,312,313,320,321,425,
    428,429,430,431,432,433,435,440,442,448}


def filter_program():
    # sock_filter tuples: code,jt,jf,k. Foreign arch/x32 execution is refused.
    rows=[(0x20,0,0,4),(0x15,1,0,AUDIT_ARCH_X86_64),(0x06,0,0,KILL),
          (0x20,0,0,0),(0x45,0,1,0x40000000),(0x06,0,0,KILL)]
    for number in sorted(DENIED_SYSCALLS):rows.extend([(0x15,0,1,number),(0x06,0,0,DENY)])
    return rows+[(0x06,0,0,ALLOW)]


def status(pid='self',proc=Path('/proc')):
    fields={}
    for line in (proc/str(pid)/'status').read_text().splitlines():
        key,_,value=line.partition(':')
        if key in ('Name','Pid','PPid','Uid','Gid','CapInh','CapPrm','CapEff','CapBnd','CapAmb','NoNewPrivs','Seccomp','Seccomp_filters'):fields[key]=value.strip()
    return fields


def require_caps(fields,mask):
    if any(int(fields[k],16)!=mask for k in ('CapEff','CapPrm')) or any(int(fields[k],16) for k in ('CapInh','CapAmb')):
        raise ValueError('unexpected effective/permitted/inheritable/ambient capability set')
    if fields.get('NoNewPrivs')!='1':raise ValueError('no-new-privileges required')


def libc():
    if sys.platform!='linux' or platform.machine()!='x86_64':raise RuntimeError('permission helper requires Linux x86_64')
    return ctypes.CDLL(None,use_errno=True)


def checked(call,result):
    if result!=0:raise OSError(ctypes.get_errno(),call)


def no_new_privileges(lib):
    checked('PR_SET_NO_NEW_PRIVS',lib.prctl(38,ctypes.c_ulong(1),ctypes.c_ulong(0),ctypes.c_ulong(0),ctypes.c_ulong(0)))


def drop_all():
    lib=libc()
    class Header(ctypes.Structure):_fields_=[('version',ctypes.c_uint32),('pid',ctypes.c_int)]
    class Data(ctypes.Structure):_fields_=[('effective',ctypes.c_uint32),('permitted',ctypes.c_uint32),('inheritable',ctypes.c_uint32)]
    header=Header(0x20080522,0);data=(Data*2)()
    lib.capset.argtypes=[ctypes.POINTER(Header),ctypes.POINTER(Data)];lib.capset.restype=ctypes.c_int
    checked('capset zero',lib.capset(ctypes.byref(header),data));no_new_privileges(lib)
    require_caps(status(),0)


def target_permissions():
    drop_all()
    # Same-UID proc inspection remains permitted; this changes only the finite target.
    checked('PR_SET_DUMPABLE',libc().prctl(4,ctypes.c_ulong(1),ctypes.c_ulong(0),ctypes.c_ulong(0),ctypes.c_ulong(0)))


def restrict_observer():
    require_caps(status(),SYS_ADMIN);lib=libc();no_new_privileges(lib)
    class Instruction(ctypes.Structure):_fields_=[('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint32)]
    class Program(ctypes.Structure):_fields_=[('length',ctypes.c_ushort),('filter',ctypes.POINTER(Instruction))]
    instructions=filter_program();array=(Instruction*len(instructions))(*(Instruction(*r) for r in instructions));program=Program(len(instructions),array)
    checked('additive observer seccomp',lib.prctl(22,ctypes.c_ulong(2),ctypes.byref(program),ctypes.c_ulong(0),ctypes.c_ulong(0)))
    require_caps(status(),SYS_ADMIN)
