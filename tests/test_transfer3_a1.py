"""Plan A1: movement-cost calibration. Public development, not a campaign."""
import unittest

from echoai.nexus0.sim3.canon import loads_strict
from echoai.nexus0.transfer3 import calib_a1, policy, screen_a1
from echoai.nexus0.transfer3.body_a1 import (
    BASE_RANGE, TURN_RANGE, CONDITIONS, CostBody, CostSpace, min_cost_between)
from echoai.nexus0.transfer3.planner_a1 import CostPlanner
from echoai.nexus0.transfer3.rehearsal import ROOT

HISTORY = ROOT/'lab/transfer3/rehearsal-v4.json'


class Body(unittest.TestCase):
    def test_turn_term_is_charged_only_on_a_heading_change(self):
        body = CostBody(base=(4, 4, 4, 4), turn=5)
        self.assertEqual(body.step_cost(None, 0), 4)
        self.assertEqual(body.step_cost(0, 0), 4)
        self.assertEqual(body.step_cost(0, 2), 9)

    def test_per_action_costs_alone_are_conservative(self):
        """Two minimum-length routes with the same endpoints cost the same."""
        body = CostBody(base=(2, 6, 3, 5), turn=0)
        self.assertEqual(body.route_cost([0, 0, 2, 2]), body.route_cost([2, 0, 2, 0]))

    def test_the_turn_term_breaks_that_equality(self):
        body = CostBody(base=(2, 6, 3, 5), turn=4)
        self.assertNotEqual(body.route_cost([0, 0, 2, 2]), body.route_cost([2, 0, 2, 0]))

    def test_declared_ranges_are_enforced(self):
        with self.assertRaises(ValueError):
            CostBody(base=(1, 4, 4, 4), turn=0)
        with self.assertRaises(ValueError):
            CostBody(base=(4, 4, 4, 4), turn=TURN_RANGE[1]+1)

    def test_world_charges_what_the_body_declares(self):
        world = CostSpace(20264601, CostBody(base=(4, 4, 4, 4), turn=6))
        first = world.step(0)
        second = world.step(2)
        self.assertEqual(first['cost'], 4)
        self.assertEqual(second['cost'], 10)
        self.assertEqual(world.turns, 1)

    def test_home_cost_is_evaluator_side_and_heading_aware(self):
        world = CostSpace(20264601, CostBody(base=(4, 4, 4, 4), turn=8))
        straight = min_cost_between(world, world.start, world.start, None)
        self.assertEqual(straight, 0)


class Calibration(unittest.TestCase):
    def test_straight_and_turning_observations_separate_the_parameters(self):
        c = calib_a1.Calibration()
        c.observe(None, 0, 3)
        c.observe(0, 0, 3)
        c.observe(0, 2, 9)
        c.observe(2, 2, 4)
        base, turn = c.resolve()
        self.assertEqual(base[0], 3)
        self.assertEqual(base[2], 4)
        self.assertEqual(turn, 5)

    def test_unobserved_parameters_fall_back_to_the_nominal_prior(self):
        base, turn = calib_a1.Calibration().resolve()
        self.assertEqual(base, [calib_a1.NOMINAL_BASE]*4)
        self.assertEqual(turn, calib_a1.NOMINAL_TURN)

    def test_export_carries_only_calibration_and_coverage(self):
        payload = calib_a1.Calibration().export()
        self.assertEqual(set(payload), {'schema', 'base', 'turn', 'samples'})
        calib_a1.validate(payload)

    def test_payload_refuses_out_of_range_or_extra_channels(self):
        payload = calib_a1.nominal()
        with self.assertRaises(ValueError):
            calib_a1.validate(dict(payload, map=[1, 2, 3]))
        with self.assertRaises(ValueError):
            calib_a1.validate(dict(payload, turn=TURN_RANGE[1]+1))
        with self.assertRaises(ValueError):
            calib_a1.validate(dict(payload, base=[BASE_RANGE[0]-1]*4))

    def test_permutation_keeps_the_numbers_and_moves_them(self):
        payload = dict(calib_a1.nominal(), base=[2, 3, 4, 5])
        out = calib_a1.permuted(payload)
        self.assertEqual(sorted(out['base']), sorted(payload['base']))
        self.assertNotEqual(out['base'], payload['base'])
        self.assertEqual(out['turn'], payload['turn'])

    def test_negative_or_zero_observed_cost_is_refused(self):
        with self.assertRaises(ValueError):
            calib_a1.Calibration().observe(None, 0, 0)


