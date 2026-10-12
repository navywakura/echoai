"""Neutral authenticated receipts for a trusted POSIX supervisor (stdlib only).

Public receipts.jsonl records contain schema/n/prev/body/sha256/hmac. Sequences
start at 1; the empty head is 64 zeroes. SHA-256 covers the canonical envelope
without either digest; HMAC-SHA256 covers that envelope plus sha256. The body is
preserved as JSON data. Authentication says nothing about a property's truth
or task success; observation/property/task schemas belong in the caller's body.

Custody: authority_dir/authority.json holds the 256-bit secret key, the external
anchor (n/head), the bound journal path and at most one pending receipt. Its
directory is mode 0700 and files 0600. The supervisor MUST keep the authority
directory, its parents, lock file, and this Python process outside candidate
mounts/access. Permissions alone do not isolate another process with the same
UID. Journal and authority directories must be disjoint. Their parent paths
must be controlled by the supervisor, not replaceable by a candidate.

Commit/recovery protocol (local filesystems with atomic rename and fsync):
1. Atomically replace and fsync authority.json with the authenticated pending
   receipt while retaining the old anchor.
2. Atomically replace and fsync the entire journal with that receipt appended.
3. Atomically replace and fsync authority.json with the new anchor, no pending.
All operations use a process lock plus flock on the stable authority lock file.
Restart, audit and subsequent operations finish a pending commit only if the
journal exactly matches the old anchored chain or that chain plus the pending
receipt. A truncated/tampered prefix or an untrusted torn tail is an error,
never a reason to reset a chain or silently discard bytes. Partial temporary
files from a killed writer are ignored; they can be removed by the supervisor
while no writer is active. Recovery is idempotent. An append which raises an
I/O error may already be durably pending/committed: audit records before retrying
the operation, using an attempt ID in the body to identify it.

The count is capped at 4096; overflow is explicit and never wraps identifiers.
This prototype rewrites and verifies the bounded journal per append. It limits
record count, not total body bytes; the supervisor must cap input/output sizes.
"""

from contextlib import contextmanager
import fcntl
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
from threading import RLock


MAX_RECORDS = 4096
GENESIS = '0' * 64
SCHEMA = 'pcworld.receipt.v1'
_AUTHORITY_SCHEMA = 'pcworld.authority.v1'
_LOCK = RLock()
_HEX = re.compile(r'[0-9a-f]{64}\Z')


class ReceiptError(RuntimeError):
    """Receipt custody or capacity failure."""


class ReceiptIntegrityError(ReceiptError):
    """The journal, authenticated pending append, or external anchor disagrees."""


class ReceiptLimitExceeded(ReceiptError):
    """The bounded receipt namespace is full; no receipt was discarded."""


def canonical(value) -> bytes:
    """Sorted, compact, finite JSON encoded as UTF-8, with string keys only.

    Reject coercions (tuple to list, integer to string key, etc.) so a caller's
    body is preserved without conflating distinguishable Python values.
    """
    active = set()

    def validate(item):
        kind = type(item)
        if item is None or kind in (str, bool, int):
            return
        if kind is float:
            if not math.isfinite(item):
                raise ValueError('non-finite numbers are not JSON')
            return
        if kind not in (dict, list):
            raise TypeError(f'not a JSON type: {kind.__name__}')
        identity = id(item)
        if identity in active:
            raise ValueError('cyclic value is not JSON')
        active.add(identity)
        try:
            if kind is dict:
                if any(type(key) is not str for key in item):
                    raise TypeError('JSON object keys must be strings')
                children = item.values()
            else:
                children = item
            for child in children:
                validate(child)
        finally:
            active.remove(identity)

    validate(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value) -> str:
    """Return the lowercase SHA-256 hex digest of canonical(value)."""
    return hashlib.sha256(canonical(value)).hexdigest()


def _decode(raw: bytes):
    def unique(pairs):
        result = {}
        for name, value in pairs:
            if name in result:
                raise ValueError('duplicate JSON key')
            result[name] = value
        return result

    def invalid_constant(value):
        raise ValueError(f'non-finite JSON constant: {value}')

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ReceiptIntegrityError('invalid JSON in receipt storage') from exc


