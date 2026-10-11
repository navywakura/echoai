import unittest
from copy import deepcopy
from echo5 import search_efficiency_study as study


class StudyTests(unittest.TestCase):
    def test_paired_receipts_and_complete_cohort_required(self):
        cfg = {'seed': 2700000, 'cases_per_family': 1, 'budget': 2000000,
               'families': ['ambiguous_reflection'], 'template_families': [],
               'strategies': list(study.STRATEGIES)}
        report = study.run_benchmark(cfg)
        self.assertEqual(len(report['rows']), 4)
        self.assertEqual({r['result']['status'] for r in report['rows']}, {'ambiguous'})
        self.assertEqual(len({r['case']['public_sha256'] for r in report['rows']}), 1)
        self.assertTrue(report['instrument_valid'])
        bad = deepcopy(report)
        bad['rows'].pop()
        with self.assertRaises(ValueError):
            study.summarize(bad['rows'], cfg)

    def test_no_unregistered_strategy_or_higher_budget(self):
        for update in ({'strategies': ['certified']}, {'budget': 2000001}):
            with self.assertRaises(ValueError):
                study.normalize_config(update)

    def test_template_receipts_keep_original_shape_and_are_scored(self):
        cfg = {'seed': 2400000, 'cases_per_family': 1,
               'families': ['ambiguous_reflection'],
               'template_families': ['fill_extract_tile']}
        report = study.run_benchmark(cfg)
        rows = [r for r in report['rows'] if r['generator'] == 'template']
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r['control_pass'] is None for r in rows))
        self.assertTrue(report['instrument_valid'])


if __name__ == '__main__':
    unittest.main()
