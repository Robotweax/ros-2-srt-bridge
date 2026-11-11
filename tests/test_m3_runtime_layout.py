import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from m3_runtime_layout import paths,matched,CALIBRATION,SENDER_CALIBRATION,PROBE_CALIBRATION,RECONCILE_CALIBRATION,SHUTDOWN_CALIBRATION,LAYOUTS
from m3_n5_progress import RUNTIMES
from m3_source_preflight import sha


class RuntimeLayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.expected={};self.baseline={}
        for name in set(RUNTIMES+paths('start-trace')):
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(name)
        for name in RUNTIMES:self.baseline[name]=sha(self.root/name)
        for name in paths('start-trace')[:-1]:self.expected[name]=sha(self.root/name)
        setup=self.root/'install/m3-start-trace-ros/setup.bash';setup.write_text('fixture setup')
        self.manifest=self.root/CALIBRATION;self.manifest.parent.mkdir(parents=True);self.save()
    def save(self):self.manifest.write_text(json.dumps(dict(new_matched_build_binaries=self.expected,installed_baseline=self.baseline)))
    def test_scenario_parsers_accept_selected_reconciliation_prefix(self):
        root=Path(__file__).resolve().parents[1]/'ros2/robotweax_srt_bridge_demo/scripts'
        for name in ('m3_scenario.py','m3_ros_multiroute_scenario.py','m3_dds_scenario.py','m3_ros_n4_sensor.py','m3_ros_n4_crash.py'):
            calls=[n for n in ast.walk(ast.parse((root/name).read_text())) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='add_argument' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='--ros-install']
            self.assertEqual(len(calls),1,name)
            choices=next(k.value for k in calls[0].keywords if k.arg=='choices')
            self.assertIn('install/m3-sender-reconcile-ros',ast.literal_eval(choices),name)

    def test_default_paths_are_original_and_provider_shared(self):
        self.assertEqual(paths('baseline'),RUNTIMES);self.assertEqual(paths('start-trace')[-1],RUNTIMES[-1]);self.assertEqual(matched(self.root,'start-trace')['ros'],'install/m3-start-trace-ros')
    def test_changed_selected_runtime_refused(self):
        (self.root/paths('start-trace')[0]).write_text('wrong binary')
        with self.assertRaisesRegex(ValueError,'matched runtime changed'):matched(self.root,'start-trace')
    def test_baseline_is_preserved_and_manifest_complete(self):
        (self.root/RUNTIMES[0]).write_text('overwritten')
        with self.assertRaisesRegex(ValueError,'preserved installed baseline changed'):matched(self.root,'start-trace')
        self.baseline.pop(RUNTIMES[-1]);self.save()
        with self.assertRaisesRegex(ValueError,'incomplete preserved baseline'):matched(self.root,'start-trace')
    def test_missing_matching_worker_and_setup_refused(self):
        self.expected.pop(paths('start-trace')[1]);self.save()
        with self.assertRaisesRegex(ValueError,'incomplete matched runtime'):matched(self.root,'start-trace')
    def test_unrecorded_sdk_archive_and_missing_setup_refused(self):
        p=self.root/'install/bridge-start-trace-qualified/lib/libunexpected.a';p.write_text('unrecorded')
        with self.assertRaisesRegex(ValueError,'incomplete matched runtime'):matched(self.root,'start-trace')
        p.unlink();(self.root/'install/m3-start-trace-ros/setup.bash').unlink()
        with self.assertRaisesRegex(ValueError,'setup missing'):matched(self.root,'start-trace')
    def test_unknown_layout_and_rebuild_are_refused(self):
        with self.assertRaises(ValueError):paths('../../wrong')
        root=Path(__file__).resolve().parents[1];p=subprocess.run([sys.executable,'tools/run_m3.py','--runtime-layout','start-trace'],cwd=root,capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertIn('requires --skip-build',p.stderr)
    def test_sender_layout_preserves_both_previous_builds(self):
        expected={}
        for name in paths('sender-visibility')[:-1]:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(name);expected[name]=sha(p)
        (self.root/'install/m3-sender-visibility-ros/setup.bash').write_text('fixture setup')
        manifest=self.root/SENDER_CALIBRATION;manifest.parent.mkdir(parents=True)
        data=dict(new_matched_build_binaries=expected,installed_baseline=self.baseline,preserved_start_trace=self.expected)
        manifest.write_text(json.dumps(data));self.assertEqual(matched(self.root,'sender-visibility')['sdk'],'install/bridge-sender-visibility')
        data['preserved_start_trace']={};manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'start-trace manifest mismatch'):matched(self.root,'sender-visibility')
    def test_sender_diagnostics_cannot_use_old_ignored_parameter_override(self):
        root=Path(__file__).resolve().parents[1]
        p=subprocess.run([sys.executable,'tools/run_m3.py','--sender-diagnostics','--command-diagnostics','--skip-build'],cwd=root,capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertIn('sender-visibility runtime layout',p.stderr)
    def test_probe_diagnostics_refuse_old_runtime(self):
        root=Path(__file__).resolve().parents[1]
        p=subprocess.run([sys.executable,'tools/run_m3.py','--probe-diagnostics','--command-diagnostics','--skip-build'],cwd=root,capture_output=True,text=True)
        self.assertEqual(p.returncode,2);self.assertIn('probe-tracing runtime layout',p.stderr)
    def test_probe_layout_verifies_preserved_sender_build(self):
        inventories={}
        for name,manifest in (('sender-visibility',SENDER_CALIBRATION),('probe-tracing',PROBE_CALIBRATION),('sender-reconcile',RECONCILE_CALIBRATION)):
            expected={}
            for path in paths(name)[:-1]:
                p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(path);expected[path]=sha(p)
            setup=self.root/('install/m3-'+name+'-ros/setup.bash');setup.write_text('fixture setup')
            data=dict(new_matched_build_binaries=expected,installed_baseline=self.baseline,preserved_start_trace=self.expected)
            if name in ('probe-tracing','sender-reconcile'):data['preserved_sender_visibility']=inventories['sender-visibility']
            if name=='sender-reconcile':data['preserved_probe_tracing']=inventories['probe-tracing']
            target=self.root/manifest;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(data));inventories[name]=expected
        self.assertEqual(matched(self.root,'probe-tracing')['sdk'],'install/bridge-probe-tracing')
        self.assertEqual(matched(self.root,'sender-reconcile')['sdk'],'install/bridge-sender-reconcile')
        data['preserved_probe_tracing']={};target.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'probe-tracing manifest mismatch'):matched(self.root,'sender-reconcile')
        data['preserved_probe_tracing']=inventories['probe-tracing'];data['preserved_sender_visibility']={};target.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'sender-visibility manifest mismatch'):matched(self.root,'sender-reconcile')

    def test_shutdown_layout_requires_complete_preserved_reconciliation_chain(self):
        inventories={}
        for name,manifest in (('sender-visibility',SENDER_CALIBRATION),('probe-tracing',PROBE_CALIBRATION),('sender-reconcile',RECONCILE_CALIBRATION),('shutdown-tracing',SHUTDOWN_CALIBRATION)):
            expected={}
            for path in paths(name)[:-1]:
                p=self.root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(path);expected[path]=sha(p)
            (self.root/LAYOUTS[name]['ros']/'setup.bash').write_text('fixture setup')
            data=dict(new_matched_build_binaries=expected,installed_baseline=self.baseline,preserved_start_trace=self.expected)
            if name!='sender-visibility':data['preserved_sender_visibility']=inventories['sender-visibility']
            if name in ('sender-reconcile','shutdown-tracing'):data['preserved_probe_tracing']=inventories['probe-tracing']
            if name=='shutdown-tracing':data['preserved_sender_reconcile']=inventories['sender-reconcile']
            p=self.root/manifest;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data));inventories[name]=expected
        self.assertEqual(matched(self.root,'shutdown-tracing')['sdk'],'install/bridge-shutdown-trace-calibration')
        data['preserved_sender_reconcile']={};p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'sender-reconcile manifest mismatch'):matched(self.root,'shutdown-tracing')


if __name__=='__main__':unittest.main()
