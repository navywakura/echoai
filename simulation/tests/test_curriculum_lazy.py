"""Small development-only regressions; no campaign or artifact access."""

import copy
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from echo5 import curriculum as old
from echo5.budget import Budget, BudgetExceeded

if importlib.util.find_spec('echo5.curriculum_lazy') is None:
    lazy = None
else:
    from echo5 import curriculum_lazy as lazy


def scene(seed, holdout=False):
    return old._scene(seed, holdout=holdout, budget=Budget(100_000))


@lru_cache(maxsize=1)
def small_report():
    return lazy.run_benchmark(seed=14011, runs=1, acquisition_steps=2,
                              budget=20_000_000)


class LazyCurriculumTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(lazy, 'the authorized lazy curriculum module is missing')
        self.hypotheses = old.grammar()
        self.ids = tuple(old.program_id(h) for h in self.hypotheses)

    def table(self, challenges):
        return lazy._LazyTable(challenges, self.hypotheses, self.ids)

    def assertLedger(self, ledger):
        self.assertEqual(ledger['used'], sum(ledger['counts'].values()))
        self.assertTrue(all(type(n) is int and n >= 0 for n in ledger['counts'].values()))

    def test_controls_do_not_execute_unused_candidates(self):
        pool = (scene(101), scene(102), scene(103))
        for mode in ('sequential', 'random'):
            with self.subTest(mode=mode):
                work = Budget(5_000_000)
                view = self.table(pool).view(work)
                calls = []
                executor = old.execute

                def observe(program, rows, *, budget):
                    calls.append(rows)
                    return executor(program, rows, budget=budget)

                with patch.object(old, 'execute', side_effect=observe):
                    index, scores = old.choose_challenge(
                        view, tuple(range(16)), work, mode=mode, rng=random.Random(71))
                    self.assertEqual(calls, [])
                    truth = old._oracle(pool[index].input, self.hypotheses[0])
                    survivors, compatible = old._learn(view, index, truth, list(range(16)), work)
                self.assertEqual(len(calls), 16)
                self.assertEqual(set(calls), {pool[index].input})
                self.assertIsNone(scores)
                self.assertIn(0, survivors)
                self.assertEqual(survivors, compatible)
                self.assertEqual(work.counts['hypothesis_executions'], 16)

    def test_adaptive_pays_for_every_consulted_prediction_and_reuses_it(self):
        pool = (scene(201), scene(202), scene(203))
        for survivors in (list(range(16)), [0, 4]):
            with self.subTest(survivors=survivors):
                table = self.table(pool)
                selection, update = Budget(5_000_000), Budget(5_000_000)
                index, scores = old.choose_challenge(
                    table.view(selection), survivors, selection, mode='adaptive')
                self.assertEqual(selection.counts['hypothesis_executions'], 3 * len(survivors))
                self.assertEqual(selection.counts['selection_prediction_reads'], 3 * len(survivors))
                self.assertEqual(len(scores), 3)
                truth = old._oracle(pool[index].input, self.hypotheses[0])
                old._learn(table.view(update), index, truth, survivors, update)
                self.assertEqual(update.counts.get('hypothesis_executions', 0), 16 - len(survivors))
                self.assertEqual(update.counts['evidence_hypothesis_comparisons'], 16)
                self.assertEqual(update.counts['evidence_cells'], 16 * 225)

    def test_exhaustive_lazy_access_has_the_old_outputs_and_entire_execution_ledger(self):
        pool = (scene(301), scene(302, holdout=True))
        eager_work, lazy_work = Budget(5_000_000), Budget(5_000_000)
        eager = old.prediction_table(pool, self.hypotheses, eager_work)
        view = self.table(pool).view(lazy_work)
        self.assertEqual(lazy_work.used, 0)
        self.assertEqual(tuple(tuple(row) for row in view.predictions), eager.predictions)
        self.assertEqual(tuple(tuple(row) for row in view.fingerprints), eager.fingerprints)
        actual = dict(lazy_work.counts)
        self.assertEqual(actual.pop('prediction_cache_lookups'), 64)
        self.assertEqual(actual.pop('prediction_cache_stores'), 32)
        self.assertEqual(actual, eager_work.counts)
        self.assertEqual(lazy_work.used, eager_work.used + 96)

    def test_cache_is_private_and_failed_executions_are_charged(self):
        pool = (scene(401),)
        programs = [{'steps': [{'op': 'invalid'}]}]
        for _ in range(2):
            work = Budget(100_000)
            table = lazy._LazyTable(pool, programs, ('invalid',))
            view = table.view(work)
            self.assertIsNone(view.predictions[0][0])
            self.assertIsNone(view.predictions[0][0])
            self.assertEqual(work.counts['hypothesis_executions'], 1)
            self.assertGreater(work.counts['program_nodes'], 0)
            self.assertEqual(work.counts['prediction_fingerprint_cells'], 1)

    def test_lazy_acquisition_preserves_old_selections_evidence_and_answers(self):
        pools = ((scene(501), scene(502)), (scene(503), scene(504)))
        query = (scene(505, holdout=True),)
        eager_pools = [old.prediction_table(p, self.hypotheses, Budget(5_000_000)) for p in pools]
        eager_query = old.prediction_table(query, self.hypotheses, Budget(5_000_000))
        for witness_index in (0, 5, 10, 15):
            witness = self.hypotheses[witness_index]
            for mode in old.CONDITIONS:
                with self.subTest(witness=witness_index, mode=mode):
                    a, b = list(range(16)), list(range(16))
                    eager_rng, lazy_rng = random.Random(17), random.Random(17)
                    lazy_query = self.table(query)
                    for pool, eager in zip(pools, eager_pools):
                        work_a, work_b = Budget(5_000_000), Budget(5_000_000)
                        view = self.table(pool).view(work_b)
                        ia, sa = old.choose_challenge(eager, a, work_a, mode=mode, rng=eager_rng)
                        ib, sb = old.choose_challenge(view, b, work_b, mode=mode, rng=lazy_rng)
                        self.assertEqual((ia, sa), (ib, sb))
                        truth = old._oracle(pool[ia].input, witness)
                        a, ca = old._learn(eager, ia, truth, a, work_a)
                        b, cb = old._learn(view, ib, truth, b, work_b)
                        self.assertEqual((a, ca), (b, cb))
                        self.assertIn(witness_index, b)
                        expected = old._predict(eager_query, 0, a, work_a)
                        actual = old._predict(lazy_query.view(work_b), 0, b, work_b)
                        self.assertEqual(actual, expected)
                        if actual['status'] == 'solved':
                            self.assertTrue(old.exact_success(actual, [old._oracle(query[0].input, witness)]))

    def test_report_has_matched_tasks_opportunities_and_additive_phase_costs(self):
        report = small_report()
        self.assertEqual(json.loads(json.dumps(report, allow_nan=False)), report)
        self.assertEqual(len(report['results']), 3)
        task_ids = [r['task_ids'] for r in report['results']]
        self.assertTrue(all(ids == task_ids[0] for ids in task_ids))
        for result in report['results']:
            with self.subTest(condition=result['condition']):
                self.assertEqual(result['hypothesis_ids'], list(self.ids))
                self.assertEqual(result['opportunities']['teacher_queries'], 2)
                self.assertEqual(result['opportunities']['evidence_hypothesis_comparisons'], 32)
                self.assertEqual(result['opportunities']['evaluation_predictions'], 16)
                self.assertEqual(result['opportunities']['external_adjudications'], 16)
                cost = result['cost']
                for ledger in cost.values():
                    self.assertLedger(ledger)
                learning = old._add_work(*(cost[name] for name in ('preparation', 'selection', 'acquisition', 'update')))
                self.assertEqual(cost['learning'], learning)
                self.assertEqual(cost['total'], old._add_work(learning, cost['heldout_evaluation']))
                self.assertLessEqual(cost['total']['used'], report['config']['budget'])
                self.assertEqual(cost['preparation']['counts'].get('hypothesis_executions', 0), 0)
                self.assertEqual(cost['acquisition']['counts']['witness_executions'], 2)
                executed = sum(cost[name]['counts'].get('hypothesis_executions', 0)
                               for name in ('selection', 'update'))
                if result['condition'] == 'adaptive':
                    consulted = sum(6 * len(step['before']) for step in result['archive'])
                    self.assertEqual(cost['selection']['counts']['hypothesis_executions'], consulted)
                    self.assertEqual(executed, sum(6 * len(s['before']) + 16 - len(s['before'])
                                                   for s in result['archive']))
                else:
                    self.assertEqual(executed, 32)
                    self.assertEqual(cost['selection']['counts'].get('hypothesis_executions', 0), 0)
                live_first = len(result['prefixes'][0]['survivors'])
                self.assertEqual(cost['heldout_evaluation']['counts']['hypothesis_executions'], 8 * live_first)
                self.assertTrue(all(not row['result']['test_verified']
                                    for prefix in result['prefixes'] for row in prefix['evaluations']))

    def test_physical_cost_counts_shared_work_once_and_audit_separately(self):
        report = small_report()
        cost = report['cost']
        actual = old._add_work(cost['shared_preparation'], cost['shared_heldout_evaluation'],
                               *(r['cost']['exclusive'] for r in report['results']))
        self.assertEqual(cost['physical_protocol'], actual)
        self.assertEqual(cost['physical_with_audit'], old._add_work(actual, cost['audit_overhead']))
        self.assertEqual(cost['audit_overhead']['counts']['witness_executions'], 20)
        self.assertEqual(report['audit']['verified_challenges'], 20)
        self.assertFalse(report['audit']['independent_replay_performed'])
        self.assertEqual(cost['shared_heldout_evaluation']['counts'].get('hypothesis_executions', 0), 0)

    def test_pairs_and_families_keep_cost_penalties_and_missing_coverage(self):
        report = small_report()
        by_mode = {r['condition']: r for r in report['results']}
        self.assertEqual(len(report['perfamily']), 16)
        self.assertEqual(sum(f['paired_runs'] for f in report['perfamily'].values()), 1)
        self.assertTrue(any(f['paired_runs'] == 0 for f in report['perfamily'].values()))
        for control in ('random', 'sequential'):
            comparison = report['pairs']['adaptive_vs_' + control]
            self.assertEqual(comparison['paired_runs'], 1)
            delta = by_mode['adaptive']['cost']['learning']['used'] - by_mode[control]['cost']['learning']['used']
            self.assertEqual(comparison['run_pairs'][0]['learning_cost_delta'], delta)
            self.assertEqual(comparison['mean_learning_cost_delta'], delta)
            self.assertEqual(comparison['unit'], 'independent_acquisition_run')
            self.assertGreater(delta, 0)
        self.assertFalse(report['promotion'])

    def test_benchmark_never_reads_old_contracts_or_artifacts(self):
        with patch.object(old, '_contract', side_effect=AssertionError('old contract read')), \
                patch.object(old, '_sources', side_effect=AssertionError('source receipt read')), \
                patch.object(old, '_prepare', side_effect=AssertionError('old exhaustive preparation')), \
                patch.object(Path, 'read_text', side_effect=AssertionError('file read')), \
                patch.object(Path, 'read_bytes', side_effect=AssertionError('file read')):
            actual = lazy.run_benchmark(seed=14011, runs=1, acquisition_steps=2, budget=20_000_000)
        self.assertEqual(actual, small_report())

    def test_heldout_verdicts_do_not_steer_acquisition_or_learning_cost(self):
        abstention = {'status': 'ambiguous', 'predictions': None, 'test_verified': False}
        with patch.object(old, '_predict', return_value=abstention):
            changed = lazy.run_benchmark(seed=14011, runs=1, acquisition_steps=2, budget=20_000_000)
        for actual, original in zip(changed['results'], small_report()['results']):
            self.assertEqual(actual['archive'], original['archive'])
            self.assertEqual(actual['survivors'], original['survivors'])
            self.assertEqual(actual['cost']['learning'], original['cost']['learning'])

    def test_audit_replays_negative_or_inconclusive_reports_and_reports_its_cost(self):
        report = small_report()
        audit = lazy.audit_report(json.loads(json.dumps(report)))
        self.assertTrue(audit['instrument_valid'])
        self.assertTrue(audit['replayed'])
        self.assertFalse(audit['scientific_superiority'])
        self.assertEqual(audit['replay_work'], report['cost']['physical_with_audit'])
        self.assertGreater(audit['receipt_comparison_work']['used'], 0)
        self.assertEqual(audit['total_work'], old._add_work(audit['replay_work'], audit['receipt_comparison_work']))

    def test_audit_rejects_state_cost_result_and_summary_tampering(self):
        report = small_report()
        mutations = (
            lambda r: r['results'][0]['survivors'].clear(),
            lambda r: r['results'][0]['cost']['selection'].update(used=0),
            lambda r: r['results'][0]['prefixes'][0]['evaluations'][0].update(success='true'),
            lambda r: r['pairs']['adaptive_vs_random'].update(mean_learning_cost_delta=0),
            lambda r: r['cost']['audit_overhead'].update(used=0),
            lambda r: r.update(instrument_valid=1),
        )
        # One real replay, reused only by this corruption test to keep CPU bounded.
        with patch.object(lazy, 'run_benchmark', return_value=report):
            for mutate in mutations:
                changed = copy.deepcopy(report)
                mutate(changed)
                with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                    lazy.audit_report(changed)

    def test_parent_budget_accepts_four_small_acquisition_steps(self):
        report = lazy.run_benchmark(seed=14012, runs=1, acquisition_steps=4, budget=2_000_000)
        for result in report['results']:
            self.assertEqual(result['opportunities']['teacher_queries'], 4)
            self.assertLessEqual(result['cost']['total']['used'], 2_000_000)

    def test_journal_observes_selection_before_labels_without_changing_report(self):
        class Journal:
            def __init__(self):
                self.events = []

            def write(self, **facts):
                self.events.append(facts)

        journal = Journal()
        actual = lazy.run_benchmark(seed=14011, runs=1, acquisition_steps=2,
                                    budget=20_000_000, journal=journal)
        self.assertEqual(actual, small_report())
        selections = 0
        for index, event in enumerate(journal.events):
            if event['kind'] == 'curriculum_lazy_selection':
                selections += 1
                self.assertNotIn('queried_label', event)
                following = journal.events[index + 1]
                self.assertEqual(following['kind'], 'curriculum_lazy_evidence')
                self.assertEqual(following['case_id'], event['case_id'])
        self.assertEqual(selections, 6)

    def test_exhaustion_raises_instead_of_returning_a_smaller_denominator(self):
        with self.assertRaises(BudgetExceeded):
            lazy.run_benchmark(seed=14011, runs=1, acquisition_steps=1, budget=1)
        with self.assertRaises(BudgetExceeded):
            old.choose_challenge(self.table((scene(601),)).view(Budget(10)), list(range(16)),
                                 Budget(10), mode='adaptive')

    def test_exhaustion_journal_distinguishes_a_resource_limit_from_an_instrument_bug(self):
        class Journal:
            def __init__(self):
                self.events = []

            def write(self, **facts):
                self.events.append(facts)

        journal = Journal()
        with self.assertRaises(BudgetExceeded):
            lazy.run_benchmark(seed=14011, runs=1, acquisition_steps=4,
                               budget=1, journal=journal)
        self.assertEqual(len(journal.events), 1)
        event = journal.events[0]
        self.assertEqual(event['kind'], 'curriculum_lazy_budget_exhausted')
        self.assertEqual(event['scientific_result'], 'budget_exhausted')
        self.assertFalse(event['instrument_error'])
        self.assertEqual(event['completed_pairs'], 0)
        self.assertEqual(event['budget'], 1)
        self.assertIn('remaining', event['error'])

    def test_configuration_rejects_invalid_values_before_any_execution(self):
        for override in ({'seed': True}, {'seed': -1}, {'runs': 0}, {'runs': 1.5},
                         {'acquisition_steps': 0}, {'acquisition_steps': True},
                         {'budget': 0}, {'budget': 1.5}):
            with self.subTest(override=override), patch.object(old, 'execute', side_effect=AssertionError('ran')):
                with self.assertRaises(ValueError):
                    lazy.run_benchmark(**override)


if __name__ == '__main__':
    unittest.main()
