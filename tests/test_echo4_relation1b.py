"""RELATION-B help task: physics, derived rows, isolation, veto, limits, parity."""
import unittest
from unittest.mock import patch

from echoai.core.cam import Cam
from echoai.nexus0.constants import GATE_BLOCK
from echoai.echo4.continuity import canonical
from echoai.echo4.relation_memory import RelationMemory
from echoai.echo4 import relation_help as h
from echoai.echo4 import relation_b_bench as bench
from echoai.tests.test_echo4_relation1a import observed

CUES = (0, 1, 2) * 12
SCHEDULE = (1, 2) * 18
FORM = 18


def session(arm="history", **kwargs):
    run = h.HelpSession(CUES, SCHEDULE, b_arm=arm, seed=7, **kwargs)
    for t in range(FORM):
        run.step(greedy=False)
    return run


def encounter(run, **kwargs):
    frame = run.help_step(**kwargs)
    run.step(greedy=True)
    return frame


class HelpPhysics(unittest.TestCase):
    def test_declared_payoffs(self):
        self.assertEqual(h.settle(0, 0, (10, 10))["paid"], (1, 3))
        self.assertEqual(h.settle(0, 0, (10, 10))["output"], (8, 0))
        self.assertEqual(h.settle(0, 1, (10, 10))["net"], (-3, 0))
        self.assertEqual(h.settle(0, 2, (10, 10))["net"], (-3, 0))
        self.assertEqual(h.settle(1, None, (10, 10))["net"], (1, 0))
        self.assertEqual(h.settle(2, None, (10, 10))["net"], (0, 0))

    def test_partner_acts_only_when_asked(self):
        for action in (1, 2):
            with self.assertRaises(ValueError):
                h.settle(action, 0, (10, 10))
        with self.assertRaises(ValueError):
            h.settle(0, None, (10, 10))

    def test_incapable_is_not_a_cost_or_a_gift(self):
        event = h.settle(0, None, (2, 10))
        self.assertEqual((event["asked"], event["paid"], event["output"]), (False, (0, 0), (0, 0)))
        event = h.settle(0, 0, (10, 2))
        self.assertEqual((event["helped"], event["paid"], event["output"]), (False, (3, 0), (0, 0)))
        self.assertEqual(h.settle(1, None, (0, 10))["net"], (0, 0))

    def test_strict_types(self):
        for bad in ((True, None, (1, 1)), (0, 0, (1.0, 1)), (3, None, (1, 1)), (0, 0, [1, 1])):
            with self.assertRaises(ValueError):
                h.settle(*bad)
        with self.assertRaises(ValueError):
            h.bucket(())
        with self.assertRaises(ValueError):
            h.row("friend", 5)

    def test_reciprocity_incentive_is_symmetric_and_bounded(self):
        self.assertEqual(h.incentive(2, 0), 16)
        self.assertEqual(h.incentive(2, 1), -16)
        self.assertEqual(h.incentive(1, 0), -16)
        self.assertEqual(h.incentive(0, 2), 16)


class HistoryBuckets(unittest.TestCase):
    def test_bucket_uses_last_window_only(self):
        memory = RelationMemory(Cam())
        observed(memory, 0, 1, own=0, remote=0, cue=0)  # success
        for tick in (1, 2):
            observed(memory, tick, 1, own=1, remote=1, cue=1)
        self.assertEqual(h.bucket(memory.history(1)), 2)
        observed(memory, 3, 1, own=1, remote=1, cue=1)
        self.assertEqual(h.bucket(memory.history(1)), 1)
        self.assertEqual(h.bucket(memory.history(1)[:2]), 0)

    def test_missing_peer_receipt_is_never_a_success(self):
        memory = RelationMemory(Cam())
        for tick in range(3):
            observed(memory, tick, 1, own=0, remote=None, cue=0)
        self.assertEqual(h.bucket(memory.history(1)), 1)

    def test_shuffled_is_same_episodes_other_order(self):
        memory = RelationMemory(Cam())
        for tick in range(9):
            observed(memory, tick, 1, own=tick % 2, remote=tick % 2, cue=0)
        rows = memory.history(1)
        mixed = h.shuffled(rows, 3, 9)
        self.assertEqual(sorted(canonical(r) for r in rows), sorted(canonical(r) for r in mixed))
        self.assertNotEqual([r["wsp"] for r in rows], [r["wsp"] for r in mixed])
        self.assertEqual(mixed, h.shuffled(rows, 3, 9))

    def test_rows_are_wsp16_and_arm_specific(self):
        raw = h.row("history", 4096, level=2)
        self.assertEqual(len(raw), 16)
        self.assertEqual(raw[10:14], bytes((0, 9, 8, h.B_STYLE)))
        self.assertEqual(raw[4:10], bytes(6))
        self.assertNotEqual(h.row("history", 4096, level=1), raw)
        self.assertNotEqual(h.row("other_only", 4096, handle=1), h.row("other_only", 4096, handle=2))


