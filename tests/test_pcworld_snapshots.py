"""PCWORLD T03/T07/T08: real filesystem capabilities, races and atomic patches."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import multiprocessing
import os
from pathlib import Path
import socket
import stat
import tempfile
import tracemalloc
import unittest
from unittest.mock import patch

from pcworld import snapshots


def sha(data):
    return hashlib.sha256(data).hexdigest()


def competing_writer(directory, base, barrier, queue, content):
    try:
        store = snapshots.SnapshotStore(directory)
        barrier.wait(timeout=10)
        result = store.apply(base, base.id, [
            {"path": "a.txt", "expected_sha256": sha(b"alpha"), "content": content}
        ], allowed_paths=("a.txt",))
        queue.put(("OK", result.id))
    except Exception as error:
        queue.put((getattr(error, "code", type(error).__name__), str(error)))


@unittest.skipUnless(os.name == "posix", "descriptor capabilities require POSIX")
class TestSnapshots(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pcworld-snapshot-test-")
        # TemporaryDirectory itself must handle sealed directories during cleanup.
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.source = self.directory / "source"
        self.source.mkdir(mode=0o755)
        self.source.chmod(0o755)
        (self.source / "a.txt").write_bytes(b"alpha")
        (self.source / "a.txt").chmod(0o644)
        self.store = snapshots.SnapshotStore(self.directory / "store")

    def edit(self, content="bravo", path="a.txt", expected=sha(b"alpha")):
        return {"path": path, "expected_sha256": expected, "content": content}

    def assert_code(self, code, operation):
        with self.assertRaises(snapshots.SnapshotError) as result:
            operation()
        self.assertEqual(result.exception.code, code)

    def identity(self, snapshot_id, **changes):
        context = dict(snapshot_id=snapshot_id, environment={"python": "3", "dep": "aaa"},
                       action={"argv": ["python3", "main.py"]}, checks={"suite": "bbb"},
                       policy={"contract": "ccc"}, seed=7, dataset={"sha256": "ddd"}, task="one")
        context.update(changes)
        return snapshots.identity(**context)

    def test_capture_full_bytes_empty_directories_and_source_modes(self):
        data = bytes(range(256)) * 1024 + b"\x00end"
        (self.source / "binary").write_bytes(data)
        (self.source / "empty").mkdir(mode=0o751)
        (self.source / "empty").chmod(0o751)
        base = self.store.capture(self.source)
        self.assertRegex(base.id, r"^[0-9a-f]{64}$")
        self.assertEqual(self.store.read(base, "binary"), data)
        self.assertTrue((base.root / "empty").is_dir())
        self.assertEqual(base.manifest["entries"]["empty"], {"type": "directory", "mode": 0o751})
        self.assertEqual(base.manifest["entries"]["a.txt"]["mode"], 0o644)
        self.assertEqual(base.manifest["entries"]["binary"]["sha256"], sha(data))

    def test_snapshot_and_nested_manifest_are_immutable(self):
        base = self.store.capture(self.source)
        self.assertIsInstance(base.manifest, dict)
        with self.assertRaises(FrozenInstanceError):
            base.id = "changed"
        with self.assertRaises(TypeError):
            base.manifest["entries"]["a.txt"]["sha256"] = "changed"
        with self.assertRaises(TypeError):
            base.manifest["entries"].clear()
        with self.assertRaises((AttributeError, TypeError)):
            base.manifest["exclude"].append("secret")
        self.assertEqual(self.store.read(base, "a.txt"), b"alpha")

    def test_snapshot_seals_root_directories_and_files_and_retains_executable(self):
        (self.source / "bin").mkdir()
        (self.source / "bin" / "tool").write_text("not executed")
        (self.source / "bin" / "tool").chmod(0o751)
        base = self.store.capture(self.source)
        for path in [base.root, base.root / "bin", base.root / "a.txt", base.root / "bin/tool"]:
            self.assertEqual(stat.S_IMODE(path.stat().st_mode) & 0o222, 0)
        self.assertEqual((base.root / "bin/tool").stat().st_mode & 0o111, 0o111)
        self.assertEqual((self.source / "a.txt").stat().st_mode & 0o777, 0o644)
        self.temp.cleanup()
        self.assertFalse(self.directory.exists())

    def test_t07_equal_head_dirty_count_and_length_do_not_alias_contents(self):
        (self.source / ".git").mkdir()
        (self.source / ".git/HEAD").write_text("same-head")
        base = self.store.capture(self.source)
        (self.source / "a.txt").write_bytes(b"bravo")
        other = self.store.capture(self.source)
        self.assertNotEqual(base.id, other.id)
        self.assertNotEqual(self.identity(base.id), self.identity(other.id))
        self.assertEqual(self.store.read(base, "a.txt"), b"alpha")

    def test_t08_each_full_context_fingerprint_invalidates_identity(self):
        base = self.store.capture(self.source)
        original = self.identity(base.id)
        for changes in ({"environment": {"python": "3", "dep": "changed"}},
                        {"checks": {"suite": "changed"}}, {"policy": {"contract": "changed"}},
                        {"dataset": {"sha256": "changed"}}, {"seed": 8}, {"task": "two"},
                        {"action": {"argv": ["python3", "other.py"]}}):
            with self.subTest(changes=changes):
                self.assertNotEqual(self.identity(base.id, **changes), original)
        self.assertEqual(original, self.identity(base.id, environment={"dep": "aaa", "python": "3"}))

    def test_identity_rejects_lossy_or_noncanonical_values_and_short_hashes(self):
        base = self.store.capture(self.source)
        for value in ({1: "ambiguous"}, {"x": float("nan")}, {"x": float("inf")}, {"x": {1, 2}},
                      {"x": Path("file")}, {"x": b"bytes"}):
            with self.subTest(value=value), self.assertRaises((ValueError, TypeError)):
                self.identity(base.id, environment=value)
        with self.assertRaises(ValueError):
            self.identity("1234")

    def test_modes_directory_names_and_untracked_content_affect_tree_identity(self):
        previous = self.store.capture(self.source).id
        changes = [lambda: (self.source / "a.txt").chmod(0o600),
                   lambda: self.source.chmod(0o750),
                   lambda: (self.source / "empty").mkdir(),
                   lambda: (self.source / "empty").rename(self.source / "renamed"),
                   lambda: (self.source / "untracked").write_bytes(b"new")]
        for change in changes:
            change()
            current = self.store.capture(self.source).id
            self.assertNotEqual(current, previous)
            previous = current

    def test_only_declared_exclusions_are_ignored_and_policy_is_fingerprinted(self):
        for name in (".git", ".echoai", "__pycache__"):
            (self.source / name).mkdir()
            (self.source / name / "data").write_bytes(b"first")
        base = self.store.capture(self.source)
        for name in (".git", ".echoai", "__pycache__"):
            (self.source / name / "data").write_bytes(b"second")
            self.assertFalse((base.root / name).exists())
        self.assertEqual(base.id, self.store.capture(self.source).id)
        self.assertNotEqual(base.id, self.store.capture(self.source, exclude=(".echoai",)).id)

    def test_candidate_python_is_copied_without_import_or_execution(self):
        marker = self.directory / "executed"
        program = f"from pathlib import Path\nPath({str(marker)!r}).touch()\nraise SystemExit(99)\n"
        (self.source / "sitecustomize.py").write_text(program)
        (self.source / "__init__.py").write_text(program)
        base = self.store.capture(self.source)
        self.assertEqual(self.store.read(base, "sitecustomize.py"), program.encode())
        self.assertFalse(marker.exists())

    def test_t03_rejects_symlinks_hardlinks_and_specials_including_excluded_aliases(self):
        neighbor = self.directory / "neighbor"
        neighbor.write_bytes(b"private")
        for name in ("link", ".git", ".echoai", "__pycache__"):
            path = self.source / name
            for kind in ("symlink", "hardlink", "fifo"):
                with self.subTest(name=name, kind=kind):
                    if kind == "symlink":
                        path.symlink_to(neighbor)
                    elif kind == "hardlink":
                        os.link(neighbor, path)
                    else:
                        os.mkfifo(path)
                    try:
                        with self.assertRaises(snapshots.SnapshotError):
                            self.store.capture(self.source)
                    finally:
                        path.unlink()
        self.assertEqual(neighbor.read_bytes(), b"private")

    def test_excluded_directory_descendants_are_audited_without_following_links(self):
        (self.source / ".git").mkdir()
        (self.source / ".git/nested").mkdir()
        (self.source / ".git/nested/alias").symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(snapshots.SnapshotError):
            self.store.capture(self.source)

    def test_unix_socket_is_rejected_without_opening_it(self):
        with socket.socket(socket.AF_UNIX) as sock:
            sock.bind(str(self.source / "socket"))
            with self.assertRaises(snapshots.SnapshotError):
                self.store.capture(self.source)

    def test_source_and_store_ancestor_symlinks_are_rejected(self):
        alias = self.directory / "alias"
        alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(snapshots.SnapshotError):
            self.store.capture(alias)
        with self.assertRaises(snapshots.SnapshotError):
            snapshots.SnapshotStore(alias / "new-store")
        self.assertFalse((self.source / "new-store").exists())

    def test_store_must_be_outside_source_even_if_its_name_is_excluded(self):
        nested = snapshots.SnapshotStore(self.source / ".echoai")
        with self.assertRaises(snapshots.SnapshotError):
            nested.capture(self.source)
        with self.assertRaises(snapshots.SnapshotError):
            self.store.capture(self.store.directory)

    def test_t03_read_rejects_path_escapes_and_forged_snapshot_capabilities(self):
        base = self.store.capture(self.source)
        for relative in ("../neighbor", "/etc/passwd", "a.txt/../a.txt", "./a.txt", "a.txt/", "", "x//y", "x\\y", "a\x00b"):
            with self.subTest(relative=relative), self.assertRaises(snapshots.SnapshotError):
                self.store.read(base, relative)
        forged = snapshots.Snapshot(base.id, self.source, base.manifest)
        with self.assertRaises(snapshots.SnapshotError):
            self.store.read(forged, "a.txt")

    def test_t03_same_size_write_with_restored_mtime_during_read_is_rejected(self):
        target = self.source / "a.txt"
        before = target.stat()
        original_read = os.read
        changed = False

        def racing_read(fd, count):
            nonlocal changed
            data = original_read(fd, count)
            if not changed and os.fstat(fd).st_ino == before.st_ino:
                changed = True
                target.write_bytes(b"bravo")
                os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            return data

        with patch("pcworld.snapshots.os.read", side_effect=racing_read):
            self.assert_code("RACE_DETECTED", lambda: self.store.capture(self.source))
        self.assertTrue(changed)
        self.assertFalse((self.store.directory / "CURRENT").exists())

    def test_file_already_read_is_rechecked_before_capture_publication(self):
        (self.source / "z.txt").write_bytes(b"last")
        last_inode = (self.source / "z.txt").stat().st_ino
        original_read = os.read
        changed = False

        def racing_read(fd, count):
            nonlocal changed
            data = original_read(fd, count)
            if not changed and os.fstat(fd).st_ino == last_inode:
                changed = True
                (self.source / "a.txt").write_bytes(b"bravo")
            return data

        with patch("pcworld.snapshots.os.read", side_effect=racing_read):
            self.assert_code("RACE_DETECTED", lambda: self.store.capture(self.source))
        self.assertTrue(changed)

    def test_t03_directory_swapped_for_symlink_between_stat_and_open(self):
        child = self.source / "child"
        child.mkdir()
        (child / "inside").write_bytes(b"inside")
        neighbor = self.directory / "neighbor"
        neighbor.mkdir()
        (neighbor / "secret").write_bytes(b"outside")
        original_open = os.open
        original_read = os.read
        changed = False
        outside_reads = []
        secret_inode = (neighbor / "secret").stat().st_ino

        def racing_open(path, flags, mode=0o777, *, dir_fd=None):
            nonlocal changed
            if not changed and str(path) == "child" and dir_fd is not None:
                changed = True
                child.rename(self.source / "moved")
                child.symlink_to(neighbor, target_is_directory=True)
            return original_open(path, flags, mode, dir_fd=dir_fd)

        def observed_read(fd, count):
            if os.fstat(fd).st_ino == secret_inode:
                outside_reads.append(fd)
            return original_read(fd, count)

        with patch("pcworld.snapshots.os.open", side_effect=racing_open), patch("pcworld.snapshots.os.read", side_effect=observed_read):
            with self.assertRaises(snapshots.SnapshotError):
                self.store.capture(self.source)
        self.assertTrue(changed)
        self.assertEqual(outside_reads, [])

    def test_reuse_read_and_apply_validate_preexisting_snapshot_hashes(self):
        base = self.store.capture(self.source)
        target = base.root / "a.txt"
        target.chmod(0o644)
        target.write_bytes(b"bravo")
        target.chmod(0o444)
        for operation in (lambda: self.store.capture(self.source),
                          lambda: self.store.read(base, "a.txt"),
                          lambda: self.store.apply(base, base.id, [self.edit()], allowed_paths=("a.txt",))):
            with self.subTest(operation=operation), self.assertRaises(snapshots.SnapshotError):
                operation()
        self.assertEqual((self.source / "a.txt").read_bytes(), b"alpha")

    def test_read_rejects_snapshot_symlink_and_writable_mode_tampering(self):
        base = self.store.capture(self.source)
        target = base.root / "a.txt"
        target.chmod(0o644)
        with self.assertRaises(snapshots.SnapshotError):
            self.store.read(base, "a.txt")
        target.chmod(0o444)
        base.root.chmod(0o755)
        target.unlink()
        target.symlink_to(self.source / "a.txt")
        base.root.chmod(0o555)
        with self.assertRaises(snapshots.SnapshotError):
            self.store.read(base, "a.txt")

    def test_file_byte_entry_and_depth_limits_fail_before_publication(self):
        (self.source / "second").write_bytes(b"six")
        for limits in ({"max_files": 1}, {"max_bytes": 7}, {"max_entries": 1}):
            with self.subTest(limits=limits):
                store = snapshots.SnapshotStore(self.directory / ("limit-" + next(iter(limits))), **limits)
                self.assert_code("LIMIT_EXCEEDED", lambda: store.capture(self.source))
                self.assertFalse((store.directory / "CURRENT").exists())
        (self.source / "deep").mkdir()
        (self.source / "deep/nested").mkdir()
        shallow = snapshots.SnapshotStore(self.directory / "shallow", max_depth=1)
        self.assert_code("LIMIT_EXCEEDED", lambda: shallow.capture(self.source))

    def test_patch_update_create_delete_is_atomic_and_keeps_base_bytes(self):
        (self.source / "delete").write_bytes(b"remove")
        base = self.store.capture(self.source)
        edits = [self.edit("café"), self.edit("new", "new/created", None), self.edit(None, "delete", sha(b"remove"))]
        result = self.store.apply(base, base.id, edits, allowed_paths=("a.txt", "new/created", "delete"))
        self.assertEqual(self.store.read(result, "a.txt"), "café".encode())
        self.assertEqual(self.store.read(result, "new/created"), b"new")
        self.assertFalse((result.root / "delete").exists())
        self.assertEqual(self.store.read(base, "a.txt"), b"alpha")
        self.assertEqual(self.store.read(base, "delete"), b"remove")
        self.assertEqual((self.source / "a.txt").read_bytes(), b"alpha")
        self.assertEqual(result.manifest["entries"]["a.txt"]["mode"], 0o644)

    def test_wrong_expected_base_or_file_hash_is_stale_and_has_no_effect(self):
        base = self.store.capture(self.source)
        for expected, edits in (("0" * 64, [self.edit()]), (base.id, [self.edit(expected="0" * 64)])):
            self.assert_code("STALE_BASE", lambda: self.store.apply(base, expected, edits, allowed_paths=("a.txt",)))
        self.assertEqual(self.store.read(base, "a.txt"), b"alpha")
        result = self.store.apply(base, base.id, [self.edit()], allowed_paths=("a.txt",))
        self.assertEqual(self.store.read(result, "a.txt"), b"bravo")

    def test_current_version_is_compared_across_stores_and_restarts(self):
        base = self.store.capture(self.source)
        reopened = snapshots.SnapshotStore(self.store.directory)
        current = reopened.apply(base, base.id, [self.edit()], allowed_paths=("a.txt",))
        self.assert_code("STALE_BASE", lambda: self.store.apply(base, base.id, [self.edit("other")], allowed_paths=("a.txt",)))
        restarted = snapshots.SnapshotStore(self.store.directory)
        self.assert_code("STALE_BASE", lambda: restarted.apply(base, base.id, [], allowed_paths=()))
        self.assertEqual(restarted.read(current, "a.txt"), b"bravo")

    def test_bad_edit_batch_never_partially_changes_base_or_current(self):
        base = self.store.capture(self.source)
        initial_files = sorted(p.name for p in self.store.directory.iterdir())
        bad_edits = [self.edit("bad", "../neighbor", None), self.edit(b"bytes"),
                     self.edit("bad", "a.txt", "0" * 64), self.edit(None, "absent", None),
                     {"path": "x", "content": "missing precondition"},
                     self.edit("bad", "a.txt/nested", None)]
        for bad in bad_edits:
            with self.subTest(edit=bad), self.assertRaises(snapshots.SnapshotError):
                self.store.apply(base, base.id, [self.edit("new", "new", None), bad],
                                 allowed_paths=("a.txt", "new", "absent", "a.txt/nested"))
            self.assertEqual(sorted(p.name for p in self.store.directory.iterdir()), initial_files)
            self.assertEqual(self.store.read(base, "a.txt"), b"alpha")
        self.store.apply(base, base.id, [self.edit()], allowed_paths=("a.txt",))

    def test_duplicate_edits_and_implicit_wildcard_permissions_are_denied(self):
        base = self.store.capture(self.source)
        with self.assertRaises(snapshots.SnapshotError):
            self.store.apply(base, base.id, [self.edit(), self.edit()], allowed_paths=("a.txt",))
        with self.assertRaises(snapshots.SnapshotError):
            self.store.apply(base, base.id, [self.edit()], allowed_paths=("*",))

    def test_protected_paths_need_exact_capability_and_echoai_is_always_denied(self):
        for name in (".git", "contracts", "tests", ".echoai"):
            (self.source / name).mkdir()
            (self.source / name / "data").write_bytes(b"old")
        base = self.store.capture(self.source, exclude=())
        for path in (".git/data", "contracts/data", "tests/data"):
            with self.assertRaises(snapshots.SnapshotError):
                self.store.apply(base, base.id, [self.edit("new", path, sha(b"old"))], allowed_paths=("*",))
        for path in (".echoai/data", "nested/.echoai/data"):
            with self.assertRaises(snapshots.SnapshotError):
                self.store.apply(base, base.id, [self.edit("new", path, None)], allowed_paths=(path,))
        allowed = self.store.apply(base, base.id, [self.edit("new", "tests/data", sha(b"old"))], allowed_paths=("tests/data",))
        self.assertEqual(self.store.read(allowed, "tests/data"), b"new")

    def test_patch_byte_limit_preserves_current(self):
        store = snapshots.SnapshotStore(self.directory / "small", max_bytes=5)
        base = store.capture(self.source)
        self.assert_code("LIMIT_EXCEEDED", lambda: store.apply(base, base.id, [self.edit("too big")], allowed_paths=("a.txt",)))
        self.assertEqual(store.read(base, "a.txt"), b"alpha")
        self.assertEqual(store.apply(base, base.id, [self.edit()], allowed_paths=("a.txt",)).root.joinpath("a.txt").read_bytes(), b"bravo")

    def test_two_process_writers_get_one_winner_one_stale(self):
        base = self.store.capture(self.source)
        context = multiprocessing.get_context("fork")
        barrier, queue = context.Barrier(2), context.Queue()
        workers = [context.Process(target=competing_writer, args=(self.store.directory, base, barrier, queue, text))
                   for text in ("first", "second")]
        try:
            for worker in workers:
                worker.start()
            outcomes = [queue.get(timeout=15) for _ in workers]
            self.assertEqual(sorted(outcome[0] for outcome in outcomes), ["OK", "STALE_BASE"])
            for worker in workers:
                worker.join(timeout=5)
                self.assertEqual(worker.exitcode, 0)
        finally:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
                    worker.join(timeout=5)
            queue.close()
        self.assertEqual(self.store.read(base, "a.txt"), b"alpha")

    def test_verified_snapshot_import_preserves_logical_modes_and_id(self):
        base = self.store.capture(self.source)
        other = snapshots.SnapshotStore(self.directory / "other")
        imported = other.capture(base)
        self.assertEqual(imported.id, base.id)
        self.assertNotEqual(imported.root, base.root)
        self.assertEqual(other.read(imported, "a.txt"), b"alpha")
        self.assertEqual(imported.manifest["entries"]["a.txt"]["mode"], 0o644)

    def test_get_and_external_validate_rehash_tree_without_advancing_current(self):
        base = self.store.capture(self.source)
        current = self.store.apply(base, base.id, [self.edit()], allowed_paths=("a.txt",))
        other = snapshots.SnapshotStore(self.directory / "verifier")
        self.assertEqual(self.store.get(base.id), base)
        self.assertEqual(other.validate(base), base)
        self.assertFalse((other.directory / "CURRENT").exists())
        self.assertEqual({path.name for path in base.root.iterdir()}, {"a.txt"})
        self.assertTrue((base.root.parent / "manifest.json").is_file())
        self.assertEqual(self.store.apply(current, current.id, [], allowed_paths=()), current)
        target = base.root / "a.txt"
        target.chmod(0o644)
        target.write_bytes(b"bravo")
        target.chmod(0o444)
        for operation in (lambda: self.store.get(base.id), lambda: other.validate(base), lambda: other.capture(base)):
            with self.subTest(operation=operation), self.assertRaises(snapshots.SnapshotError):
                operation()

    def test_manifest_corruption_and_unmanifested_files_are_rejected(self):
        base = self.store.capture(self.source)
        manifest = base.root.parent / "manifest.json"
        original = manifest.read_bytes()
        manifest.chmod(0o644)
        manifest.write_bytes(original.replace(b'"mode":420', b'"mode":448'))
        manifest.chmod(0o444)
        with self.assertRaises(snapshots.SnapshotError):
            self.store.get(base.id)
        manifest.chmod(0o644)
        manifest.write_bytes(original)
        manifest.chmod(0o444)
        base.root.chmod(0o755)
        (base.root / "unmanifested").write_bytes(b"injected")
        (base.root / "unmanifested").chmod(0o444)
        base.root.chmod(0o555)
        with self.assertRaises(snapshots.SnapshotError):
            self.store.get(base.id)

    def test_read_detects_real_same_size_race_inside_sealed_snapshot(self):
        base = self.store.capture(self.source)
        target = base.root / "a.txt"
        before = target.stat()
        original_read = os.read
        changed = False

        def racing_read(fd, count):
            nonlocal changed
            data = original_read(fd, count)
            if not changed and os.fstat(fd).st_ino == before.st_ino:
                changed = True
                target.chmod(0o644)
                target.write_bytes(b"bravo")
                os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
                target.chmod(0o444)
            return data

        with patch("pcworld.snapshots.os.read", side_effect=racing_read):
            self.assert_code("RACE_DETECTED", lambda: self.store.read(base, "a.txt"))
        self.assertTrue(changed)

    @unittest.skipUnless(Path("/proc/self/fd").is_dir(), "Linux descriptor accounting")
    def test_path_walk_race_closes_every_duplicated_descriptor(self):
        before = set(os.listdir("/proc/self/fd"))
        source_inode = self.source.stat().st_ino
        original_dup = os.dup
        changed = False

        def racing_dup(fd):
            nonlocal changed
            result = original_dup(fd)
            if not changed and os.fstat(fd).st_ino == source_inode:
                changed = True
                self.source.chmod(0o750)
            return result

        try:
            with patch("pcworld.snapshots.os.dup", side_effect=racing_dup):
                self.assert_code("RACE_DETECTED", lambda: self.store.capture(self.source))
            self.assertTrue(changed)
            self.assertEqual(set(os.listdir("/proc/self/fd")), before)
        finally:
            # Also release a leaked descriptor when proving the red regression.
            for leaked in set(os.listdir("/proc/self/fd")) - before:
                try:
                    os.close(int(leaked))
                except OSError:
                    pass

    def test_invalidated_lock_permissions_fail_closed(self):
        base = self.store.capture(self.source)
        (self.store.directory / ".lock").chmod(0o666)
        with self.assertRaises(snapshots.SnapshotError):
            self.store.apply(base, base.id, [self.edit()], allowed_paths=("a.txt",))
        self.assertEqual((base.root / "a.txt").read_bytes(), b"alpha")

    def test_oversized_patch_is_rejected_without_allocating_its_encoded_copy(self):
        store = snapshots.SnapshotStore(self.directory / "bounded", max_bytes=5)
        base = store.capture(self.source)
        too_large = "x" * (4 * 1024 * 1024)
        tracemalloc.start()
        try:
            self.assert_code("LIMIT_EXCEEDED", lambda: store.apply(base, base.id, [self.edit(too_large)], allowed_paths=("a.txt",)))
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertLess(peak, 1024 * 1024)
        self.assertEqual(store.read(base, "a.txt"), b"alpha")

    def test_partial_write_failure_removes_staging_and_keeps_current(self):
        base = self.store.capture(self.source)
        before = sorted(path.name for path in self.store.directory.iterdir())
        original_write = os.write

        def failing_write(fd, data):
            if bytes(data) == b"bravo":
                original_write(fd, data[:2])
                raise OSError("injected disk failure after partial write")
            return original_write(fd, data)

        with patch("pcworld.snapshots.os.write", side_effect=failing_write):
            with self.assertRaises(snapshots.SnapshotError):
                self.store.apply(base, base.id, [self.edit()], allowed_paths=("a.txt",))
        self.assertEqual(sorted(path.name for path in self.store.directory.iterdir()), before)
        self.assertEqual(self.store.read(base, "a.txt"), b"alpha")
        self.store.apply(base, base.id, [self.edit()], allowed_paths=("a.txt",))

    def test_head_publication_failure_leaves_old_head_and_complete_versions(self):
        base = self.store.capture(self.source)
        original_replace = os.replace

        def failing_replace(source, destination, **kwargs):
            if destination == "CURRENT":
                raise OSError("injected head publication failure")
            return original_replace(source, destination, **kwargs)

        with patch("pcworld.snapshots.os.replace", side_effect=failing_replace):
            with self.assertRaises(snapshots.SnapshotError):
                self.store.apply(base, base.id, [self.edit()], allowed_paths=("a.txt",))
        self.assertEqual((self.store.directory / "CURRENT").read_text().strip(), base.id)
        self.assertFalse(any(path.name.startswith((".staging-", ".current-")) for path in self.store.directory.iterdir()))
        for path in self.store.directory.iterdir():
            if len(path.name) == 64:
                self.store.get(path.name)
        self.store.apply(base, base.id, [self.edit()], allowed_paths=("a.txt",))


if __name__ == "__main__":
    unittest.main()
