"""Protected mounts cannot be displaced by moving an editable ancestor."""
import json
from dataclasses import replace
import textwrap
import unittest
try:
    from . import test_repoworld_supplement_integration as fixture
except ImportError:
    import test_repoworld_supplement_integration as fixture
from echoai.repoworld.environment import execute_repo, repo_store
from echoai.repoworld.supplements import apply_supplement


class DirectoryProtectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.SupplementIntegrationTests.setUpClass.__func__(cls)

    def setUp(self):
        fixture.SupplementIntegrationTests.setUp(self)

    def test_ancestor_cannot_move_but_scratch_and_python_remain_mutable(self):
        base = apply_supplement(self.base, self.generated, self.manifest, self.digest)
        code = textwrap.dedent('''\
            import ctypes, json, os
            from pathlib import Path
            blocked = []
            for target in ('pkg_moved', '.tmp/pkg_moved'):
                try: os.rename('pkg', target)
                except OSError: blocked.append(target)
                else: raise AssertionError('protected ancestor moved: ' + target)
            Path('replacement').mkdir()
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.renameat2(-100, b'pkg', -100, b'replacement', 2) == 0:
                raise AssertionError('protected ancestor exchanged')
            blocked.append('exchange')
            Path('pkg/core.py').write_text('value = 7')
            assert Path('pkg/core.py').read_text() == 'value = 7'
            for root in ('.tmp', '.home', '.out', '.shm'):
                p = Path(root) / 'disposable'
                p.mkdir(); p.rename(p.with_name('moved')); p.with_name('moved').rmdir()
            print(json.dumps({'blocked': blocked, 'scratch_cleanup': True}))
        ''')
        result = execute_repo(base, base.snapshot, ('/usr/bin/python3', '-I', '-B', '-c', code),
                              limits={}, check_artifacts=())
        self.assertEqual(result['exit_code'], 0, result)
        self.assertTrue(json.loads(result['stdout'])['scratch_cleanup'])
        self.assertEqual(len(json.loads(result['stdout'])['blocked']), 3)
        self.assertTrue(result['isolation']['job_empty'])

    def test_reserved_scratch_names_rejected_in_base_and_candidate(self):
        for name in ('.tmp', '.home', '.out', '.shm'):
            source = self.root / ('collision-' + name[1:])
            (source / name / 'pkg').mkdir(parents=True)
            (source / name / 'pkg/input.pyx').write_text('protected input')
            snapshot = repo_store(self.root / ('objects-' + name[1:])).capture(source)
            for base in (self.base, replace(self.base, snapshot=snapshot)):
                with self.subTest(name=name, in_base=base is not self.base):
                    with self.assertRaisesRegex(ValueError, 'reserved scratch'):
                        execute_repo(base, snapshot, ('/usr/bin/python3', '-c', 'print("must not run")'),
                                     limits={}, check_artifacts=())


if __name__ == '__main__': unittest.main()
