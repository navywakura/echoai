"""Prediction chronology, bounded learning, frozen exams and native wiring."""
from __future__ import annotations

import ast
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.core.cam import Cam
from echoai.core.wsp import pack
from echoai.nexus0.world import World
from echoai.nexus0.constants import GATE_BLOCK
from echoai.echo4 import sensation_predictor as module
from echoai.echo4.sensation_predictor import Prediction, SensationPredictor, assess
from echoai.echo4.sensation_agent import SensationAgent
from echoai.echo4.sensation_campaign import campaign, audit_evidence, stage_acceptance, episodes
from echoai.echo4.demo import run_demo


def packet(index):
    return pack(seq=index)


def feed(learner, packets, actions=None):
    learner.start(packets[0])
    for action, after in zip(actions or [0] * (len(packets) - 1), packets[1:]):
        learner.anticipate(action)
        learner.observe(after)


def contextual_model():
    learner = SensationPredictor(Cam(), World())
    for _ in range(8):
        feed(learner, [packet(i) for i in (0, 1, 2, 3)])
    for _ in range(16):
        feed(learner, [packet(i) for i in (4, 5, 2, 6)])
    return learner


class TestPredictor(unittest.TestCase):
    def test_imports_original_components(self):
        from echoai.nexus0.pattern import PatternMemory
        cam, world = Cam(), World()
        learner = SensationPredictor(cam, world)
        self.assertIs(learner.cam, cam)
        self.assertIs(learner.world, world)
        self.assertIsInstance(learner.memory, PatternMemory)

    def test_cold_prediction_is_not_rewritten_by_learning(self):
        learner = SensationPredictor(Cam(), World())
        learner.start(packet(0))
        before = learner.anticipate(0)
        self.assertIsNone(before.packet)
        result = learner.observe(packet(1))
        self.assertEqual((result.label, result.error, result.exact), (3, None, False))
        learner.start(packet(0))
        self.assertEqual(learner.anticipate(0).packet, packet(1))

    def test_history_overrides_ambiguous_t(self):
        learner = contextual_model()
        self.assertEqual(learner.cam.slot[learner.world.predict(learner.cam.get(packet(2)), 0)].wsp, packet(6))
        learner.freeze()
        feed(learner, [packet(i) for i in (0, 1, 2)])
        prediction = learner.anticipate(0)
        self.assertEqual((prediction.packet, prediction.source, prediction.confidence), (packet(3), "history", 3))

    def test_contradiction_withdraws_temporal_rule(self):
        learner = contextual_model()
        feed(learner, [packet(i) for i in (0, 1, 2, 7)])
        feed(learner, [packet(i) for i in (0, 1, 2)])
        self.assertEqual(learner.anticipate(0).source, "t")

    def test_zero_depth_has_no_context_entries(self):
        learner = SensationPredictor(Cam(), World(), depth=0)
        for _ in range(10):
            feed(learner, [packet(i) for i in range(8)])
        self.assertEqual((len(learner.contexts), learner.memory.size), (0, 0))

    def test_context_capacity_never_evicts(self):
        learner = SensationPredictor(Cam(), World(), context_capacity=1)
        feed(learner, [packet(i) for i in range(8)])
        contexts = dict(learner.contexts)
        feed(learner, [packet(i) for i in range(8, 16)])
        self.assertEqual(learner.contexts, contexts)
        self.assertGreater(learner.context_dropped, 0)
        self.assertEqual(learner.cam.destroyed, 0)

    def test_pattern_capacity_reports_dropped_without_overwrite(self):
        learner = SensationPredictor(Cam(), World(), pattern_capacity=1)
        feed(learner, [packet(i) for i in range(5)])
        keys = list(learner.memory.key)
        feed(learner, [packet(i) for i in range(5, 10)])
        self.assertEqual(learner.memory.key, keys)
        self.assertGreater(learner.memory.dropped, 0)

    def test_full_cam_never_falls_back_to_zero(self):
        learner = SensationPredictor(Cam(), World())
        learner.cam.used = 4096
        learner.start(packet(0))
        self.assertIsNone(learner.anticipate(0).slot)
        learner.observe(packet(1))
        self.assertEqual(learner.cam_dropped, 2)
        self.assertEqual(learner.world.n[0], [0, 0, 0])

    def test_only_observations_enter_cam(self):
        learner = contextual_model()
        for slot in learner.cam.slot:
            if slot.occupied:
                self.assertEqual((slot.has_fact, slot.extract, slot.kind), (0, "", "observation"))
                self.assertEqual(len(slot.wsp), 16)

    def test_frozen_unknown_context_and_packet_cannot_learn(self):
        learner = contextual_model()
        learner.freeze()
        before = learner.model_hash()
        feed(learner, [packet(i) for i in range(20, 40)])
        self.assertEqual(learner.model_hash(), before)
        self.assertEqual(learner.cam.get(packet(20)), -1)

    def test_predict_does_not_mutate_model(self):
        learner = contextual_model()
        learner.start(packet(0))
        before = learner.model_hash()
        learner.anticipate(0)
        self.assertEqual(learner.model_hash(), before)

    def test_invalid_actions_do_not_mutate_model_or_pending(self):
        learner = contextual_model()
        learner.start(packet(0))
        before = learner.model_hash()
        for action in (True, False, -1, 3, 0.0, "0", None):
            with self.assertRaises(ValueError):
                learner.anticipate(action)
            self.assertIsNone(learner.pending)
            self.assertEqual(learner.model_hash(), before)

    def test_invalid_consequence_keeps_pending_prediction(self):
        learner = contextual_model()
        learner.start(packet(0))
        learner.anticipate(0)
        before = learner.model_hash(), learner.pending, learner.history.snapshot()
        for value in (b"", bytes(15), bytes(17), bytearray(16), None):
            with self.assertRaises(ValueError):
                learner.observe(value)
            self.assertEqual((learner.model_hash(), learner.pending, learner.history.snapshot()), before)

    def test_sequence_errors_and_explicit_reset(self):
        learner = SensationPredictor(Cam(), World())
        with self.assertRaises(RuntimeError):
            learner.observe(packet(0))
        learner.start(packet(0))
        learner.anticipate(0)
        for operation in (lambda: learner.anticipate(1), lambda: learner.start(packet(2)), learner.freeze):
            with self.assertRaises(RuntimeError):
                operation()
        learner.observe(packet(1))
        learner.start(packet(2))
        self.assertEqual(learner.history.steps, 0)

    def test_external_t_owner_cannot_claim_frozen_exam(self):
        learner = SensationPredictor(Cam(), World(), update_base=False)
        with self.assertRaises(RuntimeError):
            learner.freeze()

    def test_invalid_constructor(self):
        for kwargs in ({"depth": True}, {"context_capacity": False}, {"context_capacity": 4097},
                       {"pattern_capacity": 0}, {"pattern_capacity": 8192}, {"update_base": 1}):
            with self.assertRaises(ValueError):
                SensationPredictor(Cam(), World(), **kwargs)
        with self.assertRaises(ValueError):
            SensationPredictor(Cam(), World(n_actions=4))

    def test_no_private_inputs_or_physics_import(self):
        tree = ast.parse(Path(module.__file__).read_text())
        allowed = {"__future__", "dataclasses", "echoai.core.cam", "echoai.core.qn", "echoai.core.wsp",
                   "echoai.nexus0.constants", "echoai.nexus0.pattern", "echoai.nexus0.world",
                   "echoai.echo4.sensation"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, allowed)
            self.assertFalse(isinstance(node, ast.Constant) and isinstance(node.value, float))
            self.assertFalse(isinstance(node, ast.Div))
        learner = SensationPredictor(Cam(), World())
        with self.assertRaises(TypeError):
            learner.anticipate(0, h=32)


