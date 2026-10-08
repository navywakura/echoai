"""Prospective BOUNDARY tests: causal controls, provenance and bounded state."""
from __future__ import annotations

import ast
from dataclasses import replace
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

from echoai.core.cam import Cam
from echoai.core.wsp import pack
from echoai.echo4 import boundary as module
from echoai.echo4.boundary import ALL, MASK, BoundaryMap, Estimate, Pair, Trial, code, validate
from echoai.echo4.boundary_bench import audit, campaign, native_probe, run_stage, stage_acceptance
from echoai.echo4.boundary_world import Experiment, experiment, judge, packet, run_pair
from echoai.echo4.sensation_predictor import SensationPredictor
from echoai.echo4.world import Body
from echoai.nexus0.world import World


def pair(identifier=1, family="full", action=0):
    return run_pair(experiment(family, action, "development", random.Random(42)),
                    identifier, fault=family)[0]


def identified(family="full", action=0, count=8):
    learner = BoundaryMap(Cam())
    for i in range(1, count + 1):
        learner.observe(pair(i, family, action))
    return learner


def snapshot(learner):
    return (learner.model_hash(), SensationPredictor(learner.cam, World()).model_hash())


class TestBoundary(unittest.TestCase):
    def test_cold_unknown_then_eight_replicates(self):
        learner = identified(count=7)
        p = pair(8)
        self.assertEqual(learner.estimate(p.treatment.packets[0], 0), Estimate())
        learner.observe(p)
        self.assertEqual(learner.estimate(p.treatment.packets[0], 0).influence, MASK)

    def test_signed_thermal_code(self):
        self.assertEqual(code(pack(E={"B": -88}), 9), -88)
        self.assertEqual(code(pack(E={"B": 88}), 9), 88)

    def test_independent_hand_calculated_contrast_and_signs(self):
        initial = pack(E={"U": 60, "B": -13})
        active = pack(E={"U": 30, "B": 13})
        reference = pack(E={"U": 60, "B": 13})
        learner = BoundaryMap(Cam())
        for i in range(1, 9):
            t = Trial(i, 0, (initial, active, active), (0, 1, 2), (0, 2), (0, 0), (False,) * 3)
            r = Trial(i, 2, (initial, reference, reference), (0, 1, 2), (2, 2), (0, 0), (False,) * 3)
            learner.observe(Pair(i, True, True, t, r))
        self.assertEqual(learner.estimate(initial, 0), Estimate(256, 512, ALL ^ MASK, (-1, 0), (1, 0)))

    def test_channels_independently_disconnected(self):
        for family, influence in (("full", 768), ("h_only", 256), ("temperature_only", 512)):
            with self.subTest(family=family):
                learner = identified(family)
                estimate = learner.estimate(pair(family=family).treatment.packets[0], 0)
                self.assertEqual((estimate.influence, estimate.no_observed_effect), (influence, MASK ^ influence))

    def test_external_predictable_change_is_not_control(self):
        learner = identified("external_only")
        p = pair(family="external_only")
        self.assertNotEqual(p.treatment.packets[0], p.treatment.packets[-1])
        self.assertEqual(learner.estimate(p.treatment.packets[0], 0).no_observed_effect, MASK)

    def test_external_common_heat_does_not_erase_own_effect(self):
        learner = identified("mixed")
        self.assertEqual(learner.estimate(pair(family="mixed").treatment.packets[0], 0).influence, MASK)

    def test_delay_ignores_pending_tick(self):
        learner = identified("delayed")
        result = learner.estimate(pair(family="delayed").treatment.packets[0], 0)
        self.assertEqual(result.first_effect, (2, 2))
        self.assertTrue(all(sum(row[0]) == 0 for row in next(iter(learner.rows.values()))))

    def test_quantization_does_not_prove_physical_absence(self):
        p, private, _ = run_pair(experiment("subband", 0, "development", random.Random(0)), 1)
        self.assertNotEqual(private["states"]["treatment"][1]["h"], private["states"]["reference"][1]["h"])
        learner = identified("subband")
        self.assertEqual(learner.estimate(p.treatment.packets[0], 0).no_observed_effect, MASK)

    def test_sign_conflict_abstains(self):
        learner = identified()
        p = pair(9)
        opposite = replace(p.treatment, packets=(p.treatment.packets[0],
                           pack(E={"U": 100, "B": -100}), pack(E={"U": 100, "B": -100})))
        learner.observe(replace(p, treatment=opposite))
        self.assertEqual(learner.estimate(p.treatment.packets[0], 0), Estimate())

    def test_seven_eighths_and_zero_replication_rule(self):
        learner = identified(count=7)
        p = pair(8)
        learner.observe(replace(p, treatment=replace(p.treatment, packets=p.reference.packets)))
        self.assertEqual(learner.estimate(p.treatment.packets[0], 0).influence, MASK)
        p = pair(9)
        learner.observe(replace(p, treatment=replace(p.treatment, packets=p.reference.packets)))
        self.assertEqual(learner.estimate(p.treatment.packets[0], 0), Estimate())

    def test_estimates_never_write_facts_and_keep_other_bytes_unknown(self):
        learner = identified()
        before = snapshot(learner)
        result = learner.estimate(pair().treatment.packets[0], 0)
        self.assertEqual(result.unknown, ALL ^ MASK)
        self.assertEqual(snapshot(learner), before)
        self.assertTrue(all(not s.has_fact and not s.extract for s in learner.cam.slot if s.occupied))
        self.assertEqual(learner.cam.destroyed, 0)

    def test_repeated_and_out_of_order_ids_reject_without_mutation(self):
        learner = identified()
        before = snapshot(learner)
        for i in (1, 7, 8):
            with self.assertRaises(ValueError):
                learner.observe(pair(i))
            self.assertEqual(snapshot(learner), before)

    def test_invalid_receipts_do_not_mutate_either_map_or_cam(self):
        learner = identified()
        p = pair(9)
        invalid = [replace(p, restored=False), replace(p, restored=1), replace(p, common_schedule=False),
                   replace(p, identifier=True), replace(p, identifier=-1), replace(p, identifier=1 << 31),
                   replace(p, treatment=replace(p.treatment, token=10)),
                   replace(p, treatment=replace(p.treatment, intended=True)),
                   replace(p, reference=replace(p.reference, intended=0)),
                   replace(p, reference=replace(p.reference, applied=(0, 2))),
                   replace(p, treatment=replace(p.treatment, applied=(0, 0))),
                   replace(p, treatment=replace(p.treatment, applied=(2, 2))),
                   replace(p, treatment=replace(p.treatment, applied=(None, 2))),
                   replace(p, treatment=replace(p.treatment, applied=(False, 2))),
                   replace(p, treatment=replace(p.treatment, gates=(1, 0))),
                   replace(p, treatment=replace(p.treatment, gates=(2, 0))),
                   replace(p, treatment=replace(p.treatment, gates=(False, 0))),
                   replace(p, treatment=replace(p.treatment, ticks=(0, 0, 2))),
                   replace(p, treatment=replace(p.treatment, ticks=(0, True, 2))),
                   replace(p, treatment=replace(p.treatment, terminal=(False, False, True))),
                   replace(p, treatment=replace(p.treatment, terminal=(False, 0, False))),
                   replace(p, treatment=replace(p.treatment, packets=(bytes(15),) * 3)),
                   replace(p, treatment=replace(p.treatment, packets=(bytearray(16),) * 3)),
                   replace(p, treatment=replace(p.treatment, packets=list(p.treatment.packets))),
                   replace(p, treatment=replace(p.treatment, packets=(bytes(16),) + p.treatment.packets[1:])),
                   None]
        before = snapshot(learner)
        for invalid_pair in invalid:
            with self.subTest(pair=invalid_pair):
                with self.assertRaises(ValueError):
                    learner.observe(invalid_pair)
                self.assertEqual(snapshot(learner), before)

    def test_equal_initial_packet_without_restore_is_insufficient(self):
        p = pair()
        self.assertEqual(p.treatment.packets[0], p.reference.packets[0])
        with self.assertRaises(ValueError):
            validate(replace(p, restored=False))

    def test_veto_and_missing_receipts_are_not_no_effect(self):
        for family in ("veto", "missing_execution", "unmatched", "stale"):
            learner = BoundaryMap(Cam())
            for i in range(1, 9):
                with self.assertRaises(ValueError):
                    learner.observe(pair(i, family))
            self.assertEqual(learner.estimate(pair(family=family).treatment.packets[0], 0), Estimate())
            self.assertEqual((learner.pairs, learner.cam.used), (0, 0))

    def test_map_capacity_preserves_rows_and_cam(self):
        learner = BoundaryMap(Cam(), capacity=1)
        learner.observe(pair())
        before = snapshot(learner)
        with self.assertRaises(OverflowError):
            learner.observe(pair(2, action=1))
        self.assertEqual(snapshot(learner), before)
        learner.observe(pair(2))  # existing row still writable

    def test_full_cam_never_aliases_row_zero(self):
        learner = BoundaryMap(Cam())
        learner.cam.used = 4096
        before = snapshot(learner)
        with self.assertRaises(OverflowError):
            learner.observe(pair())
        self.assertEqual(snapshot(learner), before)
        self.assertEqual(learner.rows, {})

    def test_pair_budget_bounds_counters(self):
        learner = BoundaryMap(Cam())
        prototype = pair()
        for i in range(1, 4097):
            p = replace(prototype, identifier=i, treatment=replace(prototype.treatment, token=i),
                        reference=replace(prototype.reference, token=i))
            learner.observe(p)
        before = snapshot(learner)
        with self.assertRaises(OverflowError):
            learner.observe(pair(4097))
        self.assertEqual(snapshot(learner), before)
        self.assertEqual(learner.resources()["retained_trials"], 0)
        self.assertTrue(all(sum(c) <= 4096 for row in learner.rows.values() for channel in row for c in channel))

    def test_freeze_refuses_training_and_unknown_queries_do_not_allocate(self):
        learner = identified()
        learner.freeze()
        before = snapshot(learner)
        with self.assertRaises(RuntimeError):
            learner.observe(pair(9))
        self.assertEqual(learner.estimate(pack(seq=250), 0), Estimate())
        self.assertEqual(snapshot(learner), before)

    def test_invalid_api(self):
        for capacity in (False, 0, 129, 1.0):
            with self.assertRaises(ValueError):
                BoundaryMap(Cam(), capacity=capacity)
        with self.assertRaises(ValueError):
            BoundaryMap(None)
        learner = BoundaryMap(Cam())
        for action in (2, True, 0.0, None):
            with self.assertRaises(ValueError):
                learner.estimate(bytes(16), action)

    def test_runtime_has_no_privileged_import_or_floating_math(self):
        tree = ast.parse(Path(module.__file__).read_text())
        allowed = {"__future__", "dataclasses", "hashlib", "json", "echoai.core.cam",
                   "echoai.core.qn", "echoai.core.wsp", "echoai.echo4.sensation"}
        self.assertTrue(all(n.module in allowed for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)))
        self.assertFalse(any(isinstance(n, ast.Div) or isinstance(n, ast.Constant) and type(n.value) is float
                             for n in ast.walk(tree)))
        self.assertEqual(set(Pair.__dataclass_fields__), {"identifier", "restored", "common_schedule", "treatment", "reference"})


