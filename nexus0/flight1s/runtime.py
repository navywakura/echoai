"""Preflight for FLIGHT-1S: PX4 and Gazebo, or an explicit not_run.

The lock is separate from SIM-3's on purpose. FLIGHT-1S composes: its
image is built FROM the frozen SIM-3 image and adds PX4, so the SIM-3
lock and its report stay reproducible and untouched. What this file adds
to the record is everything that makes a flight result comparable — the
PX4 commit, the models submodule commit, the hashes of the body and the
world assets, the toolchain that compiled it, and the image digest.

A missing dependency produces ``available=false`` and a reason. Never a
substitute: there is no Python flight model, no mock MAVLink and no
synthetic pose anywhere in this package.
"""

from __future__ import annotations

import hashlib
import os
import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0.sim3.canon import (
    Sim3Error,
    canonical_sha256,
    dump_report,
    loads_strict,
    read_bounded,
    sha256_bytes,
)

HERE = Path(__file__).resolve().parent
ECHOAI = HERE.parents[1]
IMAGE_TAG = "echoai-flight1s-px4:v1.15.4"
BASE_IMAGE_TAG = "echoai-sim3-gz:harmonic"
CONTAINERFILE = HERE / "container" / "Containerfile"
RUNNER = HERE / "assets" / "flightrunner.py"
DEFAULT_LOCK = ECHOAI / "lab" / "flight1s" / "runtime-lock.json"

PX4_TAG = "v1.15.4"
PX4_COMMIT = "99c40407ffd7ac184e2d7b4b293f36f10fe561ef"
PX4_MODELS_COMMIT = "d754381a1cecdd7f17050acd72bf5bf1327bced6"
PX4_ROOT = "/opt/PX4-Autopilot"
MODEL_DIR = f"{PX4_ROOT}/Tools/simulation/gz/models"

# Assets whose bytes decide how the body behaves. Hashed inside the image
# so a swapped model cannot pass as the same experiment.
BODY_ASSETS = (
    f"{MODEL_DIR}/x500/model.sdf",
    f"{MODEL_DIR}/x500_base/model.sdf",
    f"{PX4_ROOT}/ROMFS/px4fmu_common/init.d-posix/airframes/4001_gz_x500",
)

PINNED_PACKAGES = (
    "gz-harmonic", "libgz-sim8", "libsdformat14", "libgz-transport13",
    "libgz-physics7-dartsim", "libgz-msgs10", "python3-gz-sim8",
    "python3-gz-transport13", "python3-gz-msgs10", "cppzmq-dev",
    "cmake", "ninja-build", "g++", "python3",
)


def _run(cmd: Sequence[str], *, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), capture_output=True, timeout=timeout)


def podman() -> Optional[str]:
    return shutil.which("podman")


def code_inventory() -> Tuple[List[Dict], str]:
    """Hash every file of ours that takes part in a flight run."""
    files: List[Path] = sorted(HERE.glob("*.py"))
    files += [RUNNER, CONTAINERFILE]
    files += sorted((ECHOAI / "docs" / "schemas").glob("flight1s-*.schema.json"))
    entries = [
        {"path": str(p.relative_to(ECHOAI)),
         "sha256": sha256_bytes(read_bounded(p, code="code"))}
        for p in files if p.exists()
    ]
    return entries, canonical_sha256(entries)


@dataclass
class Runtime:
    available: bool
    reason: str = ""
    lock: Dict = field(default_factory=dict)

    @property
    def image(self) -> str:
        return str(self.lock.get("container", {}).get("image", IMAGE_TAG))

    def require(self) -> None:
        if not self.available:
            raise Sim3Error("flight_runtime_unavailable", self.reason)


def _image_info(pm: str, tag: str) -> Optional[Dict]:
    proc = _run([pm, "image", "inspect", tag, "--format", "{{.Id}}|{{.Digest}}"])
    if proc.returncode != 0:
        return None
    parts = proc.stdout.decode().strip().split("|")
    return {"id": parts[0], "digest": parts[1] if len(parts) > 1 else ""}


