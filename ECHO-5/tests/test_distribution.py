"""Publication layout regressions; no campaign, container or flight is launched."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from echo5.legacy import ROOT, module


class DistributionTests(unittest.TestCase):
    def test_core_imports_share_the_published_namespace(self):
        qn = module('core.qn')
        self.assertIs(qn, module('echoai.core.qn'))
        self.assertEqual(Path(qn.__file__).resolve(), ROOT / 'core/qn.py')
        self.assertNotIn('navi10_qn', sys.modules)
        self.assertNotIn(str(ROOT.parent), sys.path)

    def test_all_source_readers_bind_the_flat_core(self):
        from echo5 import closure, control, release
        expected = {f'core/{name}.py' for name in
                    ('__init__', 'qn', 'cam', 'wsp', 'stdp', 'spoke', 'dag')}
        with tempfile.TemporaryDirectory() as folder:
            sources = closure.freeze(folder)
            self.assertEqual(set(sources['host']['files']), expected)
            for name, sha in sources['host']['files'].items():
                self.assertEqual(sha, hashlib.sha256((ROOT / name).read_bytes()).hexdigest())
            self.assertEqual(sources, control.source_receipts())
            self.assertEqual(sources, release.current_release_sources())
            self.assertTrue(all(r['unchanged'] for r in closure.preserve(sources).values()))
            closure.verify_archive(folder, sources)

    def test_staged_runner_helpers_import_without_the_checkout(self):
        from echo5 import sitl
        with tempfile.TemporaryDirectory() as folder:
            stage = Path(folder) / 'stage'
            config = dict(seed=12345, episode_timeout_s=60,
                          max_decisions=2, budget=10000)
            with patch.object(sitl.subprocess, 'Popen', side_effect=AssertionError('no launch')):
                sitl._prepare(stage, config, 0, 'conventional', 'distribution-test')
            code = """
import importlib, json, sys
from pathlib import Path
stage = Path(sys.argv[1])
sys.path.insert(0, str(stage))
names = json.loads(sys.argv[2])
for name in names:
    imported = importlib.import_module(name)
    assert Path(imported.__file__).resolve().is_relative_to(stage), name
assert not any(name.startswith('navi10_') for name in sys.modules)
"""
            names = ['echoai.core.' + name for name in
                     ('qn', 'cam', 'wsp', 'stdp', 'spoke', 'dag')]
            names += ['echoai.nexus0.' + name.removesuffix('.py').replace('/', '.')
                      for name in sitl.RUNNER_MODULES if not name.endswith('__init__.py')]
            result = subprocess.run([sys.executable, '-I', '-B', '-S', '-c', code,
                                     str(stage), json.dumps(names)], cwd=stage,
                                    capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            imported = json.loads((stage / 'configuration.json').read_text())['imported_sources']
            self.assertIn('core/cam.py', imported)
            self.assertTrue(all(not name.startswith('../') for name in imported))
