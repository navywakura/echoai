"""Developer test observations through the mandatory PCWorld execution boundary.

Historical PASSED means only that a command exited zero or declared tests
reported passing. Worker diagnostics, counts and coverage are UNTRUSTED: the
candidate shares the worker's Python process and can forge every report. No
localdev result verifies a property, certifies task success or opens a scientific
gate. Snapshot custody, isolation and resource measurements belong to PCWorld.
"""
from __future__ import annotations

import base64
import json
import math
from pathlib import Path
import re
import tempfile
import time
from typing import Any

from echoai.pcworld import runner as execution_backend
from echoai.pcworld.snapshots import SnapshotStore

from .common import digest, save
from .worker import DETAILS_MARKER, WORKER_DIRECTORY


def _scope() -> dict[str, Any]:
    return {"status_scope": "developer_test_observations",
            "status_meaning": "DEVELOPER TEST OBSERVATIONS: PASSED means only a zero-exit command "
                              "or declared tests reporting pass; not semantic verification",
            "attestation": "untrusted", "output_trust": "untrusted",
            "details_scope": "untrusted worker-reported diagnostics, test counts and executed lines",
            "claim_status": "unknown", "property_status": "unknown",
            "task_success": False, "scientific_gate": False}


def diagnostics(text: str) -> list[dict[str, Any]]:
    """Extract untrusted traceback/compiler text for developer feedback only."""
    # Treat implausibly large source positions as text, not integer input from
    # a trusted compiler. The original text remains in the bounded logs.
    frames = [{"file": m[0], "line": int(m[1]), "function": m[2]}
              for m in re.findall(r'File "([^"]+)", line (\d{1,9}), in ([^\n]+)', text)]
    result: list[dict[str, Any]] = [{"kind": "traceback", "frames": frames}] if frames else []
    for match in re.finditer(r"^(.+?):(\d{1,9})(?::(\d{1,9}))?:\s*(error|warning|note):\s*(.+)$", text, re.M):
        result.append({"kind": "compiler", "file": match[1], "line": int(match[2]),
                       "column": int(match[3]) if match[3] else None,
                       "severity": match[4], "message": match[5]})
    return result


def _details(stdout: str, mode: str) -> tuple[dict[str, Any] | None, str | None]:
    """Parse bounded output, never an attestation or candidate-created file.

    The RECEIPT error names are retained for legacy callers; even a well-shaped
    report remains untrusted. Reject shapes that would break engine feedback.
    """
    reports = [line[len(DETAILS_MARKER):] for line in stdout.splitlines()
               if line.startswith(DETAILS_MARKER)]
    if not reports:
        return None, "MISSING_RECEIPT"
    if len(reports) != 1:
        return None, "INVALID_RECEIPT"
    try:
        value = json.loads(reports[0])
        # Also reject non-finite JSON and excessive nesting before persistence.
        json.dumps(value, allow_nan=False)
        if not isinstance(value, dict) or value.get("mode") != mode:
            raise ValueError("invalid diagnostic mode")
        if mode == "unittest":
            counts = ("tests_run", "failures", "errors", "skipped", "expected_failures", "unexpected_successes")
            if any(type(value.get(k)) is not int or value[k] < 0 for k in counts):
                raise ValueError("invalid reported test counts")
            cases = value.get("cases")
            if not isinstance(cases, list) or any(
                    not isinstance(c, dict) or not isinstance(c.get("test"), str) or
                    c.get("outcome") not in ("passed", "failed", "error", "skipped") for c in cases):
                raise ValueError("invalid reported cases")
        elif mode == "syntax":
            if (type(value.get("files")) is not int or value["files"] < 0 or
                    not isinstance(value.get("errors"), list) or
                    any(not isinstance(error, dict) for error in value["errors"])):
                raise ValueError("invalid syntax diagnostics")
        elif type(value.get("child_exit_code")) is not int:
            raise ValueError("invalid command diagnostics")
    except (ValueError, TypeError, RecursionError):
        return None, "INVALID_RECEIPT"
    return value, None


