import unittest
from seed import village3_factorized as v
from seed.game_selfimprove import sha


class FactorizedCosts(unittest.TestCase):
    def test_observed_components_and_credit_reconstruct_actual_total(self):
        a = v.Echo(1)
        a.observed_navigation_cost = 10
        a.begin("s:0", "neg", 3, 11, 0)
        a.charge("s:0", 12)
        self.assertEqual(a.navigation["neg"], [[0, 0], [-10, 1]])
        self.assertEqual(a.writing, [-1, 1])
        self.assertEqual(a.downstream["neg"][3], [0, 0])
        a.mature(64)
        self.assertEqual(a.q["neg"][3], [-23, 1])
        self.assertEqual(a.downstream["neg"][3], [-12, 1])
        self.assertEqual(a.scores("neg")[3], -23000)

    def test_observer_parity_and_no_learning_in_probe(self):
        rows = []
        r, a = v.run(2, episodes=160, observer=rows.append)
        again, _ = v.run(2, episodes=160)
        self.assertEqual(sha(r), sha(again))
        before = {k: sha(getattr(a, k)) for k in ("q", "navigation", "writing", "downstream", "pending_returns")}
        v.run(4, actor=a, episodes=100, learn=False)
        self.assertEqual(before, {k: sha(getattr(a, k)) for k in before})
        self.assertEqual(rows, r["rows"])


if __name__ == "__main__":
    unittest.main()
