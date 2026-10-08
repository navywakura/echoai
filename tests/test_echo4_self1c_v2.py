"""SELF-C v2: causal memory ablations, native trials and artifact integrity."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.core.qn import SLOT_FLAG_INHIBIT
from echoai.echo4 import self_reuse as readout
from echoai.echo4.boundary_world import packet
from echoai.echo4.self_probe_audit import run_condition
from echoai.echo4.self_recovery_agent import SelfRecoveryAgent
from echoai.echo4.self_reuse import choose_from_memory
from echoai.echo4.self_reuse_agent import SelfReuseAgent
from echoai.echo4.self_reuse_audit import (
    school, restore_trial, task, expose, record, verify, task_memory_hash,
)
from echoai.echo4.self_recovery_world import physical_step
from echoai.echo4.world import Body


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = Body(30, 48)
        cls.base, cls.nominal, cls.school_trace = school(cls.body)

    def diagnosis(self, hc=False, tc=False, heat=0):
        model = self.base.new_self_diagnosis(packet(self.body), self.nominal)
        run_condition(model, self.body, hc, tc, heat, mode="active")
        return model

    def fresh(self):
        agent = copy.deepcopy(self.base)
        restore_trial(agent, self.body)
        return agent


class TestReadout(Fixture):
    def test_school_uses_eight_measured_transitions_per_action(self):
        self.assertEqual(len(self.school_trace), 24)
        self.assertTrue(all(t["q_unchanged"] and t["balanced"] and not t["terminal"] for t in self.school_trace))
        slot = self.base.cam.get(packet(self.body))
        self.assertEqual(self.base.t.n[slot], [8, 8, 8])
        for action in range(3):
            nxt = self.base.t.predict(slot, action)
            self.assertEqual(self.base.cam.slot[nxt].wsp, packet(physical_step(self.body, action, True, True, 0)))

    def test_target_lookup_actually_uses_t(self):
        agent = self.fresh()
        slot = agent.cam.get(packet(self.body))
        goal = packet(physical_step(self.body, 0, True, True, 0))
        result = choose_from_memory(agent.cam, agent.t, agent.q, slot, goal, 2)
        self.assertEqual((result.action, result.source), (0, "t"))
        # A controlled mutation of T, not the goal or judge, changes the choice.
        agent.t.pred[slot][0], agent.t.pred[slot][1] = agent.t.pred[slot][1], agent.t.pred[slot][0]
        self.assertEqual(choose_from_memory(agent.cam, agent.t, agent.q, slot, goal, 2).action, 1)

    def test_no_t_ablation_does_not_read_t(self):
        agent = self.fresh()
        slot = agent.cam.get(packet(self.body))
        with patch.object(agent.t, "predict", side_effect=AssertionError("ablation read T")):
            result = choose_from_memory(agent.cam, agent.t, agent.q, slot, packet(self.body), 2, use_t=False)
        self.assertEqual((result.action, result.source), (2, "q_ablation"))

    def test_no_match_reports_q_fallback(self):
        agent = self.fresh()
        slot = agent.cam.get(packet(self.body))
        result = choose_from_memory(agent.cam, agent.t, agent.q, slot, packet(Body(100, 100)), 2)
        self.assertEqual(result.matches, ())
        self.assertEqual(result.source, "q_no_match")

    def test_request_never_writes_cam_t_or_q(self):
        agent = self.fresh()
        slot = agent.cam.get(packet(self.body))
        before = agent.sensation.model_hash(), copy.deepcopy(vars(agent.q))
        choose_from_memory(agent.cam, agent.t, agent.q, slot, packet(Body(100, 100)), 2)
        self.assertEqual(before, (agent.sensation.model_hash(), vars(agent.q)))

    def test_invalid_indices_and_ablation_types(self):
        agent = self.fresh()
        slot = agent.cam.get(packet(self.body))
        for bad in (-1, 4096, True, 2.0):
            with self.assertRaises(ValueError):
                choose_from_memory(agent.cam, agent.t, agent.q, bad, packet(self.body), 2)
        with self.assertRaises(ValueError):
            choose_from_memory(agent.cam, agent.t, agent.q, slot, packet(self.body), 2, use_t=1)

    def test_invalid_goal_packets(self):
        agent = self.fresh()
        slot = agent.cam.get(packet(self.body))
        bad = bytearray(packet(self.body))
        bad[8] = 127
        for target in (bytes(15), bytearray(16), bytes(bad)):
            with self.assertRaises(ValueError):
                choose_from_memory(agent.cam, agent.t, agent.q, slot, target, 2)

    def test_ties_use_existing_q_then_proposal(self):
        agent = self.fresh()
        slot = agent.cam.get(packet(self.body))
        goal_slot = agent.t.predict(slot, 0)
        goal = agent.cam.slot[goal_slot].wsp
        agent.t.pred[slot][1] = goal_slot
        agent.q.set(slot, 1, 9)
        self.assertEqual(choose_from_memory(agent.cam, agent.t, agent.q, slot, goal, 0).action, 1)
        agent.q.set(slot, 1, 0)
        self.assertEqual(choose_from_memory(agent.cam, agent.t, agent.q, slot, goal, 0).action, 0)

    def test_no_physics_private_fields_or_float_in_readout(self):
        tree = ast.parse(Path(readout.__file__).read_text())
        modules = {"dataclasses", "echoai.core.cam", "echoai.echo4.boundary", "echoai.echo4.sensation",
                   "echoai.nexus0.qtable", "echoai.nexus0.world"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, modules)
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, ("env", "body", "H", "temperature", "h_candidates", "t_candidates"))
            self.assertFalse(isinstance(node, ast.Div))
            self.assertFalse(isinstance(node, ast.Constant) and type(node.value) is float)


class TestNativeTrials(Fixture):
    def test_default_behavior_unchanged(self):
        a, b = SelfReuseAgent(), SelfRecoveryAgent()
        for tick in range(8):
            self.assertEqual(a.turn(tick), b.turn(tick))
        self.assertEqual(a.sensation.model_hash(), b.sensation.model_hash())

    def test_shared_cam_t_and_sensation(self):
        agent = self.fresh()
        self.assertIs(agent.cam, agent.boundary.cam)
        self.assertIs(agent.t, agent.sensation.world)

    def test_readout_before_native_execution_and_frozen_model(self):
        agent = self.fresh()
        result = task(agent, self.body, 0, packet(physical_step(self.body, 0, True, True, 0)))
        self.assertTrue(result["success"])
        self.assertTrue(result["memory_frozen"])
        self.assertEqual(result["before_execution"]["decision"]["action"], result["action"])
        self.assertEqual(result["before_execution"]["decision"]["source"], "t")

    def test_selector_cannot_use_private_registers(self):
        agent = self.fresh()
        goal = packet(physical_step(self.body, 0, True, True, 0))
        agent.arm_reuse(goal, token=25, restored=True, nominal_body_confirmed=True)
        slot = agent.cam.get(packet(self.body))
        expected = agent._propose(slot, 0, greedy=True)
        agent.env = agent.H = agent.temperature = None
        self.assertEqual(agent._propose(slot, 0, greedy=True), expected)

    def test_one_action_only_and_no_respawn(self):
        agent = self.fresh()
        task(agent, self.body, 0, packet(self.body))
        with self.assertRaises(RuntimeError):
            agent.turn(100, greedy=True)
        with self.assertRaises(RuntimeError):
            agent.respawn()

    def test_no_restore_of_unexecuted_request(self):
        agent = self.fresh()
        agent.arm_reuse(packet(self.body), token=25, restored=True, nominal_body_confirmed=True)
        with self.assertRaises(RuntimeError):
            restore_trial(agent, self.body)

    def test_strict_receipts_do_not_change_models(self):
        agent = self.fresh()
        old = task_memory_hash(agent)
        for token, restored, nominal in ((24, True, True), (True, True, True), (25, 1, True), (25, True, 1)):
            with self.assertRaises(ValueError):
                agent.arm_reuse(packet(self.body), token=token, restored=restored, nominal_body_confirmed=nominal)
        self.assertEqual(task_memory_hash(agent), old)
        self.assertFalse(agent.trial_active)

    def test_unknown_diagnosis_cannot_authorize_exposure(self):
        agent = self.fresh()
        unknown = agent.new_self_diagnosis(packet(self.body), self.nominal)
        with self.assertRaises(ValueError):
            agent.arm_exposure(unknown, 0, mode="selective", token=25, restored=True, same_context=True)
        self.assertFalse(agent.trial_active)

    def test_unknown_mode_and_missing_context(self):
        agent = self.fresh()
        for mode, context in (("invented", True), ("selective", False)):
            with self.assertRaises(ValueError):
                agent.arm_exposure(self.diagnosis(), 0, mode=mode, token=25, restored=True, same_context=context)

    def test_no_learning_resumes_after_readonly_exam(self):
        agent = self.fresh()
        task(agent, self.body, 0, packet(self.body))
        restore_trial(agent, self.body)
        with self.assertRaises(RuntimeError):
            agent.arm_school(0, token=26, restored=True)
        with self.assertRaises(RuntimeError):
            agent.arm_exposure(self.diagnosis(), 0, mode="selective", token=26, restored=True, same_context=True)

    def test_gate_still_has_final_authority(self):
        agent = self.fresh()
        agent.cam.slot[agent.cam.get(packet(self.body))].flags |= SLOT_FLAG_INHIBIT
        result = task(agent, self.body, 0, packet(physical_step(self.body, 0, True, True, 0)))
        self.assertEqual(result["proposed"], 0)
        self.assertEqual((result["action"], result["gate"]), (2, 2))
        self.assertFalse(result["success"])
        self.assertTrue(result["memory_frozen"])

    def test_full_cam_prevents_execution(self):
        agent = self.fresh()
        agent.arm_reuse(packet(self.body), token=25, restored=True, nominal_body_confirmed=True)
        agent.cam.used = 4096
        with self.assertRaises(RuntimeError):
            agent.turn(0, greedy=True)
        self.assertEqual(agent.env.total_steps, 0)

    def test_targets_outside_semantic_context_rejected(self):
        agent = self.fresh()
        target = bytearray(packet(self.body))
        target[0] = 47
        with self.assertRaises(ValueError):
            agent.arm_reuse(bytes(target), token=25, restored=True, nominal_body_confirmed=True)

    def test_protected_t_has_a_real_downstream_effect(self):
        diagnosis = self.diagnosis()
        goal = packet(physical_step(self.body, 0, True, True, 0))
        protected, report = expose(self.base, diagnosis, self.body, False, False, 0, "selective")
        unprotected, control = expose(self.base, diagnosis, self.body, False, False, 0, "unprotected")
        self.assertEqual(report["body_contamination"], 0)
        self.assertGreater(control["body_contamination"], 0)
        self.assertTrue(task(protected, self.body, 0, goal)["success"])
        self.assertFalse(task(unprotected, self.body, 0, goal)["success"])


class TestAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / "evidence"
        cls.report = record(cls.path, quick=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_smoke_cannot_close_v2_or_self(self):
        self.assertFalse(self.report["self_c_v2_green"])
        self.assertFalse(self.report["self1_green"])
        result = self.report["stages"]["smoke"]
        self.assertEqual(result["conditions"], 12)
        self.assertEqual(result["exposure_matched"], 12)
        self.assertTrue(result["checks"]["frozen_tasks"])
        self.assertTrue(result["checks"]["protection"])

    def test_physical_replay(self):
        self.assertTrue(verify(self.path)["valid"])

    def test_exclusive_artifact_creation(self):
        with self.assertRaises(FileExistsError):
            record(self.path, quick=True)

    def test_report_cannot_promote_full_self(self):
        path = self.path / "report.json"
        raw = path.read_bytes()
        try:
            altered = json.loads(raw)
            altered["self1_green"] = True
            path.write_text(json.dumps(altered))
            self.assertFalse(verify(self.path)["valid"])
        finally:
            path.write_bytes(raw)

    def test_goal_or_forecast_trace_tampering_rejected(self):
        path = self.path / "traces.jsonl"
        raw = path.read_bytes()
        try:
            path.write_bytes(raw.replace(b'"source":"t"', b'"source":"fabricated"', 1))
            self.assertFalse(verify(self.path)["valid"])
            path.write_bytes(raw + b"{}\n")
            self.assertFalse(verify(self.path)["valid"])
        finally:
            path.write_bytes(raw)

    def test_missing_source_or_artifact(self):
        self.assertFalse(verify(Path(self.temp.name) / "missing")["valid"])
        with patch("echoai.echo4.self_reuse_audit.sources", return_value={}):
            self.assertFalse(verify(self.path)["valid"])

    def test_malformed_report_is_rejected(self):
        path = self.path / "report.json"
        raw = path.read_bytes()
        try:
            for malformed in (b"[]", b"null", b"{broken"):
                path.write_bytes(malformed)
                self.assertFalse(verify(self.path)["valid"])
        finally:
            path.write_bytes(raw)


if __name__ == "__main__":
    unittest.main()
