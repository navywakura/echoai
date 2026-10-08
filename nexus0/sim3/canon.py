"""Bytes first, structure second.

Every hash SIM-3 publishes is over bytes that exist on disk, taken before
anything parses them. Every canonical form is a byte string with a fixed
recipe, so an auditor can rebuild it without trusting our parser.

Rules that are easy to get wrong and are therefore enforced here:

* a file larger than ``MAX_FILE_BYTES`` is refused before it is read into
  a parser at all;
* duplicate JSON keys are an error, not a last-one-wins;
* ``NaN``/``Infinity`` are an error, in both directions;
* a path inside a package may not escape it, and may not be a symlink.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

MAX_FILE_BYTES = 1 << 20  # 1 MiB, per the sim3-boxes-v1 profile.

COMMIT_TAG = b"SIM3/v1/commit\0"
SEED_TAG = b"SIM3/v1/seed\0"
INVENTORY_TAG = b"SIM3/v1/inventory\0"


class Sim3Error(Exception):
    """A refusal with a machine-readable cause.

    `code` is what the bench and the mutant table match on; `detail` is
    for a human reading a red report.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = str(code)
        self.detail = str(detail)

    def as_dict(self) -> Dict[str, str]:
        return {"code": self.code, "detail": self.detail}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_bounded(path: Path, *, code: str = "file") -> bytes:
    """Read a regular file, refusing symlinks and oversize inputs.

    The size check happens on the directory entry, so a 4 GiB world.sdf
    never reaches memory. ``lstat`` rather than ``stat``: a symlink that
    points at a small file is still a symlink.
    """
    p = Path(path)
    try:
        st = os.lstat(p)
    except OSError as exc:
        raise Sim3Error(f"{code}_missing", f"{p}: {exc.strerror}") from None
    if os.path.stat.S_ISLNK(st.st_mode):
        raise Sim3Error(f"{code}_symlink", str(p))
    if not os.path.stat.S_ISREG(st.st_mode):
        raise Sim3Error(f"{code}_not_regular", str(p))
    if st.st_size > MAX_FILE_BYTES:
        raise Sim3Error(f"{code}_too_large", f"{p}: {st.st_size} > {MAX_FILE_BYTES}")
    with open(p, "rb") as fh:
        return fh.read()


def safe_child(package_dir: Path, name: str, *, code: str = "path") -> Path:
    """Resolve exactly one allowed file name inside a package.

    ``world.sdf`` is a name, not a path that gets concatenated: a slash,
    a ``..`` or a symlinked directory component is refused rather than
    normalised away.
    """
    if name in ("", ".", "..") or "/" in name or "\\" in name or "\0" in name:
        raise Sim3Error(f"{code}_not_a_name", repr(name))
    base = Path(package_dir)
    if base.is_symlink():
        raise Sim3Error(f"{code}_package_symlink", str(base))
    child = base / name
    real_base = os.path.realpath(base)
    real_child = os.path.realpath(child)
    if os.path.commonpath([real_base, real_child]) != real_base:
        raise Sim3Error(f"{code}_escapes_package", str(child))
    if real_child == real_base:
        raise Sim3Error(f"{code}_is_package", str(child))
    return child


def _no_duplicates(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    seen: Dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise Sim3Error("json_duplicate_key", key)
        seen[key] = value
    return seen


def _no_constants(text: str) -> Any:
    raise Sim3Error("json_non_finite", text)


def loads_strict(data: bytes, *, code: str = "json") -> Any:
    """Parse JSON with duplicate keys and non-finite numbers refused."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Sim3Error(f"{code}_not_utf8", str(exc)) from None
    try:
        value = json.loads(
            text,
            object_pairs_hook=_no_duplicates,
            parse_constant=_no_constants,
        )
    except Sim3Error:
        raise
    except json.JSONDecodeError as exc:
        raise Sim3Error(f"{code}_malformed", str(exc)) from None
    _reject_non_finite(value, code)
    return value


def _reject_non_finite(value: Any, code: str) -> None:
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise Sim3Error(f"{code}_non_finite", repr(value))
    elif isinstance(value, dict):
        for item in value.values():
            _reject_non_finite(item, code)
    elif isinstance(value, list):
        for item in value:
            _reject_non_finite(item, code)


def canonical_bytes(value: Any) -> bytes:
    """UTF-8 JSON, sorted keys, no whitespace, integers and strings only.

    The inventory commitment in SIM3-DESIGN.md §5.4 names this exact
    shape, so it refuses floats outright rather than emitting a repr an
    auditor in another language would have to guess at.
    """
    _reject_floats(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _reject_floats(value: Any) -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, float):
        raise Sim3Error("canonical_float", repr(value))
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise Sim3Error("canonical_key", repr(key))
            _reject_floats(item)
    elif isinstance(value, list):
        for item in value:
            _reject_floats(item)


def canonical_sha256(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def report_bytes(value: Any) -> bytes:
    """Canonical form for a report digest, floats included.

    ``canonical_bytes`` refuses floats because the inventory commitment in
    SIM3-DESIGN.md §5.4 is specified over integers and strings only. A
    report carries measurements — millimetres of fall, seconds of launch —
    and hashing those needs a rule rather than a ban. The rule: JSON with
    sorted keys, no whitespace, no NaN/Infinity, and Python's shortest
    round-trip float repr, which is the same shortest-round-trip form
    every modern language produces for a double.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def report_sha256(value: Any) -> str:
    return sha256_bytes(report_bytes(value))


def dump_report(path: Path, value: Any) -> bytes:
    """Write a report the auditor can re-hash. Pretty, but stable."""
    data = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False)
    data += "\n"
    raw = data.encode("utf-8")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        fh.write(raw)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
    return raw