class TestLabels(unittest.TestCase):
    def test_four_labels(self):
        base = pack(E={"U": 0, "B": 0})
        prediction = Prediction(base, 0, 3, "history")
        for amount, label in ((0, 0), (20, 1), (33, 2)):
            result = assess(prediction, pack(E={"U": amount}))
            self.assertEqual((result.error, result.label), (amount, label))
        self.assertEqual(assess(replace(prediction, packet=None, slot=None, confidence=0), base).label, 3)

    def test_uncertainty_does_not_hide_observed_error(self):
        result = assess(Prediction(pack(), 0, 2, "t"), pack(E={"U": 40}))
        self.assertEqual((result.error, result.label, result.confidence), (40, 3, 2))

    def test_non_sensory_change_is_not_expected(self):
        result = assess(Prediction(pack(), 0, 3, "history"), pack(seq=1))
        self.assertFalse(result.exact)
        self.assertGreater(result.error, 0)


class TestAgentIntegration(unittest.TestCase):
    def test_forecast_precedes_world_transition_and_uses_executed_action(self):
        agent = SensationAgent()
        original = agent.env.step_homeostatic
        seen = []
        def step(action, h, temperature):
            self.assertIsNotNone(agent.sensation.pending)
            self.assertEqual(agent.sensation.pending[0], action)
            seen.append(action)
            return original(action, h, temperature)
        with patch.object(agent.env, "step_homeostatic", side_effect=step), patch(
                "echoai.nexus0.loop.gate", return_value=(GATE_BLOCK, 2, 0)):
            self.assertEqual(agent.turn(0), 2)
        self.assertEqual(seen, [2])
        self.assertEqual(agent.sensation.history.snapshot()[16], 2)
        self.assertIs(agent.sensation.cam, agent.cam)
        self.assertIs(agent.sensation.world, agent.t)

    def test_first_life_matches_original_policy_and_world(self):
        baseline = run_demo(include_trace=True)
        agent = SensationAgent()
        actions = []
        while not agent.episode_terminal:
            actions.append(agent.turn(len(actions)))
        self.assertEqual(actions, [r["executed_action"] for r in baseline["trace"]])
        self.assertEqual((agent.metrics.false_facts, agent.cam.destroyed, agent.metrics.cortex_calls), (0, 0, 0))
        agent.respawn()
        self.assertEqual(agent.sensation.history.steps, 0)

    def test_terminal_and_capacity_guards(self):
        agent = SensationAgent()
        agent.cam.used = 4095
        with self.assertRaises(RuntimeError):
            agent.turn(0)
        self.assertEqual(agent.env.life_steps, 0)


