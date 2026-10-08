"""ROLES-1 v2: native periodic exploration breaks the v1 tie trap."""
import unittest

from echoai.echo4.roles_c import RolesCSession
from echoai.echo4.roles_v2 import RolesV2Session


class V2(unittest.TestCase):
    def test_only_change_is_exploration_flag(self):
        s = RolesV2Session(5, 24)
        self.assertFalse(s.focal.evidence_greedy)
        a, b = RolesCSession(5, 96), RolesV2Session(5, 96, evidence_greedy=True)
        for _ in range(96):
            self.assertEqual(a.step(), b.step())
        with self.assertRaises(ValueError):
            RolesV2Session(5, 24, evidence_greedy=1)

    def test_v1_trapped_life_recovers(self):
        # Seed 264106 is from the burned v1 exam cohort (red); not a v2 exam seed.
        v1, v2 = RolesCSession(264106, 384), RolesV2Session(264106, 384)
        f1 = [v1.step() for _ in range(384)]
        f2 = [v2.step() for _ in range(384)]
        last = lambda fr: sum(f["output"][0] > 0 for f in fr[288:])
        self.assertLessEqual(last(f1), 40)
        self.assertGreaterEqual(last(f2), 72)
        self.assertTrue(v2.invariant())

    def test_fixed_arms_unchanged(self):
        for arm in ("rank_follow", "self_only"):
            a, b = RolesCSession(5, 48, arm=arm), RolesV2Session(5, 48, arm=arm)
            self.assertEqual([x.step()["assignee"] for x in (a,) for _ in range(48)],
                             [y.step()["assignee"] for y in (b,) for _ in range(48)])


if __name__ == "__main__":
    unittest.main()
