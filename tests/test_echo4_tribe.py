"""ROLES-1 v3/v4/v5 «la tribu»: world, facts vs testimony, elimination, derived rank."""
import unittest
from unittest.mock import patch

from echoai.core.cam import Cam
from echoai.echo4 import tribe as T
from echoai.echo4.tribe_v4 import proposal, TribeV4Session
from echoai.echo4.tribe_exam import TribeCSession, strip


def rec(m, tick, topic, seeker, target, kind):
    return m.record(tick, topic, seeker, target, kind)


class World(unittest.TestCase):
    def test_schedule_has_real_undeclared_hierarchy(self):
        topics, knower, seekers = T.schedule(9)
        self.assertEqual(len(topics), T.ROUNDS)
        self.assertEqual(seekers.count(T.ECHO), 256)
        for half in range(8):
            owners = [knower[half * 3 + k] for k in range(3)]
            counts = T.DISTRIBUTION[half // 2]
            self.assertEqual([owners.count(a) for a in range(3)], list(counts))
        self.assertEqual(T.true_order(0), (T.C, T.ECHO, T.B))
        self.assertEqual(T.true_order(200), (T.B, T.C, T.ECHO))

    def test_relative_mapping(self):
        self.assertEqual(T.absolute(T.ECHO, 0), T.B)
        self.assertEqual(T.absolute(T.B, 0), T.ECHO)
        self.assertEqual(T.absolute(T.B, 2), T.B)
        self.assertEqual(T.relative(T.ECHO, None), T.UNKNOWN)


class FactsAndTestimony(unittest.TestCase):
    def test_saying_no_is_a_fact_not_knowledge(self):
        m = T.TribeMemory(Cam(), T.ECHO)
        rec(m, 0, 0, T.ECHO, T.B, "said_no")
        hyp = [s for s in m.cam.slot if s.occupied and s.source == T.TESTIMONY_SOURCE]
        self.assertEqual(len(hyp), 1)
        self.assertFalse(hyp[0].has_fact or hyp[0].extract)
        self.assertEqual(m.facts()[0]["kind"], "said_no")
        self.assertTrue(m.invariant())

    def test_only_lived_events_and_strict_schema(self):
        m = T.TribeMemory(Cam(), T.ECHO)
        with self.assertRaises(ValueError):
            rec(m, 0, 0, T.B, T.C, "answered")
        with self.assertRaises(ValueError):
            rec(m, 0, 0, T.ECHO, T.ECHO, "answered")
        with self.assertRaises(ValueError):
            rec(m, 0, 0, T.ECHO, T.B, "maybe")

    def test_claim_is_hypothesis(self):
        m = T.TribeMemory(Cam(), T.ECHO)
        m.claim(0, T.B)
        self.assertEqual(m.claimants(), {T.B})
        self.assertEqual(m.facts(), [])

    def test_corrupt_fact_detected(self):
        m = T.TribeMemory(Cam(), T.ECHO)
        rec(m, 0, 0, T.ECHO, T.C, "answered")
        slot = m.cam.get(T.event_key(0))
        m.cam.slot[slot].extract += " "
        with self.assertRaises(ValueError):
            m.facts()


class Reasoning(unittest.TestCase):
    def test_elimination_then_only_c_remains(self):
        m = T.TribeMemory(Cam(), T.ECHO)
        rec(m, 0, 5, T.ECHO, T.ECHO, "self_ok")   # ECHO answered something else before
        rec(m, 1, 7, T.ECHO, T.B, "said_no")      # this round: B says no
        rec(m, 1, 7, T.ECHO, T.ECHO, "self_fail") # and ECHO cannot
        suggested, elim = T.suggestion(m.rows, 1, 7, "tribe")
        self.assertEqual(elim, {T.B, T.ECHO})
        self.assertIsNone(suggested)              # no rank evidence for C yet...
        rec(m, 0, 3, T.ECHO, T.C, "answered")     # (older verified answer by C)
        self.assertEqual(T.suggestion(m.rows, 1, 7, "tribe")[0], T.C)
        self.assertNotEqual(T.suggestion(m.rows, 1, 7, "no_elimination")[1], elim)

    def test_derived_rank_includes_self_and_is_never_a_label(self):
        m = T.TribeMemory(Cam(), T.ECHO)
        for t in range(3):
            rec(m, t, 0, T.ECHO, T.C, "answered")
        rec(m, 3, 1, T.ECHO, T.ECHO, "self_ok")
        self.assertEqual(T.derived_order(m.rows, 3), (T.C, T.ECHO, T.B))
        self.assertIsNone(T.derived_order(m.rows[:1], 0))  # C=1, ECHO=B=0: tie, no strict order
        rec(m, 4, 1, T.B, T.ECHO, "answered")               # B asked ECHO; ECHO answered
        self.assertEqual(T.rank_counts(m.rows, 4), [2, 0, 3])
        self.assertEqual(T.derived_order(m.rows, 4), (T.C, T.ECHO, T.B))
        self.assertEqual(T.derived_order(m.rows, 4 + T.WINDOW + 1), None)  # evidence expires

    def test_claims_never_enter_rank(self):
        m = T.TribeMemory(Cam(), T.ECHO)
        for t in range(5):
            m.claim(t, T.B)
        self.assertEqual(T.rank_counts(m.rows, 4), [0, 0, 0])
        self.assertIsNone(T.suggestion(m.rows, 4, 0, "tribe", frozenset({T.B}))[0])
        self.assertEqual(T.suggestion(m.rows, 4, 0, "claimed_rank", frozenset({T.B}))[0], T.B)

    def test_v4_proposal_puts_eliminated_last(self):
        m = T.TribeMemory(Cam(), T.ECHO)
        rec(m, 0, 3, T.ECHO, T.C, "answered")
        rec(m, 1, 7, T.ECHO, T.B, "said_no")
        ordered, source, n = proposal(m.rows, 1, 7, "tribe", T.ECHO, frozenset())
        self.assertEqual(ordered[-1], T.B)
        self.assertEqual((ordered[0], source, n), (T.C, 2, 1))


class Sessions(unittest.TestCase):
    def test_nominal_invariants(self):
        for cls in (T.TribeSession, TribeV4Session, TribeCSession):
            s = cls(5)
            for _ in range(60):
                s.step()
            self.assertTrue(s.invariant())

    def test_exam_session_equals_v3(self):
        a, b = T.TribeSession(5), TribeCSession(5)
        self.assertEqual([a.step() for _ in range(60)], strip([b.step() for _ in range(60)]))

    def test_random_mode_predicts_before_each_answer(self):
        s = T.TribeSession(5, mode="random")
        frames = [s.step() for _ in range(30)]
        for f in frames:
            if f["seeker"] == T.ECHO:
                self.assertEqual(len(f["predictions"]), len(f["attempts"]))

    def test_liar_never_creates_false_facts(self):
        s = TribeCSession(5, liar=(T.B, 2))
        for _ in range(T.ROUNDS):
            s.step()
        self.assertTrue(s.lies)
        self.assertTrue(s.invariant())
        self.assertEqual(sum(a.metrics.false_facts for a in s.agents), 0)

    def test_veto_asks_nothing(self):
        s = T.TribeSession(5)
        while s.seekers[s.tick] != T.ECHO:
            s.step()
        f = s.step(veto=True)
        self.assertEqual(f["attempts"], [])
        self.assertTrue(s.invariant())

    def test_capacity_stops(self):
        s = T.TribeSession(5)
        s.step()
        with patch.object(T, "allocate", return_value=(-1, None)):
            with self.assertRaises(RuntimeError):
                s.step()
        self.assertTrue(s.failed and s.stopped)

    def test_isolated_memories(self):
        s = T.TribeSession(5)
        self.assertEqual(len({id(a.cam) for a in s.agents} | {id(a.q) for a in s.agents}), 6)


if __name__ == "__main__":
    unittest.main()
