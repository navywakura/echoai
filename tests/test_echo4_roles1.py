"""ROLES-1 A/B: physics, receipts, rank claims as hypotheses, rows, veto, limits."""
import unittest
from unittest.mock import patch

from echoai.core.cam import Cam
from echoai.nexus0.constants import GATE_BLOCK
from echoai.echo4 import roles as R
from echoai.echo4 import roles_bench as bench


def receipt(tick, task=0, assignee=0, executed=True, output=9):
    paid = (R.SELF_COST if assignee == R.SELF else R.DELEGATE[0]) if (executed or assignee != R.SELF) else 0
    return {"tick": tick, "type": task, "assignee": assignee, "executed": executed,
            "paid": paid, "output": output if executed else 0}


class Physics(unittest.TestCase):
    def test_declared_payoffs(self):
        e = R.settle(0, True, True, (10, 10, 10))
        self.assertEqual((e["paid"], e["output"]), ((1, 2, 0), (9, 0, 0)))
        e = R.settle(1, True, False, (10, 10, 10))
        self.assertEqual((e["paid"], e["output"]), ((1, 0, 2), (0, 0, 0)))
        e = R.settle(0, False, True, (10, 10, 10))
        self.assertEqual((e["executed"], e["paid"], e["net"]), (False, (1, 0, 0), (-1, 0, 0)))
        self.assertEqual(R.settle(2, None, True, (10, 10, 10))["net"], (7, 0, 0))
        self.assertEqual(R.settle(2, None, False, (10, 10, 10))["net"], (-2, 0, 0))

    def test_incapable_is_neither_cost_nor_gift(self):
        self.assertEqual(R.settle(2, None, True, (1, 9, 9))["paid"], (0, 0, 0))
        self.assertEqual(R.settle(0, None, True, (0, 9, 9))["paid"], (0, 0, 0))
        e = R.settle(0, True, True, (9, 1, 9))
        self.assertEqual((e["executed"], e["output"], e["incapable"]), (False, (0, 0, 0), (False, True, False)))

    def test_strict_types(self):
        for bad in ((True, None, True, (1, 1, 1)), (2, True, True, (5, 5, 5)), (0, None, True, (5, 5, 5)),
                    (0, True, 1, (5, 5, 5)), (0, True, True, [5, 5, 5])):
            with self.assertRaises(ValueError):
                R.settle(*bad)
        with self.assertRaises(ValueError):
            R.row("elder", 0, 5)
        with self.assertRaises(ValueError):
            R.row("cumulative", 0, 5, evidence=5)

    def test_schedule_balanced_with_real_drift(self):
        types, regimes = R.schedule(9, 384)
        self.assertEqual([types.count(t) for t in range(3)], [128] * 3)
        self.assertEqual(len(regimes), 4)
        for a, b in zip(regimes, regimes[1:]):
            self.assertGreaterEqual(sum(x != y for x, y in zip(a, b)), 2)
            self.assertEqual(sorted(a), [0, 1, 2])