class TestExperiment(unittest.TestCase):
    def test_trial_order_does_not_change_physics(self):
        spec = experiment("mixed", 0, "development", random.Random(8))
        a, p, _ = run_pair(spec, 1)
        b, q, _ = run_pair(spec, 1, reverse=True)
        self.assertEqual(a, b)
        self.assertEqual(p["states"], q["states"])

    def test_forecast_precedes_physics(self):
        import echoai.echo4.boundary_world as world
        sensory = SensationPredictor(Cam(), World())
        original = world.transition
        calls = []

        def checked(*args):
            self.assertIsNotNone(sensory.pending)
            calls.append(args[1])
            return original(*args)

        with patch.object(world, "transition", checked):
            run_pair(Experiment(Body(30, 50), 0), 1, sensation=sensory)
        self.assertEqual(len(calls), 8)

    def test_terminal_trial_does_not_act_again(self):
        with self.assertRaises(RuntimeError):
            run_pair(Experiment(Body(1, 50), 1), 1)

    def test_native_agent_shares_original_components(self):
        self.assertTrue(native_probe()["passed"])

    def test_original_native_gate_veto_is_honored(self):
        from echoai.echo4.boundary_bench import _ScheduledProbe
        from echoai.nexus0.constants import GATE_BLOCK
        agent = _ScheduledProbe(initial=Body(30, 50))
        agent.pulse = 0
        with patch("echoai.nexus0.loop.gate", return_value=(GATE_BLOCK, 2, 128)):
            self.assertEqual(agent.turn(0), 2)
        self.assertEqual(agent.last_gate_decision, GATE_BLOCK)
        self.assertEqual(agent.boundary.pairs, 0)

    def test_development_and_acceptance_negative_controls(self):
        result = run_stage("development", 1)
        self.assertTrue(result["passed"])
        self.assertEqual(result["total"], 88)
        for field, value, check in (("correct", 0, "accuracy"), ("false_influence", 1, "no_false_influence"),
                                    ("invalid_abstained", 0, "invalid_abstention"), ("frozen_blocks", 0, "frozen"),
                                    ("lag_correct", 0, "lag"), ("baseline_correct", 88, "beats_coincidence"),
                                    ("cam_destroyed", 1, "invariants"), ("max_rows", 129, "bounded")):
            self.assertFalse(stage_acceptance({**result, field: value})[check])

    def test_bad_b_never_opens_c(self):
        from echoai.echo4.boundary_bench import run_campaign
        visited = []

        def stage(name, blocks, emit):
            visited.append(name)
            return {"passed": name != "B"}

        with patch("echoai.echo4.boundary_bench.run_stage", stage):
            self.assertFalse(run_campaign(quick=True)["passed"])
        self.assertEqual(visited, ["development", "B"])


class TestAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name) / "smoke"
        cls.report = campaign(cls.directory, quick=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_full_replay_valid_but_smoke_cannot_close(self):
        result = audit(self.directory)
        self.assertTrue(result["valid"])
        self.assertFalse(result["closure_eligible"])

    def test_evidence_never_overwrites(self):
        with self.assertRaises(FileExistsError):
            campaign(self.directory, quick=True)

    def test_tampered_report_is_rejected(self):
        path = self.directory / "report.json"
        original = path.read_bytes()
        try:
            altered = json.loads(original)
            altered["stages"]["B"]["correct"] += 1
            path.write_text(json.dumps(altered))
            self.assertFalse(audit(self.directory)["valid"])
        finally:
            path.write_bytes(original)

    def test_tampered_receipt_and_trace_are_rejected(self):
        path = self.directory / "development.jsonl"
        original = path.read_bytes()
        lines = original.splitlines(keepends=True)
        try:
            first = json.loads(lines[0])
            first["public"]["restored"] = False
            path.write_bytes(json.dumps(first).encode() + b"\n" + b"".join(lines[1:]))
            self.assertFalse(audit(self.directory)["valid"])
            path.write_bytes(original + b"{}\n")
            self.assertFalse(audit(self.directory)["valid"])
        finally:
            path.write_bytes(original)

    def test_tampered_source_manifest_rejected_before_execution(self):
        with patch("echoai.echo4.boundary_bench.sources", return_value={}):
            self.assertFalse(audit(self.directory)["valid"])

    def test_missing_artifact_fails_closed(self):
        self.assertFalse(audit(Path(self.temp.name) / "missing")["valid"])


if __name__ == "__main__":
    unittest.main()
