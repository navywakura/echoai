"""ARCH-1: bounded plan commitment. Gates must survive the commitment."""
import unittest

from echoai.nexus0.transfer3 import costs_a2, filter_arch1, gain_b1
from echoai.nexus0.transfer3.planner_arch1 import COMMITMENT_RANGE, CommittedPlanner
from echoai.nexus0.transfer3.planner_b1 import GainPlanner


def agent(commitment, believed=(1, 1, 1, 1), seed=filter_arch1.ROOM_SEED):
    room = gain_b1.GainRoom(seed, gain_b1.declared_body(), (1, 1, 1, 1))
    planner = CommittedPlanner(gain_b1.programmed(believed), room.goal,
                               costs_a2.nominal(), reserve=filter_arch1.RESERVE,
                               commitment=commitment)
    return room, planner


class Commitment(unittest.TestCase):
    def test_declared_range_is_enforced(self):
        with self.assertRaises(ValueError):
            agent(0)
        with self.assertRaises(ValueError):
            agent(COMMITMENT_RANGE[1]+1)

    def test_commitment_one_keeps_nothing(self):
        room, planner = agent(1)
        for _ in range(8):
            decision = planner.decide(room.scan())
            self.assertEqual(planner.committed, [])
            if decision['status'] not in ('moving', 'returning'):
                break
            room.step(bytes.fromhex(decision['wsp'])[13])

    def test_a_longer_commitment_actually_keeps_actions(self):
        room, planner = agent(4)
        kept = 0
        for _ in range(20):
            decision = planner.decide(room.scan())
            if decision['status'] not in ('moving', 'returning'):
                break
            room.step(bytes.fromhex(decision['wsp'])[13])
            kept = max(kept, planner.commitments_kept)
        self.assertGreater(kept, 0)

    def test_commitment_one_reproduces_the_historical_planner(self):
        """Same rooms, same body: one-step commitment must match GainPlanner."""
        body = gain_b1.declared_body()
        for seed in range(filter_arch1.ROOM_SEED, filter_arch1.ROOM_SEED+6):
            traces = []
            for factory in (GainPlanner, lambda *a, **k: CommittedPlanner(*a, commitment=1, **k)):
                room = gain_b1.GainRoom(seed, body, (1, 1, 1, 1))
                planner = factory(gain_b1.programmed((1, 1, 1, 1)), room.goal,
                                  costs_a2.nominal(), reserve=filter_arch1.RESERVE)
                trace = []
                for _ in range(40):
                    decision = planner.decide(room.scan())
                    trace.append(decision['status'])
                    if decision['status'] not in ('moving', 'returning'):
                        break
                    action = bytes.fromhex(decision['wsp'])[13]
                    trace.append(action)
                    room.step(action)
                traces.append(trace)
            self.assertEqual(traces[0], traces[1], seed)

    def test_a_derailed_plan_is_abandoned(self):
        """Believing gain 1 in a gain-3 world derails every committed plan."""
        room = gain_b1.GainRoom(filter_arch1.ROOM_SEED, gain_b1.declared_body(),
                                (3, 1, 1, 1), aligned=True)
        planner = CommittedPlanner(gain_b1.programmed((1, 1, 1, 1)), room.goal,
                                   costs_a2.nominal(), reserve=filter_arch1.RESERVE,
                                   commitment=4)
        for _ in range(30):
            decision = planner.decide(room.scan())
            if decision['status'] not in ('moving', 'returning'):
                break
            room.step(bytes.fromhex(decision['wsp'])[13])
        self.assertGreater(planner.commitments_derailed, 0)
        self.assertEqual(planner.committed, [])

    def test_an_exact_model_does_not_derail(self):
        room = gain_b1.GainRoom(filter_arch1.ROOM_SEED, gain_b1.declared_body(),
                                (3, 1, 1, 1), aligned=True)
        planner = CommittedPlanner(gain_b1.programmed((3, 1, 1, 1)), room.goal,
                                   costs_a2.nominal(), reserve=filter_arch1.RESERVE,
                                   commitment=4)
        for _ in range(30):
            decision = planner.decide(room.scan())
            if decision['status'] not in ('moving', 'returning'):
                break
            room.step(bytes.fromhex(decision['wsp'])[13])
        self.assertEqual(planner.commitments_derailed, 0)


class Gates(unittest.TestCase):
    def test_a_committed_action_still_passes_the_burst_gate(self):
        room, planner = agent(4, believed=(3, 1, 1, 1))
        planner.decide(room.scan())
        planner.committed = [0, 0, 0]
        planner.free_path = lambda node, delta: False
        decision = planner.decide(room.scan())
        self.assertIn(decision['status'], ('access_not_found', 'evidence_block',
                                           'returning', 'abandoned_at_home'))

    def test_returning_drops_any_commitment(self):
        room, planner = agent(4)
        planner.decide(room.scan())
        planner.committed = [0, 0, 0]
        planner.returning = True
        planner.decide(room.scan())
        self.assertEqual(planner.committed, [])

    def test_no_collisions_are_produced_at_any_commitment(self):
        body = gain_b1.declared_body()
        for commitment in filter_arch1.COMMITMENTS:
            room = gain_b1.GainRoom(filter_arch1.ROOM_SEED, body, (2, 1, 1, 1), aligned=True)
            planner = CommittedPlanner(gain_b1.programmed((2, 1, 1, 1)), room.goal,
                                       costs_a2.nominal(), reserve=filter_arch1.RESERVE,
                                       commitment=commitment)
            for _ in range(40):
                decision = planner.decide(room.scan())
                if decision['status'] not in ('moving', 'returning'):
                    break
                room.step(bytes.fromhex(decision['wsp'])[13])
            self.assertEqual(room.collisions, 0, commitment)


class Protocol(unittest.TestCase):
    def test_retraction_rule_is_declared(self):
        self.assertIn('retracts', filter_arch1.PROTOCOL['retraction_rule'])
        self.assertTrue(filter_arch1.PROTOCOL['gates_applied_to_committed_actions'])
        self.assertTrue(filter_arch1.PROTOCOL['derailed_plans_are_abandoned'])
        self.assertTrue(filter_arch1.PROTOCOL['commitment_one_reproduces_history'])

    def test_it_is_a_filter_not_a_campaign(self):
        self.assertFalse(filter_arch1.PROTOCOL['school'])
        self.assertFalse(filter_arch1.PROTOCOL['campaign_ready'])
        self.assertIn(1, filter_arch1.COMMITMENTS)

    def test_audit_refuses_a_report_without_the_verdict_field(self):
        with self.assertRaises(ValueError):
            filter_arch1.audit({'conditions': {}})


if __name__ == '__main__':
    unittest.main()
