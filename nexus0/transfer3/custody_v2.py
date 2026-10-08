"""Bound, ordered PUBLIC custody fixture. Real campaigns fail closed.

This API provides sequencing, not access control against its own OS user.
Actual custody needs an external principal; no string or callback proves it.
Frozen SIM3/custody v1 remain unchanged for historical reproduction.
"""
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import os
from pathlib import Path

from echoai.nexus0.sim3.canon import canonical_bytes, sha256_bytes
from echoai.nexus0.sim3.seal import open_once, seal, inventory_bytes
from .custody import validate_notice, verify_reveal, digest


def validate_public_fixture(notice):
    validate_notice(notice)
    if notice['kind'] != 'rehearsal':
        raise ValueError('campaign disabled: external custody integration required')


def seal_fixture(path, notice, split, inventory_sha256):
    validate_public_fixture(notice)
    if split not in ('B', 'C'):
        raise ValueError('reserved split')
    digest(inventory_sha256)
    # Use the same lock as open_once, including initial creation, avoiding
    # simultaneous creators replacing each other's seals.
    path = Path(path)
    lock = path.with_suffix(path.suffix+'.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        row = notice['splits'][split]
        # Bind the entire notice (protocol, publication, split commitments),
        # not just an unverified custodian string, in the existing seal field.
        binding = 'public-notice-sha256:'+sha256_bytes(canonical_bytes(notice))
        return seal(path, split=split, commitment=row['inventory_commitment'],
                    inventory_sha256=inventory_sha256, custodian=binding,
                    n_packages=row['count'])
    finally:
        os.close(fd)


@contextmanager
def open_verified_fixture(path, notice, split, reveal):
    """Call reveal ONLY under the opened latch; verify before yielding data.

    Wrong notice/inventory/salt or callback errors consume the attempted exam.
    The caller supplies a loader, never a pre-read inventory. No public
    verification endpoint accepts a merely fabricated 'opened' SealState.
    """
    notice = deepcopy(notice)
    validate_public_fixture(notice)
    if split not in ('B', 'C') or not callable(reveal):
        raise ValueError('split/reveal loader')
    with open_once(Path(path)) as state:
        row = notice['splits'][split]
        binding = 'public-notice-sha256:'+sha256_bytes(canonical_bytes(notice))
        if (state.data['split'] != split or state.data['commitment'] != row['inventory_commitment']
                or state.data['n_packages'] != row['count'] or state.data['custodian'] != binding):
            raise ValueError('notice/latch binding mismatch')
        entries, salt = reveal()
        entries = deepcopy(entries)
        actual = verify_reveal(notice, split, entries, salt)
        if actual != state.data['inventory_sha256']:
            raise ValueError('revealed inventory/latch mismatch')
        # Both the salted public commitment and existing latch hash now match.
        yield dict(entries=entries, inventory_sha256=sha256_bytes(inventory_bytes(entries)))
