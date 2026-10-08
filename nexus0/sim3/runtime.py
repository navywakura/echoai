"""Preflight: find the real tools, or say plainly that they are missing.

``runtime-lock.json`` is the answer to "what actually ran". It records
the host, the container image digest, the exact Debian package versions
of gz-sim, libsdformat and gz-transport inside it, the Python that drove
them, the sandbox binary and the hashes of every file of ours that took
part. ``latest`` appears nowhere and no Fuel asset is fetched.

A missing dependency produces ``available=false`` and a reason. It never
produces a substitute: SIM-3 would rather publish ``not_run`` than a
number a mock invented.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import tempfile
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
IMAGE = "localhost/echoai-sim3-gz:harmonic"
IMAGE_TAG = "echoai-sim3-gz:harmonic"
CONTAINERFILE = HERE / "container" / "Containerfile"
RUNNER = HERE / "assets" / "gzrunner.py"
PROBE = HERE / "assets" / "probe.py"
PROBE_ABUSIVE = HERE / "assets" / "probe_abusive.py"
DEFAULT_LOCK = ECHOAI / "lab" / "sim3" / "runtime-lock.json"

PINNED_PACKAGES = (
    "gz-harmonic", "gz-sim8-cli", "libgz-sim8", "libsdformat14",
    "libgz-transport13", "libgz-physics7-dartsim", "libgz-msgs10",
    "python3-gz-sim8", "python3-gz-transport13", "python3-gz-msgs10",
    "python3",
)

# What the consumer sandbox is allowed to see. Anything outside this list
# failing to be absent is an isolation failure, not a warning.
SANDBOX_ENV = {"PATH": "/usr/bin", "LANG": "C.UTF-8", "HOME": "/work"}
# bwrap itself exports PWD when it honours --chdir, so the expected set is
# the allowlist plus that one. Anything else appearing is a leak.
SANDBOX_ENV_EXPECTED = {**SANDBOX_ENV, "PWD": "/work"}
SANDBOX_ARGV = ["/usr/bin/python3", "/probe/probe.py"]
# What the consumer sees in ``sys.argv``: the interpreter is argv[0] of the
# process, not of the script.
SANDBOX_CONSUMER_ARGV = ["/probe/probe.py"]
SANDBOX_HOSTNAME = "sim3"


def _run(cmd: Sequence[str], *, timeout: int = 120,
         stdin: Optional[bytes] = None) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), capture_output=True, timeout=timeout,
                          input=stdin)


def code_inventory() -> Tuple[List[Dict], str]:
    """Hash every file of ours that participates in a run."""
    files: List[Path] = sorted(HERE.glob("*.py"))
    files += [RUNNER, PROBE, PROBE_ABUSIVE, CONTAINERFILE]
    schema_dir = ECHOAI / "docs" / "schemas"
    files += sorted(schema_dir.glob("sim3-*.schema.json"))
    files += [schema_dir / "echo3-slice.schema.json"]
    entries = []
    for path in files:
        if not path.exists():
            continue
        entries.append({
            "path": str(path.relative_to(ECHOAI)),
            "sha256": sha256_bytes(read_bounded(path, code="code")),
        })
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
            raise Sim3Error("runtime_unavailable", self.reason)


def _podman() -> Optional[str]:
    return shutil.which("podman")


def _image_digest(podman: str) -> Optional[Dict]:
    proc = _run([podman, "image", "inspect", IMAGE_TAG, "--format",
                 "{{.Id}}|{{.Digest}}|{{.Created}}"])
    if proc.returncode != 0:
        return None
    parts = proc.stdout.decode().strip().split("|")
    return {"id": parts[0], "digest": parts[1] if len(parts) > 1 else "",
            "created": parts[2] if len(parts) > 2 else ""}


def _container_versions(podman: str) -> Dict:
    script = (
        "set -e; "
        "gz sim --versions | head -1; "
        "echo '---'; "
        "dpkg-query -W -f='${Package} ${Version}\\n' " + " ".join(PINNED_PACKAGES)
        + " 2>/dev/null; "
        "echo '---'; python3 -c 'import sys;print(sys.version.split()[0])'; "
        "echo '---'; uname -m"
    )
    proc = _run([podman, "run", "--rm", "--pull=never", "--network=none",
                 "--read-only", "--tmpfs", "/tmp", "--tmpfs", "/home",
                 "-e", "HOME=/home", IMAGE_TAG, "bash", "-lc", script], timeout=180)
    if proc.returncode != 0:
        raise Sim3Error("container_probe_failed", proc.stderr.decode()[-400:])
    blocks = proc.stdout.decode().split("---")
    packages = {}
    for line in blocks[1].strip().splitlines():
        name, _, version = line.partition(" ")
        if name:
            packages[name] = version
    return {
        "gz_sim_version": blocks[0].strip(),
        "packages": packages,
        "python": blocks[2].strip(),
        "arch": blocks[3].strip(),
    }


def _bwrap() -> Optional[Dict]:
    path = shutil.which("bwrap")
    if not path:
        return None
    proc = _run([path, "--version"])
    return {"path": path, "version": proc.stdout.decode().strip()}


def preflight(*, lock_path: Optional[Path] = None, write: bool = True) -> Runtime:
    """Discover the runtime and freeze it. Never installs anything."""
    entries, code_sha = code_inventory()
    host = {
        "os": platform.platform(),
        "kernel": platform.release(),
        "arch": platform.machine(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
    }
    try:
        host["os_release"] = dict(
            line.split("=", 1)
            for line in Path("/etc/os-release").read_text().splitlines() if "=" in line
        ).get("PRETTY_NAME", "").strip('"')
    except OSError:
        host["os_release"] = ""

    sandbox = _bwrap()
    podman = _podman()
    reasons = []
    container: Dict = {}
    if podman is None:
        reasons.append("podman not on PATH")
    else:
        proc = _run([podman, "--version"])
        container["podman"] = proc.stdout.decode().strip()
        digest = _image_digest(podman)
        if digest is None:
            reasons.append(
                f"image {IMAGE_TAG} absent; build it with: podman build -t "
                f"{IMAGE_TAG} -f {CONTAINERFILE.relative_to(ECHOAI)} "
                f"{CONTAINERFILE.parent.relative_to(ECHOAI)}"
            )
        else:
            container["image"] = IMAGE_TAG
            container["image_id"] = digest["id"]
            container["image_digest"] = digest["digest"]
            container["image_created"] = digest["created"]
            container.update(_container_versions(podman))
    if sandbox is None:
        reasons.append("bwrap not on PATH")

    lock = {
        "schema_version": 1,
        "scope": "simulation_infrastructure",
        "host": host,
        "container": container,
        "sandbox": {
            "tool": "bubblewrap",
            **(sandbox or {}),
            "unshare": ["user", "ipc", "pid", "net", "uts", "cgroup"],
            "env_allowlist": sorted(SANDBOX_ENV_EXPECTED),
            "argv": SANDBOX_ARGV,
            "hostname": SANDBOX_HOSTNAME,
            "filesystem": "ro /usr + tmpfs /work + ro /probe/probe.py; no repo, no lab",
        },
        "code": {"files": entries, "code_sha256": code_sha},
        "fuel_downloads": False,
        "available": not reasons,
        "reason": "; ".join(reasons),
    }
    lock["lock_sha256"] = canonical_sha256(
        {k: v for k, v in lock.items() if k != "lock_sha256"}
    )
    if write:
        dump_report(Path(lock_path or DEFAULT_LOCK), lock)
    return Runtime(available=not reasons, reason="; ".join(reasons), lock=lock)


def load_lock(path: Optional[Path] = None) -> Runtime:
    p = Path(path or DEFAULT_LOCK)
    if not p.exists():
        return Runtime(available=False, reason=f"no lock at {p}")
    lock = loads_strict(read_bounded(p, code="lock"), code="lock")
    recomputed = canonical_sha256({k: v for k, v in lock.items()
                                   if k != "lock_sha256"})
    if recomputed != lock.get("lock_sha256"):
        raise Sim3Error("lock_tampered", f"recomputed {recomputed}")
    return Runtime(available=bool(lock.get("available")),
                   reason=str(lock.get("reason", "")), lock=lock)


def check_sdf(runtime: Runtime, data: bytes, *, name: str = "world.sdf") -> Dict:
    """Ask the real libsdformat, not our parser, whether Gazebo can load it."""
    runtime.require()
    podman = _podman()
    assert podman is not None
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / name
        target.write_bytes(data)
        proc = _run([
            podman, "run", "--rm", "--pull=never", "--network=none", "--read-only",
            "--security-opt", "label=disable", "--tmpfs", "/tmp",
            "--tmpfs", "/home", "-e", "HOME=/home",
            "-v", f"{tmp}:/sdf:ro", runtime.image,
            "gz", "sdf", "-k", f"/sdf/{name}",
        ], timeout=120)
    out = (proc.stdout + proc.stderr).decode(errors="replace").strip()
    return {
        "tool": "gz sdf -k (libsdformat)",
        "returncode": proc.returncode,
        "valid": proc.returncode == 0 and out.startswith("Valid"),
        "output": out[-600:],
    }
