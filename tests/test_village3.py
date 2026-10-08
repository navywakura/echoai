import copy
import unittest

from seed import village3 as v
from seed.game_selfimprove import sha


class CompletedReturnTests(unittest.TestCase):
    def test_costs_count_once_only_after_maturity_and_late_charge_still_applies(self):
        a = v.Echo(1)
        a.begin("s:0", "neg", 3, 11, 0)
        a.charge("s:0", 12)
        a.mature(63)
        self.assertEqual(a.q["neg"][3], [0, 0])
        a.mature(64)
        self.assertEqual(a.q["neg"][3], [-23, 1])
        a.mature(100)
        a.charge("s:0", 12)
        self.assertEqual(a.q["neg"][3], [-35, 1])
        self.assertEqual(a.matured, 1)
        self.assertEqual(a.diary, [])

    def test_own_action_gets_its_actual_cost_without_private_claim_information(self):
        r, a = v.run(1, episodes=120)
        expected = {c: [[0, 0] for _ in range(4)] for c in a.q}
        for row in r["rows"][:56]:
            cell = expected[row["context"]][row["action"]]
            cell[0] -= row["result"]["cost"] + int(row["wrote"])
            cell[1] += 1
        for row in r["rows"]:
            for claim in row["claims"]:
                if claim["episode"] < 56:
                    origin = r["rows"][claim["episode"]]
                    expected[origin["context"]][origin["action"]][0] -= claim["cost"]
        self.assertEqual(a.q, expected)
        self.assertEqual(len(a.pending_returns), 64)
        self.assertTrue(all(len(x) == 2 for x in a.credit.values()))

    def test_probe_never_matures_or_updates_Q_and_replay_is_exact(self):
        r, a = v.run(1, episodes=100)
        again, _ = v.run(1, episodes=100)
        self.assertEqual(sha(r), sha(again))
        before = copy.deepcopy(a.q)
        pending = copy.deepcopy(a.pending_returns)
        v.run(2, actor=a, episodes=100, learn=False)
        self.assertEqual(a.q, before)
        self.assertEqual(a.pending_returns, pending)

    def test_passive_observer_does_not_change_decisions(self):
        observed = []
        r, _ = v.run(4, episodes=100, observer=lambda row: observed.append(copy.deepcopy(row)))
        plain, _ = v.run(4, episodes=100)
        self.assertEqual(sha(r), sha(plain))
        self.assertEqual(observed, r["rows"])


if __name__ == "__main__":
    unittest.main()
