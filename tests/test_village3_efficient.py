import unittest
from seed import village3_efficient as v
from seed.game_selfimprove import sha


class EvidenceExploration(unittest.TestCase):
    def test_reduction_depends_on_completed_evidence_not_pending_claims(self):
        a = v.Echo(1)
        a.observed_navigation_cost = 3
        for i in range(500):
            a.begin(f"s:{i}", "zero", 0, 3, 0)
        self.assertEqual(a.exploration_pm(), 100)
        a.mature(64)
        self.assertLess(a.exploration_pm(), 100)
        before = a.rng.getstate()
        for _ in range(100):
            a.choose("zero", learn=False)
        self.assertEqual(a.rng.getstate(), before)

    def test_controls_keep_disabled_actions_and_replay(self):
        r, a = v.run(9, diary=False, verification=False, episodes=500)
        again, _ = v.run(9, diary=False, verification=False, episodes=500)
        self.assertEqual(sha(r), sha(again))
        self.assertTrue(all(row["action"] == 0 for row in r["rows"]))
        self.assertEqual(a.diary, [])


if __name__ == "__main__":
    unittest.main()
