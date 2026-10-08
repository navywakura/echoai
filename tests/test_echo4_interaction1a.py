"""INTERACTION-A physics, real native execution and fail-closed scope."""
import ast
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.nexus0.loop import Agent
from echoai.echo4 import interaction_bench as b
from echoai.echo4.interaction_world import InteractionWorld
from echoai.echo4.interaction_session import InteractionSession
from echoai.echo4.other_model import decode
from echoai.echo4.other_replay import digest, replay, transcript


class Physics(unittest.TestCase):
    def test_census_243_transitions_and_exchange_symmetry(self):
        result = b.census()
        self.assertEqual(len(result["rows"]), 243)
        self.assertTrue(result["passed"])

    def test_joint_action_can_help_cost_more_or_produce_nothing(self):
        for cue, net in enumerate(((7, 7), (1, 1), (-3, -3))):
            result = InteractionWorld((cue,)).advance((0, 0))
            self.assertEqual(result["net"], net)
            self.assertTrue(result["joint_executed"])
            solo = InteractionWorld((cue,)).advance((1, 1))
            self.assertEqual(solo["net"], (4, 4))

    def test_unilateral_join_pays_without_phantom_partner(self):
        result = InteractionWorld((0,)).advance((0, 1))
        self.assertEqual((result["paid"], result["output"], result["net"]), ((3, 1), (0, 5), (-3, 4)))
        self.assertFalse(result["joint_executed"])

    def test_wait_is_not_agreement(self):
        result = InteractionWorld((0,)).advance((0, 2))
        self.assertEqual(result["net"], (-3, 0))
        self.assertFalse(result["joint_executed"])

    def test_insufficient_resource_never_becomes_partial_contribution(self):
        result = InteractionWorld((0,), (2, 8)).advance((0, 0))
        self.assertEqual(result["paid"], (0, 3))
        self.assertEqual(result["after"], (2, 5))
        self.assertEqual(result["incapable"], (True, False))
        self.assertEqual(result["output"], (0, 0))

    def test_exact_resource_and_exhaustion(self):
        world = InteractionWorld((0, 0), (3, 3))
        self.assertEqual(world.advance((0, 0))["net"], (7, 7))
        last = world.advance((0, 0))
        self.assertEqual(last["net"], (0, 0))
        self.assertEqual(world.resources, (0, 0))
        self.assertEqual(world.spent, (3, 3))
        self.assertEqual(world.output, (10, 10))
        with self.assertRaises(RuntimeError):
            world.advance((2, 2))

    def test_wait_consumes_time_even_without_resources(self):
        world = InteractionWorld((0,), (0, 0))
        world.advance((2, 2))
        self.assertEqual(world.tick, 1)
        self.assertEqual(world.spent, (0, 0))
        self.assertTrue(world.done)

    def test_invalid_construction_rejects_not_coerces(self):
        for cues in ((), [0], (False,), (1.0,), (3,), (0,)*513):
            with self.subTest(cues=str(cues)[:20]), self.assertRaises(ValueError):
                InteractionWorld(cues)
        for resources in ((True, 1), (1.0, 1), (-1, 1), (8193, 1), [1, 1]):
            with self.assertRaises(ValueError):
                InteractionWorld((0,), resources)

    def test_bad_actions_leave_world_unchanged(self):
        world = InteractionWorld((0,))
        before = copy.deepcopy(vars(world))
        for actions in ((True, 0), (0, 1.0), (0, -1), (3, 0), [0, 0], (0,)):
            with self.assertRaises(ValueError):
                world.advance(actions)
            self.assertEqual(vars(world), before)

    def test_stop_is_latched(self):
        world = InteractionWorld((0, 1))
        world.advance((1, 1))
        world.stop()
        before = copy.deepcopy(vars(world))
        with self.assertRaises(RuntimeError):
            world.advance((0, 0))
        self.assertEqual(vars(world), before)

    def test_maximum_512_rounds_is_enforced(self):
        world = InteractionWorld((0,)*512)
        for _ in range(512):
            world.advance((2, 2))
        with self.assertRaises(RuntimeError):
            world.advance((2, 2))


