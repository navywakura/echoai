"""Validate collected B24 closure custody using metadata only, without replay.

The local manager collects identically named files for original B24 and R1.
Their evidence archives use different exact roots. Source hashes belong to the
archived profile; they are never compared with or imported from this workspace.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import re
import tarfile


_ROOTS = {'b24-results', 'b24-r1-results'}
_EXPORTS = {'b24-closed.json': 'closed.json',
            'b24-arithmetic-review.json': 'arithmetic-review.json',
            'b24-status.json': 'status.json', 'b24-micro.json': 'micro.json',
            'b24-transfer.json': 'transfer.json', 'b24-models.json': 'input/models.json'}
_REQUIRED = set(_EXPORTS) | {'b24-evidence.tar.gz', 'b24-native.tar.gz'}
_MAX_JSON = 16 * 1024 * 1024


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _unique(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def _finite(value):
    result = float(value)
    _require(math.isfinite(result), 'nonfinite JSON number')
    return result


def _object(raw):
    value = json.loads(raw, object_pairs_hook=_unique, parse_float=_finite,
                       parse_constant=_finite)
    _require(type(value) is dict, 'JSON object required')
    return value


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _profile(value):
    # Same canonical representation as the B24 arithmetic reviewer.
    return _sha(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def _count(value, name, minimum=0):
    _require(type(value) is int and value >= minimum, 'invalid ' + name)
    return value


def _hashes(value):
    _require(type(value) is dict and bool(value), 'nonempty file hash mapping required')
    for name, digest in value.items():
        _require(type(name) is str and type(digest) is str and
                 re.fullmatch('[0-9a-f]{64}', digest) is not None, 'invalid file hash')
    return value


def _json_bytes(path):
    with path.open('rb') as stream:
        raw = stream.read(_MAX_JSON + 1)
    _require(len(raw) <= _MAX_JSON, 'metadata too large')
    return raw


def _archive_metadata(path):
    """Read only custody metadata; never extract files or parse game evidence."""
    root, seen, metadata = None, set(), {}
    with tarfile.open(path, 'r|gz') as archive:
        for member in archive:
            name = member.name.rstrip('/') if member.isdir() else member.name
            parts = PurePosixPath(name).parts
            _require(bool(parts) and parts[0] in _ROOTS and '..' not in parts and
                     PurePosixPath(name).as_posix() == name, 'unexpected archive member path')
            _require(name not in seen, 'duplicate archive member: ' + name)
            seen.add(name)
            root = root or parts[0]
            _require(parts[0] == root, 'mixed B24 archive roots')
            _require(member.isdir() or member.isfile(), 'archive links/special files are not custody')
            if member.isdir():
                continue
            relative = '/'.join(parts[1:])
            needed = relative in set(_EXPORTS.values()) | {'format-preflight/receipt.json'}
            needed |= len(parts) == 3 and parts[1] == 'input' and parts[2].endswith('.json')
            if needed:
                _require(0 <= member.size <= _MAX_JSON, 'archive metadata too large')
                # Bound retained metadata even for a malformed archive with many inputs.
                _require(len(metadata) < 64, 'too many archive metadata files')
                with archive.extractfile(member) as stream:
                    raw = stream.read(_MAX_JSON + 1)
                _require(len(raw) == member.size, 'truncated archive metadata')
                metadata[relative] = raw
    _require(root is not None, 'empty evidence archive')
    return root, metadata


def _validate(path):
    _require(path.name == 'b24-closed.json', 'expected collected b24-closed.json')
    folder = path.parent.resolve()
    collection_path = folder / 'collection.json'
    _require(not collection_path.is_symlink() and collection_path.is_file(),
             'collection must be a local regular file')
    collection_raw = _json_bytes(collection_path)
    collection = _object(collection_raw)
    version = _count(collection['version'], 'collection version', 1)
    files = _hashes(collection['files'])
    _require(_REQUIRED <= files.keys(), 'partial collection: required files are missing')
    local = {}
    for name, expected in files.items():
        _require(name not in ('', '.', '..', 'collection.json') and
                 '/' not in name and '\\' not in name, 'unsafe collection filename')
        target = folder / name
        _require(not target.is_symlink() and target.is_file(), 'missing/nonregular collected file: ' + name)
        if name in _EXPORTS:
            local[name] = _json_bytes(target)
            actual = _sha(local[name])
        else:
            with target.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        _require(actual == expected, 'collected file hash mismatch: ' + name)

    root, archived = _archive_metadata(folder / 'b24-evidence.tar.gz')
    for name, member in _EXPORTS.items():
        _require(archived.get(member) == local[name], 'archive copy differs or is missing: ' + member)
    manifest_raw = archived['input/manifest.json']
    manifest = _object(manifest_raw)
    config = manifest['configuration']
    _require(config['condition'] == 'S6-B24' and config['exam_allowed'] is False,
             'manifest is not a non-exam S6-B24 profile')
    _require(type(manifest['execution_root']) is str and
             PurePosixPath(manifest['execution_root']).is_absolute() and
             PurePosixPath(manifest['execution_root']).name == root, 'archive/execution root mismatch')
    _hashes(manifest['sources'])
    inputs = _hashes(manifest['inputs'])
    for name, expected in inputs.items():
        _require('/' not in name and '\\' not in name and name not in ('', '.', '..', 'manifest.json'),
                 'unsafe manifest input name')
        _require(_sha(archived['input/' + name]) == expected, 'archived input hash mismatch: ' + name)
    _require('models.json' in inputs, 'model registry is not bound to manifest')
    profile = _profile(manifest)

    closed = _object(local['b24-closed.json'])
    audit = _object(local['b24-arithmetic-review.json'])
    status = _object(local['b24-status.json'])
    for name, document in (('closure', closed), ('audit', audit)):
        _require(document['valid'] is True and document['exam_opened'] is False and
                 document['s6_green'] is False, 'invalid or exam-bearing ' + name)
        _require(document.get('condition', 'S6-B24') == 'S6-B24', 'unrelated ' + name)
    _require(closed['result'] == 'DIAGNOSTIC_COMPLETE' and
             closed['confirmation'] == closed['campaign'] == 'NOT_RUN', 'B24 diagnostic is not complete')
    _require(audit['profile_sha256'] == profile, 'audit/profile hash mismatch')
    _require(status['stage'] == 'CLOSED' and status['condition'] == 'S6-B24' and
             all(status.get(key) == value for key, value in closed.items() if key != 'at'),
             'collection status does not describe the closure')
    games = _count(closed['physical_games'], 'physical games', 1)
    science = _count(closed['model_calls'], 'scientific model calls')
    _require(games == _count(audit['completed_games'], 'audited games', 1) and
             science == _count(audit['model_calls'], 'audited model calls'), 'closure/audit totals differ')
    _require(games <= _count(config['max_games'], 'game cap', 1), 'physical game cap exceeded')

    preflight = _object(archived['format-preflight/receipt.json'])
    current = _count(preflight['model_calls'], 'current format calls')
    _require(preflight['valid'] is True and preflight['profile_sha256'] == profile and current == 8,
             'missing valid same-profile eight-case format preflight')
    prior = 0
    recovery_fields = {'prior_format_calls', 'current_profile_format_calls',
                       'current_profile_total_model_calls', 'recovery_sha256'}
    if root == 'b24-r1-results':
        _require(config['model']['transport_revision'] == 'B24-R1' and 'recovery.json' in inputs,
                 'R1 recovery is not declared in the profile')
        recovery_raw = archived['input/recovery.json']
        recovery = _object(recovery_raw)
        prior = _count(recovery['parent']['charged_format_calls'], 'prior charged format calls')
        _require(closed['recovery_sha256'] == _sha(recovery_raw), 'closure/recovery hash mismatch')
        _require(_count(closed['prior_format_calls'], 'prior format calls') == prior and
                 _count(closed['current_profile_format_calls'], 'current profile format calls') == current and
                 _count(closed['current_profile_total_model_calls'], 'current profile model calls') == science + current,
                 'R1 prior/current totals differ')
    else:
        _require(not recovery_fields.intersection(closed) and 'recovery.json' not in inputs and
                 'transport_revision' not in config['model'], 'recovery metadata with original archive root')
    _require(_count(closed['format_calls'], 'total format calls') == prior + current and
             _count(closed['total_model_calls'], 'total model calls') == science + prior + current,
             'cumulative model/format totals differ')
    return dict(schema='echo45-b24-closure-custody-1', condition='S6-B24',
                receipt=closed, sha256=files['b24-closed.json'],
                audit_sha256=files['b24-arithmetic-review.json'],
                collection_sha256=_sha(collection_raw), collection_version=version,
                evidence_sha256=files['b24-evidence.tar.gz'],
                manifest_sha256=_sha(manifest_raw), profile_sha256=profile,
                archive_root=root, files=files)


def validate(path):
    """Return JSON-serializable custody provenance or raise PermissionError('B24...').

    This verifies the collected review's identity and accounting, not game results
    anew. It performs no extraction, source imports, inference, network or replay.
    """
    try:
        return _validate(Path(path))
    except Exception as exc:
        raise PermissionError('B24 closure custody invalid: ' + str(exc)) from exc
