"""ROLES-1 annex L v2: metaknowledge is a hypothesis; deduction considers itself."""
import unittest

from echoai.echo4 import tribe as T
from echoai.echo4 import tribe_exam as E
from echoai.echo4 import tribe_liar2 as M
from echoai.echo4.tribe_liar import LiarMemory
from echoai.core.cam import Cam


class Deduction(unittest.TestCase):
    def test_verified_fact_beats_feeling(self):
        m = LiarMemory(Cam(), T.ECHO)
        m.record(0, 4, T.ECHO, T.C, "answered")
        m.record(1, 4, T.ECHO, T.B, "wrong_answer")
        self.assertEqual(M.suggestion_meta(m.rows, 1, 4, True)[0], T.C)

    def test_feeling_makes_echo_consider_itself(self):
        m = LiarMemory(Cam(), T.ECHO)
        m.record(0, 4, T.ECHO, T.B, "wrong_answer")
        self.assertEqual(M.suggestion_meta(m.rows, 0, 4, True)[0], T.ECHO)
        self.assertNotEqual(M.suggestion_meta(m.rows, 0, 4, False)[0], T.ECHO)

    def test_self_fail_eliminates_even_if_it_feels_it_knows(self):
        m = LiarMemory(Cam(), T.ECHO)
        m.record(0, 4, T.ECHO, T.ECHO, "self_fail")
        self.assertNotEqual(M.suggestion_meta(m.rows, 0, 4, True)[0], T.ECHO)


class Session(unittest.TestCase):
    def test_off_and_zero_rate_is_v5(self):
        a, b = E.TribeCSession(5), M.MetaSession(5, meta=False, rate=0)
        self.assertEqual(E.strip([a.step() for _ in range(96)]), E.strip([b.step() for _ in range(96)]))

    def test_metaknowledge_never_fact(self):
        s = M.MetaSession(5, rate=50)
        for _ in range(T.ROUNDS):
            s.step()
        rows = [x for x in s.agents[T.ECHO].cam.slot if x.occupied and x.source == M.META_SOURCE]
        self.assertTrue(rows)
        self.assertTrue(all(not x.has_fact and not x.extract for x in rows))
        self.assertEqual(sum(a.metrics.false_facts for a in s.agents), 0)
        self.assertTrue(s.invariant())

    def test_signal_accuracy_is_declared(self):
        s = M.MetaSession(5)
        right = sum(s.feels[t] == (s.knower[t] == T.ECHO) for t in s.feels)
        self.assertGreaterEqual(right, len(s.feels) // 2)
        with self.assertRaises(ValueError):
            M.MetaSession(5, meta=1)


if __name__ == "__main__":
    unittest.main()