class NativeWiring(unittest.TestCase):
    def make(self, cues=(0, 1, 2)*12, **kwargs):
        return InteractionSession(cues, **kwargs)

    def test_two_original_agents_q_zero_then_learning(self):
        run = self.make()
        for a in run.agents:
            self.assertIs(type(a), Agent)
            self.assertTrue(all(not any(row) for row in a.q.q))
        for _ in range(24):
            run.step()
        self.assertTrue(run.invariant())
        self.assertTrue(all(a.metrics.deltas > 0 for a in run.agents))

    def test_no_shared_memories(self):
        run = self.make()
        a, other = run.agents
        for key in ("cam", "q", "t", "env"):
            self.assertIsNot(getattr(a, key), getattr(other, key))
        before = digest(run.models[0])
        other.q.q[0][0] = -127
        self.assertEqual(digest(run.models[0]), before)
        self.assertIs(run.models[0].world, a.t)

    def test_joint_physics_once_q_updates_once_and_only_after_both_actions(self):
        run = self.make()
        originals = [a.q.update for a in run.agents]
        calls = [0, 0]
        def update(i):
            def observed(*args, **kwargs):
                self.assertEqual(run.world.tick, 1)
                self.assertNotIn(None, run._pending)
                self.assertEqual(args[2], run.world.last["net"][i])
                calls[i] += 1
                return originals[i](*args, **kwargs)
            return observed
        with patch.object(run.world, "advance", wraps=run.world.advance) as advance, \
                patch.object(run.agents[0].q, "update", side_effect=update(0)), \
                patch.object(run.agents[1].q, "update", side_effect=update(1)):
            run.step()
        self.assertEqual(calls, [1, 1])
        advance.assert_called_once()

    def test_other_agent_observes_old_cue_before_atomic_advance(self):
        run = self.make((0, 1))
        original = run.agents[1]._propose
        def check(*args, **kwargs):
            self.assertEqual(run.world.tick, 0)
            self.assertIsNone(run.world.last)
            self.assertEqual(run.agents[1].env.cell().index, 0)
            return original(*args, **kwargs)
        with patch.object(run.agents[1], "_propose", side_effect=check):
            run.step()
        self.assertEqual(run.agents[0].env.cell().index, 1)

    def test_reverse_execution_order_preserves_full_trace(self):
        a, b_run = self.make(), self.make()
        for tick in range(36):
            self.assertEqual(a.step(greedy=tick >= 24), b_run.step(order=(1, 0), greedy=tick >= 24))
        self.assertTrue(a.invariant() and b_run.invariant())

    def test_veto_blocks_join_and_no_joint_reward_is_invented(self):
        run = self.make((0,)*4)
        run.step()
        run.inhibit(1)
        row = run.step(greedy=True)
        self.assertEqual(row["proposals"], (0, 0))
        self.assertEqual(row["actions"], (0, 2))
        self.assertEqual(row["gates"][1], 2)
        self.assertEqual(row["net"], (-3, 0))
        self.assertEqual(decode(bytes.fromhex(row["outcomes"][0][1]), action=True)[2], 2)
        self.assertTrue(run.invariant())

    def test_veto_requires_known_origin(self):
        run = self.make()
        with self.assertRaises(ValueError):
            run.inhibit(0)

    def test_ports_cannot_advance_outside_joint_transaction(self):
        run = self.make()
        with self.assertRaises(RuntimeError):
            run.agents[0].env.step(0)
        self.assertEqual(run.world.tick, 0)

    def test_duplicate_commit_cannot_spend_twice(self):
        run = self.make()
        def duplicate(*args, **kwargs):
            run.agents[0].env.step(0)
            return 0
        with patch.object(run.agents[1], "_propose", side_effect=duplicate):
            with self.assertRaises(RuntimeError):
                run.step()
        self.assertEqual(run.world.spent, (0, 0))
        self.assertTrue(run.failed)

    def test_invalid_step_options_do_not_move_or_poison_session(self):
        run = self.make()
        for kwargs in ({"order": (False, True)}, {"order": (1, 1)}, {"order": [0, 1]},
                       {"greedy": 1}, {"visible": (0, True)}, {"outcomes": [True, True]}):
            with self.assertRaises(ValueError):
                run.step(**kwargs)
            self.assertEqual(run.world.tick, 0)
            self.assertFalse(run.failed)
            self.assertTrue(all(m.pending is None for m in run.models))
        run.step()

    def test_partial_failure_blocks_retry_without_claiming_rollback(self):
        run = self.make()
        with patch.object(run.agents[1], "turn", side_effect=RuntimeError("failed peer")):
            with self.assertRaises(RuntimeError):
                run.step()
        self.assertTrue(run.failed and run.stopped and run.world.stopped)
        self.assertEqual(run.world.tick, 0)
        with self.assertRaises(RuntimeError):
            run.step()
        with self.assertRaises(RuntimeError):
            run.agents[0].env.step(0)

    def test_stop_between_commits_cannot_award_reward(self):
        run = self.make()
        original = run.agents[1]._propose
        def halted(*args, **kwargs):
            run.stop()
            return original(*args, **kwargs)
        with patch.object(run.agents[1], "_propose", side_effect=halted):
            with self.assertRaises(RuntimeError):
                run.step()
        self.assertEqual(run.world.output, (0, 0))
        self.assertEqual(run.world.tick, 0)

    def test_operator_stop_preserves_memories_and_cannot_resume(self):
        run = self.make()
        run.step()
        used = tuple(a.cam.used for a in run.agents)
        run.stop()
        with self.assertRaises(RuntimeError):
            run.step()
        self.assertEqual(tuple(a.cam.used for a in run.agents), used)
        self.assertTrue(all(m.stopped for m in run.models))

    def test_missing_outcome_is_not_observed_wait(self):
        run = self.make((0,)*5)
        row = run.step(outcomes=(False, False))
        self.assertTrue(all(p[1] is None for p in row["outcomes"]))
        for model in run.models:
            public = [s for s in model.cam.slot if s.occupied and s.source == "other1-sensor"]
            self.assertFalse(any(s.wsp[0] == 3 and s.wsp[13] == 1 for s in public))

    def test_hidden_peer_cue_abstains(self):
        run = self.make((0,)*12)
        for _ in range(8):
            run.step(greedy=True)
        self.assertEqual(run.step(visible=(False, False))["predictions"], (None, None))

    def test_passive_observer_modes_cannot_change_actions(self):
        a, other = self.make(), self.make(observer_mode="no_history")
        for _ in range(36):
            left, right = a.step(), other.step()
            self.assertEqual(left["actions"], right["actions"])
            self.assertEqual(left["net"], right["net"])

    def test_public_replay_does_not_execute_physics(self):
        run = self.make()
        rows = [run.step() for _ in range(36)]
        with patch.object(InteractionWorld, "advance", side_effect=AssertionError("physics executed")):
            for i in range(2):
                reconstructed = replay(transcript(rows, i), "identity")
                self.assertEqual(reconstructed["memory_sha256"], digest(run.models[i]))
                self.assertEqual(reconstructed["predictions"], [r["predictions"][i] for r in rows])


