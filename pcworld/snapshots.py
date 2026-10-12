"""Bounded, content-addressed filesystem capabilities; never execute candidate code.

Linux/POSIX supervisor API. A store is private (0700), outside its source, with
one CURRENT head and an advisory flock shared by all cooperating writers.
Objects live at <store>/<sha256>/tree; their canonical manifest.json is a
sibling of tree, never part of the candidate mount. Files are copied, not linked.

Manifests fingerprint every included regular file byte, original permission
mode, type and directory name (including empty directories and the root).
Exclusions are exact basenames at every depth, recorded in the manifest;
.echoai is always excluded. Excluded trees are still audited for links/specials
but their bytes are never read. Owners, timestamps, ACLs and xattrs are not
reproduced: the supervisor owns copies, and only POSIX permission modes describe
the source. Symlinks, hardlinks, devices, sockets, FIFOs and cross-device trees
are rejected. All pathname components are opened with dir_fd and O_NOFOLLOW.

Defaults: 10,000 regular files, 64 MiB included bytes, 20,000 tree entries,
depth 64, 16 MiB manifest. Excluded entries count toward traversal/file limits.
Capture keeps bounded bytes in memory and performs a second metadata walk.
Stat comparisons include ctime_ns (not atime, which reads may change).
This detects observed races; a portable walk is not a filesystem transaction.
The supervisor must quiesce writers for a point-in-time source guarantee.

Sealed directories are 0555; files are 0444 plus original executable bits.
Read-only modes are not isolation from the owner/root: the supervisor must keep
the store inaccessible to candidates and mount only tree read-only. A Snapshot
is a supervisor capability, not an untrusted candidate-supplied object.
capture(snapshot) preserves original modes and ID through a verified import;
capture(snapshot.root) fingerprints the actual sealed filesystem modes.

Edits authorize exact file paths, never globs or directory prefixes. Protected
.git/contracts/tests paths therefore require explicit entries; .echoai is
always denied. expected_sha256=None authorizes creation of an absent file;
content=None deletes an existing file. Deletion retains empty directories.
Bad edits cannot modify a base or advance CURRENT. Publication is an atomic
head replacement after a complete sealed version exists. A crash may leave an
unreferenced version/staging directory; it cannot publish a partial tree.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import uuid

try:
    import fcntl
except ImportError:  # Explicit failure; no unsafe platform fallback.
    fcntl = None


_DEFAULT_EXCLUDE = (".git", ".echoai", "__pycache__")
_MANIFEST_BYTES = 16 * 1024 * 1024
_CHUNK = 64 * 1024


class SnapshotError(ValueError):
    """Fail-closed API error with a stable machine-readable code."""

    def __init__(self, code: str, detail: str):
        self.code = code
        super().__init__(f"{code}: {detail}")


class _FrozenDict(dict):
    def _deny(self, *args, **kwargs):
        raise TypeError("snapshot manifest is immutable")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = __ior__ = _deny


def _freeze(value):
    if isinstance(value, dict):
        return _FrozenDict({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class Snapshot:
    id: str
    root: Path
    manifest: dict

    def __post_init__(self):
        object.__setattr__(self, "root", Path(self.root))
        object.__setattr__(self, "manifest", _freeze(self.manifest))


def _canonical(value) -> bytes:
    def checked(item, depth=0):
        if depth > 64:
            raise SnapshotError("INVALID_INPUT", "canonical data is too deep")
        if item is None or type(item) in (str, int, bool):
            return item
        if type(item) is float and math.isfinite(item):
            return item
        if isinstance(item, dict):
            if any(type(key) is not str for key in item):
                raise SnapshotError("INVALID_INPUT", "JSON keys must be strings")
            return {key: checked(part, depth + 1) for key, part in item.items()}
        if isinstance(item, (tuple, list)):
            return [checked(part, depth + 1) for part in item]
        raise SnapshotError("INVALID_INPUT", "finite JSON values are required")

    return json.dumps(checked(value), sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash(value):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise SnapshotError("INVALID_INPUT", "a full lowercase SHA-256 is required")
    return value


def identity(*, snapshot_id, environment, action, checks, policy, seed,
             dataset=None, task="") -> str:
    """Hash complete canonical JSON fingerprints; callers supply full context.

    Nothing is summarized to HEAD, a dirty count, repr(), or truncated hashes.
    This function cannot discover dependencies omitted by its caller.
    """
    return _digest(_canonical(dict(version="pcworld.identity.v1", task=task,
                                   tree=_hash(snapshot_id), environment=environment,
                                   action=action, checks=checks, policy=policy,
                                   seed=seed, dataset=dataset)))


def _parts(relative):
    if (type(relative) is not str or not relative or "\0" in relative or "\\" in relative
            or len(os.fsencode(relative)) > 4096):
        raise SnapshotError("UNSAFE_PATH", "invalid relative path")
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise SnapshotError("UNSAFE_PATH", "path must be canonical and relative")
    return parts


def _absolute(path):
    path = Path(path)
    if ".." in path.parts or "\0" in str(path):
        raise SnapshotError("UNSAFE_PATH", "parent traversal is forbidden")
    return path.absolute()


def _stamp(info):
    # atime is deliberately omitted: our reads may update it.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_uid,
            info.st_gid, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _kind(info):
    if stat.S_ISDIR(info.st_mode):
        return "directory"
    if stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
        return "file"
    raise SnapshotError("UNSAFE_PATH", "links and special files are forbidden")


def _same(before, after):
    if _stamp(before) != _stamp(after):
        raise SnapshotError("RACE_DETECTED", "filesystem object changed during observation")


@contextmanager
def _checked(parent, name, *, kind=None):
    before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    actual_kind = _kind(before)
    if kind is not None and actual_kind != kind:
        raise SnapshotError("UNSAFE_PATH", f"expected {kind}")
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    if actual_kind == "directory":
        flags |= os.O_DIRECTORY
    fd = os.open(name, flags, dir_fd=parent)
    try:
        _same(before, os.fstat(fd))
        yield fd, before
        _same(before, os.fstat(fd))
        _same(before, os.stat(name, dir_fd=parent, follow_symlinks=False))
    finally:
        os.close(fd)


@contextmanager
def _directory(path, *, create=False):
    """Walk from / without resolving any link, including ancestor aliases."""
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
            next_fd = _duplicate_directory(fd, part)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


@contextmanager
def _descend(root, parts):
    fd = os.dup(root)
    try:
        for part in parts:
            next_fd = _duplicate_directory(fd, part)
            os.close(fd)
            fd = next_fd
        yield fd
    finally:
        os.close(fd)


def _duplicate_directory(parent, name):
    duplicate = None
    try:
        with _checked(parent, name, kind="directory") as (child, _):
            duplicate = os.dup(child)
        return duplicate
    except BaseException:
        # _checked may reject the post-open stat after dup has succeeded.
        if duplicate is not None:
            os.close(duplicate)
        raise


def _read_bytes(fd, before, limit):
    if before.st_size > limit:
        raise SnapshotError("LIMIT_EXCEEDED", "byte limit exceeded")
    chunks, total = [], 0
    while True:
        block = os.read(fd, min(_CHUNK, limit - total + 1))
        if not block:
            break
        total += len(block)
        if total > limit:
            raise SnapshotError("LIMIT_EXCEEDED", "byte limit exceeded")
        chunks.append(block)
    _same(before, os.fstat(fd))
    if total != before.st_size:
        raise SnapshotError("RACE_DETECTED", "file length changed during read")
    return b"".join(chunks)


def _write_new(parent, name, data, mode):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=parent)
    try:
        remaining = memoryview(data)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise OSError("short snapshot write")
            remaining = remaining[written:]
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)


def _remove_staging(parent, name):
    """Supervisor cleanup: make only private staging directories writable."""
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
    try:
        os.fchmod(fd, 0o700)
        for child in os.listdir(fd):
            info = os.stat(child, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                _remove_staging(fd, child)
            else:
                os.unlink(child, dir_fd=fd)
    finally:
        os.close(fd)
    os.rmdir(name, dir_fd=parent)


class SnapshotStore:
    def __init__(self, directory: Path, *, max_files=10_000, max_bytes=64 * 1024 * 1024,
                 max_entries=20_000, max_depth=64):
        if fcntl is None or any(not hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_DIRECTORY")):
            raise SnapshotError("UNSUPPORTED_ENVIRONMENT", "POSIX descriptor operations and flock required")
        for value in (max_files, max_bytes, max_entries, max_depth):
            if type(value) is not int or value < 0:
                raise SnapshotError("INVALID_INPUT", "limits must be nonnegative integers")
        if max_depth > 128:
            raise SnapshotError("INVALID_INPUT", "maximum supported depth is 128")
        self.directory = _absolute(directory)
        self.max_files, self.max_bytes = max_files, max_bytes
        self.max_entries, self.max_depth = max_entries, max_depth
        try:
            with _directory(self.directory, create=True) as fd:
                info = os.fstat(fd)
                if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
                    raise SnapshotError("UNSAFE_STORE", "store must be owned by supervisor with mode 0700")
                self._inode = (info.st_dev, info.st_ino)
                try:
                    _write_new(fd, ".lock", b"", 0o600)
                except FileExistsError:
                    pass
                with _checked(fd, ".lock", kind="file") as (_, lock):
                    if stat.S_IMODE(lock.st_mode) != 0o600 or lock.st_uid != os.geteuid():
                        raise SnapshotError("UNSAFE_STORE", "invalid writer lock")
                    self._lock_inode = (lock.st_dev, lock.st_ino)
        except OSError as error:
            raise SnapshotError("UNSAFE_PATH", str(error)) from error

    @contextmanager
    def _locked(self):
        try:
            with _directory(self.directory) as fd:
                info = os.fstat(fd)
                if ((info.st_dev, info.st_ino) != self._inode or stat.S_IMODE(info.st_mode) != 0o700
                        or info.st_uid != os.geteuid()):
                    raise SnapshotError("UNSAFE_STORE", "store was replaced or made accessible")
                with _checked(fd, ".lock", kind="file") as (lock, info):
                    if ((info.st_dev, info.st_ino) != self._lock_inode
                            or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.geteuid()):
                        raise SnapshotError("UNSAFE_STORE", "writer lock was replaced or made accessible")
                    fcntl.flock(lock, fcntl.LOCK_EX)
                    try:
                        yield fd
                    finally:
                        fcntl.flock(lock, fcntl.LOCK_UN)
        except OSError as error:
            raise SnapshotError("UNSAFE_PATH", str(error)) from error

    def _exclusions(self, exclude):
        if not isinstance(exclude, (tuple, list)):
            raise SnapshotError("INVALID_INPUT", "exclusions must be basename tuples")
        for name in exclude:
            if len(_parts(name)) != 1:
                raise SnapshotError("INVALID_INPUT", "exclusions are single basenames")
        return sorted(set(exclude) | {".echoai"})

    def _scan(self, root, exclude=(), *, collect=True):
        entries, contents, stamps = {}, {}, {}
        count = files = byte_count = 0
        device = os.fstat(root).st_dev

        def walk(fd, path, hidden, depth):
            nonlocal count, files, byte_count
            before = os.fstat(fd)
            if before.st_dev != device or (before.st_dev, before.st_ino) == self._inode:
                raise SnapshotError("UNSAFE_PATH", "tree crosses a filesystem/store boundary")
            stamps[path] = _stamp(before)
            if not hidden:
                entries[path] = {"type": "directory", "mode": stat.S_IMODE(before.st_mode)}
            names = []
            with os.scandir(fd) as iterator:
                for entry in iterator:
                    count += 1
                    if count > self.max_entries:
                        raise SnapshotError("LIMIT_EXCEEDED", "tree entry limit exceeded")
                    _parts(entry.name)
                    names.append(entry.name)
            for name in sorted(names):
                relative = name if path == "." else f"{path}/{name}"
                _parts(relative)
                if depth + 1 > self.max_depth:
                    raise SnapshotError("LIMIT_EXCEEDED", "tree depth limit exceeded")
                omit = hidden or name in exclude
                with _checked(fd, name) as (child, info):
                    if info.st_dev != device:
                        raise SnapshotError("UNSAFE_PATH", "cross-device entry")
                    stamps[relative] = _stamp(info)
                    if stat.S_ISDIR(info.st_mode):
                        walk(child, relative, omit, depth + 1)
                    else:
                        files += 1
                        if files > self.max_files:
                            raise SnapshotError("LIMIT_EXCEEDED", "file count limit exceeded")
                        if not omit:
                            byte_count += info.st_size
                            if byte_count > self.max_bytes:
                                raise SnapshotError("LIMIT_EXCEEDED", "tree byte limit exceeded")
                            if collect:
                                data = _read_bytes(child, info, self.max_bytes - byte_count + info.st_size)
                                contents[relative] = data
                                entries[relative] = {"type": "file", "mode": stat.S_IMODE(info.st_mode),
                                                     "size": len(data), "sha256": _digest(data)}
            _same(before, os.fstat(fd))

        walk(root, ".", False, 0)
        return entries, contents, stamps

    def _stable_tree(self, root, exclude=()):
        entries, contents, stamps = self._scan(root, exclude)
        if stamps != self._scan(root, exclude, collect=False)[2]:
            raise SnapshotError("RACE_DETECTED", "tree changed before publication")
        return entries, contents

    def _check_manifest(self, manifest):
        if not isinstance(manifest, dict) or set(manifest) != {"version", "exclude", "entries"}:
            raise SnapshotError("CORRUPT_SNAPSHOT", "invalid manifest shape")
        if type(manifest["version"]) is not int or manifest["version"] != 1:
            raise SnapshotError("CORRUPT_SNAPSHOT", "unknown manifest version")
        exclude = self._exclusions(manifest["exclude"])
        if tuple(exclude) != tuple(manifest["exclude"]):
            raise SnapshotError("CORRUPT_SNAPSHOT", "noncanonical exclusions")
        entries = manifest["entries"]
        if not isinstance(entries, dict) or "." not in entries:
            raise SnapshotError("CORRUPT_SNAPSHOT", "missing root metadata")
        if len(entries) - 1 > self.max_entries:
            raise SnapshotError("LIMIT_EXCEEDED", "manifest entry limit exceeded")
        files = total = 0
        for path, entry in entries.items():
            parts = [] if path == "." else _parts(path)
            if len(parts) > self.max_depth:
                raise SnapshotError("LIMIT_EXCEEDED", "manifest depth limit exceeded")
            if any(part in exclude for part in parts):
                raise SnapshotError("CORRUPT_SNAPSHOT", "excluded path in manifest")
            if not isinstance(entry, dict) or entry.get("type") not in ("directory", "file"):
                raise SnapshotError("CORRUPT_SNAPSHOT", "invalid entry type")
            if type(entry.get("mode")) is not int or not 0 <= entry["mode"] <= 0o7777:
                raise SnapshotError("CORRUPT_SNAPSHOT", "invalid source mode")
            if entry["type"] == "directory":
                if set(entry) != {"type", "mode"}:
                    raise SnapshotError("CORRUPT_SNAPSHOT", "invalid directory metadata")
            else:
                if path == "." or set(entry) != {"type", "mode", "size", "sha256"}:
                    raise SnapshotError("CORRUPT_SNAPSHOT", "invalid file metadata")
                _hash(entry["sha256"])
                if type(entry["size"]) is not int or entry["size"] < 0:
                    raise SnapshotError("CORRUPT_SNAPSHOT", "invalid file size")
                files += 1
                total += entry["size"]
            if parts:
                parent = "/".join(parts[:-1]) or "."
                if not isinstance(entries.get(parent), dict) or entries[parent].get("type") != "directory":
                    raise SnapshotError("CORRUPT_SNAPSHOT", "missing directory parent")
        if files > self.max_files or total > self.max_bytes:
            raise SnapshotError("LIMIT_EXCEEDED", "manifest file/byte limit exceeded")
        raw = _canonical(manifest)
        if len(raw) > _MANIFEST_BYTES:
            raise SnapshotError("LIMIT_EXCEEDED", "manifest byte limit exceeded")
        return raw

    def _verify_tree(self, root, manifest):
        actual, contents = self._stable_tree(root)
        expected = {}
        for path, entry in manifest["entries"].items():
            expected[path] = dict(entry)
            expected[path]["mode"] = 0o555 if entry["type"] == "directory" else 0o444 | (entry["mode"] & 0o111)
        if actual != expected:
            raise SnapshotError("CORRUPT_SNAPSHOT", "stored bytes, names, types or sealed modes differ")
        return contents

    def _load(self, store, identifier):
        _hash(identifier)
        with _checked(store, identifier, kind="directory") as (container, info):
            if stat.S_IMODE(info.st_mode) != 0o555 or set(os.listdir(container)) != {"tree", "manifest.json"}:
                raise SnapshotError("CORRUPT_SNAPSHOT", "invalid snapshot container")
            with _checked(container, "manifest.json", kind="file") as (fd, info):
                if stat.S_IMODE(info.st_mode) != 0o444:
                    raise SnapshotError("CORRUPT_SNAPSHOT", "manifest is not sealed")
                raw = _read_bytes(fd, info, _MANIFEST_BYTES)
            try:
                manifest = json.loads(raw)
            except (ValueError, UnicodeError, RecursionError) as error:
                raise SnapshotError("CORRUPT_SNAPSHOT", "invalid manifest JSON") from error
            if raw != self._check_manifest(manifest) or _digest(raw) != identifier:
                raise SnapshotError("CORRUPT_SNAPSHOT", "manifest identity mismatch")
            with _checked(container, "tree", kind="directory") as (root, _):
                contents = self._verify_tree(root, manifest)
        return Snapshot(identifier, self.directory / identifier / "tree", manifest), contents

    def _external(self, snapshot):
        if not isinstance(snapshot, Snapshot):
            raise SnapshotError("INVALID_INPUT", "Snapshot capability required")
        if _digest(self._check_manifest(snapshot.manifest)) != _hash(snapshot.id):
            raise SnapshotError("CORRUPT_SNAPSHOT", "snapshot manifest identity mismatch")
        path = _absolute(snapshot.root)
        with _directory(path) as root:
            before = os.fstat(root)
            contents = self._verify_tree(root, snapshot.manifest)
            with _directory(path) as reopened:
                _same(before, os.fstat(reopened))
        return contents

    def validate(self, snapshot: Snapshot) -> Snapshot:
        """Verify an explicit supervisor capability, reading only its tree."""
        with self._locked():
            self._external(snapshot)
        return snapshot

    def get(self, snapshot_id: str) -> Snapshot:
        """Load and fully verify an existing store object, including every hash."""
        with self._locked() as store:
            return self._load(store, snapshot_id)[0]

    def _current(self, store):
        try:
            with _checked(store, "CURRENT", kind="file") as (fd, info):
                if stat.S_IMODE(info.st_mode) != 0o600:
                    raise SnapshotError("UNSAFE_STORE", "invalid CURRENT permissions")
                raw = _read_bytes(fd, info, 65)
        except FileNotFoundError:
            return None
        if len(raw) != 65 or raw[-1:] != b"\n":
            raise SnapshotError("CORRUPT_SNAPSHOT", "invalid CURRENT pointer")
        try:
            return _hash(raw[:-1].decode("ascii"))
        except UnicodeError as error:
            raise SnapshotError("CORRUPT_SNAPSHOT", "invalid CURRENT encoding") from error

    def _advance(self, store, identifier):
        temporary = ".current-" + uuid.uuid4().hex
        try:
            _write_new(store, temporary, (identifier + "\n").encode("ascii"), 0o600)
            os.replace(temporary, "CURRENT", src_dir_fd=store, dst_dir_fd=store)
            os.fsync(store)
        finally:
            try:
                os.unlink(temporary, dir_fd=store)
            except FileNotFoundError:
                pass

    def _publish(self, store, manifest, contents):
        raw = self._check_manifest(manifest)
        identifier = _digest(raw)
        try:
            os.stat(identifier, dir_fd=store, follow_symlinks=False)
        except FileNotFoundError:
            temporary = ".staging-" + uuid.uuid4().hex
            os.mkdir(temporary, 0o700, dir_fd=store)
            try:
                with _descend(store, [temporary]) as container:
                    os.mkdir("tree", 0o700, dir_fd=container)
                    with _descend(container, ["tree"]) as root:
                        entries = manifest["entries"]
                        directories = sorted((path for path, item in entries.items()
                                              if path != "." and item["type"] == "directory"),
                                             key=lambda path: (path.count("/"), path))
                        for path in directories:
                            parts = _parts(path)
                            with _descend(root, parts[:-1]) as parent:
                                os.mkdir(parts[-1], 0o700, dir_fd=parent)
                        for path, data in contents.items():
                            parts = _parts(path)
                            with _descend(root, parts[:-1]) as parent:
                                _write_new(parent, parts[-1], data, 0o444 | (entries[path]["mode"] & 0o111))
                        for path in reversed(directories):
                            with _descend(root, _parts(path)) as fd:
                                os.fchmod(fd, 0o555)
                                os.fsync(fd)
                        os.fchmod(root, 0o555)
                        os.fsync(root)
                    _write_new(container, "manifest.json", raw, 0o444)
                    os.fchmod(container, 0o555)
                    os.fsync(container)
                os.rename(temporary, identifier, src_dir_fd=store, dst_dir_fd=store)
                os.fsync(store)
            finally:
                try:
                    _remove_staging(store, temporary)
                except FileNotFoundError:
                    pass
        # Validate even existing objects; no cache can bless tampered bytes.
        snapshot, _ = self._load(store, identifier)
        self._advance(store, identifier)
        return snapshot

    def capture(self, source: Path | Snapshot, *, exclude: tuple[str, ...] = _DEFAULT_EXCLUDE) -> Snapshot:
        """Capture a path capability, or import a verified immutable Snapshot."""
        with self._locked() as store:
            if isinstance(source, Snapshot):
                if exclude != _DEFAULT_EXCLUDE:
                    raise SnapshotError("INVALID_INPUT", "snapshot imports preserve existing exclusions")
                return self._publish(store, source.manifest, self._external(source))
            path = _absolute(source)
            if path == self.directory or path in self.directory.parents or self.directory in path.parents:
                raise SnapshotError("UNSAFE_STORE", "source and store must not overlap")
            exclusions = self._exclusions(exclude)
            with _directory(path) as root:
                before = os.fstat(root)
                entries, contents = self._stable_tree(root, exclusions)
                with _directory(path) as reopened:
                    _same(before, os.fstat(reopened))
            return self._publish(store, {"version": 1, "exclude": exclusions, "entries": entries}, contents)

    def _bound(self, snapshot):
        if not isinstance(snapshot, Snapshot):
            raise SnapshotError("INVALID_INPUT", "Snapshot capability required")
        _hash(snapshot.id)
        if snapshot.root != self.directory / snapshot.id / "tree":
            raise SnapshotError("UNSAFE_PATH", "snapshot does not belong to this store")

    def read(self, snapshot: Snapshot, relative: str) -> bytes:
        parts = _parts(relative)
        if ".echoai" in parts:
            raise SnapshotError("UNSAFE_PATH", ".echoai is supervisor-only")
        self._bound(snapshot)
        with self._locked() as store:
            verified, contents = self._load(store, snapshot.id)
            if verified.manifest != snapshot.manifest:
                raise SnapshotError("CORRUPT_SNAPSHOT", "capability manifest mismatch")
            if relative not in contents:
                raise SnapshotError("UNSAFE_PATH", "path is not an included regular file")
            return contents[relative]

    def apply(self, base: Snapshot, expected_base: str, edits: list[dict], *,
              allowed_paths: tuple[str, ...]) -> Snapshot:
        """Atomically replace the current version; stale proposals never rebase."""
        self._bound(base)
        with self._locked() as store:
            if expected_base != base.id or self._current(store) != expected_base:
                raise SnapshotError("STALE_BASE", "expected base is not this store's current version")
            verified, contents = self._load(store, base.id)
            if verified.manifest != base.manifest:
                raise SnapshotError("CORRUPT_SNAPSHOT", "base manifest mismatch")
            if type(edits) is not list or not isinstance(allowed_paths, tuple):
                raise SnapshotError("INVALID_EDIT", "edits list and exact allowed_paths tuple required")
            allowed = set()
            for path in allowed_paths:
                _parts(path)
                allowed.add(path)
            if len(edits) > self.max_entries:
                raise SnapshotError("LIMIT_EXCEEDED", "edit count limit exceeded")
            manifest = json.loads(_canonical(base.manifest))
            entries = manifest["entries"]
            seen = set()
            replaced = {edit["path"] for edit in edits
                        if type(edit) is dict and type(edit.get("path")) is str}
            byte_count = sum(len(data) for path, data in contents.items() if path not in replaced)
            for edit in edits:
                if type(edit) is not dict or set(edit) != {"path", "expected_sha256", "content"}:
                    raise SnapshotError("INVALID_EDIT", "edit requires path, expected_sha256 and content")
                path, expected, content = edit["path"], edit["expected_sha256"], edit["content"]
                parts = _parts(path)
                if path not in allowed or any(part in manifest["exclude"] for part in parts):
                    raise SnapshotError("UNSAFE_PATH", "edit is outside explicit capabilities")
                if path in seen:
                    raise SnapshotError("INVALID_EDIT", "duplicate edit path")
                seen.add(path)
                if content is not None and type(content) is not str:
                    raise SnapshotError("INVALID_EDIT", "content must be UTF-8 text or None")
                if expected is not None:
                    _hash(expected)
                previous = base.manifest["entries"].get(path)
                if previous is not None and previous["type"] != "file":
                    raise SnapshotError("INVALID_EDIT", "only regular files may be edited")
                actual_hash = previous["sha256"] if previous is not None else None
                if actual_hash != expected or (previous is None and content is None):
                    raise SnapshotError("STALE_BASE", "file precondition does not match base")
                if content is None:
                    entries.pop(path)
                    contents.pop(path)
                    continue
                for depth in range(1, len(parts)):
                    parent = "/".join(parts[:depth])
                    if parent in entries and entries[parent]["type"] != "directory":
                        raise SnapshotError("INVALID_EDIT", "parent is not a directory")
                    # A deletion must not turn a base file into a parent directory.
                    if parent in base.manifest["entries"] and base.manifest["entries"][parent]["type"] != "directory":
                        raise SnapshotError("INVALID_EDIT", "base parent is not a directory")
                    entries.setdefault(parent, {"type": "directory", "mode": 0o755})
                if path in entries and entries[path]["type"] != "file":
                    raise SnapshotError("INVALID_EDIT", "file/directory edit conflict")
                # UTF-8 uses at least one byte per character. Bound allocation
                # before encoding, and charge all replacements cumulatively.
                if len(content) > self.max_bytes - byte_count:
                    raise SnapshotError("LIMIT_EXCEEDED", "patch byte limit exceeded")
                try:
                    data = content.encode("utf-8")
                except UnicodeError as error:
                    raise SnapshotError("INVALID_EDIT", "invalid UTF-8 content") from error
                byte_count += len(data)
                if byte_count > self.max_bytes:
                    raise SnapshotError("LIMIT_EXCEEDED", "patch byte limit exceeded")
                contents[path] = data
                entries[path] = {"type": "file", "mode": previous["mode"] if previous else 0o644,
                                 "size": len(data), "sha256": _digest(data)}
            return self._publish(store, manifest, contents)
