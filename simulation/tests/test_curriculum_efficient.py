"""Small CPU fixtures for bounded curriculum optimization; no campaign I/O."""

import copy
from functools import lru_cache
import hashlib
import inspect
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from echo5 import curriculum as old
from echo5 import curriculum_lazy as lazy
from echo5.budget import Budget, BudgetExceeded


def program(op):
    return {'steps': [{'op': op}]}


def challenge(rows):
    rows = tuple(tuple(row) for row in rows)
    return old.PublicChallenge(old._digest(rows), rows)


SYMMETRIC = challenge(((1, 1), (0, 0)))
ASYMMETRIC = challenge(((1, 0), (0, 0)))


def table(pool, hypotheses):
    return lazy._LazyTable(pool, hypotheses, tuple(old.program_id(h) for h in hypotheses))


@lru_cache(maxsize=1)
def comparison():
    return lazy.run_benchmark(seed=14011, runs=1, acquisition_steps=2,
                              budget=2_000_000, efficient=True)


class EfficientPolicyTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(lazy, 'choose_challenge_efficient', None)),
                        'bounded efficient selector is missing')
        self.assertTrue(callable(getattr(lazy, '_learn_survivors', None)),
                        'survivor-only evidence update is missing')

    def select(self, pool, hypotheses, survivors):
        cache, work = table(pool, hypotheses), Budget(2_000_000)
        index, scores = lazy.choose_challenge_efficient(cache.view(work), survivors, work)
        return index, scores, cache, work

    def test_singleton_uses_first_index_without_any_prediction(self):
        hypotheses = [program('identity'), program('fliplr'), program('flipud')]
        index, scores, cache, work = self.select(
            (ASYMMETRIC, SYMMETRIC, ASYMMETRIC), hypotheses, [2])
        self.assertEqual(index, 0)
        self.assertEqual(scores, [None, None, None])
        self.assertEqual(cache._cache, {})
        self.assertEqual(work.counts.get('hypothesis_executions', 0), 0)
        self.assertEqual(work.counts.get('selection_prediction_reads', 0), 0)
        self.assertGreater(work.used, 0)
        label = ((0, 0), (1, 0))  # flipud, hand derived
        update = Budget(100_000)
        survivors, compatibility = lazy._learn_survivors(cache.view(update), index, label, [2], update)
        self.assertEqual(survivors, [2])
        self.assertEqual(compatibility, [None, None, True])
        self.assertEqual(update.counts['hypothesis_executions'], 1)
        self.assertEqual(update.counts['evidence_hypothesis_comparisons'], 1)
        self.assertEqual(update.counts['evidence_cells'], 4)

    def test_proven_maximum_stops_at_first_best_and_reuses_paid_predictions(self):
        hypotheses = [program('identity'), program('fliplr')]
        pool = (SYMMETRIC, ASYMMETRIC, ASYMMETRIC)
        index, scores, cache, work = self.select(pool, hypotheses, [0, 1])
        reference = Budget(100_000)
        expected = old.choose_challenge(table(pool, hypotheses).view(reference), [0, 1],
                                         reference, mode='adaptive')
        self.assertEqual(expected, (1, [0, 1, 1]))
        self.assertEqual((index, scores), (1, [0, 1, None]))
        self.assertEqual(work.counts['hypothesis_executions'], 4)
        self.assertEqual(work.counts['selection_candidates'], 2)
        self.assertEqual(work.counts['selection_rank_comparisons'], 1)
        self.assertEqual(work.counts['selection_bound_checks'], 2)
        self.assertLess(work.used, reference.used)
        update = Budget(100_000)
        survivors, compatibility = lazy._learn_survivors(
            cache.view(update), index, ASYMMETRIC.input, [0, 1], update)
        self.assertEqual((survivors, compatibility), ([0], [True, False]))
        self.assertEqual(update.counts.get('hypothesis_executions', 0), 0)
        self.assertEqual(update.counts['prediction_cache_lookups'], 2)
        self.assertEqual(update.counts['evidence_cells'], 8)

    def test_ninety_percent_agreement_neither_stops_scoring_nor_certifies_query(self):
        hypotheses = [program('identity') for _ in range(9)] + [program('fliplr')]
        index, scores, _, work = self.select(
            (SYMMETRIC, ASYMMETRIC, ASYMMETRIC), hypotheses, list(range(10)))
        self.assertEqual((index, scores), (1, [0, 9, 9]))
        self.assertEqual(work.counts['hypothesis_executions'], 30)
        query_work = Budget(100_000)
        result = old._predict(table((ASYMMETRIC,), hypotheses).view(query_work),
                              0, list(range(10)), query_work)
        self.assertEqual(result, {'status': 'ambiguous', 'predictions': None, 'test_verified': False})
        self.assertEqual(query_work.counts['consensus_prediction_reads'], 10)

    def test_eliminated_hypothesis_compatibility_is_unknown_even_if_it_would_match(self):
        hypotheses = [program('identity'), program('fliplr')]
        survivors = [0, 1]
        for scene, expected in ((ASYMMETRIC, [True, False]), (SYMMETRIC, [True, None])):
            work = Budget(100_000)
            before = survivors[:]
            survivors, compatibility = lazy._learn_survivors(
                table((scene,), hypotheses).view(work), 0, scene.input, survivors, work)
            self.assertEqual(survivors, [0])
            self.assertEqual(compatibility, expected)
            self.assertEqual(work.counts['hypothesis_executions'], len(before))
            self.assertEqual(work.counts['evidence_hypothesis_comparisons'], len(before))
            self.assertEqual(work.counts['evidence_cells'], 4 * len(before))
            self.assertEqual(work.counts['survivor_intersections'], len(before))
        full_work = Budget(100_000)
        _, compatible = old._learn(table((SYMMETRIC,), hypotheses).view(full_work),
                                    0, SYMMETRIC.input, [0], full_work)
        self.assertEqual(compatible, [0, 1])

    def test_real_grammar_preserves_each_selection_survivor_and_heldout_answer(self):
        hypotheses = old.grammar()
        pools = [tuple(old._scene(seed, holdout=False, budget=Budget(100_000))
                       for seed in seeds) for seeds in ((501, 502), (503, 504))]
        query = (old._scene(505, holdout=True, budget=Budget(100_000)),)
        for target in (0, 5, 10, 15):
            for mode in old.CONDITIONS:
                with self.subTest(target=target, mode=mode):
                    a = b = list(range(16))
                    rng_a, rng_b = random.Random(17), random.Random(17)
                    for pool in pools:
                        wa, wb = Budget(2_000_000), Budget(2_000_000)
                        va, vb = table(pool, hypotheses).view(wa), table(pool, hypotheses).view(wb)
                        ia, sa = old.choose_challenge(va, a, wa, mode=mode, rng=rng_a)
                        if mode == 'adaptive':
                            ib, sb = lazy.choose_challenge_efficient(vb, b, wb)
                            for actual, expected in zip(sb, sa):
                                if actual is not None:
                                    self.assertEqual(actual, expected)
                        else:
                            ib, _ = old.choose_challenge(vb, b, wb, mode=mode, rng=rng_b)
                        self.assertEqual(ia, ib)
                        # Teacher work is separate from both selectors, after selection.
                        truth = old._label(pool[ia], hypotheses[target], Budget(100_000))
                        entering = b[:]
                        a, full = old._learn(va, ia, truth, a, wa)
                        b, partial = lazy._learn_survivors(vb, ib, truth, b, wb)
                        self.assertEqual(a, b)
                        self.assertIn(target, b)
                        self.assertEqual(partial, [h in full if h in entering else None for h in range(16)])
                        qa, qb = Budget(2_000_000), Budget(2_000_000)
                        self.assertEqual(old._predict(table(query, hypotheses).view(qa), 0, a, qa),
                                         old._predict(table(query, hypotheses).view(qb), 0, b, qb))

    def test_only_public_predictions_are_available_during_selection(self):
        hypotheses = [program('identity'), program('fliplr')]
        with patch.object(old, '_oracle', side_effect=AssertionError('truth leaked to selector')), \
                patch.object(old, '_label', side_effect=AssertionError('teacher called by selector')):
            index, scores, _, _ = self.select((SYMMETRIC, ASYMMETRIC), hypotheses, [0, 1])
        self.assertEqual((index, scores), (1, [0, 1]))

    def test_empty_state_invalid_shapes_and_total_elimination_fail_closed(self):
        hypotheses = [program('identity'), program('invalid')]
        for pool, live in (((), [0]), ((ASYMMETRIC,), [])):
            with self.subTest(pool=pool, live=live), self.assertRaises(ValueError):
                self.select(pool, hypotheses, live)
        for live, label in (([1], ASYMMETRIC.input), ([0], ((0,),)), ([0], ((0, 0), (0, 0))),
                            ([], ASYMMETRIC.input)):
            work = Budget(100_000)
            with self.subTest(live=live, label=label), self.assertRaises(ValueError):
                lazy._learn_survivors(table((ASYMMETRIC,), hypotheses).view(work), 0, label, live, work)

    def test_exact_work_allowance_succeeds_and_one_less_propagates_exhaustion(self):
        hypotheses = [program('identity'), program('fliplr')]
        for live in ([0], [0, 1]):
            _, _, _, measured = self.select((SYMMETRIC, ASYMMETRIC), hypotheses, live)
            for limit, succeeds in ((measured.used, True), (measured.used - 1, False)):
                work = Budget(limit)
                view = table((SYMMETRIC, ASYMMETRIC), hypotheses).view(work)
                if succeeds:
                    lazy.choose_challenge_efficient(view, live, work)
                    self.assertEqual(work.used, limit)
                    self.assertEqual(work.used, sum(work.counts.values()))
                else:
                    with self.assertRaises(BudgetExceeded):
                        lazy.choose_challenge_efficient(view, live, work)
        measured = Budget(100_000)
        lazy._learn_survivors(table((ASYMMETRIC,), hypotheses).view(measured),
                              0, ASYMMETRIC.input, [0], measured)
        short = Budget(measured.used - 1)
        with self.assertRaises(BudgetExceeded):
            lazy._learn_survivors(table((ASYMMETRIC,), hypotheses).view(short),
                                  0, ASYMMETRIC.input, [0], short)