class Isolation(unittest.TestCase):
    def test_planner_never_imports_the_simulator(self):
        import echoai.nexus0.transfer3.planner_a1 as module
        from pathlib import Path
        source = Path(module.__file__).read_text()
        for forbidden in ('body_a1 import CostSpace', 'rehearsal_v2 import Space', 'CostSpace'):
            self.assertNotIn(forbidden, source)

    def test_reserve_is_identical_and_declared(self):
        payload = calib_a1.nominal()
        agent = CostPlanner(policy.restore(policy.scratch()).snapshot(), (1, 0, 0), payload)
        self.assertEqual(agent.reserve, 12+2)
        agent = CostPlanner(policy.restore(policy.scratch()).snapshot(), (1, 0, 0), payload,
                            reserve=screen_a1.RESERVE)
        self.assertEqual(agent.reserve, 4)

    def test_calibration_is_frozen_when_not_learning(self):
        payload = dict(calib_a1.nominal(), base=[3, 3, 3, 3], turn=5)
        agent = CostPlanner(policy.restore(policy.scratch()).snapshot(), (1, 0, 0), payload)
        self.assertIsNone(agent.calibration)
        self.assertEqual(agent.frozen(), ([3, 3, 3, 3], 5))


class School(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        history = loads_strict(HISTORY.read_bytes())
        cls.seeds = [r['seed'] for r in history['school_rooms']]

    def test_school_recovers_the_true_costs_in_every_declared_condition(self):
        for name in CONDITIONS:
            body = CostBody.named(name)
            taught = screen_a1.school(self.seeds, body)
            self.assertEqual(calib_a1.error_against(taught['payload'], body)['absolute'], 0, name)

    def test_school_spends_exactly_its_declared_budget(self):
        taught = screen_a1.school(self.seeds, CostBody.named('turn4'))
        self.assertEqual(taught['moves'], screen_a1.SCHOOL_BUDGET)

    def test_school_budget_must_be_spendable(self):
        with self.assertRaises(ValueError):
            screen_a1.school([], CostBody.named('turn4'))
        with self.assertRaises(ValueError):
            screen_a1.school(self.seeds, CostBody.named('turn4'), budget=0)


class Exam(unittest.TestCase):
    def test_calibration_never_changes_during_an_exam(self):
        row = screen_a1.episode(20264601, CostBody.named('turn4'), calib_a1.nominal())
        self.assertTrue(row['calibration_unchanged'])
        self.assertEqual(row['imagined_writes'], 0)

    def test_flat_condition_gives_learning_nothing_to_find(self):
        """Negative control: with turn 0 the learned vector equals the prior."""
        history = loads_strict(HISTORY.read_bytes())
        seeds = [r['seed'] for r in history['school_rooms']]
        taught = screen_a1.school(seeds, CostBody.named('flat'))
        self.assertEqual(taught['payload']['base'], calib_a1.nominal()['base'])
        self.assertEqual(taught['payload']['turn'], calib_a1.nominal()['turn'])

    def test_protocol_declares_no_exam_learning_and_no_campaign(self):
        self.assertFalse(screen_a1.PROTOCOL['learning_in_exam'])
        self.assertFalse(screen_a1.PROTOCOL['campaign_ready'])
        self.assertFalse(screen_a1.PROTOCOL['q_table_used'])
        self.assertEqual(screen_a1.PROTOCOL['ceiling'], 'oracle')
        self.assertNotIn('oracle', screen_a1.PROTOCOL['arms'])


if __name__ == '__main__':
    unittest.main()
