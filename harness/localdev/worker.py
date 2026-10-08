"""Trusted worker, mounted read-only outside the candidate source tree."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
import trace
import traceback
import unittest
from typing import Any, cast


def failure(exc: tuple[Any, Any, Any]) -> dict[str, Any]:
    kind, value, tb = exc
    return {"type": kind.__name__, "message": str(value),
            "frames": [{"file": f.filename, "line": f.lineno, "function": f.name}
                       for f in traceback.extract_tb(tb)],
            "traceback": "".join(traceback.format_exception(kind, value, tb))}


def resources() -> dict[str, Any]:
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {"cpu_seconds": own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime,
            "max_process_rss_kib": max(own.ru_maxrss, children.ru_maxrss),
            "scope": "worker and reaped children; maximum process RSS, not simultaneous sum"}


def main() -> int:
    spec = json.loads(Path("/spec.json").read_text())
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (spec["memory_mb"] * 1048576,) * 2)
    cpu = math.ceil(spec["timeout_s"]) + 1
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1048576,) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
    command = spec.get("command")
    if command:
        command_result = subprocess.run(command, check=False)
        Path("/out/details.json").write_text(json.dumps({"mode": "command", "child_exit_code": command_result.returncode,
                                                         "resources": resources()}))
        return command_result.returncode
    mode = spec["mode"]
    if mode == "syntax":
        files, errors = [], []
        for path in sorted(Path.cwd().rglob("*.py")):
            if "lab" in path.relative_to(Path.cwd()).parts:
                continue
            files.append(str(path.relative_to(Path.cwd())))
            try:
                compile(path.read_bytes(), str(path), "exec")
            except (SyntaxError, ValueError) as exc:
                errors.append({"file": str(path), "line": getattr(exc, "lineno", None),
                               "type": type(exc).__name__, "message": str(exc)})
        Path("/out/details.json").write_text(json.dumps({"mode": mode, "files": len(files), "errors": errors,
                                                         "resources": resources()}))
        print(f"Compiled {len(files)} Python files; errors {len(errors)}", flush=True)
        return int(bool(errors) or not files)

    class Result(unittest.TextTestResult):
        records: list[dict[str, Any]]

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            self.records = []
            self.started = 0.0

        def startTest(self, test: Any) -> None:
            self.started = time.monotonic()
            super().startTest(test)

        def record(self, test: Any, outcome: str, exc: Any = None) -> None:
            item = {"test": test.id(), "outcome": outcome,
                    "seconds": round(time.monotonic() - self.started, 6)}
            if exc:
                item["error"] = failure(exc)
            self.records.append(item)

        def addSuccess(self, test: Any) -> None:
            self.record(test, "passed")
            super().addSuccess(test)

        def addFailure(self, test: Any, err: Any) -> None:
            self.record(test, "failed", err)
            super().addFailure(test, err)

        def addError(self, test: Any, err: Any) -> None:
            self.record(test, "error", err)
            super().addError(test, err)

        def addSkip(self, test: Any, reason: str) -> None:
            self.record(test, "skipped")
            super().addSkip(test, reason)

        def addSubTest(self, test: Any, subtest: Any, err: Any) -> None:
            if err:
                self.record(subtest, "failed", err)
            super().addSubTest(test, subtest, err)

    suite = unittest.defaultTestLoader.loadTestsFromNames(spec["tests"])
    tracer = trace.Trace(count=True, trace=False, ignoredirs=[sys.base_prefix])
    runner = unittest.TextTestRunner(verbosity=2, resultclass=Result)
    result = cast(Result, tracer.runfunc(runner.run, suite) if spec.get("coverage") else runner.run(suite))
    covered: dict[str, list[int]] = {}
    if spec.get("coverage"):
        cwd = Path.cwd()
        for (filename, line), count in tracer.results().counts.items():
            path = Path(filename)
            if path.is_relative_to(cwd) and "lab" not in path.relative_to(cwd).parts and count:
                covered.setdefault(str(path.relative_to(cwd)), []).append(line)
    for filename in covered:
        covered[filename] = sorted(set(covered[filename]))
    details = {"mode": mode, "tests_run": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "skipped": len(result.skipped),
               "expected_failures": len(result.expectedFailures),
               "unexpected_successes": len(result.unexpectedSuccesses), "cases": result.records,
               "executed_lines": covered,
               "coverage_scope": "executed Python lines in this profile; not branch coverage or project completion",
               "resources": resources()}
    Path("/out/details.json").write_text(json.dumps(details))
    return int(not result.wasSuccessful() or result.testsRun == 0 or bool(result.skipped)
               or bool(result.expectedFailures))


if __name__ == "__main__":
    raise SystemExit(main())
