"""Run unchanged fresh-interpreter import regressions against this candidate."""
import importlib.util
from pathlib import Path
import unittest
HERE=Path(__file__).resolve().parents[1];ROOT=HERE.parents[1]
source=ROOT/'evidence/m3-current-n0-identity-binding-fix-2026-11-10/validation/test_runtime_import_order.py'
spec=importlib.util.spec_from_file_location('prior_runtime_import_checks',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.HERE=HERE
names=('test_parent_runtime_order_with_actual_ros_helper_cached','test_wrapper_runtime_order_with_actual_ros_helper_cached','test_parent_ignores_poisoned_collision_cache','test_wrapper_ignores_poisoned_collision_cache')
result=unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(module.RuntimeImportOrderTests(name) for name in names))
raise SystemExit(not result.wasSuccessful())
