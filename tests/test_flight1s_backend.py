#!/usr/bin/env python3
"""FLIGHT-1S backend bank: real PX4 and Gazebo, or an explicit skip.

Nothing here has a fallback. If the pinned image is missing the tests
skip and say why; they never substitute a fixture for a flight, because
a green produced that way would be a lie about the only thing this slice
is trying to establish.

Run the full preregistered bench with:

    PYTHONPATH=.. python3 -m echoai.nexus0.flight1s bench --rehearsal \\
        --output lab/echo3_flight1s_report.json
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from echoai.nexus0.sim3.canon import loads_strict
from echoai.nexus0.sim3.generate import generate_suite, rehearsal_assignment
from echoai.nexus0.sim3.pkg import load_protocol as load_world_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from echoai.nexus0.flight1s import evaluate, mutants, protocol as protomod
from echoai.nexus0.flight1s import runtime as runtimemod
from echoai.nexus0.flight1s.audit import audit_report, self_test as audit_self_test
from echoai.nexus0.flight1s.bench import WORLD_PROTOCOL
from echoai.nexus0.flight1s.session import run_episode

ECHOAI = ROOT / "echoai"
REPORT = ECHOAI / "lab" / "echo3_flight1s_report.json"

_RUNTIME = runtimemod.load_lock()
if not _RUNTIME.lock:
    _RUNTIME = runtimemod.preflight(write=False)
_REASON = _RUNTIME.reason or "PX4 SITL runtime unavailable"


@unittest.skipUnless(_RUNTIME.available, f"backend not_run: {_REASON}")
class TestFlight(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.proto = protomod.load()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.packages = generate_suite(
            Path(cls.tmp.name), load_world_protocol(WORLD_PROTOCOL),
            REHEARSAL_SECRET, rehearsal_assignment())
        cls.pkg = cls.packages[0]
        cls.episode = run_episode(_RUNTIME, cls.pkg.package, cls.proto.data,
                                  condition="perturbed", label="unittest")
        cls.metrics = evaluate.episode_metrics(cls.episode, cls.proto.data,
                                               package=cls.pkg.package)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_px4_pinned_commit_is_what_was_built(self) -> None:
        container = _RUNTIME.lock["container"]
        self.assertEqual(container["px4_commit"], runtimemod.PX4_COMMIT)
        self.assertEqual(container["px4_models_commit"],
                         runtimemod.PX4_MODELS_COMMIT)
        self.assertTrue(container["px4_binary_sha256"])

    def test_it_armed_took_off_hovered_and_landed(self) -> None:
        self.assertTrue(self.episode.ok, self.episode.cause)
        self.assertEqual(self.metrics["status"], "measured")
        marks = self.episode.stage_marks
        self.assertGreater(marks["disarmed_ns"], marks["armed_ns"])
        self.assertLessEqual(
            abs(self.metrics["timing"]["landed_z_um"] - marks["rest_z_um"]),
            10_000)

    def test_px4_flew_it_not_the_harness(self) -> None:
        sig = self.metrics["px4_signature"]
        self.assertTrue(sig["ok"], sig)
        self.assertTrue(sig["ulog_present"])
        self.assertTrue(sig["driver_armed"])
        self.assertTrue(sig["driver_mode_switch"])
        self.assertGreater(self.episode.ulog_bytes, 100_000)

    def test_the_disturbance_entered_the_physics(self) -> None:
        """One episode can show the force was applied, not that it was big.

        The frozen ``min_disturb_excursion_mm`` floor is a property of the
        48-episode bench and is judged there; on a single flight the
        excursion is a closed-loop outcome and PX4 sometimes rejects the
        push harder than the floor allows. What one episode does settle is
        that a wrench was published once and that the body's momentum
        changed by roughly F*dt, well clear of the nominal envelope.
        """
        imp = self.metrics["impulse"]
        self.assertEqual(imp["status"], "measured")
        self.assertGreaterEqual(imp["ratio_ppk"], 500)
        self.assertEqual(self.episode.wrench_published, 1)
        self.assertGreater(self.metrics["disturb_excursion_mm"],
                           self.proto["bands"]["hover_horiz_max_mm"])

    def test_it_came_back_and_stayed(self) -> None:
        rec = self.metrics["recovery"]
        self.assertEqual(rec["status"], "recovered", rec)
        self.assertLessEqual(rec["recovery_ms"],
                             self.proto["bands"]["recovery_timeout_ms"])

    def test_no_unauthorised_contact_and_a_clean_clock(self) -> None:
        self.assertEqual(self.metrics["collisions"]["unauthorised"], 0)
        self.assertEqual(self.metrics["timing"]["clock_regressions"], 0)

    def test_a_declared_force_that_is_never_applied_is_caught(self) -> None:
        ep = run_episode(_RUNTIME, self.pkg.package, self.proto.data,
                         condition="perturbed", label="unittest-noforce",
                         runner_path=mutants.NOFORCE)
        m = evaluate.episode_metrics(ep, self.proto.data,
                                     package=self.pkg.package)
        self.assertTrue(ep.ok, "the mutant should still fly")
        self.assertLess(m["impulse"]["ratio_ppk"], 500)

    def test_a_teleport_harness_has_no_px4_signature(self) -> None:
        ep = run_episode(_RUNTIME, self.pkg.package, self.proto.data,
                         condition="perturbed", label="unittest-teleport",
                         runner_path=mutants.TELEPORT)
        m = evaluate.episode_metrics(ep, self.proto.data,
                                     package=self.pkg.package)
        self.assertFalse(m["px4_signature"]["ok"])

    def test_the_episode_container_has_no_network(self) -> None:
        case = mutants._no_network_control(_RUNTIME)
        self.assertTrue(case["ok"], case)


@unittest.skipUnless(REPORT.exists(), f"no report at {REPORT}")
class TestReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = loads_strict(REPORT.read_bytes(), code="report")

    def test_mandatory_flags(self) -> None:
        self.assertEqual(self.report["hardware_status"], "not_available")
        self.assertIs(self.report["agent_in_gazebo"], False)
        self.assertEqual(self.report["cortex_calls"], 0)
        self.assertEqual(self.report["dataset_kind"], "rehearsal")

    def test_denominator_is_forty_eight(self) -> None:
        self.assertEqual(len(self.report["episodes"]), 48)

    def test_evidence_reconstructs(self) -> None:
        result = audit_report(self.report)
        self.assertTrue(result["evidence_valid"],
                        json.dumps(result["findings"][:6], indent=1))

    def test_auditor_rejects_tampered_copies(self) -> None:
        result = audit_self_test(self.report)
        for case in result["cases"]:
            with self.subTest(mutant=case["mutant"]):
                self.assertTrue(case["ok"], json.dumps(case)[:300])


if __name__ == "__main__":
    unittest.main(verbosity=2)
