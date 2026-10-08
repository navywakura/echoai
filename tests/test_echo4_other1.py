"""OTHER-1: public interfaces and real native agents, only development seeds."""
import ast
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.core.cam import Cam
from echoai.nexus0.world import World
from echoai.nexus0.loop import Agent
from echoai.echo4 import other_bench as b
from echoai.echo4.other_model import OtherModel, context, outcome, decode, MODES, LIMIT
from echoai.echo4.other_world import ChoiceEnv, Encounter, new_agent, PRIVATE_STEPS
from echoai.echo4.other_replay import digest, replay, transcript


class PublicPackets(unittest.TestCase):
    def test_all_packets_are_canonical_16_bytes(self):
        for subject in range(3):
            for cue in (None, 0, 1, 2):
                raw = context(subject, cue)
                self.assertEqual(len(raw), 16)
                self.assertEqual(decode(raw), (subject, cue, None))
                self.assertEqual(raw[4:10], bytes(6))
                for action in range(3):
                    raw = outcome(subject, cue, action)
                    self.assertEqual(len(raw), 16)
                    self.assertEqual(decode(raw, action=True), (subject, cue, action))

    def test_invalid_fields_never_wrap_or_coerce(self):
        for value in (True, False, 1.0, -1, 3, 256, "1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                context(value, 0)
            with self.subTest(value=value), self.assertRaises(ValueError):
                context(1, value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                outcome(1, 0, value)

    def test_every_changed_packet_byte_fails_canonical_validation(self):
        for raw, action in ((context(1, 0), False), (outcome(1, 0, 0), True)):
            for index in range(16):
                modified = bytearray(raw)
                modified[index] = 254
                with self.subTest(index=index), self.assertRaises(ValueError):
                    decode(bytes(modified), action=action)

    def test_own_other_and_new_identity_do_not_alias(self):
        self.assertEqual(len({context(s, c) for s in range(3) for c in range(3)}), 9)
        self.assertNotEqual(context(1, None), context(1, 0))
        self.assertNotEqual(context(1, 2), outcome(1, 2, 2))


class ObservableModel(unittest.TestCase):
    def model(self, mode="identity"):
        return OtherModel(Cam(), World(), mode=mode)

    def feed(self, model, tick, peer=1, cue=1, action=1):
        forecasts = model.begin(tick, (context(0, 0), context(peer, cue)))
        pred = model.finish(tick, 0, (outcome(0, 0, 0), outcome(peer, cue, action)))
        self.assertEqual(pred, forecasts[1][0])
        return pred

    def test_unknown_until_enough_executions_and_same_original_memory(self):
        model = self.model()
        cam, world = model.cam, model.world
        self.assertEqual([self.feed(model, t) for t in range(4)], [None, None, None, 1])
        self.assertIs(model.cam, cam)
        self.assertIs(model.world, world)
        origin = cam.get(context(1, 1))
        target = world.predict(origin, 0)
        self.assertEqual(cam.slot[target].wsp, outcome(1, 1, 1))
        self.assertEqual(world.n[origin][0], 4)

    def test_prediction_is_committed_before_learning_and_does_not_write_fact(self):
        model = b.witness_model()
        before = model.cam.used
        forecasts = model.begin(4, (context(0, 0), context(1, 1)))
        self.assertEqual(model.cam.used, before)
        predicted = model.finish(4, 0, (outcome(0, 0, 0), outcome(1, 1, 2)))
        self.assertEqual(predicted, 1)  # Wrong but honestly committed beforehand.
        self.assertEqual(forecasts[1][0], 1)
        self.assertTrue(all(s.extract == "observed_wsp="+s.wsp.hex()
                            for s in model.cam.slot if s.occupied and s.has_fact))

    def test_conflict_stops_asserting_without_deleting_old_evidence(self):
        model = b.witness_model()
        self.feed(model, 4, action=2)
        old = model.cam.get(outcome(1, 1, 1))
        self.assertIsNone(self.feed(model, 5, action=2))
        self.assertTrue(model.cam.slot[old].occupied)
        self.assertEqual(model.cam.destroyed, 0)

    def test_unseen_identity_is_not_inferred_from_another_person(self):
        model = b.witness_model()
        self.assertIsNone(self.feed(model, 4, peer=2))
        self.assertGreaterEqual(model.cam.get(context(1, 1)), 0)

    def test_hidden_context_is_unknown_and_not_used_as_private_label(self):
        model = b.witness_model()
        self.assertIsNone(self.feed(model, 4, cue=None))
        slot = model.cam.get(context(1, None))
        self.assertFalse(any(model.world.n[slot]))

    def test_missing_action_is_not_a_wait_or_negative_observation(self):
        model = b.witness_model()
        slot = model.cam.get(context(1, 1))
        before = copy.deepcopy((model.world.pred[slot], model.world.n[slot], model.world.alt_n[slot]))
        model.begin(4, (context(0, 0), context(1, 1)))
        model.finish(4, 0, (outcome(0, 0, 0), None))
        self.assertEqual((model.world.pred[slot], model.world.n[slot], model.world.alt_n[slot]), before)
        self.assertEqual(model.cam.get(outcome(1, 1, 2)), -1)

    def test_untracked_peer_does_not_get_a_default_identity(self):
        model = self.model()
        forecast = model.begin(0, (context(0, 0), None))
        self.assertEqual(forecast[1], (None, None, None))
        model.finish(0, 0, (outcome(0, 0, 0), None))
        self.assertEqual(model.cam.get(context(1, 0)), -1)

    def test_malformed_stale_and_mismatched_receipts_are_transactional(self):
        model = b.witness_model()
        model.begin(4, (context(0, 0), context(1, 1)))
        before = digest(model)
        bad = ((5, 0, (outcome(0, 0, 0), outcome(1, 1, 1))),
               (4, 0, (outcome(0, 0, 0), outcome(2, 1, 1))),
               (4, 0, (outcome(0, 0, 0), outcome(1, 2, 1))),
               (4, 1, (outcome(0, 0, 0), outcome(1, 1, 1))),
               (4, 0, (None, None)), (4, 0, (outcome(0, 0, 0), b"x")))
        for args in bad:
            with self.subTest(args=args), self.assertRaises(ValueError):
                model.finish(*args)
            self.assertEqual(digest(model), before)

    def test_duplicate_tick_and_pending_capture_rejected(self):
        model = b.witness_model()
        with self.assertRaises(ValueError):
            model.begin(3, (context(0, 0), context(1, 1)))
        model.begin(4, (context(0, 0), context(1, 1)))
        with self.assertRaises(ValueError):
            model.begin(5, (context(0, 0), context(1, 1)))

    def test_source_order_and_bad_mode_rejected(self):
        with self.assertRaises(ValueError):
            self.model("oracle")
        model = self.model()
        for views in ((None, context(1, 1)), (context(1, 0), context(0, 1)), [context(0, 0), context(1, 1)]):
            with self.assertRaises(ValueError):
                model.begin(0, views)
        self.assertEqual(model.cam.used, 0)

    def test_all_ablations_are_explicit(self):
        # Self-copy has never observed its own response to peer cue 1.
        for mode, expected in (("identity", 1), ("self_copy", None), ("no_history", None), ("pooled", 1)):
            model = self.model(mode)
            values = [self.feed(model, tick) for tick in range(4)]
            self.assertEqual(values[-1], expected)

    def test_ablations_with_same_observed_cue_but_different_behavior(self):
        for mode, expected in (("identity", 1), ("self_copy", 0), ("no_history", None), ("pooled", None)):
            model = self.model(mode)
            values = [self.feed(model, tick, cue=0) for tick in range(4)]
            self.assertEqual(values[-1], expected)

    def test_pooled_derived_contexts_never_become_facts(self):
        model = self.model("pooled")
        for tick in range(4):
            self.feed(model, tick)
        derived = [s for s in model.cam.slot if s.occupied and s.source == "other1-derived-index"]
        self.assertTrue(derived)
        self.assertTrue(all(not s.has_fact and not s.extract for s in derived))

    def test_cannot_predict_an_unrelated_t_destination(self):
        model = b.witness_model()
        slot = model.cam.get(context(1, 1))
        model.world.pred[slot][0] = model.cam.get(outcome(0, 0, 0))
        self.assertIsNone(model.begin(4, (context(0, 0), context(1, 1)))[1][0])

    def test_full_cam_drops_instead_of_aliasing_slot_zero(self):
        model = self.model()
        # Native allocator's documented capacity guard, no deletion fallback.
        model.cam.used = 4096
        before = copy.deepcopy(model.world.pred[0])
        self.feed(model, 0)
        self.assertGreater(model.capacity_drops, 0)
        self.assertEqual(model.world.pred[0], before)
        self.assertEqual(model.cam.destroyed, 0)

    def test_stop_and_budget_are_latched_before_new_observations(self):
        model = b.witness_model()
        model.stop()
        before = digest(model)
        with self.assertRaises(RuntimeError):
            self.feed(model, 4)
        self.assertEqual(digest(model), before)
        model = self.model()
        for tick in range(LIMIT):
            self.feed(model, tick)
        before = digest(model)
        with self.assertRaises(RuntimeError):
            self.feed(model, LIMIT)
        self.assertEqual(digest(model), before)

    def test_integer_model_has_no_peer_or_environment_import(self):
        tree = ast.parse((b.ROOT/"echo4/other_model.py").read_text())
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertFalse(names & {"Encounter", "ChoiceEnv", "Agent", "random", "eval", "exec"})
        self.assertFalse(any(isinstance(n, ast.Constant) and isinstance(n.value, float) for n in ast.walk(tree)))


class NativeEncounter(unittest.TestCase):
    def make(self, mode="identity"):
        return Encounter(((0, 1, 2), (1, 2, 0)), seed=11, mode=mode)

    def test_original_q_and_gate_not_scripted_actions(self):
        run = self.make()
        for agent in run.agents:
            self.assertIs(type(agent), Agent)
            self.assertGreater(agent.metrics.deltas, 0)
            self.assertFalse(agent.cortex_enabled)
            self.assertEqual(agent.env.steps, PRIVATE_STEPS)
        frames = [run.step() for _ in range(24)]
        self.assertEqual(sum(v == 16 for e in frames for v in e["rewards"]), 48)
        self.assertTrue(run.invariant())

    def test_memories_worlds_and_observations_are_independent(self):
        run = self.make()
        a, peer = run.agents
        for name in ("cam", "q", "t", "env"):
            self.assertIsNot(getattr(a, name), getattr(peer, name))
        model_before = digest(run.models[0])
        # Intervene on the peer's private memory; no observer read occurs.
        for row in peer.q.q:
            row[0] = -127
        peer.env._preferences = (2, 0, 1)
        self.assertEqual(digest(run.models[0]), model_before)
        self.assertTrue(run.invariant())

    def test_reversing_native_execution_order_cannot_benefit_first_agent(self):
        first, second = self.make(), self.make()
        for _ in range(40):
            self.assertEqual(first.step(), second.step(order=(1, 0)))

    def test_native_actions_identical_across_observer_ablations(self):
        rows = []
        for mode in MODES:
            run = self.make(mode)
            rows.append([run.step()["actions"] for _ in range(40)])
        self.assertTrue(all(v == rows[0] for v in rows))

    def test_gate_changes_applied_action_and_sensor_records_that(self):
        run = self.make()
        e = run.step(veto=(False, True))
        self.assertEqual((e["actions"][1], e["gates"][1]), (2, 2))
        self.assertEqual(decode(bytes.fromhex(e["outcomes"][0][1]), action=True)[2], 2)
        self.assertTrue(run.invariant())

    def test_occlusion_and_lost_tracking(self):
        run = self.make()
        for _ in range(32):
            run.step()
        e = run.step(visible=(False, False))
        self.assertEqual(e["predictions"], (None, None))
        e = run.step(handles=(None, None))
        self.assertEqual(e["outcomes"][0][1], None)
        self.assertEqual(e["predictions"], (None, None))

    def test_bad_parameters_rejected_before_any_agent_moves(self):
        run = self.make()
        for kwargs in ({"visible": (1, True)}, {"handles": (True, 1)}, {"order": (0, 0)}, {"veto": [False, False]}):
            with self.assertRaises(ValueError):
                run.step(**kwargs)
            self.assertEqual(run.tick, 0)
            self.assertEqual(run.agents[0].env.steps, PRIVATE_STEPS)

    def test_partial_failure_prevents_retry(self):
        run = self.make()
        with patch.object(run.agents[1], "turn", side_effect=RuntimeError("interruption")):
            with self.assertRaises(RuntimeError):
                run.step()
        self.assertTrue(run.failed)
        with self.assertRaises(RuntimeError):
            run.step()

    def test_operator_stop_cannot_be_bypassed(self):
        run = self.make()
        run.step()
        run.stop()
        with self.assertRaises(RuntimeError):
            run.step()
        with self.assertRaises(RuntimeError):
            run.agents[0].env.step(0)
        self.assertEqual(run.tick, 1)

    def test_native_q_starts_zero_then_learns_not_preloaded(self):
        agent = new_agent((0, 1, 2), tuple(range(3))*100)
        self.assertTrue(all(not any(row) for row in agent.q.q))
        for tick in range(240):
            agent.turn(tick)
        self.assertTrue(any(any(row) for row in agent.q.q))

    def test_private_environment_rejects_bad_inputs_and_exhaustion(self):
        for prefs in ((False, 1, 2), (0, 0, 1), [0, 1, 2]):
            with self.assertRaises(ValueError):
                ChoiceEnv(prefs, (0,))
        env = ChoiceEnv((0, 1, 2), (0,))
        with self.assertRaises(ValueError):
            env.step(True)
        self.assertEqual(env.steps, 0)
        env.step(0)
        with self.assertRaises(RuntimeError):
            env.step(0)


class ReplayAndProtocol(unittest.TestCase):
    def test_replay_has_no_world_or_peer_dependency(self):
        run = Encounter(((0, 1, 2), (1, 2, 0)), seed=11)
        frames = [run.step() for _ in range(32)]
        records = transcript(frames, 0)
        with patch.object(ChoiceEnv, "step", side_effect=AssertionError("world executed")), \
                patch.object(Agent, "turn", side_effect=AssertionError("agent executed")):
            reproduced = replay(records, "identity")
        self.assertEqual(reproduced["memory_sha256"], digest(run.models[0]))
        self.assertEqual(reproduced["predictions"], [r["predictions"][0] for r in frames])

    def test_every_mode_has_exact_public_reconstruction(self):
        for mode in MODES:
            row = b.episode(11, False, mode)
            self.assertTrue(row["replay_equal"])
            self.assertTrue(row["invariants"])

    def test_fresh_process_replay(self):
        c = b.controls()
        self.assertTrue(c["passed"], c["checks"])
        with tempfile.TemporaryDirectory() as directory:
            rows = b.fresh_replay(Path(directory), c, False)
            self.assertTrue(all(r["equal"] for r in rows))

    def test_fresh_replay_checks_original_forecasts_not_only_replay_against_itself(self):
        c = b.controls()
        c["rows"][0]["predictions"] = (2, 2)  # No history exists at the first tick.
        with tempfile.TemporaryDirectory() as directory:
            rows = b.fresh_replay(Path(directory), c, False)
            self.assertTrue(all(not r["equal"] for r in rows))

    def test_replay_rejects_out_of_order_or_injected_private_fields(self):
        run = Encounter(((0, 1, 2), (1, 2, 0)), seed=11)
        records = transcript([run.step(), run.step()], 0)
        with self.assertRaises(ValueError):
            replay(records[::-1], "identity")
        with self.assertRaises(ValueError):
            replay(records+[records[-1]], "identity")
        records[0]["private_preferences"] = [1, 2, 0]
        with self.assertRaises(ValueError):
            replay(records, "identity")

    def test_parent_and_99_sources_unchanged(self):
        self.assertTrue(b.parent())
        self.assertEqual(len(b.sources()), 99)

    def test_missing_or_forged_report_never_issues_green(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            self.assertFalse(b.verify(path)["valid"])
            b.persist(path, "report.json", {"reproduction_sha256": "invented", "sources": {}, "other1_green": True}, False)
            result = b.verify(path)
            self.assertFalse(result["valid"])
            self.assertFalse(result["other1_green"])

    def test_preregistration_before_execution_and_failed_development_keeps_exam_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            def failed(seeds, progress):
                self.assertTrue((path/"lock.json").exists())
                self.assertEqual(seeds, b.DEVELOPMENT)
                return {"checks": {"synthetic": False}, "passed": False}
            with patch.object(b, "sources", return_value={}), patch.object(b, "parent", return_value={}), \
                    patch.object(b, "batch", side_effect=failed) as batch, \
                    patch.object(b, "controls", return_value={"checks": {}, "passed": True, "rows": []}), \
                    patch.object(b, "fresh_replay", return_value=[{"equal": True}]):
                report = b.campaign(path)
            batch.assert_called_once()
            self.assertEqual(report["exams"], [])
            self.assertFalse(report["other1_green"])
            self.assertFalse(report["criteria_passed"])


if __name__ == "__main__":
    unittest.main()
