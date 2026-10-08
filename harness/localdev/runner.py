"""Bubblewrap execution with bounded output, wall time and recorded child resource use."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import time
from typing import Any, BinaryIO, cast

from .common import TOOLS, digest, save


def diagnostics(text: str) -> list[dict[str, Any]]:
    frames = [{"file": m[0], "line": int(m[1]), "function": m[2]}
              for m in re.findall(r'File "([^"]+)", line (\d+), in ([^\n]+)', text)]
    result: list[dict[str, Any]] = [{"kind": "traceback", "frames": frames}] if frames else []
    for match in re.finditer(r"^(.+?):(\d+)(?::(\d+))?:\s*(error|warning|note):\s*(.+)$", text, re.M):
        result.append({"kind": "compiler", "file": match[1], "line": int(match[2]),
                       "column": int(match[3]) if match[3] else None,
                       "severity": match[4], "message": match[5]})
    return result


def process_memory(pid: int) -> tuple[int, int]:
    """Sample our process tree using host PIDs, without exposing process arguments."""
    stack, seen = [pid], set()
    maximum, total = 0, 0
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        base = Path("/proc") / str(current)
        try:
            data = base.joinpath("status").read_text()
            rss = re.search(r"^VmRSS:\s+(\d+)", data, re.M)
            high = re.search(r"^VmHWM:\s+(\d+)", data, re.M)
            total += int(rss[1]) if rss else 0
            maximum = max(maximum, int(high[1]) if high else 0)
            stack.extend(int(n) for n in (base/"task"/str(current)/"children").read_text().split())
        except (OSError, ValueError):
            pass  # Process exit between reads is normal.
    return maximum, total


def execute(workspace: Path, job: Path, specification: dict[str, Any]) -> dict[str, Any]:
    if not shutil.which("bwrap"):
        raise RuntimeError("Bubblewrap required; no fallback to unsandboxed execution")
    if job.exists():
        raise ValueError("job directory already exists; preserve prior evidence")
    job.mkdir(parents=True)
    out, scratch = job / "out", job / "scratch"
    out.mkdir()
    scratch.mkdir()
    spec = {"timeout_s": 60, "memory_mb": 1536, "output_kb": 512, **specification}
    if not 0 < spec["timeout_s"] <= 600 or not 64 <= spec["memory_mb"] <= 8192:
        raise ValueError("invalid resource budget")
    if not 1 <= spec["output_kb"] <= 4096:
        raise ValueError("invalid output budget")
    (workspace / "lab").mkdir(exist_ok=True)
    save(job / "spec.json", spec)
    worker = Path(__file__).parent / "worker.py"
    trusted_worker = job / "worker.py"
    trusted_worker.write_bytes(worker.read_bytes())
    stdin = str(spec.get("stdin", "")).encode()
    (job / "stdin.txt").write_bytes(stdin)
    workdir = f"/work/{workspace.name}"
    args = ["bwrap", "--unshare-all", "--unshare-user", "--die-with-parent", "--new-session", "--cap-drop", "ALL",
            "--disable-userns", "--ro-bind", "/usr", "/usr", "--symlink", "usr/bin", "/bin",
            "--symlink", "usr/lib", "/lib", "--symlink", "usr/lib64", "/lib64",
            "--proc", "/proc", "--dev", "/dev", "--size", "67108864", "--tmpfs", "/tmp",
            "--ro-bind", str(workspace.parent), "/work",
            "--bind", str(scratch), workdir + "/lab", "--bind", str(out), "/out",
            "--ro-bind", str(trusted_worker), "/worker.py",
            "--ro-bind", str(job / "spec.json"), "/spec.json", "--chdir", workdir,
            "--clearenv", "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp",
            "--setenv", "TMPDIR", "/tmp", "--setenv", "LANG", "C.UTF-8", "--setenv", "TZ", "UTC",
            "--setenv", "PYTHONPATH", "/work:" + workdir, "--setenv", "PYTHONHASHSEED", "0",
            "--setenv", "PYTHONDONTWRITEBYTECODE", "1", "--setenv", "OMP_NUM_THREADS", "1",
            "--setenv", "OPENBLAS_NUM_THREADS", "1", "--setenv", "LOCALDEV_IN_SANDBOX", "1"]
    if TOOLS.is_dir():
        args += ["--ro-bind", str(TOOLS), "/tools"]
    args += ["--", "/usr/bin/python3", "/worker.py"]
    start = time.monotonic()
    read_bytes, reason, usage, code = 0, None, None, None
    sampled_max_rss, sampled_tree_rss = 0, 0
    stdout_path, stderr_path = job / "stdout.log", job / "stderr.log"
    with (job / "stdin.txt").open("rb") as input_file, stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        proc = subprocess.Popen(args, stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
        selector = selectors.DefaultSelector()
        assert proc.stdout is not None and proc.stderr is not None
        for stream, target in ((proc.stdout, stdout), (proc.stderr, stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, target)
        last_disk_check = start
        last_memory_check = 0.0
        while selector.get_map() or code is None:
            now = time.monotonic()
            if now - last_memory_check >= .1:
                high, total = process_memory(proc.pid)
                sampled_max_rss = max(sampled_max_rss, high)
                sampled_tree_rss = max(sampled_tree_rss, total)
                last_memory_check = now
            if reason is None and now - start > spec["timeout_s"]:
                reason = "TIMEOUT"
            if reason is None and now - last_disk_check > 0.5:
                sizes = []
                for folder in (out, scratch):
                    for path in folder.rglob("*"):
                        try:
                            if path.is_file() and not path.is_symlink():
                                sizes.append(path.stat().st_size)
                        except FileNotFoundError:
                            pass
                if len(sizes) > 2000 or sum(sizes) > 32 * 1048576:
                    reason = "DISK_LIMIT"
                last_disk_check = now
            if reason is not None and code is None:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            for key, _ in selector.select(0.05):
                stream = cast(BinaryIO, key.fileobj)
                chunk = os.read(stream.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    stream.close()
                    continue
                available = max(0, spec["output_kb"] * 1024 - read_bytes)
                key.data.write(chunk[:available])
                key.data.flush()
                read_bytes += len(chunk)
                if read_bytes > spec["output_kb"] * 1024 and reason is None:
                    reason = "OUTPUT_LIMIT"
            if code is None:
                pid, status, current_usage = os.wait4(proc.pid, os.WNOHANG)
                if pid:
                    code = os.waitstatus_to_exitcode(status)
                    proc.returncode = code
                    usage = current_usage
        selector.close()
    detail_path = out / "details.json"
    try:
        details = json.loads(detail_path.read_text()) if detail_path.exists() else None
        if details is not None and not isinstance(details, dict):
            raise ValueError("invalid receipt")
    except (ValueError, OSError):
        details = None
        reason = reason or "INVALID_RECEIPT"
    if reason is None and spec.get("mode") in ("unittest", "syntax") and details is None:
        reason = "MISSING_RECEIPT"
    if reason is None and code == 0 and spec.get("mode") in ("unittest", "syntax"):
        assert isinstance(details, dict)
        if spec["mode"] == "unittest":
            if (not isinstance(details.get("tests_run"), int) or details["tests_run"] <= 0 or
                any(details.get(k) != 0 for k in ("failures", "errors", "skipped", "expected_failures", "unexpected_successes"))
                or len(details.get("cases", [])) != details["tests_run"] or
                any(c.get("outcome") != "passed" for c in details.get("cases", []))):
                reason = "INVALID_RECEIPT"
        elif not details.get("files") or details.get("errors") != []:
            reason = "INVALID_RECEIPT"
    verdict = reason or ("PASSED" if code == 0 else "FAILED")
    measured = (details or {}).get("resources", {})
    record = {"schema": 1, "status": verdict, "exit_code": code,
              "wall_seconds": round(time.monotonic() - start, 6),
              "cpu_seconds": measured.get("cpu_seconds"),
              "supervisor_cpu_seconds": round(usage.ru_utime + usage.ru_stime, 6) if usage else None,
              "max_process_rss_kib": max(sampled_max_rss, measured.get("max_process_rss_kib", 0)),
              "peak_tree_rss_kib_sampled": sampled_tree_rss,
              "rss_scope": "worker getrusage plus host /proc sampling every 100ms; tree sum is sampled, not an exact peak",
              "stdout_sha256": digest(stdout_path.read_bytes()), "stderr_sha256": digest(stderr_path.read_bytes()),
              "spec_sha256": digest((job / "spec.json").read_bytes()),
              "worker_sha256": digest(trusted_worker.read_bytes()),
              "details": details, "diagnostics": diagnostics(stdout_path.read_text(errors="replace") + "\n" + stderr_path.read_text(errors="replace")),
              "isolation": {"backend": "bubblewrap", "network": False, "source_readonly": True,
                            "home_mounted": False, "hardware_devices": False},
              "declared_mocks": spec.get("mocks", []), "scientific_gate": False}
    save(job / "result.json", record)
    print(json.dumps({"job": str(job), "status": verdict, "seconds": record["wall_seconds"]}), flush=True)
    return record


def validate(workspace: Path, output: Path, checks: list[dict[str, Any]],
             deadline: float | None = None) -> dict[str, Any]:
    results = []
    for index, check in enumerate(checks):
        if deadline is not None:
            left = deadline - time.monotonic()
            if left <= 0:
                results.append({"id": check["id"], "status": "BUDGET_EXHAUSTED"})
                break
            check = {**check, "timeout_s": min(check.get("timeout_s", 60), left)}
        result = execute(workspace, output / f"{index:02d}-{check['id']}", check)
        results.append({"id": check["id"], **result})
    summary = {"status": "PASSED" if results and all(r["status"] == "PASSED" for r in results) else "FAILED",
               "checks": results, "scientific_gate": False}
    save(output / "result.json", summary)
    return summary
