import tempfile
import unittest
from pathlib import Path
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.repoworld.dependencies import freeze_dependencies, dependency_runtime
from echoai.repoworld.environment import environment_ref


class DependencyTests(unittest.TestCase):
    def test_wheels_manifest_is_byte_identity_and_rejects_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'module.py').write_text('x=1\n')
            a=freeze_dependencies(p)
            self.assertEqual(a,freeze_dependencies(p))
            (p/'module.py').write_text('x=2\n')
            self.assertNotEqual(a,freeze_dependencies(p))
            (p/'link').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError): freeze_dependencies(p)

    def test_third_party_runtime_requires_provenance(self):
        from echoai.pcworld.runtime import load_runtime,repository_runtime
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);deps=p/'deps';deps.mkdir();(deps/'sentinel_dependency.py').write_text('value=67\n')
            stdlib=load_runtime(ROOT/'repository/artifacts/runtime-python314-20261013')
            runtime=dependency_runtime(stdlib,deps,p/'runtime',expected_manifest=freeze_dependencies(deps))
            ref=environment_ref(runtime,scope='public-dependencies')
            self.assertEqual(ref.rootfs_sha256,runtime.id)
            with self.assertRaises(ValueError): dependency_runtime(stdlib,deps,p/'bad',expected_manifest={})

    def test_production_only_patch_and_readonly_tests(self):
        from echoai.repoworld.workspace import production_path, protected_paths
        self.assertTrue(production_path('pallets/flask','src/flask/app.py'))
        for path in ('README.md','src/flask/test_fake.py','tests/test_basic.py','setup.py'):
            with self.assertRaises(ValueError): production_path('pallets/flask',path)
        self.assertEqual(protected_paths({'tests':{},'tests/a.py':{},'src/test_x.py':{},'src/ok.py':{}}),['tests','src/test_x.py'])

