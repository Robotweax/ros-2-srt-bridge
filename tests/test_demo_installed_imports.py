"""Offline install/import checks: no ROS imports, native build or runtime."""
import ast
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'ros2/robotweax_srt_bridge_demo'


def missing_local_imports(installed, source_modules):
    """Find source-local imports absent from the isolated libexec directory."""
    available = {p.stem for p in installed.glob('*.py')}
    missing = []
    for path in sorted(installed.glob('*.py')):
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Import):
                names = [alias.name.split('.')[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split('.')[0]]
            else:
                continue
            for name in names:
                if name in source_modules and name not in available:
                    missing.append((path.name, node.lineno, name))
    return missing


class InstalledDemoImportsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        root = Path(cls.tmp.name)
        project = root / 'project'
        (project / 'scripts').mkdir(parents=True)
        for path in (PACKAGE / 'scripts').glob('*.py'):
            shutil.copyfile(path, project / 'scripts' / path.name)
        # Exercise the real install(PROGRAMS ...) declarations with a language-
        # free CMake project. No ROS discovery, compiler or build is invoked.
        declarations = re.findall(
            r'\binstall\s*\(\s*PROGRAMS\b.*?\)',
            (PACKAGE / 'CMakeLists.txt').read_text(), re.DOTALL)
        if not declarations:
            raise AssertionError('demo has no script install declarations')
        (project / 'CMakeLists.txt').write_text(
            'cmake_minimum_required(VERSION 3.20)\n'
            'project(robotweax_srt_bridge_demo LANGUAGES NONE)\n'
            + '\n'.join(declarations) + '\n')
        cls.prefix = root / 'prefix'
        for args in (
            ['cmake', '-S', str(project), '-B', str(root / 'build'),
             '-DCMAKE_INSTALL_PREFIX=' + str(cls.prefix)],
            ['cmake', '--install', str(root / 'build')],
        ):
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)
        cls.installed = cls.prefix / 'lib/robotweax_srt_bridge_demo'
        cls.source_modules = {p.stem for p in (PACKAGE / 'scripts').glob('*.py')}

    def test_installed_local_import_closure(self):
        self.assertTrue(list(self.installed.glob('*.py')))
        self.assertEqual(missing_local_imports(self.installed, self.source_modules), [])

    def test_missing_transitive_helper_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory)
            (installed / 'entry.py').write_text('import helper\n')
            (installed / 'helper.py').write_text('if True:\n    from dependency import value\n')
            self.assertEqual(
                missing_local_imports(installed, {'entry', 'helper', 'dependency'}),
                [('helper.py', 2, 'dependency')])
            (installed / 'dependency.py').write_text('value = 1\n')
            self.assertEqual(
                missing_local_imports(installed, {'entry', 'helper', 'dependency'}), [])

    def test_timeline_imports_without_source_tree_on_path(self):
        # -I omits the cwd, user site and PYTHONPATH. Only libexec is added;
        # importing the pure helper does not instantiate it or run a scenario.
        result = subprocess.run(
            [sys.executable, '-I', '-c',
             'import sys; sys.path.insert(0, sys.argv[1]); '
             'import scenario_timeline; '
             'assert scenario_timeline.__file__ == sys.argv[2]',
             str(self.installed), str(self.installed / 'scenario_timeline.py')],
            cwd=self.prefix, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