def _regular(fd: int) -> None:
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ReceiptIntegrityError('storage must be a regular file without links')


@contextmanager
def _read_file(path: Path):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ReceiptIntegrityError(f'cannot safely read {path.name}') from exc
    try:
        _regular(fd)
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            yield stream
    finally:
        os.close(fd)


def _sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write(path: Path, data: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        remaining = memoryview(data)
        while remaining:
            written = os.write(fd, remaining)
            if written <= 0:
                raise OSError('short write to receipt storage')
            remaining = remaining[written:]
        os.fsync(fd)
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        os.close(fd)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


class ReceiptStore:
    """A bounded receipt chain with protected authentication and restart state."""

    def __init__(self, directory: Path, authority_dir: Path):
        directory, authority_dir = Path(directory), Path(authority_dir)
        if directory.is_symlink() or authority_dir.is_symlink():
            raise ValueError('storage directories must not be symlinks')
        self.directory = directory.resolve()
        self.authority_dir = authority_dir.resolve()
        if (self.directory.is_relative_to(self.authority_dir)
                or self.authority_dir.is_relative_to(self.directory)):
            raise ValueError('journal and authority directories must be disjoint')
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.authority_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.authority_dir.chmod(0o700)
        _sync_directory(self.directory.parent)
        _sync_directory(self.authority_dir.parent)
        self._journal = self.directory / 'receipts.jsonl'
        self._authority = self.authority_dir / 'authority.json'
        with self._locked():
            self._snapshot(initialize=True)

    @contextmanager
    def _locked(self):
        with _LOCK:
            try:
                fd = os.open(self.authority_dir / 'lock',
                             os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
            except OSError as exc:
                raise ReceiptIntegrityError('cannot safely open authority lock') from exc
            try:
                _regular(fd)
                fcntl.flock(fd, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def _state(self, initialize: bool) -> dict:
        try:
            with _read_file(self._authority) as stream:
                state = _decode(stream.read())
        except FileNotFoundError as exc:
            if not initialize:
                raise ReceiptIntegrityError('external authority is missing') from exc
            try:
                with _read_file(self._journal) as stream:
                    nonempty = bool(stream.read(1))
            except FileNotFoundError:
                nonempty = False
            if nonempty:
                raise ReceiptIntegrityError('cannot rekey an existing receipt journal') from exc
            state = {'schema': _AUTHORITY_SCHEMA, 'directory': str(self.directory),
                     'key': secrets.token_hex(32), 'n': 0, 'head': GENESIS, 'pending': None}
            _atomic_write(self._authority, canonical(state))
        if (type(state) is not dict
                or set(state) != {'schema', 'directory', 'key', 'n', 'head', 'pending'}
                or state['schema'] != _AUTHORITY_SCHEMA
                or state['directory'] != str(self.directory)
                or type(state['n']) is not int or not 0 <= state['n'] <= MAX_RECORDS
                or type(state['head']) is not str or not _HEX.fullmatch(state['head'])
                or type(state['key']) is not str or not _HEX.fullmatch(state['key'])
                or (state['n'] == 0 and state['head'] != GENESIS)):
            raise ReceiptIntegrityError('invalid or misplaced external authority')
        return state

    @staticmethod
    def _verify(record: dict, n: int, previous: str, key: bytes) -> None:
        if (type(record) is not dict
                or set(record) != {'schema', 'n', 'prev', 'body', 'sha256', 'hmac'}
                or record['schema'] != SCHEMA
                or type(record['n']) is not int or record['n'] != n
                or record['prev'] != previous or type(record['body']) is not dict
                or any(type(record[name]) is not str or not _HEX.fullmatch(record[name])
                       for name in ('sha256', 'hmac'))):
            raise ReceiptIntegrityError(f'invalid receipt envelope at sequence {n}')
        payload = {name: record[name] for name in ('schema', 'n', 'prev', 'body')}
        try:
            expected_digest = digest(payload)
            expected_mac = hmac.new(key, canonical(dict(payload, sha256=record['sha256'])),
                                    'sha256').hexdigest()
        except (TypeError, ValueError, RecursionError) as exc:
            raise ReceiptIntegrityError(f'invalid receipt body at sequence {n}') from exc
        if (not hmac.compare_digest(record['sha256'], expected_digest)
                or not hmac.compare_digest(record['hmac'], expected_mac)):
            raise ReceiptIntegrityError(f'receipt digest or HMAC mismatch at sequence {n}')

    def _records(self, key: bytes) -> list[dict]:
        records = []
        previous = GENESIS
        try:
            with _read_file(self._journal) as stream:
                for n, raw in enumerate(stream, start=1):
                    if n > MAX_RECORDS:
                        raise ReceiptIntegrityError('receipt count exceeds 4096')
                    record = _decode(raw)
                    self._verify(record, n, previous, key)
                    if raw != canonical(record) + b'\n':
                        raise ReceiptIntegrityError(f'noncanonical or torn receipt at sequence {n}')
                    records.append(record)
                    previous = record['sha256']
        except FileNotFoundError:
            pass
        return records

    @staticmethod
    def _matches_anchor(records: list[dict], state: dict) -> None:
        head = records[-1]['sha256'] if records else GENESIS
        if len(records) != state['n'] or head != state['head']:
            raise ReceiptIntegrityError('journal does not match external anchor (rewrite or suffix deletion)')

    def _finish_pending(self, state: dict, records: list[dict]) -> tuple[dict, list[dict]]:
        pending = state['pending']
        if state['n'] >= MAX_RECORDS:
            raise ReceiptIntegrityError('pending receipt exceeds 4096')
        self._verify(pending, state['n'] + 1, state['head'], bytes.fromhex(state['key']))
        self._matches_anchor(records[:state['n']], state)
        if len(records) == state['n']:
            records = records + [pending]
            _atomic_write(self._journal, b''.join(canonical(record) + b'\n' for record in records))
        elif len(records) != state['n'] + 1 or records[-1] != pending:
            raise ReceiptIntegrityError('journal tail does not match authenticated pending receipt')
        else:
            # A killed writer may have renamed the journal without syncing its
            # directory. Make that rename durable before clearing the pending
            # receipt; otherwise a later power loss could orphan the new anchor.
            _sync_directory(self.directory)
        state = dict(state, n=pending['n'], head=pending['sha256'], pending=None)
        _atomic_write(self._authority, canonical(state))
        return state, records

    def _snapshot(self, initialize: bool = False) -> tuple[dict, list[dict]]:
        state = self._state(initialize)
        records = self._records(bytes.fromhex(state['key']))
        if state['pending'] is not None:
            state, records = self._finish_pending(state, records)
        self._matches_anchor(records, state)
        return state, records

    def append(self, body: dict) -> dict:
        """Durably append a neutral JSON body or raise an explicit error."""
        if type(body) is not dict:
            raise ValueError('receipt body must be a JSON object')
        body = json.loads(canonical(body))
        with self._locked():
            state, records = self._snapshot()
            if state['n'] >= MAX_RECORDS:
                raise ReceiptLimitExceeded('receipt count limit 4096 reached')
            record = {'schema': SCHEMA, 'n': state['n'] + 1, 'prev': state['head'], 'body': body}
            record['sha256'] = digest(record)
            record['hmac'] = hmac.new(bytes.fromhex(state['key']), canonical(record), 'sha256').hexdigest()
            state = dict(state, pending=record)
            _atomic_write(self._authority, canonical(state))
            self._finish_pending(state, records)
            return record

    @property
    def records(self) -> list[dict]:
        """Fresh authenticated records; mutations of the returned list are local."""
        with self._locked():
            return self._snapshot()[1]

    @property
    def head(self) -> str:
        """Authenticated SHA-256 head, or 64 zeroes for an empty store."""
        with self._locked():
            return self._snapshot()[0]['head']

    def audit(self) -> dict:
        """Recover authorized pending work and report chain/custody integrity.

        On error count/head are None, not unauthenticated claims about data.
        ``ok`` describes storage integrity only, never semantic task success.
        """
        try:
            with self._locked():
                state, records = self._snapshot()
            return {'ok': True, 'count': len(records), 'head': state['head'], 'errors': []}
        except (ReceiptError, OSError) as exc:
            return {'ok': False, 'count': None, 'head': None, 'errors': [str(exc)]}
