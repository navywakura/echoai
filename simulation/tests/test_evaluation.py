import tempfile
import unittest
from pathlib import Path

from echo5.evaluation import exact_success, paired, source_snapshot, check_sources, audit_grid_rows
from echo5.audit import enforce_grid_contract


class EvaluationTests(unittest.TestCase):
    def test_judge_ignores_claimed_success_and_requires_exact_output(self):
        expected = [[[1, 2], [3, 4]]]
        self.assertFalse(exact_success({'status': 'SOLVED', 'test_verified': True,
                                       'predictions': [[[1, 2], [3, 0]]]}, expected))
        self.assertFalse(exact_success({'status': 'BUDGET_EXHAUSTED', 'predictions': expected}, expected))
        self.assertTrue(exact_success({'status': 'SOLVED', 'predictions': expected}, expected))

    def test_paired_regression_cannot_hide_in_aggregate(self):
        report = paired([True, False, True], [True, True, False])
        self.assertEqual((report['wins'], report['losses'], report['delta']), (1, 1, 0))
        self.assertFalse(report['accuracy_advantage_without_regression'])

    def test_source_snapshot_detects_change_and_addition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'x.py').write_text('x=1\n')
            receipt = source_snapshot(root, ['.'])
            self.assertTrue(check_sources(root, receipt)['unchanged'])
            (root / 'y.py').write_text('y=1\n')
            self.assertFalse(check_sources(root, receipt)['unchanged'])

    def test_auditor_rejects_forged_success(self):
        row = {'id': 'sample', 'condition': 'new_empty', 'expected': [[[2]]],
               'result': {'status': 'SOLVED', 'predictions': [[[1]]]}, 'success': True}
        with self.assertRaises(ValueError):
            audit_grid_rows([row])

    def test_receipts_cannot_change_conditions_seeds_or_budget(self):
        config = dict(conditions=['a', 'b'], families=['rotate'], confirmation_seed=7,
                      confirmation_cases_per_family=1, work_per_case=10)
        rows = [dict(condition=name, family='rotate', seed=7, work={'limit': 10})
                for name in ('a', 'b')]
        enforce_grid_contract(rows, config)
        for key, value in (('condition', 'other'), ('seed', 8), ('work', {'limit': 11})):
            damaged = [dict(row) for row in rows]
            damaged[0][key] = value
            with self.assertRaises(ValueError):
                enforce_grid_contract(damaged, config)
        with self.assertRaises(ValueError):
            enforce_grid_contract(rows[:1], config)


if __name__ == '__main__':
    unittest.main()
