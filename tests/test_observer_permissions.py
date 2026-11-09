import errno
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import m3_observer_permissions as p


def evaluate(arch,number):
    pc=0;value=0;rows=p.filter_program()
    while pc<len(rows):
        code,jt,jf,k=rows[pc]
        if code==0x20:value=arch if k==4 else number
        elif code==0x15:pc+=jt if value==k else jf
        elif code==0x45:pc+=jt if value&k else jf
        elif code==0x06:return k
        else:raise AssertionError('unknown BPF opcode')
        pc+=1
    raise AssertionError('missing filter result')


class PermissionTests(unittest.TestCase):
    def test_read_only_collection_and_initial_exec_remain_allowed(self):
        for number in (0,1,3,5,9,10,13,14,15,59,61,62,202,228,230,231,257,262,267,318,334):
            with self.subTest(number=number):self.assertEqual(evaluate(p.AUDIT_ARCH_X86_64,number),p.ALLOW)
    def test_administrative_network_ptrace_and_child_creation_are_denied(self):
        for number in (41,56,57,58,101,103,155,165,166,169,175,176,246,272,298,304,308,310,311,313,320,321,425,428,429,430,431,432,435,442):
            with self.subTest(number=number):self.assertEqual(evaluate(p.AUDIT_ARCH_X86_64,number),0x50000|errno.EPERM)
    def test_other_architecture_and_x32_cannot_bypass_filter(self):
        self.assertEqual(evaluate(0x40000003,165),p.KILL);self.assertEqual(evaluate(p.AUDIT_ARCH_X86_64,0x40000000|165),p.KILL)
    def test_only_exact_process_capability_lease_is_accepted(self):
        fields=dict(CapEff='00200000',CapPrm='00200000',CapInh='0',CapAmb='0',NoNewPrivs='1');p.require_caps(fields,p.SYS_ADMIN)
        for key,value in [('CapEff','00280000'),('CapPrm','0'),('CapAmb','1'),('CapInh','1'),('NoNewPrivs','0')]:
            with self.subTest(key=key),self.assertRaises(ValueError):p.require_caps(dict(fields,**{key:value}),p.SYS_ADMIN)
        p.require_caps(dict(CapEff='0',CapPrm='0',CapAmb='0',CapInh='0',NoNewPrivs='1'),0)

if __name__=='__main__':unittest.main()