class Protocol(unittest.TestCase):
    def test_witnesses_are_labeled_scripts_and_include_losses(self):
        result = b.witnesses()
        self.assertEqual(len(result["rows"]), 9)
        self.assertTrue(result["passed"])
        self.assertEqual(result["rows"][6]["summary"]["net"], (-36, -36))

    def test_native_development_reports_control_costs_without_asserting_gain(self):
        row = b.native(17)
        self.assertTrue(row["passed"])
        self.assertEqual(row["scripted_controls"]["solo"]["net"], (576, 576))
        self.assertEqual(row["scripted_controls"]["wait"]["paid"], (0, 0))
        self.assertEqual(row["summary"]["rounds"], 144)

    def test_inherited_99_sources_and_five_additions(self):
        self.assertTrue(b.parent())
        self.assertEqual(len(b.sources()), 104)

    def test_runtime_has_no_float_or_llm_calls(self):
        for path in ("interaction_world.py", "interaction_session.py"):
            tree = ast.parse((b.ROOT/"echo4"/path).read_text())
            self.assertFalse(any(isinstance(n, ast.Constant) and isinstance(n.value, float) for n in ast.walk(tree)))
            names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            self.assertFalse(names & {"eval", "exec", "requests", "subprocess"})

    def test_missing_or_forged_evidence_never_issues_green(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.assertFalse(b.verify(path)["valid"])
            b.persist(path, "report.json", {"reproduction_sha256": "fake", "sources": {}, "interaction1_green": True}, False)
            result = b.verify(path)
            self.assertFalse(result["valid"])
            self.assertFalse(result["interaction1_green"])

    def test_campaign_lock_precedes_native_runs_and_valid_a_is_not_green(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            def native(seed):
                self.assertTrue((path/"lock.json").exists())
                return {"seed": seed, "summary": {}, "first_half": {}, "last_half": {},
                        "remaining_resources": (0, 0), "scripted_controls": {}, "checks": {}, "passed": True}
            with patch.object(b, "sources", return_value={}), patch.object(b, "parent", return_value={}), \
                    patch.object(b, "native", side_effect=native):
                result = b.campaign(path)
            self.assertTrue(result["phase_a_valid"])
            self.assertFalse(result["interaction1_green"])
            self.assertFalse(result["autonomous_interaction_gain_tested"])

    def test_reconstruction_checks_actual_artifact_bytes_and_keeps_phase_open(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            report = b.campaign(path)
            receipt = b.verify(path)
            self.assertTrue(receipt["valid"] and receipt["phase_a_valid"])
            self.assertEqual(receipt["reproduction_sha256"], report["reproduction_sha256"])
            self.assertFalse(receipt["interaction1_green"])
            with (path/"census.json").open("ab") as handle:
                handle.write(b" ")
            rejected = b.verify(path)
            self.assertFalse(rejected["valid"])
            self.assertFalse(rejected["phase_a_valid"])
            self.assertFalse(rejected["interaction1_green"])


if __name__ == "__main__":
    unittest.main()
