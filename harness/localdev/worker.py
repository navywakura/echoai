"""Host-supplied diagnostic worker in a read-only private candidate snapshot.

After candidate imports, this process and ALL its output are untrusted. Reports
are developer test observations, never attestations, property checks or task
success. The outside PCWorld supervisor owns resource limits and measurements.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import trace
import traceback
import unittest
from typing import Any, cast

DETAILS_MARKER = "ECHO_LOCALDEV_DETAILS_V1:"
WORKER_DIRECTORY = "__localdev_worker__"


def report(details: dict[str, Any]) -> None:
    """Emit forgeable diagnostics through the same bounded stdout as candidates."""
    print("\n" + DETAILS_MARKER + json.dumps(details, separators=(",", ":")), flush=True)


def failure(exc: tuple[Any, Any, Any]) -> dict[str, Any]:
    kind, value, tb = exc
    return {"type": kind.__name__, "message": str(value),
            "frames": [{"file": f.filename, "line": f.lineno, "function": f.name}
                       for f in traceback.extract_tb(tb)],
            "traceback": "".join(traceback.format_exception(kind, value, tb))}


def main() -> int:
    spec = json.loads(base64.b64decode(sys.argv[1], validate=True))
    os.environ["LOCALDEV_IN_SANDBOX"] = "1"
    command = spec.get("command")
    if command:
        command_result = subprocess.run(command, check=False)
        report({"mode": "command", "child_exit_code": command_result.returncode})
        return command_result.returncode
    mode = spec["mode"]
    if mode == "syntax":
        files, errors = [], []
        for path in sorted(Path.cwd().rglob("*.py")):
            if any(part in ("lab", WORKER_DIRECTORY) for part in path.relative_to(Path.cwd()).parts):
                continue
            files.append(str(path.relative_to(Path.cwd())))
            try:
                compile(path.read_bytes(), str(path), "exec")
            except (SyntaxError, ValueError) as exc:
                errors.append({"file": str(path), "line": getattr(exc, "lineno", None),
                               "type": type(exc).__name__, "message": str(exc)})
        print(f"Compiled {len(files)} Python files; errors {len(errors)}", flush=True)
        report({"mode": mode, "files": len(files), "errors": errors})
        return int(bool(errors) or not files)

    # Import candidates only after -I initialized the trusted worker's stdlib,
    # and only inside the mandatory sandbox. Preserve flat and echoai.* tests
    # without adding the host parent or any sibling package to sys.path.
    root = Path.cwd()
    sys.path.insert(0, str(root))
    if (root / "__init__.py").is_file():
        package_spec = importlib.util.spec_from_file_location("echoai", root / "__init__.py",
                                                             submodule_search_locations=[str(root)])
        assert package_spec is not None and package_spec.loader is not None
        package = importlib.util.module_from_spec(package_spec)
        sys.modules["echoai"] = package
        package_spec.loader.exec_module(package)

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
            if (path.is_relative_to(cwd) and count and
                    not any(part in ("lab", WORKER_DIRECTORY) for part in path.relative_to(cwd).parts)):
                covered.setdefault(str(path.relative_to(cwd)), []).append(line)
    for filename in covered:
        covered[filename] = sorted(set(covered[filename]))
    details = {"mode": mode, "tests_run": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "skipped": len(result.skipped),
               "expected_failures": len(result.expectedFailures),
               "unexpected_successes": len(result.unexpectedSuccesses), "cases": result.records,
               "executed_lines": covered,
               "coverage_scope": "untrusted reported Python lines in this profile; not branch coverage or project completion",
               "counts_scope": "untrusted reported developer test counts; not semantic verification"}
    report(details)
    return int(not result.wasSuccessful() or result.testsRun == 0 or bool(result.skipped)
               or bool(result.expectedFailures))


if __name__ == "__main__":
    raise SystemExit(main())
