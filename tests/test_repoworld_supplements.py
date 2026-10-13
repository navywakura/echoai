"""Supplement admission and stale native artifact regressions; stdlib only."""
import copy
import dataclasses
import difflib
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.pcworld.receipts import canonical
from echoai.repoworld.environment import repo_store
from echoai.repoworld.types import EnvironmentRef, PublicTask, RepoBase
from echoai.repoworld.workspace import Workspace, protected_paths, stage_patch


def sha(data):
    return hashlib.sha256(data).hexdigest()


def patch_text(path, before, after):
    return ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                      fromfile='a/'+path, tofile='b/'+path))


class SupplementTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.find_spec('echoai.repoworld.supplements')
        self.assertIsNotNone(spec, 'supplement admission module must exist')
        self.api = importlib.import_module('echoai.repoworld.supplements')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root/'source'
        self.source.mkdir()
        sources = {'pkg/__init__.py': '', 'pkg/core.py': 'value = 1\n',
                   'pkg/kernel.pyx': 'value = 1\n', 'pkg/kernel.pxd': 'cdef int value\n',
                   'pkg/include/kernel.h': '#define VALUE 1\n',
                   'pkg/generator.py': 'VALUE = 1\n',
                   'setup.py': '# build config\n', 'pyproject.toml': '# config\n',
                   'tests/test_core.py': 'assert True\n'}
        for name, value in sources.items():
            p = self.source/name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(value)
            p.chmod(0o644)
        (self.source/'pkg/core.py').chmod(0o640)
        (self.source/'pkg/alias.py').symlink_to('core.py')
        self.store = repo_store(self.root/'objects')
        self.base = RepoBase(PublicTask('fixture-1', 'fixture/project', 'a'*40, 'public fixture'),
                             self.store.capture(self.source, exclude=('.git',)),
                             EnvironmentRef('b'*64, 'c'*64, self.root/'unused-runtime'))
        self.directory = self.root/'generated'
        self.directory.mkdir()
        self.manifest = dict(schema='repoworld.base-supplement.v1',
                             base_commit=self.base.task.base_commit,
                             base_snapshot_sha256=self.base.snapshot.id,
                             build=dict(status='success', dirty=False, artifact_sha256='d'*64,
                                        builder='fixture', command=['cc', '-shared']),
                             native_build_inputs={}, files={})
        self.add_artifact('pkg/kernel.cpython-39-x86_64-linux-gnu.so', b'\x7fELFfixture', 'native-extension', 0o755)
        self.add_artifact('pkg/_version.py', b"__version__ = version = '1.2.dev1'\n__version_tuple__ = version_tuple = (1, 2, 'dev1')\n", 'generated-version')
        self.add_artifact('pkg/generated.c', b'/* generated */\n', 'native-source')
        for path in ('pkg/kernel.pyx', 'pkg/kernel.pxd', 'pkg/include/kernel.h',
                     'pkg/generator.py', 'setup.py', 'pyproject.toml'):
            self.manifest['native_build_inputs'][path] = self.base.snapshot.manifest['entries'][path]['sha256']

    def add_artifact(self, path, data, kind, mode=0o644):
        p = self.directory/path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        p.chmod(mode)
        self.manifest['files'][path] = dict(kind=kind, sha256=sha(data), size=len(data), mode=mode)

    def apply(self, manifest=None, digest=None):
        m = self.manifest if manifest is None else manifest
        return self.api.apply_supplement(self.base, self.directory, m,
                                         sha(canonical(m)) if digest is None else digest)

    def test_capture_preserves_source_identity_links_modes_and_binds_provenance(self):
        result = self.apply()
        self.assertEqual(result.task, self.base.task)
        self.assertEqual(result.environment, self.base.environment)
        self.assertNotEqual(result.snapshot.id, self.base.snapshot.id)
        for path, entry in self.base.snapshot.manifest['entries'].items():
            self.assertEqual(result.snapshot.manifest['entries'][path], entry, path)
        self.assertTrue((result.snapshot.root/'pkg/alias.py').is_symlink())
        self.assertEqual(os.readlink(result.snapshot.root/'pkg/alias.py'), 'core.py')
        self.assertEqual(result.snapshot.manifest['entries']['pkg/core.py']['mode'], 0o640)
        self.assertEqual(result.snapshot.manifest['entries']['pkg/kernel.cpython-39-x86_64-linux-gnu.so']['mode'], 0o755)
        record = json.loads((result.snapshot.root/'.repoworld-build.json').read_bytes())
        self.assertEqual(record['manifest'], self.manifest)
        self.assertEqual(record['manifest_sha256'], sha(canonical(self.manifest)))
        self.assertEqual(self.apply().snapshot.id, result.snapshot.id)
        self.store.validate(result.snapshot)
        self.assertFalse((self.base.snapshot.root/'.repoworld-build.json').exists())
        changed = copy.deepcopy(self.manifest)
        changed['build']['builder'] = 'different build'
        self.assertNotEqual(self.apply(changed).snapshot.id, result.snapshot.id)

    def test_unicode_manifest_uses_shared_receipts_canonical_authority_hash(self):
        self.manifest['build']['builder'] = {'name': 'compilador España 日本語'}
        self.add_artifact('pkg/versión.c', b'/* generated */\n', 'native-source')
        result = self.apply()
        record = json.loads((result.snapshot.root/'.repoworld-build.json').read_bytes())
        self.assertEqual(record['manifest_sha256'], sha(canonical(self.manifest)))
        self.assertEqual(record['manifest'], self.manifest)
        self.assertIn('pkg/versión.c', self.api.supplement_protected_paths(result))

    def test_wrong_authority_base_or_dirty_build_rejected_without_advancing_head(self):
        head = (self.store.directory/'CURRENT').read_bytes()
        cases = [('base_commit', 'e'*40), ('base_snapshot_sha256', 'f'*64),
                 ('schema', 'untrusted'), ('native_build_inputs', {})]
        for key, value in cases:
            with self.subTest(key=key):
                m = copy.deepcopy(self.manifest); m[key] = value
                with self.assertRaises(ValueError): self.apply(m)
        with self.assertRaises(ValueError): self.apply(digest='0'*64)
        for key, value in [('dirty', True), ('status', 'failed'), ('modified_tracked', ['pkg/core.py']),
                           ('missing_tracked', ['setup.py'])]:
            with self.subTest(build=key):
                m = copy.deepcopy(self.manifest); m['build'][key] = value
                with self.assertRaises(ValueError): self.apply(m)
        self.assertEqual((self.store.directory/'CURRENT').read_bytes(), head)

    def test_overwrite_tracked_source_test_config_or_link_is_refused(self):
        for path in ('pkg/core.py', 'tests/test_core.py', 'setup.py', 'pkg/alias.py'):
            with self.subTest(path=path):
                self.add_artifact(path, b"version = 'bad'\n", 'generated-version')
                with self.assertRaises(ValueError): self.apply()
                (self.directory/path).unlink(); del self.manifest['files'][path]

    def test_missing_additional_ignored_and_changed_artifacts_rejected(self):
        target = self.directory/'pkg/_version.py'
        original = target.read_bytes()
        target.write_bytes(b"version = 'wrong'\n")
        with self.assertRaises(ValueError): self.apply()
        target.write_bytes(original); target.chmod(0o600)
        with self.assertRaises(ValueError): self.apply()
        target.chmod(0o644); target.unlink()
        with self.assertRaises(ValueError): self.apply()
        target.write_bytes(original)
        for path in ('pkg/extra.so', '.echoai/hidden', '__pycache__/extra.pyc', '.git/config'):
            p = self.directory/path; p.parent.mkdir(exist_ok=True)
            p.write_bytes(b'extra')
            with self.subTest(path=path), self.assertRaises(ValueError): self.apply()
            p.unlink()
            if p.parent != self.directory/'pkg': p.parent.rmdir()
        (self.directory/'unrelated-empty-directory').mkdir()
        with self.assertRaises(ValueError): self.apply()

    def test_artifact_root_parent_file_symlinks_hardlinks_and_fifo_rejected(self):
        target = self.directory/'pkg/_version.py'; original = target.read_bytes()
        outside = self.root/'outside'; outside.write_bytes(original)
        target.unlink(); target.symlink_to(outside)
        with self.assertRaises(ValueError): self.apply()
        target.unlink(); os.link(outside, target)
        with self.assertRaises(ValueError): self.apply()
        target.unlink(); os.mkfifo(target)
        with self.assertRaises(ValueError): self.apply()
        target.unlink(); target.write_bytes(original)
        alias = self.root/'alias'; alias.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.api.apply_supplement(self.base, alias, self.manifest, sha(canonical(self.manifest)))
        nested = self.root/'nested'; nested.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.api.apply_supplement(self.base, nested/'generated', self.manifest, sha(canonical(self.manifest)))

    def test_unsafe_paths_special_modes_and_undeclared_kinds_rejected(self):
        for path in ('../outside.so', '/outside.so', 'pkg/../escape.so', 'pkg//a.so',
                     'pkg\\a.so', '.repoworld-build.json', 'tests/new.so', 'new-root/a.so',
                     'pkg/alias.py/nested.so'):
            with self.subTest(path=path):
                m = copy.deepcopy(self.manifest)
                m['files'][path] = dict(kind='native-extension', sha256='a'*64, size=1, mode=0o644)
                with self.assertRaises(ValueError): self.apply(m)
        for key, value in [('kind', 'python'), ('mode', 0o4755), ('mode', True),
                           ('size', -1), ('sha256', 'BAD')]:
            with self.subTest(field=key):
                m = copy.deepcopy(self.manifest); m['files']['pkg/_version.py'][key] = value
                with self.assertRaises(ValueError): self.apply(m)

    def test_generated_python_is_literal_metadata_not_code_or_arbitrary_module(self):
        for content in (b"import os\nversion = os.system('false')\n", b"version = __import__('os')\n",
                        b"version = (lambda: 1)()\n", b"version = [x for x in ()]\n",
                        b"__builtins__ = {}\n", b"def version(): pass\n", b"version = 'x'\nraise RuntimeError\n"):
            with self.subTest(content=content):
                self.add_artifact('pkg/_version.py', content, 'generated-version')
                with self.assertRaises(ValueError): self.apply()
        self.add_artifact('pkg/_version.py', b"version = '1.2'\n", 'generated-version')
        for path, kind, data in [('pkg/evil.py', 'generated-version', b"version = '1'\n"),
                                  ('pkg/evil.py', 'native-source', b'/* c */'),
                                  ('pkg/evil.py', 'native-extension', b'\x7fELF'),
                                  ('pkg/fake.so', 'native-extension', b'not ELF')]:
            with self.subTest(path=path, kind=kind):
                self.add_artifact(path, data, kind)
                with self.assertRaises(ValueError): self.apply()
                (self.directory/path).unlink(); del self.manifest['files'][path]

    def test_version_only_pytest_supplement_does_not_require_native_inputs(self):
        source = self.root/'pytest-source'; (source/'src/_pytest').mkdir(parents=True)
        (source/'src/_pytest/__init__.py').write_text('')
        self.base = dataclasses.replace(self.base, task=dataclasses.replace(self.base.task, repo='pytest-dev/pytest'),
                                        snapshot=self.store.capture(source))
        for p in tuple(self.manifest['files']): (self.directory/p).unlink()
        (self.directory/'pkg').rmdir()
        self.manifest['files'] = {}; self.manifest['native_build_inputs'] = {}
        self.manifest['base_snapshot_sha256'] = self.base.snapshot.id
        self.add_artifact('src/_pytest/_version.py', b"__version__: str = '7.1.0'\nversion_tuple = (7, 1, 0)\n", 'generated-version')
        result = self.apply()
        self.assertEqual((result.snapshot.root/'src/_pytest/_version.py').read_bytes(), (self.directory/'src/_pytest/_version.py').read_bytes())

    def test_native_inputs_and_artifacts_are_denied_but_python_edits_roundtrip(self):
        result = self.apply()
        frozen = self.api.supplement_protected_paths(result)
        for path in ('pkg/kernel.pyx', 'pkg/kernel.pxd', 'pkg/include/kernel.h',
                     'pkg/generator.py', 'setup.py', 'pyproject.toml', 'pkg/generated.c',
                     'pkg/_version.py', 'pkg/kernel.cpython-39-x86_64-linux-gnu.so', '.repoworld-build.json'):
            with self.subTest(path=path):
                self.assertIn(path, frozen)
                with self.assertRaises(ValueError): self.api.supplement_production_path(result, path)
                old = (result.snapshot.root/path).read_text(errors='replace')
                with self.assertRaises(ValueError):
                    stage_patch(result, result.snapshot, patch_text(path, old, 'modified\n'),
                                expected_snapshot_id=result.snapshot.id, purpose='solution')
        with self.assertRaises(ValueError): self.api.supplement_production_path(result, 'pkg/new.pyx')
        mounted = protected_paths(result.snapshot.manifest['entries'], snapshot=result.snapshot)
        self.assertIn('pkg/generator.py', mounted)
        self.assertIn('.repoworld-build.json', mounted)
        self.assertIn('pkg/kernel.pyx', mounted)
        self.assertNotIn('pkg/core.py', mounted)
        self.assertNotIn('pkg/alias.py', mounted)
        self.assertTrue(self.api.supplement_production_path(result, 'pkg/core.py'))
        session = Workspace(self.root/'session', result)
        diff = patch_text('pkg/core.py', 'value = 1\n', 'value = 2\n')
        candidate = session.stage(diff, session.current.id)
        self.assertEqual(session._export_diff(candidate.snapshot), diff)
        self.assertEqual((candidate.snapshot.root/'pkg/kernel.cpython-39-x86_64-linux-gnu.so').read_bytes(), b'\x7fELFfixture')
        reopened = Workspace(session.directory)
        self.assertIn('pkg/generator.py', self.api.supplement_protected_paths(reopened.base))

    def test_native_module_python_shadow_and_package_creation_are_rejected(self):
        result = self.apply()
        for path in ('pkg/kernel.py', 'pkg/kernel/__init__.py'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.api.supplement_production_path(result, path)
            with self.subTest(stage=path), self.assertRaises(ValueError):
                diff = patch_text(path, '', 'value = 2\n').replace('--- a/'+path, '--- /dev/null')
                stage_patch(result, result.snapshot, diff,
                            expected_snapshot_id=result.snapshot.id, purpose='solution')

    def test_pure_python_native_source_requires_frozen_input_declaration(self):
        (self.source/'pkg/kernel.py').write_text('value = 1\n')
        self.base = dataclasses.replace(self.base, snapshot=self.store.capture(self.source))
        self.manifest['base_snapshot_sha256'] = self.base.snapshot.id
        with self.assertRaises(ValueError): self.apply()
        self.manifest['native_build_inputs']['pkg/kernel.py'] = sha(b'value = 1\n')
        result = self.apply()
        with self.assertRaises(ValueError): self.api.supplement_production_path(result, 'pkg/kernel.py')

    def test_snapshot_exclusions_cannot_silently_drop_authorized_artifacts(self):
        self.base = dataclasses.replace(self.base, snapshot=self.store.capture(self.source, exclude=('_version.py',)))
        self.manifest['base_snapshot_sha256'] = self.base.snapshot.id
        with self.assertRaises(ValueError): self.apply()

    def test_manifest_generator_inventories_actual_bytes_without_authorizing_them(self):
        self.assertTrue(hasattr(self.api, 'build_supplement_manifest'), 'supervisor manifest generator required')
        result = self.api.build_supplement_manifest(self.base, self.directory,
            build=self.manifest['build'], extra_build_inputs=('pkg/generator.py',))
        self.assertEqual(result, self.manifest)
        self.assertEqual(self.apply(result).snapshot.id, self.apply().snapshot.id)
        self.add_artifact('pkg/evil.py', b'import os\n', 'generated-version')
        with self.assertRaises(ValueError):
            self.api.build_supplement_manifest(self.base, self.directory,
                build=self.manifest['build'], extra_build_inputs=('pkg/generator.py',))

    def test_source_alias_cannot_bypass_frozen_input_protection(self):
        result = self.apply()
        with self.assertRaises(ValueError):
            self.api.supplement_production_path(result, 'pkg/alias.py')

    def test_native_base_alias_freezes_real_input_without_mounting_alias(self):
        (self.source/'pkg/alternate.pyx').symlink_to('core.py')
        self.base = dataclasses.replace(self.base, snapshot=self.store.capture(self.source))
        self.manifest['base_snapshot_sha256'] = self.base.snapshot.id
        inputs = self.api.native_build_inputs(self.base)
        self.assertIn('pkg/core.py', inputs)
        self.assertNotIn('pkg/alternate.pyx', inputs)
        with self.assertRaises(ValueError): self.apply()
        self.manifest['native_build_inputs']['pkg/core.py'] = sha(b'value = 1\n')
        result = self.apply()
        mounted = protected_paths(result.snapshot.manifest['entries'], snapshot=result.snapshot)
        self.assertIn('pkg', mounted)  # alias parent must itself be immutable
        self.assertNotIn('pkg/alternate.pyx', mounted)
        with self.assertRaises(ValueError): self.api.supplement_production_path(result, 'pkg/core.py')

    def test_public_test_link_target_cannot_be_staged_without_supplement(self):
        (self.source/'tests/test_public.py').symlink_to('../pkg/core.py')
        base = dataclasses.replace(self.base, snapshot=self.store.capture(self.source))
        session = Workspace(self.root/'public-link-workspace', base)
        with self.assertRaises(ValueError):
            session.stage(patch_text('pkg/core.py', 'value = 1\n', 'value = 2\n'), session.current.id)
        self.assertIn('pkg/core.py', protected_paths(base.snapshot.manifest['entries'], snapshot=base.snapshot))
        with self.assertRaises(ValueError): self.api.supplement_production_path(base, 'pkg/core.py')

    def test_native_alias_target_cannot_be_staged_without_provenance(self):
        (self.source/'pkg/alternate.pyx').symlink_to('core.py')
        base = dataclasses.replace(self.base, snapshot=self.store.capture(self.source))
        session = Workspace(self.root/'native-link-workspace', base)
        with self.assertRaises(ValueError):
            session.stage(patch_text('pkg/core.py', 'value = 1\n', 'value = 2\n'), session.current.id)
        mounted = protected_paths(base.snapshot.manifest['entries'], snapshot=base.snapshot)
        self.assertIn('pkg', mounted)  # alias parent must itself be immutable
        self.assertNotIn('pkg/alternate.pyx', mounted)

    def test_protected_link_directory_closure_is_transitive_and_does_not_freeze_docs(self):
        (self.source/'public_data').mkdir()
        (self.source/'public_data/reference.txt').write_text('fixture\n')
        (self.source/'public_data/next').symlink_to('../pkg/core.py')
        (self.source/'tests/fixtures').symlink_to('../public_data')
        (self.source/'docs').mkdir()
        (self.source/'docs/source_alias').symlink_to('../pkg/generator.py')
        base = dataclasses.replace(self.base, snapshot=self.store.capture(self.source))
        session = Workspace(self.root/'directory-link-workspace', base)
        for path, before in (('pkg/core.py', 'value = 1\n'),
                             ('public_data/reference.txt', 'fixture\n')):
            with self.subTest(path=path), self.assertRaises(ValueError):
                session.stage(patch_text(path, before, 'changed\n'), session.current.id)
        with self.assertRaises(ValueError):
            diff = patch_text('public_data/new.py', '', 'value = 2\n').replace(
                '--- a/public_data/new.py', '--- /dev/null')
            session.stage(diff, session.current.id)
        mounted = protected_paths(base.snapshot.manifest['entries'], snapshot=base.snapshot)
        self.assertIn('public_data', mounted)
        self.assertIn('pkg/core.py', mounted)
        self.assertNotIn('docs', mounted)
        self.assertNotIn('pkg/generator.py', mounted)
        candidate = session.stage(patch_text('pkg/generator.py', 'VALUE = 1\n', 'VALUE = 2\n'), session.current.id)
        self.assertEqual((candidate.snapshot.root/'pkg/generator.py').read_text(), 'VALUE = 2\n')

    def test_protected_link_chain_freezes_canonical_target_and_intermediate_route(self):
        (self.source/'routing').mkdir()
        (self.source/'routing/bridge').symlink_to('../pkg/core.py')
        (self.source/'tests/test_chain.py').symlink_to('../routing/bridge')
        base = dataclasses.replace(self.base, snapshot=self.store.capture(self.source))
        mounted = protected_paths(base.snapshot.manifest['entries'], snapshot=base.snapshot)
        self.assertIn('pkg/core.py', mounted)
        self.assertIn('routing', mounted)
        self.assertNotIn('routing/bridge', mounted)
        self.assertNotIn('pkg', mounted)

    def test_protected_link_to_workspace_root_fails_closed(self):
        (self.source/'tests/everything').symlink_to('..')
        base = dataclasses.replace(self.base, snapshot=self.store.capture(self.source))
        with self.assertRaisesRegex(ValueError, 'root'):
            protected_paths(base.snapshot.manifest['entries'], snapshot=base.snapshot)
        with self.assertRaises(ValueError):
            stage_patch(base, base.snapshot, patch_text('pkg/core.py', 'value = 1\n', 'value = 2\n'),
                        expected_snapshot_id=base.snapshot.id, purpose='solution')

    def test_protected_chain_with_root_level_intermediate_alias_fails_closed(self):
        (self.source/'bridge').symlink_to('pkg/core.py')
        (self.source/'tests/test_chain.py').symlink_to('../bridge')
        base = dataclasses.replace(self.base, snapshot=self.store.capture(self.source))
        with self.assertRaisesRegex(ValueError, 'root'):
            protected_paths(base.snapshot.manifest['entries'], snapshot=base.snapshot)

    def test_standalone_public_test_link_requires_protected_ancestor(self):
        entries = {'.': {'type': 'directory'},
                   'test_public.py': {'type': 'symlink', 'target': 'pkg/core.py'},
                   'pkg': {'type': 'directory'},
                   'pkg/core.py': {'type': 'file'}}
        with self.assertRaisesRegex(ValueError, 'protected.*(symlink|link)'):
            protected_paths(entries)
        self.assertEqual(protected_paths({
            'tests': {'type': 'directory'},
            'tests/test_alias.py': {'type': 'symlink', 'target': '../pkg/core.py'},
            'pkg': {'type': 'directory'},
            'pkg/core.py': {'type': 'file'},
            'docs/image': {'type': 'symlink', 'target': '../image'},
            'pkg/alias.py': {'type': 'symlink', 'target': 'core.py'},
        }), ['tests', 'pkg/core.py'])

    def test_native_build_input_hash_and_record_tampering_rejected(self):
        m = copy.deepcopy(self.manifest); m['native_build_inputs']['pkg/kernel.pyx'] = 'e'*64
        with self.assertRaises(ValueError): self.apply(m)
        result = self.apply()
        marker = result.snapshot.root/'.repoworld-build.json'; marker.chmod(0o644)
        record = json.loads(marker.read_bytes()); record['manifest']['native_build_inputs'] = {}
        marker.write_bytes(canonical(record)); marker.chmod(0o444)
        with self.assertRaises(ValueError): self.api.supplement_protected_paths(result)


if __name__ == '__main__':
    unittest.main()
