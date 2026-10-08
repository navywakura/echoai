"""SELF-C actual-loop recovery, selective T/PATTERN gating and replay."""
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.core.qn import SLOT_FLAG_INHIBIT
from echoai.echo4 import self_recovery as runtime
from echoai.echo4.boundary_world import packet
from echoai.echo4.self_probe_agent import SelfProbeAgent
from echoai.echo4.self_probe_audit import run_condition
from echoai.echo4.self_recovery import RecoveryBelief, RecoveryStop, advance
from echoai.echo4.self_recovery_agent import SelfRecoveryAgent
from echoai.echo4.self_recovery_audit import school, episode, viable, record, verify, sensory_hash, row_state
from echoai.echo4.self_recovery_world import RecoveryEnv, physical_step
from echoai.echo4.world import Body


class RecoveryFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = Body(34, 60)
        cls.base, cls.nominal = school(cls.body)

    def diagnosis(self, hc=False, tc=True, heat=0):
        model = self.base.new_self_diagnosis(packet(self.body), self.nominal)
        run_condition(model, self.body, hc, tc, heat, mode="active")
        return model

    def agent(self, hc=False, tc=True, heat=0, mode="selective"):
        agent = copy.deepcopy(self.base)
        agent.env = RecoveryEnv(self.body, h_coupled=hc, temperature_coupled=tc, heat=heat)
        agent.start_recovery(self.diagnosis(hc, tc, heat), restored=True, same_context=True, mode=mode)
        return agent


class TestBelief(RecoveryFixture):
    def test_unknown_and_pending_do_not_authorize_recovery(self):
        unknown = self.base.new_self_diagnosis(packet(self.body), self.nominal)
        with self.assertRaises(ValueError):
            RecoveryBelief(unknown, restored=True, same_context=True)
        unknown.choose(18)
        with self.assertRaises(ValueError):
            RecoveryBelief(unknown, restored=True, same_context=True)

    def test_restoration_receipts_are_strict(self):
        for restored, same in ((False, True), (1, True), (True, 1), (True, False)):
            with self.assertRaises(ValueError):
                RecoveryBelief(self.diagnosis(), restored=restored, same_context=same)

    def test_no_observation_without_forecast(self):
        model = RecoveryBelief(self.diagnosis(), restored=True, same_context=True)
        with self.assertRaises(RuntimeError):
            model.observe(model.current, 2, model.current)

    def test_pending_forecast_not_overwritten(self):
        model = RecoveryBelief(self.diagnosis(), restored=True, same_context=True)
        model.prepare(model.current, 2, 0)
        before = copy.deepcopy(model.pending)
        with self.assertRaises(RuntimeError):
            model.prepare(model.current, 1, 0)
        self.assertEqual(before, model.pending)

    def test_stale_and_malformed_execution_fail_closed(self):
        for before, action, after in ((None, 2, packet(self.body)), (packet(self.body), True, packet(self.body)),
                                     (packet(self.body), 0, packet(self.body)), (packet(self.body), 2, bytes(15))):
            model = RecoveryBelief(self.diagnosis(), restored=True, same_context=True)
            model.prepare(model.current, 2, 0)
            self.assertFalse(model.observe(before, action, after))
            self.assertEqual(model.stopped, "invalid_execution")

    def test_contradiction_abstains_and_stops(self):
        model = RecoveryBelief(self.diagnosis(), restored=True, same_context=True)
        before = model.current
        model.prepare(before, 2, 0)
        self.assertFalse(model.observe(before, 2, packet(Body(100, 110))))
        self.assertEqual(model.stopped, "model_contradiction")
        with self.assertRaises(RecoveryStop):
            model.choose(model.current, (0, 0, 0), 2)

    def test_no_safe_action_is_not_a_fourth_action(self):
        model = RecoveryBelief(self.diagnosis(), restored=True, same_context=True)
        model.h = ((1, False),)
        with self.assertRaises(RecoveryStop):
            model.choose(model.current, (0, 0, 0), 2)
        self.assertIsNone(model.pending)
        self.assertEqual(model.steps, 0)

    def test_resource_bounds_and_counter_saturation(self):
        model = RecoveryBelief(self.diagnosis(), restored=True, same_context=True)
        model.held = runtime.LIMIT
        model.prepare(model.current, 2, 0)
        model.observe(None, 2, model.current)
        self.assertEqual(model.held, runtime.LIMIT)
        self.assertLessEqual(model.resources()["h_candidates"], 64)
        self.assertLessEqual(model.resources()["t_candidates"], 160)
        self.assertEqual(model.resources()["retained_traces"], 0)

    def test_first_pulse_is_not_repeated(self):
        self.assertEqual(advance((64, False, 16), 1, thermal=True, first=True), (84, False, 16))
        self.assertEqual(advance((84, False, 16), 1, thermal=True, first=False), (88, False, 16))

    def test_current_candidates_advance_not_restored(self):
        model = RecoveryBelief(self.diagnosis(), restored=True, same_context=True)
        before = model.current
        model.prepare(before, 2, 0)
        after = physical_step(self.body, 2, False, True, 0)
        model.observe(before, 2, packet(after))
        self.assertIn((after.h, False), model.h)
        self.assertNotIn((self.body.h, False), model.h)

    def test_runtime_has_no_executor_or_private_register_access(self):
        tree = ast.parse(Path(runtime.__file__).read_text())
        allowed = {"echoai.echo4.boundary", "echoai.echo4.self_attribution"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, allowed)
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, ("env", "body", "H", "temperature", "_hc", "_tc", "_heat"))
            self.assertFalse(isinstance(node, ast.Div))
            self.assertFalse(isinstance(node, ast.Constant) and type(node.value) is float)


