import copy
import unittest

from echo5.budget import Budget, BudgetExceeded
from echo5.cases import make_case, FAMILIES, public_task, validate_witness
from echo5.adversarial import repair, choose_challenge


class CaseTests(unittest.TestCase):
    def test_oracle_is_deterministic_and_private(self):
        a = make_case(177, 'right_recolor', split='development')
        self.assertEqual(a, make_case(177, 'right_recolor', split='development'))
        public = public_task(a)
        self.assertEqual(set(public), {'train', 'test'})
        self.assertEqual(set(public['test'][0]), {'input'})
        public['train'][0]['input'][0][0] = 9
        self.assertNotEqual(public['train'], a['task']['train'])

    def test_all_families_have_executable_witnesses(self):
        for family in FAMILIES:
            for split in ('acquisition', 'confirmation'):
                case = make_case(187, family, split=split)
                budget = Budget(1000000)
                self.assertTrue(validate_witness(case, budget))
                self.assertGreater(budget.used, 0)

    def test_forged_witness_or_answer_is_not_resolvable(self):
        case = make_case(197, 'right_recolor')
        case['expected'][0][0][0] = 7
        self.assertFalse(validate_witness(case, Budget(1000000)))

    def test_easy_challenges_are_solvable_for_every_family(self):
        for family in FAMILIES:
            for seed in range(5):
                case = make_case(seed, family, easy=True)
                self.assertTrue(validate_witness(case, Budget(1000000)), (family, seed))

    def test_generation_costs_are_not_free(self):
        with self.assertRaises(BudgetExceeded):
            make_case(1, FAMILIES[0], budget=Budget(1))


class AdversarialTests(unittest.TestCase):
    def test_repair_rechecks_children_and_retains_counterexample(self):
        case = make_case(10, 'right_recolor')
        wrong = {'steps': [{'op': 'rot90'}]}
        right = case['witness']
        result = repair([wrong, right], [case['task']['train'][0]], Budget(200000))
        self.assertEqual(result['survivors'], [right])
        self.assertEqual(len(result['rejected']), 1)
        self.assertEqual(result['rejected'][0]['reason'], 'observed_mismatch')

    def test_invalid_worlds_cannot_earn_adversarial_credit(self):
        case = make_case(11, 'right_recolor')
        case['expected'][0][0][0] = 7
        chosen = choose_challenge([case], [case['witness']], Budget(1000000), mode='adaptive', seed=1)
        self.assertIsNone(chosen['case'])
        self.assertEqual(chosen['invalid'], 1)

    def test_public_hypothesis_does_not_receive_solution(self):
        case = make_case(12, 'right_recolor')
        before = copy.deepcopy(case)
        choose_challenge([case], [{'steps': [{'op': 'rot90'}]}], Budget(1000000), mode='adaptive', seed=1)
        self.assertEqual(case, before)


if __name__ == '__main__':
    unittest.main()