class HelpSessionTests(unittest.TestCase):
    def test_level_uses_prior_episodes_only(self):
        run = session()
        count = run.relations[0].count
        prior = h.bucket(run.relations[0].history(SCHEDULE[FORM]))
        frame = run.help_step()
        self.assertEqual(frame["level"], prior)
        self.assertEqual(run.relations[0].count, count)  # B writes no episode
        run.step()
        self.assertEqual(run.relations[0].count, count + 1)

    def test_one_b_step_per_encounter(self):
        run = session()
        run.help_step()
        with self.assertRaises(RuntimeError):
            run.help_step()
        # Rejected before execution: nothing ran, the A step still proceeds.
        self.assertFalse(run.failed)
        run.step()
        self.assertTrue(run.invariant())

    def test_partner_incentive_reads_only_partner_memory(self):
        run = session()
        handle = SCHEDULE[FORM]
        expected = h.bucket(run.relations[handle].history(1))
        with patch.object(run.relations[0], "history", side_effect=AssertionError("learner memory read")):
            self.assertEqual(run.partner_level(handle), expected)

    def test_b_rows_are_not_facts_and_invariants_hold(self):
        run = session()
        for _ in range(6):
            encounter(run)
        rows = [s for s in run.focal.cam.slot if s.occupied and s.source == h.B_SOURCE]
        self.assertTrue(rows)
        self.assertTrue(all(not s.has_fact and not s.extract for s in rows))
        self.assertTrue(run.invariant())
        for agent in run.all_agents:
            self.assertEqual((agent.metrics.false_facts, agent.cam.destroyed, agent.metrics.cortex_calls), (0, 0, 0))
            self.assertFalse(agent.cortex_enabled)

    def test_learner_veto_blocks_asking(self):
        run = session("always_ask")
        frame = run.help_step(veto=(True, False))
        self.assertEqual((frame["gate"], frame["action"], frame["asked"]), (GATE_BLOCK, 2, False))
        self.assertEqual(frame["paid"], (0, 0))

    def test_partner_veto_uses_its_gate(self):
        run = session("always_ask")
        handle = SCHEDULE[FORM]
        before = run.b_turns[handle]
        frame = run.help_step(veto=(False, True))
        self.assertEqual((frame["asked"], frame["helped"], frame["help_action"]), (True, False, 2))
        self.assertEqual(run.partners[handle-1].last_gate_decision, GATE_BLOCK)
        self.assertEqual(run.b_turns[handle], before + 1)
        self.assertEqual(frame["net"], (-3, 0))

    def test_untracked_identity_has_no_history(self):
        run = session()
        frame = run.help_step(tracked=False)
        self.assertEqual(frame["level"], 0)
        self.assertEqual(frame["row"], h.row("history", run.ledger[0] + frame["paid"][0], level=0).hex())

    def test_exhausted_budget_cannot_ask(self):
        run = session("always_ask", resources=(2, 4096, 4096))
        frame = run.help_step()
        self.assertEqual((frame["asked"], frame["paid"], frame["incapable"][0]), (False, (0, 0), True))

    def test_failure_after_execution_keeps_costs_and_stops(self):
        run = session("solo")
        ledger = run.ledger[0]
        with patch.object(h, "settle", side_effect=RuntimeError("receipt lost")):
            with self.assertRaises(RuntimeError):
                run.help_step()
        self.assertTrue(run.failed and run.stopped)
        self.assertEqual(run.ledger[0], ledger)  # nothing settled, nothing forged
        with self.assertRaises(RuntimeError):
            run.step()

    def test_fixed_controls_are_not_learned_policies(self):
        self.assertEqual(session("solo").help_step()["proposal"], 1)
        self.assertEqual(session("always_ask").help_step()["proposal"], 0)

    def test_a_arm_is_always_identity(self):
        with self.assertRaises(ValueError):
            h.HelpSession(CUES, SCHEDULE, b_arm="history", arm="pooled")
        with self.assertRaises(ValueError):
            h.HelpSession(CUES, SCHEDULE, b_arm="friendship")

    def test_a_parity_across_b_arms(self):
        digests = set()
        for arm in ("history", "solo", "always_ask"):
            run = session(arm)
            frames = [f for _ in range(12) for f in (run.help_step(), run.step(greedy=True))][1::2]
            digests.add(canonical([{k: v for k, v in f.items() if k not in bench.RESOURCE_FIELDS}
                                   for f in frames]))
        self.assertEqual(len(digests), 1)

    def test_b_replay_from_receipts(self):
        run = session()
        frames = [encounter(run) for _ in range(12)]
        self.assertTrue(bench.reconstruct_b(frames, run.relations[0].history(), "history", 7))

    def test_reverse_a_order_reproduces_traces(self):
        runs = []
        for order in ((0, 1), (1, 0)):
            run = h.HelpSession(CUES, SCHEDULE, b_arm="history", seed=7)
            frames = []
            for t in range(len(CUES)):
                if t >= FORM:
                    frames.append(run.help_step())
                frames.append(run.step(order=order))
            runs.append(canonical(frames))
        self.assertEqual(*runs)


if __name__ == "__main__":
    unittest.main()
