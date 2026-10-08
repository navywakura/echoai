"""V7: coverage/conflict curve over school budget. Diagnostic, not selection."""
import unittest

from echoai.nexus0.sim3.canon import loads_strict
from echoai.nexus0.transfer3 import curve_v7, school_v6
from echoai.nexus0.transfer3 import rehearsal_v4
from echoai.nexus0.transfer3.rehearsal import ROOT

HISTORY = ROOT/'lab/transfer3/rehearsal-v4.json'


class Conflict(unittest.TestCase):
    def test_opposite_returns_on_one_pair_are_a_conflict(self):
        out = curve_v7.conflict({'aa': [[7, -9], [], [], []]})
        self.assertEqual(out['conflicting_pairs'], 1)
        self.assertEqual(out['conflicting_features'], 1)

    def test_agreeing_returns_are_not_a_conflict(self):
        out = curve_v7.conflict({'aa': [[7, 7, 39], [-9, -9], [], []]})
        self.assertEqual(out['conflicting_pairs'], 0)

    def test_blocked_return_alone_is_not_a_conflict(self):
        out = curve_v7.conflict({'aa': [[7, -1], [], [], []]})
        self.assertEqual(out['conflicting_pairs'], 0)

    def test_conflict_is_counted_per_pair_not_per_feature(self):
        out = curve_v7.conflict({'aa': [[7, -9], [39, -9], [], []]})
        self.assertEqual(out['conflicting_pairs'], 2)
        self.assertEqual(out['conflicting_features'], 1)

    def test_observed_pairs_counts_only_sampled_actions(self):
        self.assertEqual(curve_v7.conflict({'aa': [[7], [], [-9], []]})['observed_pairs'], 2)


class Coverage(unittest.TestCase):
    def test_counts_sampled_pairs_and_capacity(self):
        out = curve_v7.coverage({'aa': [3, 0, 0, 0], 'bb': [1, 2, 0, 0]})
        self.assertEqual(out['features'], 2)
        self.assertEqual(out['sampled_pairs'], 3)
        self.assertEqual(out['possible_pairs'], 8)
        self.assertEqual(out['one_action_features'], 1)
        self.assertEqual(out['samples'], 6)


class TracedSchool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        history = loads_strict(HISTORY.read_bytes())
        cls.seeds = [r['seed'] for r in history['school_rooms']]
        cls.traced = curve_v7.train_traced(cls.seeds, 128)

    def test_registered_prediction_traced_school_is_the_v6_school(self):
        self.assertEqual(self.traced['payload'],
                         school_v6.train(self.seeds, 128)['payload'])

    def test_spends_exactly_its_budget(self):
        self.assertEqual(self.traced['moves'], 128)
        self.assertEqual(sum(sum(r) for r in self.traced['counts'].values()), 128)

    def test_one_return_is_recorded_per_executed_move(self):
        recorded = sum(len(o) for actions in self.traced['returns'].values() for o in actions)
        self.assertEqual(recorded, 128)

    def test_returns_and_counts_agree_pair_by_pair(self):
        for feature, actions in self.traced['returns'].items():
            for action, observed in enumerate(actions):
                self.assertEqual(len(observed), self.traced['counts'][feature][action])

    def test_failure_bonus_does_not_contaminate_these_rooms(self):
        self.assertEqual(self.traced['failure_bonus_applied'], 0)

    def test_budget_must_be_spendable(self):
        with self.assertRaises(ValueError):
            curve_v7.train_traced(self.seeds, 0)


class Harness(unittest.TestCase):
    def test_criterion_is_imported_not_copied(self):
        self.assertIs(curve_v7.screen, rehearsal_v4.screen)

    def test_protocol_declares_the_tests_are_not_independent(self):
        self.assertFalse(curve_v7.PROTOCOL['independent_tests'])
        self.assertFalse(curve_v7.PROTOCOL['learning_in_exam'])
        self.assertFalse(curve_v7.PROTOCOL['campaign_ready'])

    def test_budgets_are_increasing(self):
        budgets = curve_v7.PROTOCOL['budgets']
        self.assertEqual(budgets, sorted(set(budgets)))
        self.assertIn(rehearsal_v4.PROTOCOL['budget'], budgets)

    def test_audit_refuses_a_report_without_isolation_field(self):
        with self.assertRaises(ValueError):
            curve_v7.audit({'isolated': 1})


if __name__ == '__main__':
    unittest.main()
