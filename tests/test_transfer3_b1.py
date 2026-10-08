"""Plan B1: actuation gain, burst-aware gate, pre-campaign filter."""
import unittest

from echoai.nexus0.compose1.space import DIRECTIONS
from echoai.nexus0.transfer3 import costs_a2, filter_b1, gain_b1
from echoai.nexus0.transfer3.planner_b1 import GainPlanner, unit


class Body(unittest.TestCase):
    def test_gain_above_one_is_allowed_on_a_single_action_only(self):
        gain_b1.validate_gains((2, 1, 1, 1))
        with self.assertRaises(ValueError):
            gain_b1.validate_gains((2, 2, 1, 1))

    def test_declared_range_is_enforced(self):
        with self.assertRaises(ValueError):
            gain_b1.validate_gains((5, 1, 1, 1))
        with self.assertRaises(ValueError):
            gain_b1.validate_gains((0, 1, 1, 1))

    def test_every_declared_condition_is_valid(self):
        for gains in gain_b1.CONDITIONS.values():
            gain_b1.validate_gains(gains)

    def test_a_burst_covers_several_cells_for_one_actuation(self):
        """Rooms are rotated, so look for a seed where the gain action is free."""
        body = gain_b1.declared_body()
        for seed in range(filter_b1.ROOM_SEED, filter_b1.ROOM_SEED+40):
            room = gain_b1.GainRoom(seed, body, (2, 1, 1, 1))
            start = room.pos
            out = room.step(0)
            if out['cells'] == 2:
                self.assertEqual(out['cost'], costs_a2.NOMINAL_BASE)
                self.assertEqual(sum(abs(a-b) for a, b in zip(room.pos, start)), 2)
                return
        self.fail('no room let the gain action complete a burst')

    def test_a_burst_stops_before_an_obstacle_instead_of_colliding(self):
        body = gain_b1.declared_body()
        for seed in range(filter_b1.ROOM_SEED, filter_b1.ROOM_SEED+40):
            room = gain_b1.GainRoom(seed, body, (3, 1, 1, 1))
            for _ in range(12):
                out = room.step(0)
                self.assertLessEqual(out['cells'], 3)
                if out['blocked']:
                    self.assertEqual(out['cells'], 0)
            self.assertNotIn(room.pos, room.solids)

    def test_the_body_never_leaves_the_domain(self):
        room = gain_b1.GainRoom(filter_b1.ROOM_SEED, gain_b1.declared_body(), (3, 1, 1, 1))
        for action in (0, 0, 0, 2, 2, 1, 3, 0):
            room.step(action)
            self.assertIn(room.pos, room.domain)


class Planner(unittest.TestCase):
    def agent(self, believed):
        room = gain_b1.GainRoom(filter_b1.ROOM_SEED, gain_b1.declared_body(), (1, 1, 1, 1))
        agent = GainPlanner(gain_b1.programmed(believed), room.goal,
                            costs_a2.nominal(), reserve=filter_b1.RESERVE)
        agent.update(room.scan())
        return agent

    def test_believed_reach_reads_the_model_not_the_world(self):
        self.assertEqual(self.agent((1, 1, 1, 1)).believed_reach(), 1)
        self.assertEqual(self.agent((3, 1, 1, 1)).believed_reach(), 3)

    def test_reserve_per_cell_follows_the_believed_reach(self):
        self.assertEqual(self.agent((1, 1, 1, 1)).per_cell_reserve(), filter_b1.RESERVE)
        self.assertEqual(self.agent((2, 1, 1, 1)).per_cell_reserve(), 3)
        self.assertEqual(self.agent((3, 1, 1, 1)).per_cell_reserve(), 2)

    def test_the_rule_is_shared_and_only_the_belief_differs(self):
        one, three = self.agent((1, 1, 1, 1)), self.agent((3, 1, 1, 1))
        self.assertEqual(type(one), type(three))
        self.assertEqual(one.reserve, three.reserve)
        self.assertNotEqual(one.per_cell_reserve(), three.per_cell_reserve())

    def test_unit_reduces_a_burst_to_its_direction(self):
        self.assertEqual(unit((3, 0, 0)), (1, 0, 0))
        self.assertEqual(unit((0, -2, 0)), (0, -1, 0))

    def test_the_gate_checks_every_cell_a_burst_traverses(self):
        agent = self.agent((3, 1, 1, 1))
        agent.beliefs = {}
        agent.free = lambda p: p != tuple(a+b for a, b in zip(agent.pos, DIRECTIONS[0]))
        self.assertFalse(agent.free_path(agent.pos, (3, 0, 0)))


class Filter(unittest.TestCase):
    def test_the_oracle_is_declared_an_upper_bound(self):
        self.assertTrue(filter_b1.PROTOCOL['oracle_is_an_upper_bound_on_any_learner'])
        self.assertFalse(filter_b1.PROTOCOL['campaign_ready'])
        self.assertFalse(filter_b1.PROTOCOL['school'])

    def test_beliefs_bracket_the_truth(self):
        beliefs = filter_b1.beliefs_for((2, 1, 1, 1))
        self.assertEqual(beliefs['oracle'], (2, 1, 1, 1))
        self.assertEqual(beliefs['nominal'], (1, 1, 1, 1))
        self.assertGreater(beliefs['over'][0], 2)
        self.assertLess(beliefs['under'][0], 2)

    def test_on_the_flat_condition_oracle_and_nominal_are_the_same_belief(self):
        beliefs = filter_b1.beliefs_for((1, 1, 1, 1))
        self.assertEqual(beliefs['oracle'], beliefs['nominal'])

    def test_audit_refuses_a_report_without_the_filter_field(self):
        with self.assertRaises(ValueError):
            filter_b1.audit({'conditions': {}})


if __name__ == '__main__':
    unittest.main()
