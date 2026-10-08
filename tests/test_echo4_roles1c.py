"""ROLES-C: veto fix, refusal window, relay hypotheses, absence, new member."""
import unittest

from echoai.nexus0.constants import GATE_BLOCK, SLOT_FLAG_INHIBIT
from echoai.echo4 import roles as R
from echoai.echo4.roles_c import RolesCSession, relay_key, RELAY_SOURCE


class VetoFix(unittest.TestCase):
    def test_learner_veto_is_a_noop_not_self_execution(self):
        s = RolesCSession(5, 12, arm="rank_follow")
        f = s.step(veto=(True, False, False))
        self.assertEqual(f["gate"], GATE_BLOCK)
        self.assertEqual((f["executed"], f["paid"]), (False, (0, 0, 0)))
        self.assertEqual(s.ledger, [4096] * 3)
        self.assertTrue(s.invariant())

    def test_nominal_equals_sealed_session(self):
        a, b = R.RolesSession(5, 48), RolesCSession(5, 48)
        for _ in range(48):
            fa, fb = a.step(), b.step()
            fb.pop("absent")
            self.assertEqual(fa, fb)


class Scenarios(unittest.TestCase):
    def test_refusal_window_uses_real_gate_and_is_temporary(self):
        s = RolesCSession(5, 24, arm="rank_follow", claimant=1, declines=(0, 0, 6))
        frames = [s.step() for _ in range(12)]
        self.assertTrue(all(f["accepted"] is False for f in frames[:6]))
        self.assertTrue(all(f["accepted"] is True for f in frames[6:]))
        self.assertEqual(s.declined_rounds, 6)
        partner = s.partners[0]
        self.assertFalse(any(x.flags & SLOT_FLAG_INHIBIT for x in partner.cam.slot if x.occupied))
        self.assertTrue(s.invariant())

    def test_relay_is_hypothesis_with_provenance(self):
        s = RolesCSession(5, 24, arm="rank_follow", relay=True)  # claimant 2 -> action 1
        for _ in range(6):
            s.step()
        relayed = [x for x in s.focal.cam.slot if x.occupied and x.source == RELAY_SOURCE]
        self.assertEqual(len(relayed), 6)
        self.assertTrue(all(not x.has_fact and not x.extract and x.wsp[14] == 1 for x in relayed))
        self.assertEqual(s.memory.receipts(), [])
        self.assertTrue(s.invariant())
        with self.assertRaises(ValueError):
            relay_key(0, 1, 1)

    def test_absence_invents_nothing(self):
        s = RolesCSession(5, 24, arm="rank_follow", absent=(1, 0, 6))
        frames = [s.step() for _ in range(8)]
        self.assertTrue(all(f["absent"] and f["paid"] == (0, 0, 0) for f in frames[:6]))
        self.assertEqual(s.skipped, 6)
        self.assertEqual([r["tick"] for r in s.memory.receipts()], [6, 7])
        self.assertTrue(s.invariant())

    def test_new_member_changes_competence_only_in_simulator(self):
        s = RolesCSession(5, 24, member=(6, 0, 2))
        old = s.partners[0]
        for _ in range(8):
            s.step()
        self.assertIsNot(s.partners[0], old)
        t = s.types[7]
        before = R.competent(s.regimes, 7, t)
        swapped = {0: 2, 2: 0}.get(before, before)
        self.assertEqual(s.competent_now(7, t), swapped)
        self.assertTrue(s.invariant())

    def test_plans_are_strict(self):
        for kwargs in ({"absent": (2, 0, 5)}, {"declines": (0, 5, 3)}, {"member": (5, 1, 1)},
                       {"relay": 1}):
            with self.assertRaises(ValueError):
                RolesCSession(5, 24, **kwargs)


if __name__ == "__main__":
    unittest.main()
