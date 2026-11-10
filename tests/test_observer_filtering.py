import errno
import importlib.util
import json
import tempfile
from unittest.mock import patch
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import m3_observer_filtering as policy


class NativeFilterTests(unittest.TestCase):
    def test_observer_must_match_daemon_not_target(self):
        self.assertEqual(policy.profile('aarch64','arm64')['architectures'],['SCMP_ARCH_AARCH64'])
        self.assertEqual(policy.profile('x86_64','amd64')['architectures'],['SCMP_ARCH_X86_64'])
        with self.assertRaisesRegex(ValueError,'daemon-native'):policy.profile('aarch64','amd64')
        with self.assertRaises(ValueError):policy.profile('riscv64','riscv64')
    def test_default_deny_and_no_administrative_or_child_operations(self):
        p=policy.profile('arm64','arm64');self.assertEqual(p['defaultAction'],'SCMP_ACT_ERRNO');self.assertEqual(p['defaultErrnoRet'],errno.EPERM)
        allowed=set(p['syscalls'][0]['names'])
        for name in ('mount','umount2','unshare','setns','clone','clone3','fork','vfork','socket','connect','ptrace','process_vm_readv','bpf','reboot','capset','prctl','clock_settime','init_module'):
            self.assertNotIn(name,allowed)
        for name in ('openat','read','write','getdents64','clock_nanosleep','execve','exit_group'):self.assertIn(name,allowed)
    def test_target_has_no_bounding_or_active_capability(self):
        f=dict(CapEff='0',CapPrm='0',CapBnd='0',CapAmb='0',CapInh='0',NoNewPrivs='1',Seccomp='2');policy.require_role(f,0)
        with self.assertRaises(ValueError):policy.require_role(dict(f,CapBnd='200000'),0)
        policy.require_role(dict(f,CapEff='200000',CapPrm='200000',CapBnd='200000'),1<<21)
    def test_ambient_inheritance_and_unconfined_modes_refused(self):
        f=dict(CapEff='200000',CapPrm='200000',CapBnd='200000',CapAmb='0',CapInh='0',NoNewPrivs='1',Seccomp='2')
        for key,value in [('CapAmb','1'),('CapInh','1'),('NoNewPrivs','0'),('Seccomp','0')]:
            with self.subTest(key=key),self.assertRaises(ValueError):policy.require_role(dict(f,**{key:value}),1<<21)


class EntryDiagnosticsTests(unittest.TestCase):
    def load_entry(self):
        path=Path(__file__).resolve().parents[1]/'evidence/m3-observer-native-filter-2026-11-10/observer_entry.py'
        spec=importlib.util.spec_from_file_location('native_observer_entry_test',path)
        entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
        return entry
    def test_architecture_failure_has_stage_errno_and_traceback(self):
        entry=self.load_entry()
        with tempfile.TemporaryDirectory() as folder:
            entry.OUT=Path(folder)
            with patch.object(entry.platform,'machine',return_value='x86_64'),patch.object(entry.Path,'read_text',return_value=json.dumps(dict(native='arm64',daemon='aarch64'))),patch.object(entry,'status',return_value={}):
                self.assertEqual(entry.main(),125)
            rows=[json.loads(x) for x in (entry.OUT/'observer-exec.jsonl').read_text().splitlines()]
            self.assertEqual([x['kind'] for x in rows],['entry','exec_failed'])
            self.assertEqual(rows[-1]['stage'],'native_architecture');self.assertIsNone(rows[-1]['errno'])
            self.assertIn('ValueError',rows[-1]['traceback'])
    def test_exec_errno_is_preserved(self):
        entry=self.load_entry()
        fields=dict(CapEff='200000',CapPrm='200000',CapBnd='200000',CapAmb='0',CapInh='0',NoNewPrivs='1',Seccomp='2')
        import hashlib
        import types
        expected=dict(native='arm64',daemon='aarch64',profile_sha256=hashlib.sha256(b'profile').hexdigest())
        def read(path,*args,**kwargs):
            if path.name=='observer-architecture.json':return json.dumps(expected)
            if path.name=='target-info.json':return json.dumps(dict(pid=42,start_ticks=99))
            return '0'
        collector=types.SimpleNamespace(same_identity=lambda proc,identity:True)
        with tempfile.TemporaryDirectory() as folder:
            entry.OUT=Path(folder)
            with patch.object(entry.platform,'machine',return_value='aarch64'),patch.object(entry.Path,'read_text',read),patch.object(entry.Path,'read_bytes',return_value=b'profile'),patch.object(entry,'status',return_value=fields),patch.dict(sys.modules,shutdown_observer=collector),patch.object(entry.os,'execv',side_effect=FileNotFoundError(errno.ENOENT,'missing interpreter')),patch.object(entry.sys,'argv',['observer_entry.py']):
                self.assertEqual(entry.main(),125)
            rows=[json.loads(x) for x in (entry.OUT/'observer-exec.jsonl').read_text().splitlines()]
            self.assertEqual([x['kind'] for x in rows],['entry','preexec_verified','exec_begin','exec_failed'])
            self.assertEqual(rows[-1]['stage'],'exec');self.assertEqual(rows[-1]['errno'],errno.ENOENT)
            self.assertEqual(rows[-1]['type'],'FileNotFoundError');self.assertIn('missing interpreter',rows[-1]['message'])

if __name__=='__main__':unittest.main()
