"""The v2 runtime lock, beside v1's and never on top of it.

The image, PX4, the models and the container are exactly v1's — v2
repairs a measurement contract, not a vehicle — so this reuses v1's
preflight probe wholesale and adds two things: the v2 code inventory,
which covers ``nexus0/flight1s/v2/*.py`` and the v2 schema on top of
every v1 file it depends on, and a recorded fingerprint of v1's own
inventory so that a v2 report carries proof that v1 was not disturbed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from echoai.nexus0.sim3.canon import (
    Sim3Error,
    canonical_sha256,
    dump_report,
    loads_strict,
    read_bounded,
    sha256_bytes,
)
from echoai.nexus0.flight1s import runtime as v1rt
from echoai.nexus0.flight1s.v2 import V1_CODE_SHA256

HERE = Path(__file__).resolve().parent
ECHOAI = v1rt.ECHOAI
DEFAULT_LOCK = ECHOAI / "lab" / "flight1s-v2" / "runtime-lock.json"
V2_SCHEMA = (ECHOAI / "docs" / "schemas" / "flight1s-v2"
             / "flight1s-protocol-v2.schema.json")

Runtime = v1rt.Runtime


def code_inventory() -> Tuple[List[Dict], str]:
    """v2's own files plus every v1 file a v2 episode actually executes."""
    v1_entries, v1_sha = v1rt.code_inventory()
    files: List[Path] = sorted(HERE.glob("*.py")) + [V2_SCHEMA]
    entries = [
        {"path": str(p.relative_to(ECHOAI)),
         "sha256": sha256_bytes(read_bounded(p, code="code"))}
        for p in files if p.exists()
    ]
    combined = {"v1": v1_entries, "v2": entries, "v1_code_sha256": v1_sha}
    return entries, canonical_sha256(combined)


def check_v1_undisturbed() -> Dict:
    """v1's inventory must still hash to what v1's report recorded."""
    _, v1_sha = v1rt.code_inventory()
    return {
        "expected": V1_CODE_SHA256,
        "observed": v1_sha,
        "ok": v1_sha == V1_CODE_SHA256,
        "note": "v1 hashes nexus0/flight1s/*.py with a non-recursive glob; v2 "
                "lives in a subpackage and edits none of those files",
    }


def preflight(*, lock_path: Optional[Path] = None, write: bool = True,
              protocol_sha256: Optional[str] = None) -> Runtime:
    base = v1rt.preflight(write=False)
    entries, code_sha = code_inventory()
    v1_state = check_v1_undisturbed()
    reasons = [base.reason] if base.reason else []
    if not v1_state["ok"]:
        reasons.append(
            f"v1 code inventory changed: {v1_state['observed']} != "
            f"{v1_state['expected']}; v2 must not disturb v1")

    lock = {
        "schema_version": 2,
        "scope": "flight_software_in_the_loop",
        "slice": "FLIGHT-1S",
        "protocol_version": 2,
        "protocol_sha256": protocol_sha256 or "",
        "host": base.lock.get("host", {}),
        "container": base.lock.get("container", {}),
        "px4": base.lock.get("px4", {}),
        "code": {"files": entries, "code_sha256": code_sha},
        "v1": {
            "code_sha256": v1_state["observed"],
            "expected_code_sha256": v1_state["expected"],
            "undisturbed": v1_state["ok"],
            "files": base.lock.get("code", {}).get("files", []),
        },
        "fuel_downloads": False,
        "network_during_bench": False,
        "available": not reasons,
        "reason": "; ".join(reasons),
    }
    lock["lock_sha256"] = canonical_sha256(
        {k: v for k, v in lock.items() if k != "lock_sha256"})
    if write:
        dump_report(Path(lock_path or DEFAULT_LOCK), lock)
    return Runtime(available=not reasons, reason="; ".join(reasons), lock=lock)


def load_lock(path: Optional[Path] = None) -> Runtime:
    p = Path(path or DEFAULT_LOCK)
    if not p.exists():
        return Runtime(available=False, reason=f"no lock at {p}")
    lock = loads_strict(read_bounded(p, code="lock"), code="lock")
    fresh = canonical_sha256({k: v for k, v in lock.items()
                              if k != "lock_sha256"})
    if fresh != lock.get("lock_sha256"):
        raise Sim3Error("lock_tampered", f"recomputed {fresh}")
    if int(lock.get("protocol_version", 0)) != 2:
        raise Sim3Error("lock_not_v2", str(lock.get("protocol_version")))
    return Runtime(available=bool(lock.get("available")),
                   reason=str(lock.get("reason", "")), lock=lock)
