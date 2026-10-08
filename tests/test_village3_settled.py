import unittest
from seed import village3_settled as v


class SettlementBoundary(unittest.TestCase):
    def test_latest_allowed_claim_enters_return_before_first_use(self):
        a = v.Echo(1)
        a.observed_navigation_cost = 10
        a.begin("s:0", "neg", 3, 11, 0)
        a.mature(48)
        self.assertEqual(a.q["neg"][3], [0, 0])
        a.charge("s:0", 12)
        a.mature(49)
        self.assertEqual(a.q["neg"][3], [-23, 1])
        self.assertEqual(a.state()["return_horizon"], 49)

    def test_only_completed_returns_count(self):
        r, a = v.run(2, episodes=100)
        self.assertEqual(a.matured, 51)
        self.assertEqual(len(a.pending_returns), 49)
        self.assertEqual(sum(c[1] for row in a.q.values() for c in row), 51)


if __name__ == "__main__":
    unittest.main()
