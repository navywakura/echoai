"""One host runner for ``preflight → bench → audit``.

It builds the pinned local image only when it is absent. It never pulls a
different image, and it refuses to overwrite a changed runtime lock without
an explicit acknowledgement. That makes a host/runtime change visible before
it can become an apparently comparable report.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional

from echoai.nexus0.sim3 import audit, bench
from echoai.nexus0.sim3.canon import canonical_sha256
from echoai.nexus0.sim3.runtime import (
    CONTAINERFILE,
    DEFAULT_LOCK,
    ECHOAI,
    IMAGE_TAG,
    Runtime,
    _image_digest,
    _podman,
    load_lock,
    preflight,
)


def _runtime_identity(lock: Dict) -> str:
    """Everything that makes results non-comparable, including our code."""
    return canonical_sha256({
        "container": lock.get("container", {}),
        "sandbox": lock.get("sandbox", {}),
        "code": lock.get("code", {}),
        "fuel_downloads": lock.get("fuel_downloads"),
    })


def _not_run(reason: str, next_command: str) -> Dict:
    return {"status": "not_run", "reason": reason, "next_command": next_command,
            "sim3_green": False}


def ensure_image() -> Dict:
    podman = _podman()
    if not podman:
        return _not_run("podman not on PATH", "install podman, then rerun sim3 runner")
    if not shutil.which("bwrap"):
        return _not_run("bwrap not on PATH", "install bubblewrap, then rerun sim3 runner")
    try:
        if _image_digest(podman):
            return {"status": "present", "image": IMAGE_TAG}
        # The base image is digest-pinned. --pull=never prevents an unnoticed
        # network refresh from changing an experimental host during a rerun.
        proc = subprocess.run(
            [podman, "build", "--pull=never", "-t", IMAGE_TAG,
             "-f", str(CONTAINERFILE), str(CONTAINERFILE.parent)],
            capture_output=True, timeout=1800,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _not_run(f"image build could not start: {exc}",
                        "pre-provision the digest-pinned base image and rerun")
    if proc.returncode:
        return _not_run("image build failed: " + proc.stderr.decode(errors="replace")[-500:],
                        "pre-provision the digest-pinned base image, then rerun")
    return {"status": "built", "image": IMAGE_TAG}


def run(*, lock_path: Path = DEFAULT_LOCK, report_path: Path = bench.DEFAULT_REPORT,
        protocol_path: Path = bench.EXAMPLE_PROTOCOL,
        accept_lock_change: bool = False, verbose: bool = True) -> Dict:
    image = ensure_image()
    if image["status"] == "not_run":
        return {"image": image, **image}

    previous = load_lock(lock_path) if Path(lock_path).exists() else Runtime(False)
    candidate = preflight(lock_path=lock_path, write=False)
    if not candidate.available:
        return {"image": image, **_not_run(candidate.reason,
                "fix the preflight cause and rerun sim3 runner")}
    changed = bool(previous.lock and _runtime_identity(previous.lock)
                   != _runtime_identity(candidate.lock))
    if changed and not accept_lock_change:
        return {"image": image, "status": "not_run", "sim3_green": False,
                "reason": "runtime lock changed; existing report is not comparable",
                "previous_lock_sha256": previous.lock.get("lock_sha256"),
                "candidate_lock_sha256": candidate.lock.get("lock_sha256"),
                "next_command": "rerun with --accept-lock-change, then rerun the full bank"}

    # Write only after all comparisons above. Bench itself verifies this exact
    # code inventory before it executes a single backend episode.
    runtime = preflight(lock_path=lock_path, write=True)
    report = bench.run(report_path=report_path, protocol_path=protocol_path,
                       lock_path=lock_path, verbose=verbose)
    audit_result = audit.run(report_path)
    return {
        "image": image,
        "status": "pass" if report["sim3_green"] and audit_result["evidence_valid"] else "fail",
        "sim3_green": report["sim3_green"],
        "evidence_valid": audit_result["evidence_valid"],
        "lock_sha256": runtime.lock["lock_sha256"],
        "report": str(report_path),
        "report_sha256": report["report_sha256"],
        "audit": audit_result,
    }