class EfficientComparisonTests(unittest.TestCase):
    def setUp(self):
        self.assertIn('efficient', inspect.signature(lazy.run_benchmark).parameters,
                      'explicit opt-in comparison is missing')

    def assertLedger(self, ledger):
        self.assertEqual(ledger['used'], sum(ledger['counts'].values()))
        self.assertTrue(all(type(n) is int and n >= 0 for n in ledger['counts'].values()))

    def test_runner_entry_point_and_fresh_process_digest_match_exactly(self):
        entry = getattr(lazy, 'run_efficient_benchmark', None)
        self.assertTrue(callable(entry), 'stable experiment-runner entry point is missing')
        report = entry(seed=14011, runs=1, acquisition_steps=2, budget=2_000_000)
        self.assertEqual(report, comparison())
        encoded = json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        source = str(Path(__file__).resolve().parents[1] / 'src')
        script = (
            'import hashlib,json,sys; '
            f'sys.path.insert(0, {source!r}); '
            'from echo5.curriculum_lazy import run_efficient_benchmark, audit_report; '
            'report=run_efficient_benchmark(seed=14011,runs=1,acquisition_steps=2,budget=2000000); '
            "assert audit_report(report)['valid']; "
            "print(hashlib.sha256(json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest())"
        )
        digest = subprocess.check_output([sys.executable, '-I', '-B', '-c', script], text=True).strip()
        self.assertEqual(digest, hashlib.sha256(encoded).hexdigest())

    def test_default_full_receipt_matches_frozen_prechange_fixture(self):
        kwargs = dict(seed=14011, runs=1, acquisition_steps=2, budget=2_000_000)
        report = lazy.run_benchmark(**kwargs)
        canonical = json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                         '45180dbda37a38d381b9e752e91962d53dc91b6640d67fe6ab4512fa37946384')
        self.assertEqual(report, lazy.run_benchmark(**kwargs, efficient=False))

    def test_four_arms_share_samples_queries_and_total_ceiling_with_honest_costs(self):
        report = comparison()
        self.assertEqual(report['schema'], 'echo5-curriculum-efficient-v1')
        self.assertTrue(report['config']['efficient'])
        arms = {r['condition']: r for r in report['results']}
        self.assertEqual(set(arms), {'adaptive', 'adaptive_efficient', 'random', 'sequential'})
        for mode, arm in arms.items():
            with self.subTest(mode=mode):
                self.assertEqual(arm['task_ids'], arms['adaptive']['task_ids'])
                self.assertEqual(arm['hypothesis_ids'], arms['adaptive']['hypothesis_ids'])
                self.assertEqual(arm['opportunities']['teacher_queries'], 2)
                self.assertEqual(arm['opportunities']['evaluation_predictions'], 16)
                self.assertEqual(arm['opportunities']['external_adjudications'], 16)
                cost = arm['cost']
                for ledger in cost.values():
                    self.assertLedger(ledger)
                self.assertLessEqual(cost['total']['used'], 2_000_000)
                self.assertEqual(cost['learning'], old._add_work(*(cost[p] for p in lazy.LEARNING_PHASES)))
                self.assertEqual(cost['total'], old._add_work(cost['learning'], cost['heldout_evaluation']))
                self.assertEqual(cost['acquisition']['counts']['witness_executions'], 2)
                compared = 32 if mode == 'adaptive' else sum(len(r['before']) for r in arm['archive'])
                self.assertEqual(arm['opportunities']['evidence_hypothesis_comparisons'], compared)
                self.assertEqual(arm['opportunities']['evidence_cells'], 225 * compared)
                if mode in ('random', 'sequential'):
                    self.assertEqual(cost['selection']['counts'].get('hypothesis_executions', 0), 0)
                    self.assertEqual(cost['update']['counts']['hypothesis_executions'], compared)
                for record in arm['archive']:
                    if mode != 'adaptive':
                        self.assertEqual(record['compatibility_scope'], 'entering_survivors')
                        vector = record['compatibility']
                        self.assertEqual(len(vector), 16)
                        self.assertEqual([i for i, value in enumerate(vector) if value is not None], record['before'])
                        self.assertEqual([i for i, value in enumerate(vector) if value is True], record['compatible'])
                self.assertTrue(all(not row['result']['test_verified']
                                    for prefix in arm['prefixes'] for row in prefix['evaluations']))
        cost = report['cost']
        self.assertEqual(cost['physical_protocol'], old._add_work(
            cost['shared_preparation'], cost['shared_heldout_evaluation'],
            *(arm['cost']['exclusive'] for arm in arms.values())))
        self.assertEqual(cost['physical_with_audit'], old._add_work(cost['physical_protocol'], cost['audit_overhead']))
        self.assertEqual(report['audit']['verified_challenges'], 20)
        self.assertEqual(cost['audit_overhead']['counts']['witness_executions'], 20)
        self.assertFalse(report['promotion'])
        self.assertFalse(report['scientific_superiority'])

    def test_optimized_arm_keeps_reference_states_and_accounts_for_actual_selection(self):
        arms = {r['condition']: r for r in comparison()['results']}
        a, b = arms['adaptive'], arms['adaptive_efficient']
        scored = 0
        for full, optimized in zip(a['archive'], b['archive']):
            for key in ('selected_index', 'queried_label', 'before', 'after', 'rejected'):
                self.assertEqual(full[key], optimized[key])
            scored += len(optimized['before']) * sum(s is not None for s in optimized['disagreement_scores'])
        self.assertEqual(b['cost']['selection']['counts']['hypothesis_executions'], scored)
        self.assertEqual([p['survivors'] for p in a['prefixes']], [p['survivors'] for p in b['prefixes']])
        self.assertEqual([[r['result'] for r in p['evaluations']] for p in a['prefixes']],
                         [[r['result'] for r in p['evaluations']] for p in b['prefixes']])
        self.assertLess(b['cost']['learning']['used'], a['cost']['learning']['used'])

    def test_pairs_include_old_adaptive_and_both_controls_without_claiming_a_win(self):
        report = comparison()
        arms = {r['condition']: r for r in report['results']}
        for control in ('adaptive', 'random', 'sequential'):
            pair = report['pairs']['adaptive_efficient_vs_' + control]
            self.assertEqual(pair['paired_runs'], 1)
            expected = arms['adaptive_efficient']['cost']['learning']['used'] - arms[control]['cost']['learning']['used']
            self.assertEqual(pair['mean_learning_cost_delta'], expected)
            self.assertEqual(pair['observed_mean_cost_saving'], expected < 0)
            self.assertEqual(pair['unit'], 'independent_acquisition_run')
        self.assertEqual(len(report['perfamily']), 16)
        self.assertEqual(sum(f['paired_runs'] for f in report['perfamily'].values()), 1)
        for family in report['perfamily'].values():
            self.assertEqual(set(family['arms']), set(arms))
        self.assertEqual(report['scientific_result'], 'inconclusive')

    def test_determinism_and_replay_cover_partial_scores_unknowns_and_costs(self):
        report = comparison()
        actual = lazy.run_benchmark(seed=14011, runs=1, acquisition_steps=2, budget=2_000_000, efficient=True)
        self.assertEqual(actual, report)
        self.assertEqual(json.loads(json.dumps(report)), report)
        audit = lazy.audit_report(report)
        self.assertTrue(audit['valid'])
        self.assertTrue(audit['replayed'])
        self.assertEqual(audit['replay_work'], report['cost']['physical_with_audit'])
        mutations = (
            lambda r: r['results'][-1]['archive'][-1]['compatibility'].__setitem__(0, 'unknown'),
            lambda r: r['results'][-1]['archive'][-1]['disagreement_scores'].__setitem__(0, 999),
            lambda r: r['results'][-1]['cost']['learning'].update(used=0),
            lambda r: r['pairs']['adaptive_efficient_vs_adaptive'].update(mean_learning_cost_delta=0),
            lambda r: r['config'].update(efficient=1),
        )
        with patch.object(lazy, 'run_benchmark', return_value=report):
            for mutate in mutations:
                changed = copy.deepcopy(report)
                mutate(changed)
                with self.assertRaises(ValueError):
                    lazy.audit_report(changed)

    def test_query_truth_verdicts_and_mutating_observer_cannot_steer_acquisition(self):
        baseline = comparison()
        prepare = lazy._prepare

        def different_truth(config, index):
            prepared = prepare(config, index)
            # A read-only evaluator input, never given to acquisition.
            prepared['truths'] = [((9,),)] * len(prepared['truths'])
            return prepared

        class MutatingJournal:
            def write(self, **facts):
                for value in facts.values():
                    if isinstance(value, (dict, list)):
                        value.clear()

        # Deliberately inconsistent heldout receipts cannot pass the real audit;
        # isolate the learner here. Real audit is exercised by comparison/replay.
        with patch.object(lazy, '_prepare', side_effect=different_truth):
            config = lazy._config(14011, 1, 2, 2_000_000, efficient=True)
            prepared = lazy._prepare(config, 0)
            changed = [lazy._run_arm(config, prepared, condition, MutatingJournal())
                       for condition in ('sequential', 'random', 'adaptive', 'adaptive_efficient')]
        for original, altered in zip(baseline['results'], changed):
            self.assertEqual(original['archive'], altered['archive'])
            self.assertEqual(original['survivors'], altered['survivors'])
            self.assertEqual(original['cost']['learning'], altered['cost']['learning'])
        self.assertTrue(any(a['final_accuracy'] != b['final_accuracy']
                            for a, b in zip(baseline['results'], changed)))

    def test_opt_in_validation_and_budget_failure_never_return_partial_success(self):
        for invalid in (1, 0, None, 'true'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                lazy.run_benchmark(efficient=invalid)
        events = []

        class Journal:
            def write(self, **facts):
                events.append(facts)

        with self.assertRaises(BudgetExceeded):
            lazy.run_benchmark(seed=14011, runs=1, acquisition_steps=2, budget=1,
                               efficient=True, journal=Journal())
        self.assertEqual(events[-1]['kind'], 'curriculum_lazy_budget_exhausted')
        self.assertFalse(events[-1]['instrument_error'])
        self.assertEqual(events[-1]['completed_pairs'], 0)


if __name__ == '__main__':
    unittest.main()
