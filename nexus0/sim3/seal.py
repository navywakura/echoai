"""Commitments, derived seeds, and an exam you can only open once.

Three separate mechanisms, deliberately not merged:

* **commitment to the protocol** — publish ``SHA256(tag || protocol
  digest || secret)`` before anything is generated, so the rules cannot
  be rewritten afterwards;
* **seed derivation** — ``HMAC-SHA256(secret, tag || split || index)``,
  so seeds are reproducible by the custodian and unguessable by anyone
  else;
* **inventory commitment plus a sealed→opened→consumed latch** — so a C
  partition is opened exactly once, by one process, and stays consumed
  even if that process dies mid-run.

SIM-3 exercises all three with a **rehearsal** secret that is published
on purpose (32 bytes of ``0x01``). A hash alone is not custody: the
custodian and the access log live outside this file, and outside this
repository.
"""

from __future__ import annotations

import fcntl
import hashlib
import hmac
import os
import secrets
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, Sequence

from echoai.nexus0.sim3.canon import (
    COMMIT_TAG,
    INVENTORY_TAG,
    SEED_TAG,
    Sim3Error,
    canonical_bytes,
    loads_strict,
    read_bounded,
    sha256_bytes,
)

# Published on purpose. Rehearsal only: it proves the machinery, and it
# proves nothing about a campaign, because everyone can recompute it.
REHEARSAL_SECRET = bytes([0x01]) * 32
REHEARSAL_SALT = bytes([0x02]) * 32

SPLITS = ("A", "B", "C")
STATE_SEALED = "sealed"
STATE_OPENED = "opened"
STATE_CONSUMED = "consumed"


def protocol_commitment(protocol_sha256: str, secret: bytes) -> str:
    """``SHA256(b"SIM3/v1/commit\\0" + protocol_digest + secret)``."""
    digest = bytes.fromhex(protocol_sha256)
    if len(digest) != 32:
        raise Sim3Error("commit_digest_length", protocol_sha256)
    if len(secret) != 32:
        raise Sim3Error("commit_secret_length", str(len(secret)))
    return sha256_bytes(COMMIT_TAG + digest + secret)


def derive_seed(secret: bytes, split: str, index: int) -> int:
    """First 8 bytes of the HMAC, big-endian. Nothing else."""
    if split not in SPLITS:
        raise Sim3Error("seed_split", split)
    if not 0 <= index < 2 ** 32:
        raise Sim3Error("seed_index", str(index))
    msg = SEED_TAG + split.encode("ascii") + b"\0" + index.to_bytes(4, "big")
    mac = hmac.new(secret, msg, hashlib.sha256).digest()
    return int.from_bytes(mac[:8], "big")


def inventory_bytes(entries: Sequence[Dict]) -> bytes:
    """Canonical JSON of the ordered hash inventory. Integers and strings."""
    ordered = sorted(entries, key=lambda e: (e["split"], e["index"]))
    return canonical_bytes(ordered)


def inventory_commitment(salt: bytes, inventory: bytes) -> str:
    if len(salt) != 32:
        raise Sim3Error("inventory_salt_length", str(len(salt)))
    return sha256_bytes(INVENTORY_TAG + salt + inventory)


def new_secret() -> bytes:
    """256 bits from the OS. Used by a custodian, never by the bench."""
    return secrets.token_bytes(32)


@dataclass
class SealState:
    path: Path
    data: Dict

    @property
    def state(self) -> str:
        return str(self.data["state"])


def _atomic_write(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(canonical_bytes(payload))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def seal(path: Path, *, split: str, commitment: str, inventory_sha256: str,
         custodian: str, n_packages: int) -> SealState:
    """Create a latch in ``sealed``. Refuses to overwrite an existing one."""
    p = Path(path)
    if p.exists():
        raise Sim3Error("seal_exists", str(p))
    payload = {
        "schema_version": 1,
        "split": split,
        "state": STATE_SEALED,
        "commitment": commitment,
        "inventory_sha256": inventory_sha256,
        "custodian": custodian,
        "n_packages": int(n_packages),
        "opens": 0,
        "crash_recovered": 0,
    }
    _atomic_write(p, payload)
    return SealState(path=p, data=payload)


def read_seal(path: Path) -> SealState:
    p = Path(path)
    data = loads_strict(read_bounded(p, code="seal"), code="seal")
    return SealState(path=p, data=data)


@contextmanager
def open_once(path: Path) -> Iterator[SealState]:
    """Open a sealed partition exactly once, under an exclusive lock.

    The transition is written before the caller sees the contents, and
    ``consumed`` is written on the way out whether or not the body
    raised. A process that dies between the two leaves ``opened`` on
    disk; the next reader records ``crash_recovered`` and treats it as
    consumed. A partially used exam is a used exam.
    """
    p = Path(path)
    lock = p.with_suffix(p.suffix + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Sim3Error("seal_busy", str(p)) from None
        state = read_seal(p)
        if state.state == STATE_OPENED:
            state.data["state"] = STATE_CONSUMED
            state.data["crash_recovered"] = int(state.data.get("crash_recovered", 0)) + 1
            _atomic_write(p, state.data)
            raise Sim3Error("seal_crash_consumed", str(p))
        if state.state != STATE_SEALED:
            raise Sim3Error("seal_already_consumed", state.state)
        state.data["state"] = STATE_OPENED
        state.data["opens"] = int(state.data.get("opens", 0)) + 1
        _atomic_write(p, state.data)
        try:
            yield state
        finally:
            state.data["state"] = STATE_CONSUMED
            _atomic_write(p, state.data)
    finally:
        os.close(fd)


def verify_inventory(state: SealState, entries: Sequence[Dict], salt: bytes) -> None:
    raw = inventory_bytes(entries)
    if sha256_bytes(raw) != state.data["inventory_sha256"]:
        raise Sim3Error("inventory_mismatch", sha256_bytes(raw))
    _ = inventory_commitment(salt, raw)