def execute(workspace: Path, job: Path, specification: dict[str, Any]) -> dict[str, Any]:
    """Run a legacy profile; PASSED is a developer observation, never success.

    The host copies its worker into a private snapshot using PCWorld's custody API.
    The spec travels in argv and input in stdin; there are no extra mounts. All
    candidate execution, including commands, crosses execution_backend.execute.
    """
    if job.exists():
        raise ValueError("job directory already exists; preserve prior evidence")
    if job.resolve().is_relative_to(workspace.resolve()):
        raise ValueError("job evidence must be outside the candidate workspace")
    spec = {"timeout_s": 60, "memory_mb": 1536, "output_kb": 512, **specification}
    if (type(spec["timeout_s"]) not in (int, float) or not 0 < spec["timeout_s"] <= 600 or
            type(spec["memory_mb"]) is not int or not 64 <= spec["memory_mb"] <= 2048):
        raise ValueError("invalid resource budget")
    if type(spec["output_kb"]) is not int or not 1 <= spec["output_kb"] <= 4096:
        raise ValueError("invalid output budget")
    mode = "command" if spec.get("command") else spec.get("mode")
    if mode not in ("command", "unittest", "syntax"):
        raise ValueError("unsupported developer check mode")
    if mode == "command" and (not isinstance(spec.get("command"), list) or not spec["command"] or
                              any(not isinstance(arg, str) or "\0" in arg for arg in spec["command"])):
        raise ValueError("command must be structured argv")
    if mode == "unittest" and (not isinstance(spec.get("tests"), list) or not spec["tests"] or
                               any(not isinstance(name, str) for name in spec["tests"])):
        raise ValueError("explicit developer tests required")
    spec["mode"] = mode
    worker_spec = {key: spec[key] for key in ("mode", "command", "tests", "coverage") if key in spec}
    encoded = base64.b64encode(json.dumps(worker_spec, allow_nan=False).encode()).decode("ascii")
    if len(encoded) > 65536:
        raise ValueError("worker specification exceeds argv budget")
    stdin = str(spec.get("stdin", "")).encode()
    limits = {"wall_ms": max(1, math.ceil(spec["timeout_s"] * 1000)),
              "cpu_ms": spec.get("cpu_ms", max(1, math.ceil(spec["timeout_s"] * 1000))),
              "memory_bytes": spec["memory_mb"] * 1048576, "output_bytes": spec["output_kb"] * 1024}
    limits.update({key: spec[key] for key in ("pids", "disk_bytes") if key in spec})
    worker = Path(__file__).with_name("worker.py").read_bytes()
    worker_path = WORKER_DIRECTORY + "/worker.py"
    start = time.monotonic()
    job.mkdir(parents=True)
    save(job / "spec.json", spec)
    with tempfile.TemporaryDirectory(prefix="echo-localdev-") as temporary:
        store = SnapshotStore(Path(temporary) / "snapshots")
        source = store.capture(workspace)
        if WORKER_DIRECTORY in source.manifest["entries"]:
            raise ValueError("reserved localdev worker directory in candidate")
        candidate = store.apply(source, source.id,
            [{"path": worker_path, "expected_sha256": None, "content": worker.decode("utf-8")}],
            allowed_paths=(worker_path,))
        observed = execution_backend.execute(candidate,
            ["/usr/bin/python3", "-I", "-B", "/workspace/" + worker_path, encoded],
            limits=limits, stdin=stdin)

    # PCWorld bounds raw bytes. UTF-8 replacement can expand them, so also bound
    # the persisted diagnostic text. These log hashes identify that text only.
    remaining = limits["output_bytes"]
    streams = {}
    for name in ("stdout", "stderr"):
        raw = observed[name].encode("utf-8")[:remaining].decode("utf-8", errors="ignore").encode("utf-8")
        remaining -= len(raw)
        (job / (name + ".log")).write_bytes(raw)
        streams[name] = raw.decode("utf-8")
    details, report_error = _details(streams["stdout"], mode)
    status = observed["status"]
    if status == "EXITED":
        if observed["exit_code"] != 0:
            status = "FAILED"
        elif mode in ("unittest", "syntax") and report_error:
            status = report_error
        elif mode == "unittest" and details is not None and (
                details["tests_run"] <= 0 or len(details["cases"]) != details["tests_run"] or
                any(details[k] != 0 for k in ("failures", "errors", "skipped", "expected_failures", "unexpected_successes")) or
                any(c["outcome"] != "passed" for c in details["cases"])):
            status = "INVALID_RECEIPT"
        elif mode == "syntax" and details is not None and (not details["files"] or details["errors"]):
            status = "INVALID_RECEIPT"
        else:
            status = "PASSED"
    measured = observed["resources"]
    record = {"schema": 1, "status": status, "execution_status": observed["status"],
              "exit_code": observed["exit_code"], "signal": observed.get("signal"),
              "wall_seconds": round(time.monotonic() - start, 6),
              "cpu_seconds": measured["cpu_us"] / 1_000_000,
              "cpu_scope": "PCWorld supervisor-observed cumulative cgroup CPU; not worker-reported",
              "supervisor_cpu_seconds": None,  # Host supervisor CPU is not separately measured.
              "max_process_rss_kib": measured["memory_peak_bytes"] // 1024,
              "peak_tree_rss_kib_sampled": measured["memory_peak_bytes"] // 1024,
              "rss_scope": "Legacy aliases of cgroup memory_peak_bytes / 1024, including charged tmpfs/cache; "
                           "not per-process RSS or a sampled tree sum",
              "resources": measured, "limits": observed["limits"],
              "stdout": streams["stdout"], "stderr": streams["stderr"],
              "stdout_sha256": digest((job / "stdout.log").read_bytes()),
              "stderr_sha256": digest((job / "stderr.log").read_bytes()),
              "execution_stdout_sha256": observed["stdout_sha256"],
              "execution_stderr_sha256": observed["stderr_sha256"],
              "spec_sha256": digest((job / "spec.json").read_bytes()), "worker_sha256": digest(worker),
              "source_snapshot": source.id, "snapshot": observed["snapshot"],
              "details": details, "details_status": report_error or "UNTRUSTED_REPORT",
              "diagnostics": diagnostics(streams["stdout"] + "\n" + streams["stderr"]),
              "isolation": observed["isolation"],
              "observation_integrity": observed["observation_integrity"],
              "declared_mocks": spec.get("mocks", []), **_scope()}
    save(job / "result.json", record)
    print(json.dumps({"job": str(job), "status": status, "seconds": record["wall_seconds"],
                      "status_scope": record["status_scope"], "task_success": False}), flush=True)
    return record


def validate(workspace: Path, output: Path, checks: list[dict[str, Any]],
             deadline: float | None = None) -> dict[str, Any]:
    """Aggregate developer test observations; PASSED confers no semantic authority."""
    results = []
    for index, check in enumerate(checks):
        if deadline is not None:
            left = deadline - time.monotonic()
            if left <= 0:
                results.append({"id": check["id"], "status": "BUDGET_EXHAUSTED", **_scope()})
                break
            check = {**check, "timeout_s": min(check.get("timeout_s", 60), left)}
        result = execute(workspace, output / f"{index:02d}-{check['id']}", check)
        results.append({"id": check["id"], **result})
    summary = {"status": "PASSED" if results and all(r["status"] == "PASSED" for r in results) else "FAILED",
               "checks": results, **_scope()}
    save(output / "result.json", summary)
    return summary
