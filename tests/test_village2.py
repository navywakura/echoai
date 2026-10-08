import copy
import unittest

from seed import village2 as v
from seed.game_selfimprove import sha
from seed.village2_campaign import diary_valid


class VillageBoundary(unittest.TestCase):
    def false_offer(self, world):
        for episode in range(100):
            offer = world.offer(episode)
            result = world.execute(episode, True)
            if offer["said"] != result["checked"]:
                return offer, result
        self.fail("no false hint in fixture")

    def test_receipt_requires_verification_and_tampering_or_cross_world_does_not_pay(self):
        world = v.World(1)
        offer, result = self.false_offer(world)
        actor = v.Echo(1)
        entry = actor.remember(offer, result, True)
        claim = {k: offer[k] for k in ("session", "episode", "agent")}
        self.assertEqual(world.settle(claim, entry)["cost"], 0)
        bad = copy.deepcopy(entry)
        bad["proof"] = "forged"
        self.assertEqual(world.settle(claim, bad)["cost"], v.CLAIM_COST)
        direct = world.execute(offer["episode"], False)
        no_proof = actor.remember(offer, direct, False)
        self.assertEqual(world.settle(claim, no_proof)["cost"], v.CLAIM_COST)
        other = v.World(2)
        foreign, foreign_result = self.false_offer(other)
        self.assertIsNone(actor.evidence({k: foreign[k] for k in ("session", "episode", "agent")}))

    def test_verification_is_costly_immediately_and_paired_world_offers_are_equal(self):
        debt, control = v.World(4, debts=True), v.World(4, debts=False)
        for episode in range(100):
            offer = debt.offer(episode)
            self.assertEqual(offer, control.offer(episode))
            self.assertNotIn("liar", offer)
            self.assertNotIn("checked", offer)
            self.assertGreater(debt.execute(episode, True)["cost"], debt.execute(episode, False)["cost"])

    def test_only_chosen_actions_are_updated_and_credit_cannot_answer_claims(self):
        actor = v.Echo(9, diary=False, verification=False)
        record, actor = v.run(9, debts=False, actor=actor, episodes=20)
        self.assertEqual(sum(c[1] for cells in actor.q.values() for c in cells), 20)
        self.assertTrue(all(c == [0, 0] for cells in actor.q.values() for c in cells[1:]))
        self.assertEqual(actor.diary, [])
        self.assertTrue(all(set(x) <= {"zero", 0} for x in actor.credit.values()))
        self.assertTrue(all(not r["wrote"] and not r["verified"] for r in record["rows"]))

    def test_ablation_hides_causal_memory_without_rewriting_history_or_Q(self):
        actor = v.Echo(4)
        fact = {"session": "s", "episode": 0, "agent": "B", "said": 1}
        entry = actor.remember(fact, {"checked": 2, "cost": 10, "proof": "receipt"}, True)
        actor.q["neg"][3] = [-1, 1]
        actor.q["zero"][0] = [-1, 1]
        original = actor.state()
        clone = copy.deepcopy(actor)
        clone.suppressed.add(entry["hash"])
        self.assertEqual(actor.context("B"), "neg")
        self.assertEqual(clone.context("B"), "zero")
        self.assertEqual(clone.q, actor.q)
        self.assertEqual(clone.diary, actor.diary)
        self.assertEqual(sha(actor.state()), sha(original))
        diary_valid({"final": clone.state()})
        tampered = copy.deepcopy(clone.state())
        tampered["diary"][0]["valence"] = 100
        with self.assertRaises(AssertionError):
            diary_valid({"final": tampered})

    def test_replays_include_all_actions_receipts_and_values(self):
        first, _ = v.run(2, episodes=100)
        repeated, _ = v.run(2, episodes=100)
        self.assertEqual(sha(first), sha(repeated))
        self.assertTrue(all(type(x) is int for cells in first["final"]["q"].values() for c in cells for x in c))

    def test_viewer_uses_executed_decisions_and_observed_costs(self):
        from observe import render
        row = {"kind": "village_decision", "episode": 7, "agent": "B", "context": "neg",
               "q_values": [-9, -10, -10, -11], "verified": True, "wrote": True,
               "cost": 11, "claims": [], "entry_hash": "receipt"}
        text = "\n".join(render(row))
        self.assertIn("Coste observado: 11", text)
        self.assertIn("verificar True", text)
        self.assertIn(str(row["q_values"]), text)


if __name__ == "__main__":
    unittest.main()