class TestNativeIntegration(RecoveryFixture):
    def test_default_agent_behavior_unchanged(self):
        new, old = SelfRecoveryAgent(), SelfProbeAgent()
        for tick in range(8):
            self.assertEqual(new.turn(tick), old.turn(tick))
        self.assertEqual(new.sensation.model_hash(), old.sensation.model_hash())

    def test_shared_tables_and_reference(self):
        agent = self.agent()
        self.assertIs(agent.cam, agent.boundary.cam)
        self.assertIs(agent.t, agent.sensation.world)
        self.assertIs(agent.self_change.boundary, agent.boundary)
        self.assertEqual(len(agent.q.q), 4096)
        self.assertEqual(agent.t.n_actions, 3)

    def test_prediction_is_present_before_every_execution(self):
        agent = self.agent()
        step = agent.env.step_homeostatic
        records = []

        def observe(action, h, temperature):
            pending = agent.recovery.pending
            self.assertIsNotNone(pending)
            self.assertEqual(pending[1], action)
            self.assertEqual(pending[0], agent.observation(agent.env.cell()))
            records.append(copy.deepcopy(pending))
            return step(action, h, temperature)

        with patch.object(agent.env, "step_homeostatic", side_effect=observe):
            for tick in range(4):
                agent.turn(tick, greedy=True)
        self.assertEqual(len(records), 4)
        self.assertIsNone(agent.recovery.pending)

    def test_body_effect_holds_both_t_and_sensation(self):
        agent = self.agent(hc=False, tc=False)
        # Force a diagnostic action to test the learning gate, not the selector.
        before = copy.deepcopy(vars(agent.t))
        pattern = sensory_hash(agent.sensation)
        history = agent.sensation.history.snapshot()
        with patch.object(agent.recovery, "choose", return_value=0):
            agent.turn(0, greedy=True)
        self.assertFalse(agent.recovery.last["allowed"])
        self.assertEqual(vars(agent.t), before)
        self.assertEqual(sensory_hash(agent.sensation), pattern)
        self.assertNotEqual(agent.sensation.history.snapshot(), history)
        self.assertFalse(agent.sensation.frozen)
        self.assertEqual(agent.life_turns, 1)

    def test_nominal_body_allows_real_learning(self):
        agent = self.agent(hc=True, tc=True)
        before = copy.deepcopy(vars(agent.t))
        agent.turn(0, greedy=True)
        self.assertTrue(agent.recovery.last["allowed"])
        self.assertNotEqual(vars(agent.t), before)

    def test_external_pulse_is_not_mislabeled_body_damage(self):
        agent = self.agent(hc=True, tc=True, heat=16)
        agent.turn(0, greedy=True)
        self.assertTrue(agent.recovery.last["allowed"])

    def test_gate_veto_and_no_more_actions(self):
        agent = self.agent()
        slot = agent.cam.get(packet(self.body))
        agent.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
        before = copy.deepcopy(vars(agent.t))
        action = agent.turn(0, greedy=True)
        self.assertEqual(action, 2)
        self.assertEqual(agent.last_gate_decision, 2)
        self.assertEqual(agent.recovery.stopped, "gate_veto")
        self.assertEqual(vars(agent.t), before)
        with self.assertRaises(RecoveryStop):
            agent.turn(1, greedy=True)
        self.assertEqual(agent.env.total_steps, 1)

    def test_no_reset_or_respawn_after_attachment(self):
        agent = self.agent()
        with self.assertRaises(RuntimeError):
            agent.env.reset()
        with self.assertRaises(RecoveryStop):
            agent.respawn()

    def test_capacity_guard_prevents_physical_step(self):
        agent = self.agent()
        agent.cam.used = 4096
        with self.assertRaises(RuntimeError):
            agent.turn(0)
        self.assertEqual(agent.env.total_steps, 0)

    def test_invalid_attachment_no_mutation(self):
        agent = copy.deepcopy(self.base)
        for diagnosis in (None, False):
            with self.assertRaises(ValueError):
                agent.start_recovery(diagnosis, restored=True, same_context=True)
        self.assertIsNone(agent.recovery)
        self.assertIsNone(agent.self_model)

    def test_no_reinstallation_hides_a_new_life(self):
        agent = self.agent()
        with self.assertRaises(RuntimeError):
            agent.start_recovery(self.diagnosis(), restored=True, same_context=True)

    def test_control_freeze_all_really_freezes_both(self):
        agent = self.agent(mode="all_self")
        before, pattern = copy.deepcopy(vars(agent.t)), sensory_hash(agent.sensation)
        agent.turn(0, greedy=True)
        self.assertEqual(vars(agent.t), before)
        self.assertEqual(sensory_hash(agent.sensation), pattern)

    def test_continuous_executor_matches_probe_first_step(self):
        from echoai.echo4.self_probe_world import run_probe
        from echoai.echo4.self_attribution import ProbePlan
        for hc in (False, True):
            for tc in (False, True):
                for heat in (-16, 0, 16):
                    for action in range(3):
                        trace, _ = run_probe(self.body, ProbePlan(1, 0, (action,), 0, 0),
                                             h_coupled=hc, temperature_coupled=tc, heat=heat)
                        env = RecoveryEnv(self.body, h_coupled=hc, temperature_coupled=tc, heat=heat)
                        env.step_homeostatic(action, self.body.h, self.body.temperature)
                        self.assertEqual(packet(env.body), trace.packets[-1])

    def test_physiological_mismatch_does_not_teleport(self):
        env = RecoveryEnv(self.body)
        with self.assertRaises(ValueError):
            env.step_homeostatic(2, 100, 100)
        self.assertEqual(env.body, self.body)
        self.assertEqual(env.total_steps, 0)

    def test_private_viability_accounts_for_impossible_cases(self):
        self.assertTrue(viable(34, 60, True, True, 0, 24))
        self.assertFalse(viable(34, 60, False, False, 16, 24))
        self.assertFalse(viable(1, 64, False, True, 0, 2))

    def test_proposal_cannot_read_physical_registers(self):
        agent = self.agent()
        slot = agent.cam.get(packet(self.body))
        expected = agent._propose(slot, 0, greedy=True)
        agent.H = agent.temperature = None
        agent.env = None
        self.assertEqual(agent._propose(slot, 0, greedy=True), expected)

    def test_resource_ledger_uses_actual_coupled_channel(self):
        for hc in (False, True):
            env = RecoveryEnv(self.body, h_coupled=hc, temperature_coupled=False, heat=-16)
            for action in (0, 1, 2):
                result = env.advance(action)
                self.assertTrue(result.balanced)
                self.assertTrue(env.balanced)
            self.assertEqual(env.total_steps, 3)

    def test_no_action_after_physical_death(self):
        env = RecoveryEnv(Body(1, 64), h_coupled=False)
        env.advance(2)
        self.assertFalse(env.body.alive)
        with self.assertRaises(RuntimeError):
            env.advance(0)
        self.assertEqual(env.total_steps, 1)


class TestAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / "evidence"
        cls.report = record(cls.path, quick=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_smoke_preserves_invariants_not_full_green(self):
        self.assertFalse(self.report["self1_green"])
        self.assertTrue(self.report["checks"]["invariants"])
        self.assertTrue(self.report["checks"]["selective_protection"])
        self.assertTrue(self.report["checks"]["retained_models"])
        self.assertEqual(self.report["same_actions_without_protection"], 20)

    def test_replay(self):
        self.assertTrue(verify(self.path)["valid"])

    def test_refuses_overwrite(self):
        with self.assertRaises(FileExistsError):
            record(self.path, quick=True)

    def test_rejects_fabricated_full_green(self):
        path = self.path / "report.json"
        raw = path.read_bytes()
        try:
            report = json.loads(raw)
            report["self1_green"] = True
            path.write_text(json.dumps(report))
            self.assertFalse(verify(self.path)["valid"])
        finally:
            path.write_bytes(raw)

    def test_rejects_physical_trace_tampering(self):
        path = self.path / "traces.jsonl"
        raw = path.read_bytes()
        try:
            path.write_bytes(raw.replace(b'"restored":true', b'"restored":false', 1))
            self.assertFalse(verify(self.path)["valid"])
        finally:
            path.write_bytes(raw)

    def test_missing_artifact_changed_source(self):
        self.assertFalse(verify(Path(self.temp.name) / "missing")["valid"])
        with patch("echoai.echo4.self_recovery_audit.sources", return_value={}):
            self.assertFalse(verify(self.path)["valid"])

    def test_trailing_or_truncated_trace(self):
        path = self.path / "traces.jsonl"
        raw = path.read_bytes()
        try:
            path.write_bytes(raw + b"{}\n")
            self.assertFalse(verify(self.path)["valid"])
            path.write_bytes(raw[:100])
            self.assertFalse(verify(self.path)["valid"])
        finally:
            path.write_bytes(raw)


if __name__ == "__main__":
    unittest.main()