class Receipts(unittest.TestCase):
    def test_receipts_are_canonical_facts(self):
        m = R.RoleMemory(Cam())
        m.record(receipt(0))
        m.record(receipt(3, 1, 2, True, 0))
        self.assertEqual([r["tick"] for r in m.receipts()], [0, 3])
        self.assertTrue(m.invariant())
        for bad in (receipt(3), receipt(2), {**receipt(5), "output": 4}, {**receipt(6), "extra": 1}):
            with self.assertRaises(ValueError):
                m.record(bad)

    def test_rank_claim_is_a_hypothesis_not_a_fact(self):
        m = R.RoleMemory(Cam())
        m.claim(0, 2)
        slot = m.cam.get(R.claim_key(0, 2))
        self.assertFalse(m.cam.slot[slot].has_fact)
        self.assertEqual(m.cam.slot[slot].extract, "")
        self.assertEqual(m.claimants(), {2})
        self.assertEqual(m.receipts(), [])
        m.cam.slot[slot].has_fact = 1
        self.assertFalse(m.invariant())

    def test_corrupt_receipt_rejected(self):
        # Structural validation only: a forged receipt that is canonical AND
        # physically possible (9 -> 0) is NOT detectable; no crypto is claimed.
        for old, new in (('"output":9', '"output":4'), ('"output":9', '"output": 9')):
            m = R.RoleMemory(Cam())
            m.record(receipt(0))
            slot = m.cam.get(R.receipt_key(0))
            m.cam.slot[slot].extract = m.cam.slot[slot].extract.replace(old, new)
            with self.assertRaises(ValueError):
                m.receipts()

    def test_evidence_functions(self):
        rows = [receipt(0, 0, 1), receipt(1, 0, 1, True, 0), receipt(2, 1, 2), receipt(3, 0, 0, False)]
        self.assertEqual(R.last_attempt(rows, 0), 1 + 3)   # last executed at type 0 failed
        self.assertEqual(R.last_attempt(rows, 1), 2)
        self.assertEqual(R.last_attempt(rows, 2), R.NO_ATTEMPT)
        self.assertEqual(R.cumulative_success(rows, 0), 1)
        self.assertEqual(R.cumulative_success(rows, 2), R.UNKNOWN)
        tie = [receipt(0, 0, 0), receipt(1, 0, 1)]
        self.assertEqual(R.cumulative_success(tie, 0), R.UNKNOWN)

    def test_rows_wsp16_and_competence_is_type_free(self):
        a = R.row("competence", 0, 4096, evidence=1)
        self.assertEqual(len(a), 16)
        self.assertEqual(a[10:14], bytes((0, 9, 8, R.ROW_STYLE)))
        self.assertEqual(a, R.row("competence", 2, 4096, evidence=1))
        self.assertNotEqual(R.row("static_role", 0, 4096), R.row("static_role", 2, 4096))


class Session(unittest.TestCase):
    def test_nominal_run_invariants_and_replay(self):
        life = bench.execute(5, "competence", rounds=96)
        self.assertTrue(all(life["checks"].values()))

    def test_claims_never_enter_competence_rows(self):
        s = R.RolesSession(5, 48, arm="competence")
        frames = [s.step() for _ in range(48)]
        receipts = s.memory.receipts()
        for f in frames:
            prior = [r for r in receipts if r["tick"] < f["tick"]]
            self.assertEqual(f["evidence"], R.last_attempt(prior, f["type"]))
        rows = [x for x in s.focal.cam.slot if x.occupied and x.source in (R.ROW_SOURCE, R.CLAIM_SOURCE)]
        self.assertTrue(all(not x.has_fact and not x.extract for x in rows))

    def test_rank_follow_is_fixed(self):
        s = R.RolesSession(5, 12, arm="rank_follow", claimant=1)
        self.assertTrue(all(s.step()["assignee"] == 0 for _ in range(12)))

    def test_learner_veto_blocks(self):
        s = R.RolesSession(5, 12, arm="rank_follow")
        f = s.step(veto=(True, False, False))
        self.assertEqual((f["gate"], f["assignee"]), (GATE_BLOCK, R.SELF))

    def test_counterpart_veto_uses_its_gate(self):
        s = R.RolesSession(5, 12, arm="rank_follow")
        f = s.step(veto=(False, False, True))
        self.assertEqual((f["accepted"], f["executed"], f["paid"]), (False, False, (1, 0, 0)))
        self.assertEqual(s.partners[1].last_gate_decision, GATE_BLOCK)
        self.assertTrue(s.invariant())

    def test_exhausted_budget(self):
        s = R.RolesSession(5, 12, arm="self_only", resources=(1, 4096, 4096))
        f = s.step()
        self.assertEqual((f["executed"], f["paid"], f["incapable"][0]), (False, (0, 0, 0), True))

    def test_failure_after_execution_stops(self):
        s = R.RolesSession(5, 12, arm="self_only")
        with patch.object(R.RoleMemory, "record", side_effect=RuntimeError("journal lost")):
            with self.assertRaises(RuntimeError):
                s.step()
        self.assertTrue(s.failed and s.stopped)
        self.assertEqual(s.ledger[0], 4096 - R.SELF_COST)  # executed cost kept, not rolled back
        with self.assertRaises(RuntimeError):
            s.step()

    def test_deterministic(self):
        self.assertEqual(bench.execute(5, "competence", rounds=48)["digest"],
                         bench.execute(5, "competence", rounds=48)["digest"])

    def test_isolated_memories(self):
        s = R.RolesSession(5, 12)
        ids = {id(a.cam) for a in s.all_agents} | {id(a.q) for a in s.all_agents}
        self.assertEqual(len(ids), 6)


if __name__ == "__main__":
    unittest.main()
