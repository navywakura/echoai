"""MAINT-A: mechanism integrity, not a learned-maintenance acceptance exam."""
from __future__ import annotations

import ast
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from echoai.echo4 import maintain_bench as bench
from echoai.echo4.maintain_agent import MaintenanceAgent
from echoai.echo4.maintain_world import MaintenanceEnv
from echoai.echo4.self_agent import SelfAgent
from echoai.echo4.world import Body, DockRules, transition
from echoai.nexus0.constants import R_SUCCESS, R_THREAT


def advance(env, actions):
    for action in actions:
        env.advance(action)
    return env


class MaintenancePhysics(unittest.TestCase):
    def test_nominal_single_actions_reuse_world1(self):
        for action in range(3):
            env = MaintenanceEnv(Body(64, 64))
            self.assertEqual(env.advance(action), transition(Body(64, 64), action, DockRules()))

    def test_clogged_and_seized_have_same_initial_response(self):
        clogged = advance(MaintenanceEnv(Body(64, 96), fault="clogged"), (1, 1))
        seized = advance(MaintenanceEnv(Body(64, 96), fault="seized"), (1, 1))
        self.assertEqual(clogged.body, seized.body)
        self.assertEqual(clogged.body, Body(58, 88))
        self.assertEqual(clogged.services_paid, 0)

    def test_repair_is_costed_and_takes_three_actual_ticks(self):
        env = advance(MaintenanceEnv(Body(64, 96), fault="clogged"), (1, 1, 1))
        self.assertEqual(env.body, Body(49, 84))
        self.assertEqual(env.resource_used, 15)
        self.assertEqual(env.service_resource_used, 6)
        self.assertEqual((env.total_steps, env.life_steps, env.resets), (3, 3, 0))
        self.assertEqual((env.repairs, env.services_paid), (1, 1))
        self.assertEqual(env.audit_state()["spares"], 0)
        self.assertTrue(env.balanced and env.spares_balanced)

    def test_capacity_recovers_only_on_the_next_action(self):
        env = advance(MaintenanceEnv(Body(64, 96), fault="clogged"), (1, 1, 1))
        self.assertEqual(env.last_transition.before.temperature - env.body.temperature, 4)
        env.advance(1)
        self.assertEqual(env.last_transition.before.temperature - env.body.temperature, 16)

    def test_irreparable_failure_spends_without_repair(self):
        env = advance(MaintenanceEnv(Body(64, 96), fault="seized"), (1, 1, 1, 1))
        self.assertEqual(env.body, Body(46, 80))
        self.assertEqual(env.audit_state()["fault"], "seized")
        self.assertEqual((env.repairs, env.services_paid, env.resource_used), (0, 1, 18))

    def test_unnecessary_service_is_not_free(self):
        env = advance(MaintenanceEnv(Body(64, 96)), (1, 1, 1))
        self.assertEqual(env.last_service.service, "unnecessary")
        self.assertEqual((env.repairs, env.services_paid, env.resource_used), (0, 1, 15))

    def test_no_spare_keeps_degraded_capacity(self):
        env = advance(MaintenanceEnv(Body(64, 96), fault="clogged", spares=0), (1, 1, 1))
        self.assertEqual(env.last_service.service, "no_spare")
        self.assertEqual(env.body, Body(55, 84))
        self.assertEqual((env.repairs, env.service_resource_used), (0, 0))

    def test_insufficient_energy_does_not_spend_spare_or_resurrect(self):
        for initial_h in (10, 15):
            env = advance(MaintenanceEnv(Body(initial_h, 96), fault="clogged"), (1, 1, 1))
            self.assertEqual(env.last_service.service, "insufficient_energy")
            self.assertEqual(env.body.h, initial_h - 9)
            self.assertEqual(env.audit_state()["spares"], 1)
            self.assertEqual(env.repairs, 0)

    def test_exact_affordability_boundary(self):
        env = advance(MaintenanceEnv(Body(16, 96), fault="clogged"), (1, 1, 1))
        self.assertEqual(env.body, Body(1, 84))
        self.assertEqual(env.last_service.service, "repaired")

    def test_wait_and_charge_interrupt_service(self):
        for action in (0, 2):
            env = advance(MaintenanceEnv(Body(64, 64), fault="clogged"), (1, 1, action, 1))
            self.assertEqual(env.audit_state()["progress"], 1)
            self.assertEqual(env.service_attempts, 0)

    def test_consumable_exhaustion_is_permanent(self):
        env = advance(MaintenanceEnv(Body(64, 96), fault="seized", spares=1), (1,) * 6)
        self.assertEqual(env.last_service.service, "no_spare")
        self.assertEqual((env.service_attempts, env.services_paid, env.repairs), (2, 1, 0))
        self.assertEqual(env.resource_used, 24)
        self.assertTrue(env.spares_balanced)

    def test_external_heat_survives_service(self):
        env = advance(MaintenanceEnv(Body(64, 80), fault="clogged", external_heat=4), (1, 1, 1))
        self.assertEqual(env.body, Body(49, 80))
        env.advance(1)
        self.assertEqual(env.body, Body(46, 68))  # -16 + external 4, not -16
        self.assertEqual(env.audit_state()["external_heat"], 4)

    def test_external_heat_does_not_revive_native_cold_terminal(self):
        env = MaintenanceEnv(Body(64, 4), external_heat=4)
        env.advance(1)
        self.assertEqual(env.body, Body(61, 0))
        self.assertFalse(env.body.alive)

    def test_no_service_on_terminal_completion(self):
        env = advance(MaintenanceEnv(Body(9, 96), fault="clogged"), (1, 1, 1))
        self.assertEqual(env.last_service.service, "terminal")
        self.assertEqual((env.body.h, env.services_paid, env.repairs), (0, 0, 0))
        self.assertEqual(env.audit_state()["spares"], 1)

    def test_terminal_actions_do_not_mutate_any_counter(self):
        env = advance(MaintenanceEnv(Body(1, 64)), (2,))
        before = copy.deepcopy(vars(env))
        with self.assertRaises(RuntimeError):
            env.advance(0)
        self.assertEqual(vars(env), before)

    def test_reset_always_rejected_without_changes(self):
        env = advance(MaintenanceEnv(Body(64, 96)), (1,))
        before = copy.deepcopy(vars(env))
        with self.assertRaises(RuntimeError):
            env.reset()
        self.assertEqual(vars(env), before)

    def test_bad_actions_never_mutate_world(self):
        env = MaintenanceEnv()
        before = copy.deepcopy(vars(env))
        for action in (-1, 3, True, False, 1.0, "1", None):
            with self.subTest(action=action), self.assertRaises(ValueError):
                env.advance(action)
            self.assertEqual(vars(env), before)

    def test_bad_constructor_parameters(self):
        for params in ({"fault": "unknown"}, {"fault": 1}, {"spares": -1}, {"spares": 4},
                       {"spares": True}, {"external_heat": -1}, {"external_heat": 5},
                       {"external_heat": 0.0}, {"initial": Body(0, 64)}):
            with self.subTest(params=params), self.assertRaises(ValueError):
                MaintenanceEnv(**params)

    def test_work_has_normal_wait_cost_and_only_task_reward(self):
        env = MaintenanceEnv(Body(64, 64))
        reward, _, h, theta = env.step_homeostatic(2, 64, 64)
        self.assertEqual((reward, h, theta, env.work_done), (R_SUCCESS, 63, 68, 1))
        self.assertEqual(env.resource_used, 1)

    def test_work_window_boundaries_and_no_work_bonus_for_cooling(self):
        for before, expected in ((43, 0), (44, 1), (76, 1), (77, 0)):
            env = advance(MaintenanceEnv(Body(64, before)), (2,))
            self.assertEqual(env.work_done, expected)
        env = MaintenanceEnv(Body(64, 80))
        self.assertEqual(env.step_homeostatic(1, 64, 80)[0], 0)
        self.assertEqual(env.work_done, 0)

    def test_death_cannot_collect_work_reward(self):
        env = MaintenanceEnv(Body(1, 64))
        self.assertEqual(env.step_homeostatic(2, 1, 64)[0], R_THREAT)
        self.assertEqual(env.work_done, 0)

    def test_register_mismatch_rejected_before_physics(self):
        env = MaintenanceEnv()
        before = copy.deepcopy(vars(env))
        with self.assertRaises(ValueError):
            env.step_homeostatic(2, 99, 99)
        self.assertEqual(vars(env), before)

    def test_boundary_grid_conserves_resources(self):
        count = 0
        for h in (1, 3, 9, 10, 15, 16, 64, 126, 127):
            for theta in (1, 4, 16, 48, 64, 80, 96, 126):
                for fault in ("healthy", "clogged", "seized"):
                    for heat in (0, 4):
                        for action in range(3):
                            env = MaintenanceEnv(Body(h, theta), fault=fault, external_heat=heat)
                            for _ in range(3):
                                if not env.body.alive:
                                    break
                                result = env.advance(action)
                                self.assertTrue(result.balanced and env.balanced and env.spares_balanced)
                                count += 1
        self.assertGreater(count, 2000)


