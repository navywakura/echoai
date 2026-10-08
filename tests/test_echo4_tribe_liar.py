"""ROLES-1 annex L: affirmative lies, prior detection, the key, derived reliability."""
import unittest

from echoai.core.cam import Cam
from echoai.echo4 import tribe as T
from echoai.echo4 import tribe_exam as E
from echoai.echo4 import tribe_liar as L


class Memory(unittest.TestCase):
    def test_failed_answer_is_a_fact_about_the_key_not_knowledge(self):
        m = L.LiarMemory(Cam(), T.ECHO)
        m.record(0, 4, T.ECHO, T.B, "wrong_answer")
        self.assertEqual(m.facts()[0]["kind"], "wrong_answer")
        self.assertIsNone(T.last_knower(m.rows, 4))          # never "B knows"
        self.assertEqual(L.reliability(m.rows), [0, 1, 0])
        self.assertTrue(m.invariant())
        with self.assertRaises(ValueError):
            m.record(1, 4, T.ECHO, T.ECHO, "wrong_answer")    # nobody lies to itself

    def test_failed_answer_eliminates_and_points_to_verified_knower(self):
        m = L.LiarMemory(Cam(), T.ECHO)
        m.record(0, 4, T.ECHO, T.C, "answered")
        m.record(1, 4, T.ECHO, T.B, "wrong_answer")
        suggested, elim = L.suggestion(m.rows, 1, 4)
        self.assertEqual((suggested, elim), (T.C, {T.B}))


class Session(unittest.TestCase):
    def test_zero_rate_is_v5(self):
        a, b = E.TribeCSession(5), L.LiarSession(5, rate=0)
        self.assertEqual(E.strip([a.step() for _ in range(96)]), E.strip([b.step() for _ in range(96)]))

    def test_lies_never_become_facts_and_are_all_caught(self):
        s = L.LiarSession(5, rate=50)
        for _ in range(T.ROUNDS):
            s.step()
        lies = [r for r in s.audit if r["lie"]]
        self.assertTrue(lies)
        self.assertTrue(all(r["detected_by_key"] for r in lies))
        self.assertEqual(sum(a.metrics.false_facts for a in s.agents), 0)
        self.assertEqual(L.reliability(s.memories[T.ECHO].rows)[T.B], len(lies))
        self.assertTrue(s.invariant())

    def test_no_false_alarm_on_honest_answers(self):
        s = L.LiarSession(7, rate=40)
        for _ in range(T.ROUNDS):
            s.step()
        self.assertFalse(any(r["suspected_before_key"] for r in s.audit if not r["lie"]))

    def test_rate_is_drawn_and_strict(self):
        self.assertIn(L.LiarSession(9).rate, L.RATES)
        with self.assertRaises(ValueError):
            L.LiarSession(9, rate=101)


if __name__ == "__main__":
    unittest.main()
