"""RELATION-C: body relief, fail-stop on corrupt history, limits, invariant."""
import unittest
from unittest.mock import patch

from echoai.echo4 import relation_help as h
from echoai.echo4.relation_c import RelationCSession, NeverHelp, HELP_MODES
from echoai.echo4.relation_help import HelpSession

CUES = (0, 1, 2) * 12
SCHEDULE = (1, 2) * 18
FORM = 18


def session(cls=RelationCSession, arm="history", **kwargs):
    run = cls(CUES, SCHEDULE, b_arm=arm, seed=7, **kwargs)
    for _ in range(FORM):
        run.step()
    return run


def encounters(run, n):
    for _ in range(n):
        run.help_step()
        run.step(greedy=True)


class Invariant(unittest.TestCase):
    def test_explicit_invariant_matches_inherited_in_nominal_run(self):
        run = session()
        encounters(run, 6)
        self.assertTrue(run.invariant())
        self.assertTrue(HelpSession.invariant(run))
        run.focal.metrics.false_facts += 1
        self.assertFalse(run.invariant())
        self.assertFalse(HelpSession.invariant(run))

    def test_nominal_frames_identical_to_help_session(self):
        runs = [session(cls) for cls in (HelpSession, RelationCSession)]
        frames = [[run.help_step() for run in runs] for _ in range(1)]
        self.assertEqual(frames[0][0], frames[0][1])


class Relief(unittest.TestCase):
    def test_new_body_has_no_memory_of_the_learner(self):
        run = session()
        old = run.partners[0]
        body = run.relieve(1, (1, 2, 0), "reciprocal", seed=3)
        self.assertIsNot(body, old)
        self.assertIs(run.partners[0], body)
        self.assertEqual(run.relations[1].count, 0)
        self.assertEqual(run.partner_level(1), 0)
        self.assertEqual(run.retired[1], FORM // 2)
        self.assertGreater(run.relations[0].summary(1)["encounters"], 0)  # learner keeps its past
        encounters(run, 6)
        self.assertTrue(run.invariant())

    def test_relief_is_strict_and_not_in_flight(self):
        run = session()
        for args in ((3, (0, 1, 2), "reciprocal"), (1, (0, 0, 1), "reciprocal"), (1, (0, 1, 2), "friend")):
            with self.assertRaises(ValueError):
                run.relieve(*args)
        run.stop()
        with self.assertRaises(RuntimeError):
            run.relieve(1, (0, 1, 2), "never")
        self.assertEqual(HELP_MODES, ("reciprocal", "never"))

    def test_never_help_rewards(self):
        env = NeverHelp((6, 6))
        self.assertEqual(env.step(0)[0], -h.RECIPROCITY - h.HELP_COST)
        self.assertEqual(env.step(1)[0], h.RECIPROCITY)
        with self.assertRaises(RuntimeError):
            env.step(1)


class FailStop(unittest.TestCase):
    def test_corrupt_history_stops_without_request(self):
        run = session()
        handle = SCHEDULE[FORM]
        slot = run.relations[0].peer_heads[handle]
        run.focal.cam.slot[slot].extract += " "
        ledger, turns = tuple(run.ledger), tuple(run.b_turns)
        with self.assertRaises(ValueError):
            run.help_step()
        self.assertTrue(run.failed and run.stopped)
        self.assertEqual((tuple(run.ledger), tuple(run.b_turns)), (ledger, turns))

    def test_precondition_rejection_does_not_fail(self):
        run = session()
        run.help_step()
        with self.assertRaises(RuntimeError):
            run.help_step()
        self.assertFalse(run.failed)

    def test_cam_full_stops(self):
        run = session()
        with patch.object(h, "allocate", return_value=(-1, None)):
            with self.assertRaises(RuntimeError):
                run.help_step()
        self.assertTrue(run.failed and run.stopped)
        with self.assertRaises(RuntimeError):
            run.step()


if __name__ == "__main__":
    unittest.main()