class TestCampaign(unittest.TestCase):
    def test_initial_partitions_are_disjoint(self):
        groups = []
        for residues in ((0, 1), (2,), (3,)):
            group = set()
            for body, actions in episodes(100, 40001, residues):
                index = (body.h - 1) * 126 + body.temperature - 1
                self.assertIn(index % 4, residues)
                self.assertEqual(len(actions), 24)
                group.add(index)
            groups.append(group)
        self.assertFalse(groups[0] & groups[1] or groups[0] & groups[2] or groups[1] & groups[2])

    def test_threshold_cannot_be_met_by_abstaining(self):
        bad = {"transitions": 10000, "arms": [
            {"correct": 7000}, {"correct": 10, "known": 10, "high_confidence": 10,
                                "high_confidence_correct": 10}, {}]}
        criteria = stage_acceptance(bad)
        self.assertFalse(criteria["gain_at_least_half_percentage_point"])
        self.assertFalse(criteria["coverage_at_least_98_percent"])
        self.assertFalse(criteria["high_confidence_coverage_at_least_5_percent"])

    def test_development_evidence_reproduces_and_detects_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence"
            report = campaign(development=True, output_dir=output)
            self.assertFalse(report["sensation_predictive_green"])
            self.assertTrue(all(report["invariants"].values()))
            audited = audit_evidence(output)
            self.assertTrue(audited["valid"])
            with self.assertRaises(FileExistsError):
                campaign(development=True, output_dir=output)
            # Mutations stay in temporary evidence, never in the actual campaign.
            report["sensation_predictive_green"] = True
            (output / "report.json").write_text(json.dumps(report))
            with (output / "B.jsonl").open("ab") as sink:
                sink.write(b"{}\n")
            bad = audit_evidence(output)
            self.assertFalse(bad["valid"])
            self.assertIn("report_does_not_reproduce", bad["findings"])
            self.assertIn("B_trace_does_not_reproduce", bad["findings"])


if __name__ == "__main__":
    unittest.main()
