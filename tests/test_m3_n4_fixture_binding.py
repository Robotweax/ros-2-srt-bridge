import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import m3_n4_fixture as fixture


class FixtureBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.sdk='install/bridge-sender-reconcile';self.peer=fixture.peer_path('sender-reconcile');self.worker=self.sdk+'/bin/robotweax-journal-worker';self.provider='install/srt-m0/lib/librobotweax-srt.a'
        for name in [self.peer,self.worker,self.provider,self.sdk+'/lib/librobotweax_srt_bridge_endpoint.a',self.sdk+'/lib/librobotweax_srt_bridge_transport.a',self.sdk+'/include/ticket.hpp',*fixture.SOURCES]:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(name)
        self.layout=dict(sdk=self.sdk,name='sender-reconcile')
        self.binding=self.root/Path(self.peer).parent/'fixture-binding.json'
    def save(self):
        self.binding.write_text(json.dumps(fixture.create_binding(self.root,self.root/self.sdk,self.root/self.peer,self.root/self.worker,self.root/self.provider)))
    def test_matching_binding_and_old_default_path(self):
        self.assertEqual(fixture.peer_path('baseline'),'build/m3-n4-peer/m3_n4_peer')
        self.save()
        with patch.object(fixture,'matched',return_value=self.layout):
            r=fixture.native_layout(self.root,'sender-reconcile');self.assertEqual(r['worker'],self.worker);self.assertIn(self.peer,r['runtime_sha256'])
    def test_missing_binding_refuses_before_missing_peer_can_launch(self):
        (self.root/self.peer).unlink()
        with patch.object(fixture,'matched',return_value=self.layout),self.assertRaisesRegex(ValueError,'binding missing'):fixture.native_layout(self.root,'sender-reconcile')
    def test_changed_peer_worker_header_library_or_source_is_stale(self):
        for name in (self.peer,self.worker,self.sdk+'/include/ticket.hpp',self.sdk+'/lib/librobotweax_srt_bridge_endpoint.a',fixture.SOURCES[0],fixture.SOURCES[1],fixture.SOURCES[2]):
            self.save();p=self.root/name;old=p.read_text();p.write_text('changed')
            with self.subTest(name=name),patch.object(fixture,'matched',return_value=self.layout),self.assertRaisesRegex(ValueError,'stale'):fixture.native_layout(self.root,'sender-reconcile')
            p.write_text(old)
    def test_foreign_worker_and_provider_are_not_bound(self):
        with self.assertRaisesRegex(ValueError,'worker'):fixture.create_binding(self.root,self.root/self.sdk,self.root/self.peer,self.root/'other-worker',self.root/self.provider)
        with self.assertRaisesRegex(ValueError,'provider'):fixture.create_binding(self.root,self.root/self.sdk,self.root/self.peer,self.root/self.worker,self.root/'other-provider')
    def test_n4_preflight_failure_never_creates_network_or_output(self):
        import m3_n4
        output=self.root/'case'
        with patch.object(m3_n4,'native_layout',side_effect=ValueError('binding missing')),patch.object(m3_n4,'NetworkLab') as lab,self.assertRaisesRegex(ValueError,'binding missing'):m3_n4.run_case(output,'admission','both',runtime_layout='sender-reconcile')
        lab.assert_not_called();self.assertFalse(output.exists())
    def test_worker_launch_flag_matches_actual_sdk_and_no_old_worker_literal(self):
        root=Path(__file__).resolve().parents[1]
        peer=(root/'tools/m3_n4_peer/main.cpp').read_text();supervisor=(root/'src/robotweax_srt_bridge_core/src/worker/supervisor.cpp').read_text()
        self.assertIn('--worker-ipc-v3',peer);self.assertIn('--worker-ipc-v3',supervisor)
        self.assertIn('worker.executable=N4_WORKER_EXECUTABLE',peer);self.assertNotIn('/workspace/install/bridge-m3',peer)
        recipe=(root/'tools/m3_n4_peer/CMakeLists.txt').read_text();self.assertIn('NO_DEFAULT_PATH',recipe);self.assertIn('POST_BUILD',recipe);self.assertIn('RobotweaxBridge::journal_worker',recipe)


if __name__=='__main__':unittest.main()
