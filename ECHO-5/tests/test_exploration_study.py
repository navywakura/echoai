import unittest
from echo5.exploration_study import case_specs, normalize_config, paired_summary, summarize


class ExplorationStudyTests(unittest.TestCase):
    def test_pairing_shares_native_task_and_budget_not_mode(self):
        rows = case_specs({'cases_per_profile': 1})
        for i in range(0, len(rows), 3):
            normalized = [{k:v for k,v in row['spec'].items() if k != 'mode'} for row in rows[i:i+3]]
            self.assertEqual(normalized[0], normalized[1])
            self.assertEqual(normalized[0], normalized[2])
            self.assertIsNone(normalized[0]['mission'])

    def test_statistics_do_not_treat_ties_as_certainty(self):
        result = paired_summary([True]*4, [True]*4)
        self.assertEqual(result['discordance_exact_p_two_sided'], 1.)
        self.assertLess(result['difference_interval'][0], 0.)
        self.assertGreater(result['difference_interval'][1], 0.)
        one = paired_summary([False]*8, [True]*8)
        self.assertEqual(one['wins'], 8)
        self.assertEqual(one['discordance_exact_p_two_sided'], 2/256)

    def test_missing_pair_duplicate_or_confirmation_rejected(self):
        config = {'cases_per_profile': 1, 'profiles': ['objects_small']}
        rows = [{'id': c['id'], 'profile': c['profile'], 'mode': c['spec']['mode'],
                 'success': False, 'work': 100, 'actions': 2, 'status': 'action_limit'} for c in case_specs(config)]
        self.assertTrue(summarize(rows, config)['complete_pairs'])
        for broken in (rows[:-1], rows + [rows[0]]):
            with self.assertRaises(ValueError):
                summarize(broken, config)
        with self.assertRaises(ValueError):
            normalize_config({'confirmation': True})