def _inside(pm: str) -> Dict:
    """Ask the image what it actually contains. No guessing from the recipe."""
    script = (
        "set -e; cat /opt/px4-commit.txt; echo '---'; "
        "cd /opt/PX4-Autopilot && git submodule status Tools/simulation/gz "
        "| awk '{print $1}'; echo '---'; "
        "gz sim --versions | head -1; echo '---'; "
        "dpkg-query -W -f='${Package} ${Version}\\n' " + " ".join(PINNED_PACKAGES)
        + " 2>/dev/null; echo '---'; "
        "for f in " + " ".join(BODY_ASSETS) + "; do "
        "echo \"$f $(sha256sum $f | cut -d' ' -f1)\"; done; echo '---'; "
        "sha256sum /opt/PX4-Autopilot/build/px4_sitl_default/bin/px4 "
        "| cut -d' ' -f1; echo '---'; "
        "python3 -c 'import sys;print(sys.version.split()[0])'; echo '---'; "
        "g++ --version | head -1; cmake --version | head -1; "
        "ninja --version; python3 -c \"import pymavlink;print(pymavlink.__version__)\"; "
        "echo '---'; uname -m"
    )
    proc = _run([pm, "run", "--rm", "--pull=never", "--network=none",
                 "--security-opt", "label=disable", IMAGE_TAG, "bash", "-lc", script],
                timeout=300)
    if proc.returncode != 0:
        raise Sim3Error("flight_container_probe_failed",
                        proc.stderr.decode()[-400:])
    blocks = proc.stdout.decode().split("---")
    packages = {}
    for line in blocks[3].strip().splitlines():
        name, _, version = line.partition(" ")
        if name:
            packages[name] = version
    assets = {}
    for line in blocks[4].strip().splitlines():
        path, _, digest = line.rpartition(" ")
        if path:
            assets[path.strip()] = digest.strip()
    toolchain = [t for t in blocks[7].strip().splitlines() if t]
    return {
        "px4_commit": blocks[0].strip(),
        "px4_models_commit": blocks[1].strip().lstrip("+-"),
        "gz_sim_version": blocks[2].strip(),
        "packages": packages,
        "body_assets_sha256": assets,
        "px4_binary_sha256": blocks[5].strip(),
        "python": blocks[6].strip(),
        "toolchain": toolchain,
        "arch": blocks[8].strip(),
    }


def preflight(*, lock_path: Optional[Path] = None, write: bool = True) -> Runtime:
    entries, code_sha = code_inventory()
    host = {
        "os": platform.platform(),
        "kernel": platform.release(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }
    reasons: List[str] = []
    container: Dict = {}
    pm = podman()
    if pm is None:
        reasons.append("podman not on PATH")
    else:
        container["podman"] = _run([pm, "--version"]).stdout.decode().strip()
        base = _image_info(pm, BASE_IMAGE_TAG)
        image = _image_info(pm, IMAGE_TAG)
        if base is None:
            reasons.append(f"base image {BASE_IMAGE_TAG} absent; build SIM-3 first")
        if image is None:
            reasons.append(
                f"image {IMAGE_TAG} absent; build it with: podman build -t "
                f"{IMAGE_TAG} -f {CONTAINERFILE.relative_to(ECHOAI)} "
                f"{CONTAINERFILE.parent.relative_to(ECHOAI)}")
        else:
            container.update({
                "image": IMAGE_TAG,
                "image_id": image["id"],
                "image_digest": image["digest"],
                "base_image": BASE_IMAGE_TAG,
                "base_image_id": (base or {}).get("id", ""),
            })
            inside = _inside(pm)
            container.update(inside)
            if inside["px4_commit"] != PX4_COMMIT:
                reasons.append(
                    f"px4 commit {inside['px4_commit']} != pinned {PX4_COMMIT}")
            if inside["px4_models_commit"] != PX4_MODELS_COMMIT:
                reasons.append(
                    f"px4 models commit {inside['px4_models_commit']} != pinned "
                    f"{PX4_MODELS_COMMIT}")
    if shutil.which("bwrap") is None:
        # Not used to cage a consumer here, but the SIM-3 regression needs it
        # and a host without it cannot close the slice.
        reasons.append("bwrap not on PATH (needed by the SIM-3 regression)")

    lock = {
        "schema_version": 1,
        "scope": "flight_software_in_the_loop",
        "slice": "FLIGHT-1S",
        "host": host,
        "container": container,
        "px4": {"tag": PX4_TAG, "commit": PX4_COMMIT,
                "models_commit": PX4_MODELS_COMMIT,
                "build": "px4_sitl_default", "airframe": 4001,
                "licence": "BSD-3-Clause (PX4-Autopilot, PX4-gazebo-models)"},
        "code": {"files": entries, "code_sha256": code_sha},
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
    fresh = canonical_sha256({k: v for k, v in lock.items() if k != "lock_sha256"})
    if fresh != lock.get("lock_sha256"):
        raise Sim3Error("lock_tampered", f"recomputed {fresh}")
    return Runtime(available=bool(lock.get("available")),
                   reason=str(lock.get("reason", "")), lock=lock)
