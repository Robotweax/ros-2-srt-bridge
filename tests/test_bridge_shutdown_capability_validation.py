import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
HERE=ROOT/'evidence/m3-bridge-shutdown-capability-fix-2026-11-10'
spec=importlib.util.spec_from_file_location('bridge_capability_fixed_sidecar',HERE/'sidecar.py')
sidecar=importlib.util.module_from_spec(spec);spec.loader.exec_module(sidecar)


class CapabilityValidationTests(unittest.TestCase):
    def setUp(self):
        self.actual=json.loads((ROOT/'evidence/m3-bridge-shutdown-diagnostic-2026-11-10/native-observer-policy.json').read_text())['HostConfig']
    def test_retained_docker_canonical_capability_passes_without_mutation(self):
        before=copy.deepcopy(self.actual)
        self.assertEqual(self.actual['CapAdd'],['CAP_SYS_ADMIN'])
        sidecar.validate_isolation(self.actual)
        self.assertEqual(self.actual,before)
        sidecar.validate_isolation(dict(self.actual,CapAdd=['SYS_ADMIN']))
    def test_missing_wrong_and_additional_capabilities_still_fail(self):
        for caps in (None,[],['CAP_SYS_PTRACE'],['CAP_SYS_ADMIN','CAP_SYS_PTRACE'],['SYS_ADMIN','NET_ADMIN'],['cap_sys_admin']):
            with self.subTest(caps=caps),self.assertRaises(ValueError):sidecar.validate_isolation(dict(self.actual,CapAdd=caps))
    def test_capability_normalization_preserves_all_other_isolation_gates(self):
        for key,value in [('Privileged',True),('ReadonlyRootfs',False),('NetworkMode','host'),('UsernsMode','host'),('CapDrop',[])]:
            with self.subTest(key=key),self.assertRaises(ValueError):sidecar.validate_isolation(dict(self.actual,**{key:value}))

if __name__=='__main__':unittest.main()
