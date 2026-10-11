"""Standalone PRIVATE CPU capability probe; no installs, payloads, or physics runs.

Submit this file alone. No repo, environment-variable dump, credentials, input
datasets, or sealed evaluations are needed. Runtime is bounded to 240 seconds
inside a Kaggle session with a separate 300-second service timeout.
"""

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


ROOT = Path("/kaggle/working")
LIMIT_SECONDS = 240
REPORT = {
    "schema": "echo5.kaggle.capability.v1",
    "purpose": "capability_only",
    "simulator_tested": False,
    "gpu_requested": False,
    "packages_installed": [],
    "started_unix": time.time(),
    "runtime_budget_seconds": LIMIT_SECONDS,
    "commands": [],
}
START = time.monotonic()


def checkpoint():
    REPORT["elapsed_seconds"] = round(time.monotonic() - START, 3)
    temporary = ROOT / "capability.json.partial"
    temporary.write_text(json.dumps(REPORT, sort_keys=True, indent=2) + "\n")
    temporary.replace(ROOT / "capability.json")


def remaining():
    left = LIMIT_SECONDS - (time.monotonic() - START)
    if left <= 1:
        raise TimeoutError("probe wall budget exhausted")
    return left


def command(argv, seconds=12):
    started = time.monotonic()
    row = {"argv": argv}
    process = None
    try:
        process = subprocess.Popen(
            argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, start_new_session=True,
        )
        stdout, stderr = process.communicate(timeout=min(seconds, remaining()))
        row.update(returncode=process.returncode,
                   stdout=stdout[:6000], stderr=stderr[:6000])
    except (OSError, subprocess.TimeoutExpired, TimeoutError) as exc:
        row["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=2)
            row.update(returncode=process.returncode,
                       stdout=stdout[:6000], stderr=stderr[:6000])
        row["elapsed_seconds"] = round(time.monotonic() - started, 3)
        REPORT["commands"].append(row)
        print(json.dumps({"observation": row}), flush=True)
        checkpoint()
    return row


def small_file(name):
    path = Path(name)
    try:
        return path.read_text()[:4000]
    except OSError as exc:
        return {"error": type(exc).__name__}


def timeout_handler(_signum, _frame):
    raise TimeoutError("probe hard wall timeout")


def main():
    if not ROOT.is_dir():
        raise SystemExit("Run only inside Kaggle; this is not local simulator evidence")
    if (ROOT / "capability.json").exists():
        raise SystemExit("Refusing to overwrite a prior capability receipt")
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(LIMIT_SECONDS)
    try:
        REPORT["runtime"] = {
            "python": sys.version, "platform": platform.platform(),
            "uid": os.getuid(), "euid": os.geteuid(), "gid": os.getgid(),
            "cpu_count": os.cpu_count(),
            "cpu_affinity_count": len(os.sched_getaffinity(0)),
            "os_release": small_file("/etc/os-release"),
            "memory_total_available": [line for line in
                str(small_file("/proc/meminfo")).splitlines()
                if line.startswith(("MemTotal:", "MemAvailable:"))],
            "security_status": [line for line in
                str(small_file("/proc/self/status")).splitlines()
                if line.startswith(("CapEff:", "CapBnd:", "NoNewPrivs:", "Seccomp:"))],
            "limits": {name: small_file(name) for name in (
                "/sys/fs/cgroup/cpu.max", "/sys/fs/cgroup/memory.max",
                "/sys/fs/cgroup/pids.max", "/proc/sys/user/max_user_namespaces",
                "/proc/sys/kernel/unprivileged_userns_clone")},
            "sockets": {name: Path(name).exists() for name in (
                "/var/run/docker.sock", "/run/podman/podman.sock", "/dev/fuse")},
        }
        REPORT["disk"] = {}
        for location in ("/kaggle/working", "/tmp", "/dev/shm"):
            usage = shutil.disk_usage(location)
            REPORT["disk"][location] = dict(zip(("total", "used", "free"), usage))
        binaries = {name: shutil.which(name) for name in (
            "gz", "gazebo", "px4", "podman", "docker", "unshare", "chroot",
            "proot", "bwrap", "git", "cmake", "ninja", "g++", "apt-get", "dpkg-query")}
        REPORT["binaries"] = binaries
        checkpoint()
        for executable, arguments in (
            ("gz", ["sim", "--version"]), ("gazebo", ["--version"]),
            ("podman", ["--version"]), ("docker", ["--version"]),
            ("cmake", ["--version"]), ("g++", ["--version"]),
        ):
            if binaries[executable]:
                command([binaries[executable], *arguments])
        if binaries["podman"]:
            command([binaries["podman"], "info", "--format", "json"])
        if binaries["docker"]:
            command([binaries["docker"], "info", "--format", "{{json .ServerVersion}}"])
        if binaries["unshare"]:
            for flags in (["--user", "--map-root-user"], ["--mount"], ["--net"]):
                command([binaries["unshare"], *flags, "true"], seconds=5)
        if binaries["chroot"]:
            command([binaries["chroot"], "/", "/bin/true"], seconds=5)
        if binaries["dpkg-query"]:
            command([binaries["dpkg-query"], "-W", "-f=${Package} ${Version}\n",
                     "gz-*", "libgz-*", "gazebo*", "px4*", "podman", "docker.io"])
        REPORT["px4_candidates"] = []
        candidates = ["/opt/PX4-Autopilot/build/px4_sitl_default/bin/px4",
                      "/usr/local/bin/px4", "/usr/bin/px4"]
        if binaries["px4"]:
            candidates.append(binaries["px4"])
        for name in sorted(set(candidates)):
            path = Path(name)
            row = {"path": name, "exists": path.is_file()}
            if path.is_file():
                with path.open("rb") as stream:
                    row["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
                row["size"] = path.stat().st_size
                if os.access(path, os.X_OK):
                    command([str(path), "-h"], seconds=5)
            REPORT["px4_candidates"].append(row)
        REPORT["network"] = []
        for url in (
            "https://github.com/PX4/PX4-Autopilot",
            "https://raw.githubusercontent.com/PX4/PX4-Autopilot/v1.15.4/README.md",
            "https://packages.osrfoundation.org/gazebo/ubuntu-stable/dists/jammy/Release",
            "https://archive.ubuntu.com/ubuntu/dists/jammy/Release",
        ):
            row = {"url": url, "method": "HEAD"}
            try:
                request = urllib.request.Request(url, method="HEAD")
                with urllib.request.urlopen(request, timeout=min(10, remaining())) as response:
                    row.update(status=response.status,
                               content_length=response.headers.get("Content-Length"))
            except (OSError, urllib.error.URLError) as exc:
                row["error"] = type(exc).__name__ + ": " + str(exc)
            REPORT["network"].append(row)
            checkpoint()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind(("127.0.0.1", 0))
            receiver.settimeout(2)
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                sender.sendto(b"echo5-capability", receiver.getsockname())
                REPORT["udp_loopback"] = receiver.recv(32) == b"echo5-capability"
        REPORT["status"] = "capability_probe_complete"
    except Exception as exc:
        REPORT["status"] = "capability_probe_incomplete"
        REPORT["error"] = type(exc).__name__ + ": " + str(exc)
    finally:
        signal.alarm(0)
        REPORT["finished_unix"] = time.time()
        checkpoint()
        print(json.dumps(REPORT, sort_keys=True), flush=True)
    return 0 if REPORT["status"] == "capability_probe_complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
