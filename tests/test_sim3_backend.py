#!/usr/bin/env python3
"""SIM-3 backend bank: real Gazebo, real namespaces, or an explicit skip.

Nothing in this file has a fallback. If the container image or bubblewrap
is missing the tests skip and say why; they never substitute a fixture
for a backend, because a green produced that way would be a lie about
the only thing SIM-3 is trying to establish.

Run the full preregistered bench with:

    PYTHONPATH=.. python3 -m echoai.nexus0.sim3 bench --rehearsal \\
        --output lab/echo3_sim3_report.json
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from echoai.nexus0.sim3 import evaluate, mutants, runtime as runtimemod, sandbox
from echoai.nexus0.sim3.audit import audit_report, self_test as audit_self_test
from echoai.nexus0.sim3.canon import loads_strict
from echoai.nexus0.sim3.pkg import load_package, load_protocol
from echoai.nexus0.sim3.session import run_episode

ECHOAI = ROOT / "echoai"
EXAMPLE = ECHOAI / "docs" / "examples" / "sim3"
REPORT = ECHOAI / "lab" / "echo3_sim3_report.json"

_RUNTIME = runtimemod.load_lock()
if not _RUNTIME.lock:
    _RUNTIME = runtimemod.preflight(write=False)
_REASON = _RUNTIME.reason or "runtime unavailable"


@unittest.skipUnless(_RUNTIME.available, f"backend not_run: {_REASON}")
class TestBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = load_protocol(EXAMPLE / "protocol.json")
        cls.package = load_package(EXAMPLE, cls.protocol)
        cls.canaries = mutants.canaries("selftest")
        cls.result = run_episode(_RUNTIME, cls.package, cls.protocol,
                                 canaries=cls.canaries, label="unittest")

    def test_libsdformat_accepts_the_example(self) -> None:
        check = runtimemod.check_sdf(_RUNTIME,
                                     (EXAMPLE / "world.sdf").read_bytes())
        self.assertTrue(check["valid"], check["output"])

    def test_sandbox_namespaces_really_applied(self) -> None:
        seen = sandbox.self_test(_RUNTIME)
        self.assertTrue(seen["ok"], json.dumps(seen)[:400])

    def test_the_sphere_falls_and_touches_the_floor(self) -> None:
        verdict = evaluate.physics(self.result, self.package, self.protocol)
        self.assertTrue(verdict.ok, verdict.failures)
        self.assertEqual(verdict.measured["n_ticks"], self.protocol.steps + 1)
        self.assertGreater(verdict.measured["n_contact_msgs"], 0)

    def test_the_clock_comes_from_the_backend(self) -> None:
        step = self.protocol.step_ns
        self.assertEqual(self.result.initial["sim_time_ns"], 0)
        self.assertEqual(self.result.initial["first_pre_update_sim_time_ns"], step)
        self.assertEqual([f["sim_time_ns"] for f in self.result.frames[:3]],
                         [step, 2 * step, 3 * step])
        self.assertEqual(self.result.gravity_um, [0, 0, -9810000])

    def test_the_consumer_is_caged_and_sees_no_canary(self) -> None:
        verdict = evaluate.isolation(self.result, self.canaries)
        self.assertTrue(verdict.ok, verdict.failures)
        self.assertGreater(verdict.measured["denied_accesses"], 10)

    def test_a_missing_backend_produces_no_ticks(self) -> None:
        broken = runtimemod.Runtime(
            available=True,
            lock={**_RUNTIME.lock,
                  "container": {**_RUNTIME.lock["container"],
                                "image": "localhost/sim3-does-not-exist:0"}})
        result = run_episode(broken, self.package, self.protocol, steps=10,
                             label="unittest-backend-down")
        self.assertFalse(result.ok)
        self.assertEqual(result.n_ticks, 0)
        self.assertEqual(result.cause["code"], "backend_no_ready")


@unittest.skipUnless(REPORT.exists(), f"no report at {REPORT}")
class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = loads_strict(REPORT.read_bytes(), code="report")

    def test_evidence_reconstructs(self) -> None:
        result = audit_report(self.report)
        self.assertTrue(result["evidence_valid"],
                        json.dumps(result["findings"][:6], indent=1))

    def test_mandatory_flags(self) -> None:
        self.assertEqual(self.report["hardware_status"], "not_available")
        self.assertIs(self.report["agent_in_gazebo"], False)
        self.assertEqual(self.report["dataset_kind"], "rehearsal")
        self.assertEqual(self.report["scope"], "simulation_infrastructure")

    def test_auditor_rejects_tampered_copies(self) -> None:
        result = audit_self_test(self.report)
        for case in result["cases"]:
            with self.subTest(mutant=case["mutant"]):
                self.assertTrue(case["ok"], json.dumps(case)[:300])


if __name__ == "__main__":
    unittest.main(verbosity=2)
