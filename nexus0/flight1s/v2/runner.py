"""One host runner for the v2 chain: preflight → bench → audit.

Refuses to overwrite a changed lock without an explicit acknowledgement,
and refuses outright if v1's code inventory has moved: v2 exists to
repair a contract, not to disturb the evidence it repairs.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from echoai.nexus0.sim3.canon import canonical_sha256
from echoai.nexus0.flight1s.runner import ensure_image
from echoai.nexus0.flight1s.v2 import audit, bench, protocol as protomod
from echoai.nexus0.flight1s.v2.runtime import (
    DEFAULT_LOCK,
    Runtime,
    check_v1_undisturbed,
    load_lock,
    preflight,
)


def _identity(lock: Dict) -> str:
    return canonical_sha256({"container": lock.get("container", {}),
                             "px4": lock.get("px4", {}),
                             "code": lock.get("code", {})})


def _not_run(reason: str, next_command: str) -> Dict:
    return {"status": "not_run", "reason": reason, "next_command": next_command,
            "flight1s_green": False}


def run(*, lock_path: Path = DEFAULT_LOCK,
        report_path: Path = bench.DEFAULT_REPORT,
        protocol_path: Optional[Path] = None,
        accept_lock_change: bool = False, verbose: bool = True) -> Dict:
    v1_state = check_v1_undisturbed()
    if not v1_state["ok"]:
        return {"v1": v1_state,
                **_not_run("the v1 code inventory changed; v2 must not disturb "
                           "the evidence it repairs",
                           "restore nexus0/flight1s/*.py and rerun")}
    image = ensure_image()
    if image["status"] == "not_run":
        return {"image": image, "v1": v1_state, **image}

    proto = protomod.load(protocol_path)
    previous = load_lock(lock_path) if Path(lock_path).exists() else Runtime(False)
    candidate = preflight(lock_path=lock_path, write=False,
                          protocol_sha256=proto.sha256)
    if not candidate.available:
        return {"image": image, "v1": v1_state,
                **_not_run(candidate.reason, "fix the preflight cause and rerun")}
    changed = bool(previous.lock
                   and _identity(previous.lock) != _identity(candidate.lock))
    if changed and not accept_lock_change:
        return {"image": image, "v1": v1_state, "status": "not_run",
                "flight1s_green": False,
                "reason": "runtime lock changed; the existing v2 report is not "
                          "comparable",
                "previous_lock_sha256": previous.lock.get("lock_sha256"),
                "candidate_lock_sha256": candidate.lock.get("lock_sha256"),
                "next_command": "rerun with --accept-lock-change, then rerun "
                                "the full bank"}

    runtime = preflight(lock_path=lock_path, write=True,
                        protocol_sha256=proto.sha256)
    report = bench.run(report_path=report_path, protocol_path=protocol_path,
                       lock_path=lock_path, verbose=verbose)
    result = audit.run(report_path)
    return {
        "image": image, "v1": v1_state,
        "status": "pass" if report["flight1s_green"] and result["evidence_valid"]
                  else "fail",
        "flight1s_green": report["flight1s_green"],
        "evidence_valid": result["evidence_valid"],
        "lock_sha256": runtime.lock["lock_sha256"],
        "protocol_sha256": proto.sha256,
        "report": str(report_path),
        "report_sha256": report["report_sha256"],
        "audit": result,
    }
