import os
from pathlib import Path
import tempfile
import unittest
try:
    from .repoworld_support import ROOT
except ImportError:
    from repoworld_support import ROOT
from echoai.pcworld.snapshots import SnapshotError, SnapshotStore
from echoai.repoworld.environment import repo_store


class RepoLinksTests(unittest.TestCase):
    def test_internal_links_survive_capture_edit_and_import_without_dereferencing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'src';(src/'nested').mkdir(parents=True)
            (src/'value.py').write_text('value = 1\n')
            (src/'nested/alias.py').symlink_to('../value.py')
            (src/'second.py').symlink_to('nested/alias.py')
            store=repo_store(root/'store');snap=store.capture(src)
            self.assertTrue((snap.root/'nested/alias.py').is_symlink())
            self.assertEqual(os.readlink(snap.root/'nested/alias.py'),'../value.py')
            self.assertEqual((snap.root/'second.py').read_text(),'value = 1\n')
            self.assertEqual(snap.manifest['entries']['second.py']['type'],'symlink')
            updated=store.apply(snap,snap.id,[dict(path='value.py',expected_sha256=snap.manifest['entries']['value.py']['sha256'],content='value = 2\n')],allowed_paths=('value.py',))
            self.assertEqual((updated.root/'second.py').read_text(),'value = 2\n')
            imported=repo_store(root/'other').capture(updated)
            self.assertEqual(imported.id,updated.id)
            with self.assertRaises(SnapshotError):
                SnapshotStore(root/'default').capture(src)
            with self.assertRaises(SnapshotError):
                SnapshotStore(root/'default').capture(updated)

    def test_escape_cycle_dangling_and_link_parent_edits_rejected(self):
        for destination in ('/etc/passwd','../../outside','loop','missing','dir/up/../../outside'):
            with self.subTest(destination=destination),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);src=root/'src';(src/'dir').mkdir(parents=True)
                (src/'dir/up').symlink_to('..')
                (src/'loop').symlink_to(destination)
                with self.assertRaises(SnapshotError): repo_store(root/'store').capture(src)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'src';(src/'dir').mkdir(parents=True)
            (src/'dir/value.py').write_text('ok')
            (src/'alias').symlink_to('dir')
            store=repo_store(root/'store');snap=store.capture(src)
            with self.assertRaises(SnapshotError):
                store.apply(snap,snap.id,[dict(path='alias/new.py',expected_sha256=None,content='bad')],allowed_paths=('alias/new.py',))
            with self.assertRaises(SnapshotError):
                store.read(snap,'alias/value.py')

    def test_link_tampering_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'src';src.mkdir();(src/'a').write_text('a');(src/'b').write_text('b')
            (src/'link').symlink_to('a');store=repo_store(root/'store');snap=store.capture(src)
            snap.root.chmod(0o755);(snap.root/'link').unlink();(snap.root/'link').symlink_to('b');snap.root.chmod(0o555)
            with self.assertRaises(SnapshotError):store.validate(snap)

    def test_hardlinked_symlinks_are_not_admitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);src=root/'src';src.mkdir();(src/'a').write_text('a')
            (src/'one').symlink_to('a');os.link(src/'one',src/'two',follow_symlinks=False)
            self.assertEqual((src/'one').lstat().st_nlink,2)
            with self.assertRaises(SnapshotError):repo_store(root/'store').capture(src)

if __name__=='__main__':unittest.main()
