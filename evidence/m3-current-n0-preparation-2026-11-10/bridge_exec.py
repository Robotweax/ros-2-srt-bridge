"""Explicit bridge-only capability reduction before exec; no filter or tuning."""
import ctypes
import json
import os
from pathlib import Path
import platform
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from m3_observer_filtering import status,require_role


def reduce(lib,last_cap):
    def check(value,operation):
        if value!=0:raise OSError(ctypes.get_errno(),operation)
    if not 0<=last_cap<=63:raise ValueError('unexpected kernel capability range')
    # SETPCAP is still active while dropping the inherited bounding set.
    for cap in range(last_cap+1):check(lib.prctl(24,ctypes.c_ulong(cap),0,0,0),'PR_CAPBSET_DROP')
    class Header(ctypes.Structure):_fields_=[('version',ctypes.c_uint32),('pid',ctypes.c_int)]
    class Data(ctypes.Structure):_fields_=[('effective',ctypes.c_uint32),('permitted',ctypes.c_uint32),('inheritable',ctypes.c_uint32)]
    header=Header(0x20080522,0);data=(Data*2)()
    lib.capset.argtypes=[ctypes.POINTER(Header),ctypes.POINTER(Data)];lib.capset.restype=ctypes.c_int
    check(lib.capset(ctypes.byref(header),data),'capset zero')
    check(lib.prctl(38,ctypes.c_ulong(1),0,0,0),'PR_SET_NO_NEW_PRIVS')
    check(lib.prctl(4,ctypes.c_ulong(1),0,0,0),'PR_SET_DUMPABLE')


def main():
    try:
        if sys.platform!='linux' or platform.machine()!='x86_64':raise ValueError('bridge wrapper requires pinned Linux amd64 target image')
        destination=Path(sys.argv[1]);argv=sys.argv[2:]
        if not argv or Path(argv[0]).name!='bridge_node':raise ValueError('only bridge_node may be wrapped')
        reduce(ctypes.CDLL(None,use_errno=True),int(Path('/proc/sys/kernel/cap_last_cap').read_text()))
        require_role(status(),0)
        destination.write_text(json.dumps(dict(pid=os.getpid(),permissions=status()))+'\n')
        os.execv(argv[0],argv)
    except BaseException as error:
        print(json.dumps(dict(stage='bridge_capability_drop_or_exec',type=type(error).__name__,errno=getattr(error,'errno',None),message=str(error))),file=sys.stderr,flush=True)
        return 125

if __name__=='__main__':raise SystemExit(main())
