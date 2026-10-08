"""Fast, honest SIM-3 CI entry point.

Unit validation always runs. A backend bank is requested only with
``SIM3_CI_BACKEND=1``; if unavailable its machine-readable status remains
``not_run`` in the CI report rather than becoming a synthetic green.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from echoai.nexus0.sim3 import runner
from echoai.nexus0.sim3.canon import dump_report
from echoai.nexus0.sim3.runtime import ECHOAI, preflight


def run(output: Path) -> int:
    tests = subprocess.run([sys.executable, str(ECHOAI / "tests" / "test_sim3.py")],
                           capture_output=True, text=True, timeout=300)
    report = {
        "schema_version": 1,
        "scope": "simulation_infrastructure",
        "kind": "ci",
        "unit": {"status": "pass" if tests.returncode == 0 else "fail",
                 "returncode": tests.returncode, "stdout": tests.stdout[-2000:],
                 "stderr": tests.stderr[-2000:]},
    }
    if os.environ.get("SIM3_CI_BACKEND") == "1":
        report["backend"] = runner.run(accept_lock_change=False, verbose=False)
    else:
        runtime = preflight(write=False)
        report["backend"] = {
            "status": "not_run", "reason": "SIM3_CI_BACKEND is not 1",
            "preflight_available": runtime.available, "preflight_reason": runtime.reason,
            "next_command": "SIM3_CI_BACKEND=1 python3 -m echoai.nexus0.sim3 ci",
        }
    dump_report(output, report)
    print(json.dumps(report, sort_keys=True, indent=2))
    backend_requested = os.environ.get("SIM3_CI_BACKEND") == "1"
    backend_ok = (report.get("backend", {}).get("status") == "pass")
    return 0 if report["unit"]["status"] == "pass" and (
        not backend_requested or backend_ok
    ) else 1
