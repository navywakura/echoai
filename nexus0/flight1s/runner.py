"""One host runner for ``preflight → bench → audit``.

Same discipline as the SIM-3 runner: it builds the pinned image only when
it is absent, never pulls a different one, and refuses to overwrite a
changed runtime lock without an explicit acknowledgement — so a host or a
PX4 change becomes visible before it can look like a comparable result.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

from echoai.nexus0.sim3.canon import canonical_sha256
from echoai.nexus0.flight1s import audit, bench
from echoai.nexus0.flight1s.runtime import (
    BASE_IMAGE_TAG,
    CONTAINERFILE,
    DEFAULT_LOCK,
    IMAGE_TAG,
    Runtime,
    load_lock,
    podman,
    preflight,
)


def _identity(lock: Dict) -> str:
    return canonical_sha256({
        "container": lock.get("container", {}),
        "px4": lock.get("px4", {}),
        "code": lock.get("code", {}),
    })


def _not_run(reason: str, next_command: str) -> Dict:
    return {"status": "not_run", "reason": reason, "next_command": next_command,
            "flight1s_green": False}


def ensure_image() -> Dict:
    pm = podman()
    if not pm:
        return _not_run("podman not on PATH", "install podman, then rerun")
    if not shutil.which("bwrap"):
        return _not_run("bwrap not on PATH (the SIM-3 regression needs it)",
                        "install bubblewrap, then rerun")
    have = subprocess.run([pm, "image", "exists", IMAGE_TAG]).returncode == 0
    if have:
        return {"status": "present", "image": IMAGE_TAG}
    if subprocess.run([pm, "image", "exists", BASE_IMAGE_TAG]).returncode != 0:
        return _not_run(f"base image {BASE_IMAGE_TAG} absent",
                        "build the SIM-3 image first, then rerun")
    proc = subprocess.run(
        [pm, "build", "--pull=never", "-t", IMAGE_TAG, "-f", str(CONTAINERFILE),
         str(CONTAINERFILE.parent)], capture_output=True, timeout=7200)
    if proc.returncode:
        return _not_run("image build failed: "
                        + proc.stderr.decode(errors="replace")[-500:],
                        "inspect the build log, then rerun")
    return {"status": "built", "image": IMAGE_TAG}


def run(*, lock_path: Path = DEFAULT_LOCK,
        report_path: Path = bench.DEFAULT_REPORT,
        protocol_path: Optional[Path] = None,
        accept_lock_change: bool = False, verbose: bool = True) -> Dict:
    image = ensure_image()
    if image["status"] == "not_run":
        return {"image": image, **image}

    previous = load_lock(lock_path) if Path(lock_path).exists() else Runtime(False)
    candidate = preflight(lock_path=lock_path, write=False)
    if not candidate.available:
        return {"image": image,
                **_not_run(candidate.reason, "fix the preflight cause and rerun")}
    changed = bool(previous.lock
                   and _identity(previous.lock) != _identity(candidate.lock))
    if changed and not accept_lock_change:
        return {"image": image, "status": "not_run", "flight1s_green": False,
                "reason": "runtime lock changed; the existing report is not "
                          "comparable",
                "previous_lock_sha256": previous.lock.get("lock_sha256"),
                "candidate_lock_sha256": candidate.lock.get("lock_sha256"),
                "next_command": "rerun with --accept-lock-change, then rerun "
                                "the full bank"}

    runtime = preflight(lock_path=lock_path, write=True)
    report = bench.run(report_path=report_path, protocol_path=protocol_path,
                       lock_path=lock_path, verbose=verbose)
    result = audit.run(report_path)
    return {
        "image": image,
        "status": "pass" if report["flight1s_green"] and result["evidence_valid"]
                  else "fail",
        "flight1s_green": report["flight1s_green"],
        "evidence_valid": result["evidence_valid"],
        "lock_sha256": runtime.lock["lock_sha256"],
        "report": str(report_path),
        "report_sha256": report["report_sha256"],
        "audit": result,
    }
