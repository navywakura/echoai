"""Real RepoWorld mount protection, using public synthetic fixture bytes only.

The generated C file is an inert protection fixture: it is never compiled or
imported, and this test makes no claim about native binary loading. Generated
version Python is imported inside bubblewrap. No dataset or hidden checks load.
"""
import difflib
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import textwrap
import unittest
from unittest.mock import patch

try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.pcworld.receipts import canonical
from echoai.pcworld.runtime import build_runtime, load_runtime, repository_runtime
from echoai.repoworld.environment import environment_ref, execute_repo, repo_store
from echoai.repoworld.study import prepare_entry
from echoai.repoworld.supplements import apply_supplement, build_supplement_manifest
from echoai.repoworld.types import PublicTask, RepoBase
from echoai.repoworld.workspace import Workspace, protected_paths


class SupplementIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime_temp = tempfile.TemporaryDirectory(prefix='supplement-runtime-test-')
        cls.addClassCleanup(cls.runtime_temp.cleanup)
        root = Path(cls.runtime_temp.name)
        existing = ROOT/'ECHO-5.1/artifacts/runtime-python314-20261013'
        stdlib = load_runtime(existing) if existing.exists() else build_runtime(root/'stdlib')
        cls.runtime = repository_runtime(stdlib, root/'runtime')
        cls.environment = environment_ref(cls.runtime, scope='stdlib-calibration')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='supplement-integration-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = self.root/'source'
        (source/'pkg').mkdir(parents=True)
        for path, data in {'pkg/__init__.py': '', 'pkg/core.py': 'value = 1\n',
                           'pkg/native_input.pyx': 'cdef int value = 1\n',
                           'pkg/generator.py': 'BUILD_VALUE = 1\n'}.items():
            (source/path).write_text(data)
            (source/path).chmod(0o644)
        (source/'native_links').mkdir()
        (source/'native_links/native_alias.pyx').symlink_to('../pkg/native_input.pyx')
        snapshot = repo_store(self.root/'base-objects').capture(source)
        self.base = RepoBase(PublicTask('fixture__supplement-1', 'fixture/supplement',
                                       'a'*40, 'Public mount-protection fixture'),
                             snapshot, self.environment)
        self.generated = self.root/'generated'
        (self.generated/'pkg').mkdir(parents=True)
        for name, data in {'_version.py': "__version__ = version = '1.2.3'\n",
                           'generated.c': '/* inert mount-protection fixture */\n'}.items():
            (self.generated/'pkg'/name).write_text(data)
            (self.generated/'pkg'/name).chmod(0o644)
        self.manifest = build_supplement_manifest(
            self.base, self.generated,
            build=dict(status='success', dirty=False, artifact_sha256='b'*64,
                       builder='synthetic protection fixture — no compiler'),
            extra_build_inputs=('pkg/generator.py',))
        self.digest = hashlib.sha256(canonical(self.manifest)).hexdigest()

    def test_real_bwrap_protects_supplement_after_workspace_reopen(self):
        supplemented = apply_supplement(self.base, self.generated, self.manifest, self.digest)
        Workspace(self.root/'workspace', supplemented)
        reopened = Workspace(self.root/'workspace')
        diff = ''.join(difflib.unified_diff(['value = 1\n'], ['value = 2\n'],
                                          fromfile='a/pkg/core.py', tofile='b/pkg/core.py'))
        candidate = reopened.stage(diff, reopened.current.id)
        code = textwrap.dedent('''\
            import json
            import os
            from pathlib import Path
            import sys
            sys.path.insert(0, '/work')
            from pkg._version import __version__
            assert __version__ == '1.2.3'
            record = json.loads(Path('.repoworld-build.json').read_bytes())
            assert record['manifest']['base_commit'] == 'a' * 40
            assert 'pkg/generator.py' in record['manifest']['native_build_inputs']
            expected = ('.repoworld-build.json', 'pkg/_version.py', 'pkg/generated.c',
                        'pkg/native_input.pyx', 'pkg/generator.py')
            denied = []
            def readonly(path, operation, label):
                before = path.read_bytes()
                try:
                    operation()
                except OSError:
                    assert path.read_bytes() == before
                    denied.append(str(path) + ':' + label)
                else:
                    raise AssertionError('protected path writable: ' + str(path) + ':' + label)
            for name in expected:
                path = Path(name)
                assert path.stat().st_mode & 0o777 == 0o644
                readonly(path, lambda: path.write_text('tamper'), 'write')
                readonly(path, lambda: path.chmod(0o600), 'chmod')
                readonly(path, path.unlink, 'unlink')
            alias = Path('native_links/native_alias.pyx')
            assert alias.is_symlink()
            assert os.readlink(alias) == '../pkg/native_input.pyx'
            readonly(alias, lambda: alias.write_text('through alias'), 'write')
            readonly(alias, alias.unlink, 'unlink')
            Path('replacement.pyx').write_text('replacement')
            readonly(alias, lambda: os.replace('replacement.pyx', alias), 'replace')
            assert Path('pkg/core.py').read_text() == 'value = 2\\n'
            Path('pkg/core.py').write_text('value = 3\\n')
            assert Path('pkg/core.py').read_text() == 'value = 3\\n'
            assert Path('/repo-base/pkg/core.py').read_text() == 'value = 1\\n'
            assert Path('/candidate/pkg/core.py').read_text() == 'value = 2\\n'
            for name in ('/repo-base/pkg/core.py', '/candidate/pkg/core.py'):
                path = Path(name)
                readonly(path, lambda: path.write_text('tamper'), 'write')
            print('SUPPLEMENT_PROTECTION ' + json.dumps(dict(
                version=__version__, denied=len(denied),
                manifest_sha256=record['manifest_sha256'], mutable_python=True)))
        ''')
        result = execute_repo(reopened.base, candidate.snapshot,
                              ('/usr/bin/python3', '-I', '-B', '-c', code),
                              limits={}, check_artifacts=())
        self.assertEqual(result['exit_code'], 0, result)
        self.assertEqual(result['status'], 'EXITED', result)
        observations = json.loads(result['stdout'].split('SUPPLEMENT_PROTECTION ', 1)[1].splitlines()[0])
        self.assertEqual(observations, dict(version='1.2.3', denied=20,
                                           manifest_sha256=self.digest, mutable_python=True))
        self.assertTrue(result['isolation']['job_empty'])
        self.assertFalse(result['isolation']['host_usr_mounted'])
        self.assertFalse(result['task_success'])
        self.assertEqual((candidate.snapshot.root/'pkg/core.py').read_text(), 'value = 2\n')
        self.assertEqual(reopened.current.id, supplemented.snapshot.id)
        self.assertEqual((reopened.base.snapshot.root/'pkg/core.py').read_text(), 'value = 1\n')

    def entry(self):
        # Pretty-printed UTF-8 JSON deliberately differs from canonical bytes.
        manifest_file = self.root/'manifest.json'
        manifest_file.write_text(json.dumps(self.manifest, indent=2, ensure_ascii=False)+'\n')
        return dict(source=str(self.root/'source'), runtime=str(self.root/'runtime-descriptor'),
                    supplement=dict(directory=str(self.generated), manifest=str(manifest_file),
                                    manifest_sha256=self.digest))

    def test_real_bwrap_public_link_and_native_alias_targets_are_readonly_without_provenance(self):
        source = self.root/'source'
        (source/'tests').mkdir()
        (source/'routing').mkdir()
        (source/'pkg/checks.py').write_text('CHECK = 1\n')
        (source/'tests/test_public.py').symlink_to('../pkg/checks.py')
        (source/'routing/bridge').symlink_to('../pkg/checks.py')
        (source/'tests/test_chain.py').symlink_to('../routing/bridge')
        (source/'native_links/kernel.pyx').symlink_to('../pkg/core.py')
        (source/'docs').mkdir()
        (source/'docs/source_alias').symlink_to('../pkg/generator.py')
        snapshot = repo_store(self.root/'link-objects').capture(source)
        base = replace(self.base, snapshot=snapshot)
        code = textwrap.dedent('''\
            from pathlib import Path
            assert not Path('.repoworld-build.json').exists()
            for name in ('tests/test_public.py', 'tests/test_chain.py', 'pkg/checks.py',
                         'native_links/kernel.pyx', 'pkg/core.py'):
                path = Path(name)
                before = path.read_bytes()
                try: path.write_text('tamper')
                except OSError: assert path.read_bytes() == before
                else: raise AssertionError('linked protected input writable: ' + name)
            try: Path('routing/bridge').unlink()
            except OSError: pass
            else: raise AssertionError('protected chain can be retargeted')
            assert Path('docs/source_alias').is_symlink()
            Path('docs/source_alias').write_text('ordinary mutable source')
            assert Path('pkg/generator.py').read_text() == 'ordinary mutable source'
            print('linked inputs protected; docs target mutable')
        ''')
        result = execute_repo(base, snapshot, ('/usr/bin/python3', '-I', '-B', '-c', code),
                              limits={}, check_artifacts=())
        self.assertEqual(result['exit_code'], 0, result['stderr'])
        self.assertIn('linked inputs protected; docs target mutable', result['stdout'])

    def prepared_entry(self, entry):
        # Replace expensive acquisition/export boundaries only. prepare_entry
        # reads the real descriptor and calls real apply_supplement/SnapshotStore.
        with patch('echoai.repoworld.study.load_image', return_value=self.runtime), \
             patch('echoai.repoworld.study.environment_ref', return_value=self.environment), \
             patch('echoai.repoworld.study.prepare_repo', return_value=self.base):
            return prepare_entry(self.base.task, entry, self.root/'prepared')

    def test_study_descriptor_applies_real_pinned_supplement(self):
        result = self.prepared_entry(self.entry())
        self.assertNotEqual(result.snapshot.id, self.base.snapshot.id)
        self.assertEqual(result.task, self.base.task)
        self.assertEqual(result.environment, self.environment)
        self.assertEqual((result.snapshot.root/'pkg/_version.py').read_text(),
                         "__version__ = version = '1.2.3'\n")
        record = json.loads((result.snapshot.root/'.repoworld-build.json').read_bytes())
        self.assertEqual(record['manifest'], self.manifest)
        self.assertEqual(record['manifest_sha256'], self.digest)
        frozen = protected_paths(result.snapshot.manifest['entries'], snapshot=result.snapshot)
        self.assertIn('pkg/generator.py', frozen)
        self.assertIn('pkg/_version.py', frozen)
        self.assertNotIn('pkg/core.py', frozen)
        self.assertIn('native_links', frozen)
        self.assertNotIn('native_links/native_alias.pyx', frozen)
        self.assertFalse((self.base.snapshot.root/'.repoworld-build.json').exists())

    def test_study_descriptor_rejects_artifact_changed_after_pin(self):
        entry = self.entry()
        (self.generated/'pkg/_version.py').write_text("__version__ = 'tampered'\n")
        with self.assertRaisesRegex(ValueError, 'supplement.*differ'):
            self.prepared_entry(entry)
        self.assertFalse((self.base.snapshot.root/'.repoworld-build.json').exists())
        self.assertEqual((self.base.snapshot.root/'pkg/core.py').read_text(), 'value = 1\n')


if __name__ == '__main__':
    unittest.main()