class MaintenanceWiring(unittest.TestCase):
    def test_original_policy_and_single_shared_memory(self):
        agent = MaintenanceAgent(MaintenanceEnv(Body(64, 96), fault="clogged"))
        self.assertIs(MaintenanceAgent._propose, SelfAgent._propose)
        self.assertIs(agent.sensation.cam, agent.cam)
        self.assertIs(agent.sensation.world, agent.t)
        self.assertIs(agent.boundary.cam, agent.cam)
        self.assertEqual(agent.n_actions, 3)
        self.assertFalse(agent.cortex_enabled)
        agent.turn(0)
        self.assertEqual(agent.cam.destroyed, 0)
        self.assertEqual(agent.metrics.cortex_calls, 0)

    def test_private_fault_spares_and_heat_not_in_initial_observation(self):
        packets = set()
        for fault in ("healthy", "clogged", "seized"):
            for spares in range(4):
                env = MaintenanceEnv(Body(64, 80), fault=fault, spares=spares, external_heat=spares)
                agent = MaintenanceAgent(env)
                packets.add(agent.observation(env.cell()))
        self.assertEqual(len(packets), 1)
        self.assertEqual(len(packets.pop()), 16)

    def test_no_causal_diagnosis_is_smuggled_into_self_hook(self):
        agent = MaintenanceAgent(MaintenanceEnv(fault="seized"))
        self.assertIsNone(agent.self_model)
        with patch.object(agent.env, "audit_state", side_effect=AssertionError("private truth read")):
            agent.turn(0)

    def test_native_q_receives_real_work_reward(self):
        agent = bench._ScriptedWitness(MaintenanceEnv(Body(64, 64)), (2,))
        agent.turn(0)
        self.assertEqual(agent.last_reward, 16)
        self.assertGreater(agent.metrics.deltas, 0)
        self.assertEqual(agent.env.work_done, 1)

    def test_vetoed_third_cooling_is_wait_not_service(self):
        row = bench.trial(veto_at=3)
        frame = row["frames"][2]
        self.assertEqual((frame["proposed"], frame["applied"], frame["gate"]), (1, 2, 2))
        self.assertEqual(frame["service"]["progress_after"], 0)
        self.assertEqual(row["ledger"]["services_paid"], 0)
        self.assertTrue(row["invariants"])

    def test_operator_stop_is_latched_before_memory_mutation(self):
        agent = bench._ScriptedWitness(MaintenanceEnv(Body(64, 96), fault="clogged"), (1, 1, 1))
        agent.turn(0)
        agent.turn(1)
        agent.operator_stop()
        before = copy.deepcopy((vars(agent.cam), vars(agent.q), vars(agent.t),
                                agent.sensation.model_state(), agent.sensation.history.snapshot(),
                                agent.env.audit_state(), agent.H, agent.temperature))
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                agent.turn(2)
        self.assertEqual((vars(agent.cam), vars(agent.q), vars(agent.t),
                          agent.sensation.model_state(), agent.sensation.history.snapshot(),
                          agent.env.audit_state(), agent.H, agent.temperature), before)
        self.assertEqual(agent.env.audit_state()["progress"], 0)
        self.assertEqual(agent.env.total_steps, 2)

    def test_stop_does_not_change_physiology_or_spares(self):
        env = advance(MaintenanceEnv(Body(64, 96), fault="clogged"), (1,))
        before = (env.body, env._spares, env.resource_used, env.total_steps)
        env.stop()
        with self.assertRaises(RuntimeError):
            env.advance(1)
        self.assertEqual((env.body, env._spares, env.resource_used, env.total_steps), before)

    def test_respawn_does_not_change_agent_or_environment(self):
        agent = bench._ScriptedWitness(MaintenanceEnv(Body(1, 64)), (2,))
        agent.turn(0)
        self.assertTrue(agent.episode_terminal)
        before = (agent.H, agent.temperature, agent.life_turns, agent.life_id, agent.env.audit_state())
        with self.assertRaises(RuntimeError):
            agent.respawn()
        self.assertEqual((agent.H, agent.temperature, agent.life_turns, agent.life_id, agent.env.audit_state()), before)
        with self.assertRaises(RuntimeError):
            agent.turn(1)

    def test_reject_already_used_stopped_or_wrong_environment(self):
        env = advance(MaintenanceEnv(), (2,))
        stopped = MaintenanceEnv()
        stopped.stop()
        for wrong in (None, {}, env, stopped):
            with self.subTest(wrong=wrong), self.assertRaises(ValueError):
                MaintenanceAgent(wrong)

    def test_nominal_checkpoint_profile_cannot_drop_maintenance_state(self):
        from echoai.echo4.continuity import ContinuityRun
        agent = MaintenanceAgent(MaintenanceEnv(fault="clogged"))
        with self.assertRaises(ValueError):
            ContinuityRun(agent)

    def test_inherited_thought_log_is_disabled(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "not-written.jsonl"
            with patch.dict(os.environ, {"NAVI_THOUGHT_LOG": str(path)}):
                agent = MaintenanceAgent(MaintenanceEnv())
                agent.turn(0)
            self.assertFalse(path.exists())

    def test_fast_extensions_do_not_introduce_float_constants(self):
        for path in (bench.ROOT / "echo4/maintain_world.py", bench.ROOT / "echo4/maintain_agent.py"):
            tree = ast.parse(path.read_text())
            self.assertFalse(any(isinstance(n, ast.Constant) and type(n.value) is float for n in ast.walk(tree)))


class MaintenanceAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = bench.evaluate()

    def test_preregistered_grid_complete_without_case_filtering(self):
        self.assertEqual(len(self.result["rows"]), 216)
        self.assertTrue(self.result["mechanism_checks_passed"])
        self.assertEqual(set(self.result["summary"]), set(bench.SCRIPTS))
        self.assertTrue(all(r["invariants"] for r in self.result["rows"]))

    def test_blind_scripts_can_harm_and_fail_to_work(self):
        rows = self.result["rows"]
        self.assertTrue(any(r["terminal"] for r in rows))
        self.assertTrue(any(r["ledger"]["services_paid"] and not r["ledger"]["repairs"] for r in rows))
        self.assertTrue(any(not r["ledger"]["work_done"] for r in rows))

    def test_native_baseline_is_not_relabelled_as_learned_repair(self):
        native = self.result["witnesses"]["native_q_baseline"]
        self.assertIsNone(native["script"])
        self.assertTrue(native["invariants"])
        self.assertFalse(self.result["maintain1_green"])

    def test_known_witness_recovers_capacity_and_does_work(self):
        row = self.result["witnesses"]["service"]
        self.assertEqual(row["final"], {"h": 45, "temperature": 72})
        self.assertEqual(row["ledger"]["work_done"], 1)
        self.assertEqual(row["frames"][2]["service"]["service"], "repaired")
        self.assertEqual(row["frames"][3]["transition"]["before"]["temperature"] - row["frames"][3]["transition"]["after"]["temperature"], 16)

    def test_missing_report_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = bench.verify(Path(directory))
        self.assertFalse(audit["valid"])
        self.assertFalse(audit["maintain1_green"])

    def test_full_source_locked_build_and_fresh_process_reconstruction(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            result = bench.build(path)
            completed = subprocess.run(
                [sys.executable, "-m", "echoai.echo4.maintain_bench", "verify", str(path)],
                cwd=bench.ROOT.parent, text=True, capture_output=True, timeout=120, check=True)
            audit = json.loads(completed.stdout)
            self.assertTrue(audit["valid"])
            self.assertEqual(audit["reproduction_sha256"], result["reproduction_sha256"])
            self.assertFalse(audit["maintain1_green"])
            with self.assertRaises(FileExistsError):
                bench.build(path)

    def test_tampering_rejected_even_with_recomputed_self_digest(self):
        # Short synthetic serialization fixture, not scientific campaign evidence.
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(bench, "sources", return_value={"fixture": "source"}), \
                patch.object(bench, "parent_binding", return_value={"fixture": "parent"}), \
                patch.object(bench, "evaluate", return_value=copy.deepcopy(self.result)):
            path = Path(directory)
            original = bench.build(path)
            for key, value in (("maintain1_green", True), ("mechanism_checks_passed", False),
                               ("sources", {}), ("summary", {}), ("rows", [])):
                changed = copy.deepcopy(original)
                changed[key] = value
                changed.pop("reproduction_sha256")
                changed["reproduction_sha256"] = bench.sha(bench.canonical(changed))
                (path / "report.json").write_bytes(bench.canonical(changed))
                self.assertFalse(bench.verify(path)["valid"], key)
            changed = copy.deepcopy(original)
            changed["rows"][0]["frames"][0]["transition"]["resource_used"] = 0
            changed.pop("reproduction_sha256")
            changed["reproduction_sha256"] = bench.sha(bench.canonical(changed))
            (path / "report.json").write_bytes(bench.canonical(changed))
            self.assertFalse(bench.verify(path)["valid"])

    def test_duplicate_keys_and_floats_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for raw in (b'{"schema":1,"schema":2}', b'{"schema":1.5}'):
                (path / "report.json").write_bytes(raw)
                self.assertFalse(bench.verify(path)["valid"])


if __name__ == "__main__":
    unittest.main()
