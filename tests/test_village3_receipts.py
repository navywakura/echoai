import unittest
from seed import village3_receipts as v
from seed.game_selfimprove import sha


class ReceiptAffordance(unittest.TestCase):
    def test_credit_tracks_actual_retained_proof_not_intention_and_cannot_answer_claim(self):
        a = v.Echo(1)
        a.observed_navigation_cost = 10
        a.begin("s:0", "neg", 3, 11, 0)
        self.assertEqual(a.receipt_credit["s:0"], 0)
        a.charge("s:0", 12)
        a.mature(64)
        self.assertEqual(a.proof_returns["neg"], [[-12, 1], [0, 0]])
        self.assertIsNone(a.evidence({"session": "s", "episode": 0, "agent": "B"}))

    def test_false_hint_proof_must_really_be_in_diary(self):
        a = v.Echo(2)
        offer = {"session": "s", "episode": 0, "agent": "B", "said": 1}
        a.remember(offer, {"checked": 2, "proof": "signed-receipt", "cost": 10}, True)
        a.observed_navigation_cost = 10
        a.begin("s:0", "neg", 3, 11, 0)
        a.mature(64)
        self.assertEqual(a.proof_returns["neg"], [[0, 0], [0, 1]])
        self.assertNotIn("signed-receipt", str(a.receipt_credit))
        a.charge("s:0", 12)
        self.assertEqual(a.proof_returns["neg"], [[0, 0], [-12, 1]])

    def test_real_run_and_observation_have_exact_replay(self):
        observed=[]
        first, _ = v.run(1, episodes=300, observer=observed.append)
        second, a = v.run(1, episodes=300)
        self.assertEqual(sha(first), sha(second))
        self.assertEqual(observed, first["rows"])
        self.assertEqual(sum(x[1] for row in a.proof_returns.values() for x in row), a.matured)


if __name__ == "__main__":
    unittest.main()
