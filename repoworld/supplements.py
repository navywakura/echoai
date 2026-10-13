"""Supervisor-authorized, per-BASE generated artifacts (never a candidate API).

``apply_supplement(base, directory, manifest, manifest_sha256) -> RepoBase``
accepts an artifact-only directory and a JSON mapping pinned *out of band* by
SHA256(canonical(manifest)). A digest supplied by the candidate is not authority.
The supervisor must quiesce the builder before admission. No build, import,
archive extraction, ELF loading, or generated Python execution occurs here.

Manifest schema ``repoworld.base-supplement.v1`` has exactly: schema,
base_commit, base_snapshot_sha256, build, native_build_inputs, files. ``build``
contains status='success', dirty=False, artifact_sha256 (archive identity), and
nonempty builder metadata; other finite JSON build metadata is retained.
``files`` maps relative paths to {kind, sha256, size, mode}; kinds are
native-extension (.so ELF), native-source (C/C++/Fortran/Cython headers/sources),
and generated-version (_version.py or version.py, literal metadata only).
``native_build_inputs`` maps BASE regular-file paths to their SHA256. For native
artifacts it must include native_build_inputs(base); the supervisor must ALSO
list all additional inputs, notably Python build helpers and pure-Python Cython
inputs. This is a frozen build, with no candidate rebuild facility.

The returned tree contains .repoworld-build.json with the entire manifest and
its authorization digest. Its file hash is bound into SnapshotStore's canonical
manifest; the source BASE snapshot ID and commit remain in that record. The
record survives snapshot import/Workspace reopen and must be read-only in the
runner. Call protected_paths(entries, snapshot=repo_base) for that mount list.
Original BASE links and modes survive; supplement files can never be links.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import tempfile

from ..pcworld.receipts import canonical
from ..pcworld.snapshots import Snapshot, SnapshotStore, _directory, _hash, _parts
from .types import RepoBase

BUILD_RECORD = '.repoworld-build.json'
SCHEMA = 'repoworld.base-supplement.v1'
_MAX_MANIFEST = 4 * 1024 * 1024
_NATIVE_SOURCE = {'.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.hxx',
                  '.pyx', '.pxd', '.pxi', '.f', '.f90', '.f95', '.for', '.inc',
                  '.m', '.mm', '.s', '.cu', '.cuh', '.rs'}
_NATIVE_BINARY = {'.so', '.a', '.o', '.obj', '.dll', '.pyd', '.dylib', '.lib'}
_BUILD_NAMES = {'setup.py', 'setup.cfg', 'setup_package.py', 'pyproject.toml',
                'meson.build', 'meson_options.txt', 'cmakelists.txt', 'makefile',
                'cargo.toml', 'cargo.lock', 'build.rs', 'manifest.in', 'configure',
                'configure.ac', 'configure.in'}
_VERSION_NAMES = {'version', '__version__', 'version_tuple', '__version_tuple__',
                  'version_info', '__version_info__', 'commit_id', '__commit_id__',
                  'release', '__release__', 'major', 'minor', 'micro',
                  'releaselevel', 'serial', '__all__'}


def native_only_path(path: str) -> bool:
    """Paths unsupported by the text-edit/no-rebuild production profile.

    Applied to new paths too, so creation cannot bypass frozen native inputs.
    Exact curator-declared extra inputs are enforced separately by provenance.
    """
    parts = _parts(path)
    name = parts[-1].lower()
    return (Path(name).suffix in _NATIVE_SOURCE | _NATIVE_BINARY
            or '.so.' in name or name in _BUILD_NAMES
            or name.endswith('.cmake') or name.startswith('requirements')
            or name.startswith(('setup_', 'build_')) and name.endswith('.py'))


def native_build_inputs(base: RepoBase) -> dict[str, str]:
    """Minimum native/config inventory; curator adds any other build inputs."""
    from ..pcworld.snapshots import _resolve_internal_link
    entries = base.snapshot.manifest['entries']
    result = {}
    for path, entry in entries.items():
        if path == '.' or not native_only_path(path):
            continue
        if entry['type'] == 'symlink':
            path = _resolve_internal_link(entries, path)
            entry = entries[path]
        if entry['type'] == 'file':
            result[path] = entry['sha256']
    return result


def _native_shadows(files):
    paths = set()
    for path in files:
        if Path(path).suffix == '.so':
            module = str(Path(path).with_name(Path(path).name.split('.')[0]))
            paths.update((module, module+'.py'))
    return paths


def _required_inputs(base, files):
    result = native_build_inputs(base)
    shadows = _native_shadows(files)
    result.update((p, e['sha256']) for p, e in base.snapshot.manifest['entries'].items()
                  if e['type'] == 'file' and any(p == s or p.startswith(s+'/') for s in shadows))
    return result


def _json_copy(manifest):
    # Snapshot canonicalization checks finite JSON types, string keys and depth.
    from ..pcworld.snapshots import _canonical
    value = json.loads(_canonical(manifest))
    raw = canonical(value)
    if len(raw) > _MAX_MANIFEST:
        raise ValueError('supplement manifest too large')
    return value, raw


def _manifest(base, manifest, digest):
    value, raw = _json_copy(manifest)
    if hashlib.sha256(raw).hexdigest() != _hash(digest):
        raise ValueError('supplement authorization hash mismatch')
    keys = {'schema', 'base_commit', 'base_snapshot_sha256', 'build', 'native_build_inputs', 'files'}
    if not isinstance(value, dict) or set(value) != keys or value['schema'] != SCHEMA:
        raise ValueError('supplement manifest schema')
    if (value['base_commit'] != base.task.base_commit
            or value['base_snapshot_sha256'] != base.snapshot.id):
        raise ValueError('supplement BASE identity mismatch')
    build = value['build']
    if (not isinstance(build, dict) or build.get('status') != 'success'
            or build.get('dirty') is not False or not build.get('builder')):
        raise ValueError('successful clean build metadata required')
    _hash(build.get('artifact_sha256'))
    for key in ('modified_tracked', 'missing_tracked', 'modified_tracked_files', 'missing_tracked_files'):
        if key in build and build[key] not in ([], 0):
            raise ValueError('dirty or incomplete build source inventory')
    files, inputs = value['files'], value['native_build_inputs']
    if not isinstance(files, dict) or not files or not isinstance(inputs, dict):
        raise ValueError('supplement file/input inventories required')
    entries = base.snapshot.manifest['entries']
    if BUILD_RECORD in entries:
        raise ValueError('BASE already has a supplement')
    native = False
    for path, item in files.items():
        parts = _parts(path)
        if any(p in base.snapshot.manifest['exclude'] for p in parts):
            raise ValueError('supplement path would be excluded from snapshot')
        # Import lazily: workspace uses the protection helpers in this module.
        from .workspace import production_path
        production_path(base.task.repo, path, allow_native=True)
        if path in entries:
            raise ValueError('supplement cannot overwrite a BASE entry: '+path)
        if len(parts) < 2 or entries.get(parts[0], {}).get('type') != 'directory':
            raise ValueError('supplement must be inside a BASE directory')
        for i in range(1, len(parts)):
            parent = '/'.join(parts[:i])
            if parent in entries and entries[parent]['type'] != 'directory':
                raise ValueError('supplement parent is not a BASE directory')
        if not isinstance(item, dict) or set(item) != {'kind', 'sha256', 'size', 'mode'}:
            raise ValueError('supplement file metadata shape')
        _hash(item['sha256'])
        if type(item['size']) is not int or item['size'] < 0:
            raise ValueError('supplement file size')
        if type(item['mode']) is not int or not 0 <= item['mode'] <= 0o777:
            raise ValueError('supplement file mode')
        kind = item['kind']
        suffix = Path(path).suffix.lower()
        if kind == 'native-extension' and suffix == '.so':
            native = True
        elif kind == 'native-source' and suffix in _NATIVE_SOURCE:
            native = True
        elif kind == 'generated-version' and parts[-1] in ('_version.py', 'version.py'):
            pass
        else:
            raise ValueError('unsupported supplement kind/path: '+path)
    for path, digest in inputs.items():
        _parts(path); _hash(digest)
        entry = entries.get(path, {})
        if entry.get('type') != 'file' or entry['sha256'] != digest:
            raise ValueError('native build input differs from BASE: '+path)
    if native and not _required_inputs(base, files).items() <= inputs.items():
        raise ValueError('native build inputs must be frozen completely')
    return value


def _version(data):
    if len(data) > 65536:
        raise ValueError('generated version file too large')
    try:
        tree = ast.parse(data)
    except (ValueError, SyntaxError, RecursionError) as exc:
        raise ValueError('invalid generated version syntax') from exc
    found = False
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue  # Generated header/docstring, no execution.
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            # Annotations can execute too: permit only inert builtin names.
            if not isinstance(node.annotation, ast.Name) or node.annotation.id not in ('str', 'int', 'tuple'):
                raise ValueError('unsafe version annotation')
        else:
            raise ValueError('only literal version assignments permitted')
        if any(not isinstance(t, ast.Name) or t.id not in _VERSION_NAMES for t in targets):
            raise ValueError('unexpected generated version name')
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError, RecursionError) as exc:
            raise ValueError('version metadata must be literal') from exc
        if not (type(value) in (str, int, type(None))
                or type(value) in (tuple, list) and all(type(v) in (str, int) for v in value)):
            raise ValueError('unsupported version literal')
        found |= any(t.id in ('version', '__version__') for t in targets)
    if not found:
        raise ValueError('generated version is missing version metadata')


def _write_blob(path, blob):
    with path.open('xb') as out:
        if isinstance(blob, bytes):
            out.write(blob)
        else:
            for chunk in blob.blocks():
                out.write(chunk)


def _intake(directory, private):
    from .environment import REPO_LIMITS
    strict = SnapshotStore(private/'intake', **{**REPO_LIMITS, 'internal_symlinks': False})
    with _directory(Path(directory).absolute()) as fd:
        # No exclusions: even .echoai and ignored build leftovers are errors.
        return strict._stable_tree(fd, exclude=())


def _validate_artifacts(value, inventory, artifacts):
    expected_dirs = {'.'}
    for path in value['files']:
        parts = _parts(path)
        expected_dirs.update('/'.join(parts[:i]) for i in range(1, len(parts)))
    if set(inventory) != set(value['files']) | expected_dirs:
        raise ValueError('missing or additional supplement entries')
    for path, entry in inventory.items():
        if path in expected_dirs:
            if entry['type'] != 'directory':
                raise ValueError('supplement directory required')
            continue
        item = value['files'][path]
        if entry != dict(type='file', mode=item['mode'], size=item['size'], sha256=item['sha256']):
            raise ValueError('supplement bytes/mode differ from manifest: '+path)
        blob = artifacts[path]
        if item['kind'] == 'generated-version':
            if item['size'] > 65536:
                raise ValueError('generated version file too large')
            _version(blob if isinstance(blob, bytes) else blob.read())
        elif item['kind'] == 'native-extension':
            first = blob if isinstance(blob, bytes) else next(blob.blocks(), b'')
            if not first.startswith(b'\x7fELF'):
                raise ValueError('native extension must be ELF')
    return expected_dirs


def build_supplement_manifest(base: RepoBase, directory, *, build: dict,
                              extra_build_inputs=()) -> dict:
    """Inventory a curator-owned build; caller independently approves/pins result.

    ``extra_build_inputs`` lists BASE-relative regular files beyond the inferred
    native/config inputs. Include every Python build helper/pure Cython input.
    This helper validates formats and bytes but cannot authenticate a builder
    or prove its dependency graph/cleanliness; those are supervisor attestations.
    """
    from .environment import repo_store
    repo_store(base.snapshot.root.parent.parent).validate(base.snapshot)
    with tempfile.TemporaryDirectory(prefix='repoworld-inventory-') as tmp:
        inventory, artifacts = _intake(directory, Path(tmp))
        files = {}
        for path, entry in inventory.items():
            if entry['type'] == 'directory':
                continue
            name = Path(path)
            if name.suffix == '.so':
                kind = 'native-extension'
            elif name.suffix.lower() in _NATIVE_SOURCE:
                kind = 'native-source'
            elif name.name in ('_version.py', 'version.py'):
                kind = 'generated-version'
            else:
                raise ValueError('unsupported generated artifact: '+path)
            files[path] = dict(kind=kind, **{k: entry[k] for k in ('sha256', 'size', 'mode')})
        inputs = _required_inputs(base, files) if any(v['kind'] != 'generated-version' for v in files.values()) else {}
        for path in extra_build_inputs:
            _parts(path)
            entry = base.snapshot.manifest['entries'].get(path, {})
            if entry.get('type') != 'file':
                raise ValueError('build input must be a BASE regular file: '+path)
            inputs[path] = entry['sha256']
        manifest = dict(schema=SCHEMA, base_commit=base.task.base_commit,
                        base_snapshot_sha256=base.snapshot.id, build=build,
                        native_build_inputs=inputs, files=files)
        value = _manifest(base, manifest, hashlib.sha256(canonical(manifest)).hexdigest())
        _validate_artifacts(value, inventory, artifacts)
        return value


def apply_supplement(base: RepoBase, directory, manifest, manifest_sha256) -> RepoBase:
    """Validate supervisor-pinned generated bytes and capture a supplemented BASE.

    ``directory`` contains exactly the declared artifacts and their ancestor
    directories, with no source checkout, manifest file or ignored leftovers.
    Errors are ValueError (including SnapshotError); BASE is never modified.
    """
    from .environment import repo_store
    if not isinstance(base, RepoBase):
        raise ValueError('supervisor RepoBase capability required')
    value = _manifest(base, manifest, manifest_sha256)
    store = repo_store(base.snapshot.root.parent.parent)
    with tempfile.TemporaryDirectory(prefix='repoworld-supplement-') as tmp:
        private = Path(tmp)
        # The intake uses strict PCWorld traversal, even though BASE permits links.
        inventory, artifacts = _intake(directory, private)
        expected_dirs = _validate_artifacts(value, inventory, artifacts)
        # Validate once and copy the verified spool, never reopen untrusted files.
        with store._locked():
            contents = store._external(base.snapshot)
        root = private/'materialized'
        root.mkdir()
        entries = base.snapshot.manifest['entries']
        directories = {p: e['mode'] for p, e in entries.items() if e['type'] == 'directory'}
        for path in sorted(set(directories) | expected_dirs, key=lambda p: (p.count('/'), p)):
            if path != '.':
                (root/path).mkdir(exist_ok=True, mode=0o700)
        for path, entry in entries.items():
            if entry['type'] == 'file':
                _write_blob(root/path, contents[path])
                (root/path).chmod(entry['mode'])
            elif entry['type'] == 'symlink':
                (root/path).symlink_to(entry['target'])
        for path, item in value['files'].items():
            _write_blob(root/path, artifacts[path])
            (root/path).chmod(item['mode'])
        (root/BUILD_RECORD).write_bytes(canonical(dict(schema='repoworld.build-record.v1',
                                                      manifest_sha256=manifest_sha256, manifest=value)))
        (root/BUILD_RECORD).chmod(0o644)
        # Restore source directory modes only after writing; new dirs are stable 0755.
        for path in sorted(set(directories) | expected_dirs, key=lambda p: (p.count('/'), p), reverse=True):
            (root if path == '.' else root/path).chmod(directories.get(path, 0o755))
        result = store.capture(root, exclude=tuple(base.snapshot.manifest['exclude']))
    return RepoBase(base.task, result, base.environment)


def _record(snapshot):
    from .environment import repo_store
    entry = snapshot.manifest['entries'].get(BUILD_RECORD)
    if entry is None:
        return None
    if entry.get('type') != 'file' or entry['size'] > _MAX_MANIFEST + 1024:
        raise ValueError('invalid supplement provenance entry')
    raw = repo_store(snapshot.root.parent.parent).read(snapshot, BUILD_RECORD)
    try:
        record = json.loads(raw)
        if (set(record) != {'schema', 'manifest_sha256', 'manifest'}
                or record['schema'] != 'repoworld.build-record.v1'
                or raw != canonical(record)
                or hashlib.sha256(canonical(record['manifest'])).hexdigest() != _hash(record['manifest_sha256'])):
            raise ValueError('supplement provenance hash/schema mismatch')
        return record['manifest']
    except (TypeError, KeyError, UnicodeError) as exc:
        raise ValueError('invalid supplement provenance') from exc


def protected_path_closure(entries, paths) -> tuple[str, ...]:
    """Manifest-only closure of protected files, directories and link targets.

    Descend through protected directories until every reachable link is covered.
    Preserve nonexisting policy paths for staging, but never return a symlink as
    a mount root. All aliases need their real parent directory protected
    as well: freezing just the final bytes would still allow chain retargeting.
    Protecting the entire workspace is unsupported and fails closed.
    """
    from ..pcworld.snapshots import _resolve_internal_link
    children = {}
    for path in entries:
        if path != '.':
            children.setdefault(path.rpartition('/')[0] or '.', []).append(path)

    class LinkTrace:
        # Reuse SnapshotStore's POSIX link/.. resolver, observing metadata reads
        # to identify intermediate aliases. No filesystem path is dereferenced.
        def __init__(self):
            self.links = []

        def get(self, path):
            entry = entries.get(path)
            if entry is not None and entry.get('type') == 'symlink':
                self.links.append(path)
            return entry

    pending, visited, frozen = list(paths), set(), set()
    while pending:
        path = pending.pop()
        if path == '.':
            raise ValueError('protected link closure would freeze workspace root')
        _parts(path)
        if path in visited:
            continue
        visited.add(path)
        entry = entries.get(path)
        if entry is not None and entry.get('type') == 'symlink':
            trace = LinkTrace()
            pending.append(_resolve_internal_link(trace, path))
            pending.extend(link.rpartition('/')[0] or '.' for link in trace.links)
        else:
            frozen.add(path)
            if entry is not None and entry.get('type') == 'directory':
                pending.extend(children.get(path, ()))
    # Stable minimal real mount roots, also retaining absent edit-policy paths.
    result = []
    for path in sorted(frozen, key=lambda p: (p.count('/'), p)):
        parts = path.split('/')
        if not any('/'.join(parts[:i]) in frozen for i in range(1, len(parts))):
            result.append(path)
    return tuple(result)


def supplement_protected_paths(base: RepoBase | Snapshot) -> tuple[str, ...]:
    """Exact artifacts + frozen inputs for staging and read-only runner mounts."""
    snapshot = base.snapshot if isinstance(base, RepoBase) else base
    result = {BUILD_RECORD}
    result.update(p for p in snapshot.manifest['entries'] if p != '.' and native_only_path(p))
    record = _record(snapshot)
    if record is not None:
        result.update(record['files'])
        result.update(record['native_build_inputs'])
        result.update(_native_shadows(record['files']))
    return protected_path_closure(snapshot.manifest['entries'], result)


def supplement_production_path(base: RepoBase, path: str) -> bool:
    """Production edit policy including supplement/build and symlink protection."""
    from .workspace import production_path, _frozen_paths
    production_path(base.task.repo, path)
    parts = _parts(path)
    if any(base.snapshot.manifest['entries'].get('/'.join(parts[:i]), {}).get('type') == 'symlink'
           for i in range(1, len(parts)+1)):
        raise ValueError('symlink paths are not editable')
    frozen = _frozen_paths(base.snapshot.manifest['entries'], snapshot=base.snapshot)
    if any(path == p or path.startswith(p+'/') for p in frozen):
        raise ValueError('frozen supplement/native input path')
    return True
