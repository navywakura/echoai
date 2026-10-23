"""Parent-run tests: deliberately written before any tests/benchmarks ran.

These exercise development seeds only; they never open confirmation or S6.
Scientific advantage is not assumed. Integrity failure and scientific failure
are different outcomes, and both are tested.
"""

import copy
from dataclasses import fields
import json
import random
import unittest
from unittest.mock import patch

from echo5 import curriculum as c
from echo5.budget import Budget, BudgetExceeded


def development_config(**overrides):
    config = c.default_config('development')
    config.update(paired_runs=1, rounds=3, pool_per_round=2,
                  confirmation_cases_per_run=2, bootstrap_samples=128)
    config.update(overrides)
    return config


class MemoryJournal:
    def __init__(self):
        self.events = []

    def write(self, *, kind, **facts):
        self.events.append({'kind': kind, **copy.deepcopy(facts)})


def analytic_curves(profiles):
    """Synthetic arithmetic fixture, not benchmark evidence or a cost audit.

    Thirty-two tiny paired rows exercise inference without generating scenes
    or executing an actor; profiles contain two Boolean cases per prefix.
    """
    config = development_config(paired_runs=32)
    runs, rows = [], []
    for i in range(config['paired_runs']):
        arms = {}
        for condition in c.CONDITIONS:
            states = [{'prefix': p, 'work': {'used': 100 * p + (p if condition == 'adaptive' else 0)}}
                      for p in (1, 2, 3)]
            for state in states:
                state['total_work'] = 1000 + state['work']['used']
            arms[condition] = {'prefixes': states, 'work': states[-1]['work'],
                               'total_work': states[-1]['total_work'], 'opportunities': {}}
            for prefix, answers in enumerate(profiles[condition], 1):
                for j, correct in enumerate(answers):
                    rows.append({'run_index': i, 'condition': condition, 'prefix': prefix, 'query_index': j,
                                 'result': {'status': 'solved' if correct else 'ambiguous',
                                            'predictions': [[[1]]] if correct else None,
                                            'test_verified': False},
                                 'expected': [[[1]]], 'success': not correct})
        runs.append({'run_index': i, 'run_seed': str(i), 'arms': arms, 'common_work': {'used': 1000},
                     'physical_work': 1000 + sum(a['work']['used'] for a in arms.values()),
                     'cases': [None] * (config['rounds'] * config['pool_per_round'] +
                                       config['confirmation_cases_per_run']),
                     'repeated_acquisition_inputs': 0, 'repeated_evaluation_inputs': 0})
    return config, runs, rows


class CurriculumBoundaryTests(unittest.TestCase):
    def test_confirmation_contract_is_fixed_and_at_least_32_runs(self):
        contract = json.loads(c.CONTRACT_PATH.read_text())
        config = c.default_config()
        self.assertEqual(config, contract['config'])
        self.assertGreaterEqual(config['paired_runs'], 32)
        self.assertEqual(config['rounds'], 3)
        self.assertEqual(contract['learning_curve']['prefixes'], [1, 2, 3])
        self.assertEqual(contract['report_schema'], c.SCHEMA)
        self.assertEqual(c._config(config), config)
        self.assertNotEqual(config['seed'], c.default_config('development')['seed'])
        for key, value in (('paired_runs', 31), ('seed', 1), ('rounds', 4),
                           ('bootstrap_samples', 128), ('work_per_run', 99999999)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                c._config({**config, key: value})

    def test_bad_configuration_is_rejected_before_agent_work(self):
        for delta in ({'paired_runs': True}, {'seed': 1.5}, {'rounds': 0},
                      {'pool_per_round': 0}, {'conditions': ['adaptive']},
                      {'unknown_override': 1}, {'phase': 'sealed'},
                      {'seed': c.default_config()['seed']}):
            with self.subTest(delta=delta), patch.object(c, 'execute') as executor:
                with self.assertRaises(ValueError):
                    c.run_benchmark(development_config(**delta))
                executor.assert_not_called()

    def test_grammar_is_detached_and_uses_existing_finite_programs(self):
        hypotheses = c.grammar()
        self.assertEqual(len(hypotheses), 16)
        self.assertEqual(len({c.program_id(h) for h in hypotheses}), 16)
        hypotheses[0]['steps'][0]['role'] = 'invalid'
        self.assertEqual(c.grammar()[0]['steps'][0]['role'], 'largest')
        self.assertEqual({len(h['steps']) for h in c.grammar()}, {1, 2})

    def test_all_grammar_witnesses_solve_both_generation_styles(self):
        # Includes empty-effect-but-nonempty-target scenes, composed programs,
        # and geometry on nonsquare holdout inputs. No confirmation seeds.
        for holdout in (False, True):
            for seed in (101, 102, 103):
                scene = c._scene(seed, holdout=holdout, budget=Budget(100000))
                for witness in c.grammar():
                    with self.subTest(holdout=holdout, seed=seed, witness=witness):
                        label = c._label(scene, witness, Budget(1000000))
                        self.assertEqual([list(row) for row in label], c._oracle(scene.input, witness))

    def test_invalid_witness_cannot_receive_credit_or_be_silently_replaced(self):
        scene = c._scene(201, holdout=False, budget=Budget(100000))
        with patch.object(c, 'execute', return_value=((9,),)):
            with self.assertRaisesRegex(ValueError, 'invalid curriculum witness'):
                c._label(scene, c.grammar()[0], Budget(100000))

    def test_public_prediction_table_has_no_teacher_labels_or_identity_metadata(self):
        self.assertEqual({f.name for f in fields(c.PublicChallenge)}, {'id', 'input'})
        self.assertEqual({f.name for f in fields(c.PredictionTable)},
                         {'challenges', 'predictions', 'fingerprints', 'hypothesis_ids'})
        scene = c._scene(301, holdout=False, budget=Budget(100000))
        budget = Budget(1000000)
        table = c.prediction_table([scene], c.grammar(), budget)
        self.assertEqual(budget.counts['hypothesis_executions'], 16)
        self.assertEqual(table.challenges[0].id, c._digest(table.challenges[0].input))
        with self.assertRaises((AttributeError, TypeError)):
            table.challenges[0].input = ((8,),)

    def test_adaptive_scores_disagreement_and_updates_after_evidence(self):
        # The second input is maximally informative without any truth field.
        table = c.PredictionTable(
            (c.PublicChallenge('a', ((0,),)), c.PublicChallenge('b', ((0,),))),
            ((((1,),), ((1,),), ((1,),)), (((1,),), ((2,),), ((3,),))),
            (('one', 'one', 'one'), ('one', 'two', 'three')), ('h0', 'h1', 'h2'))
        with (patch.object(c, '_oracle', side_effect=AssertionError('label access')),
              patch.object(c, 'execute', side_effect=AssertionError('extra hypothesis execution'))):
            budget = Budget(10000)
            index, scores = c.choose_challenge(table, (0, 1, 2), budget, mode='adaptive')
            self.assertEqual((index, scores), (1, [0, 3]))
            survivors, compatible = c._learn(table, index, ((2,),), [0, 1, 2], budget)
            self.assertEqual((survivors, compatible), ([1], [1]))
            self.assertEqual(c.choose_challenge(table, tuple(survivors), budget, mode='adaptive'),
                             (0, [0, 0]))
            self.assertNotIn('hypothesis_executions', budget.counts)

    def test_random_and_sequential_do_not_pad_cost_by_running_disagreement(self):
        table = c.PredictionTable((c.PublicChallenge('a', ((0,),)),
                                   c.PublicChallenge('b', ((0,),))), (), (), ('h',))
        for mode in ('sequential', 'random'):
            budget = Budget(10)
            index, scores = c.choose_challenge(table, (0,), budget, mode=mode, rng=random.Random(8))
            self.assertIn(index, (0, 1))
            self.assertIsNone(scores)
            self.assertEqual(budget.used, 1)
            self.assertFalse(any('prediction' in kind for kind in budget.counts))

    def test_teacher_is_one_label_per_round_and_never_serves_evaluation(self):
        teacher = c._Teacher({(0, 'public'): ((1,),)})
        budget = Budget(100)
        self.assertEqual(teacher.query('adaptive', 0, 'public', budget), ((1,),))
        with self.assertRaises(ValueError):
            teacher.query('adaptive', 0, 'public', budget)
        with self.assertRaises(ValueError):
            teacher.query('random', 0, 'holdout', budget)
        self.assertEqual(budget.counts['teacher_queries'], 1)

    def test_budget_exhaustion_is_an_instrument_failure_with_receipt(self):
        journal = MemoryJournal()
        with self.assertRaises(BudgetExceeded):
            c.run_benchmark(development_config(work_per_run=1), journal)
        self.assertEqual(journal.events[-1]['kind'], 'curriculum_instrument_error')
        self.assertEqual(journal.events[-1]['completed_pairs'], 0)


class CurriculumReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.journal = MemoryJournal()
        cls.report = c.run_benchmark(development_config(), cls.journal)

    def test_replay_survives_json_roundtrip_without_changing_frozen_actor(self):
        report = json.loads(json.dumps(self.report))
        before = copy.deepcopy(report)
        with patch.object(c, 'run_benchmark', side_effect=AssertionError('auditor called producer')):
            audit = c.audit_report(report)
        self.assertTrue(audit['valid'])
        self.assertTrue(audit['deterministic_replay'])
        self.assertFalse(audit['closure_success'])  # development is never confirmation
        self.assertEqual(report, before)
        self.assertEqual(self.report, c.run_benchmark(development_config()))

    def test_actual_tables_queries_and_comparisons_are_equal_without_private_execution(self):
        config = self.report['config']
        for run in self.report['runs']:
            counts = run['common_work']['counts']
            scenes = config['rounds'] * config['pool_per_round'] + config['confirmation_cases_per_run']
            self.assertEqual(counts['hypothesis_executions'], 16 * scenes)
            self.assertEqual(counts['witness_executions'], scenes)
            self.assertEqual(run['physical_work'], run['common_work']['used'] +
                             sum(arm['work']['used'] for arm in run['arms'].values()))
            opportunities = [arm['opportunities'] for arm in run['arms'].values()]
            self.assertTrue(all(value == opportunities[0] for value in opportunities))
            for arm in run['arms'].values():
                self.assertEqual(arm['opportunities']['private_hypothesis_executions'], 0)
                self.assertNotIn('hypothesis_executions', arm['work']['counts'])
                self.assertEqual(arm['work']['counts']['teacher_queries'], config['rounds'])
                self.assertEqual(arm['work']['counts']['evidence_hypothesis_comparisons'], 16 * config['rounds'])
                self.assertEqual(arm['work']['counts']['evidence_cells'], 225 * 16 * config['rounds'])
                self.assertEqual(arm['opportunities']['evaluation_predictions'],
                                 config['rounds'] * config['confirmation_cases_per_run'])
                self.assertEqual(arm['opportunities']['external_adjudications'],
                                 config['rounds'] * config['confirmation_cases_per_run'])
                self.assertEqual(arm['total_work'], run['common_work']['used'] + arm['work']['used'])
                self.assertEqual(arm['work']['used'], sum(arm['work']['counts'].values()))
                self.assertEqual(c._add_work(arm['acquisition_work'], arm['evaluation_work'])['counts'],
                                 arm['work']['counts'])
                self.assertLessEqual(arm['total_work'], config['work_per_run'])
                for prefix, state in enumerate(arm['prefixes'], 1):
                    self.assertEqual(state['prefix'], prefix)
                    self.assertEqual(state['survivors'], arm['archive'][prefix - 1]['after'])
                    self.assertEqual(state['work']['counts']['teacher_queries'], prefix)
                    self.assertEqual(state['work']['counts']['external_adjudications'],
                                     prefix * config['confirmation_cases_per_run'])
                    self.assertEqual(c._add_work(state['acquisition_work'], state['evaluation_work'])['used'],
                                     state['work']['used'])
                    self.assertEqual(state['total_work'], run['common_work']['used'] + state['work']['used'])
                self.assertEqual(arm['prefixes'][-1]['work'], arm['work'])
            self.assertGreater(run['arms']['adaptive']['work']['counts']['selection_prediction_reads'], 0)
            for control in ('sequential', 'random'):
                self.assertNotIn('selection_prediction_reads', run['arms'][control]['work']['counts'])

    def test_holdout_is_new_generation_style_and_not_fed_back_to_learning(self):
        for run in self.report['runs']:
            acquisition = [case for case in run['cases'] if case['split'] == 'acquisition']
            holdout = [case for case in run['cases'] if case['split'] == 'evaluation']
            self.assertFalse({case['id'] for case in acquisition} & {case['id'] for case in holdout})
            self.assertTrue(all(len(case['input']) == 15 and len(case['input'][0]) == 15 for case in acquisition))
            self.assertTrue(all(len(case['input']) == 21 and len(case['input'][0]) == 23 for case in holdout))
            for case in acquisition:
                self.assertLessEqual(max(cell for row in case['input'] for cell in row), 4)
            for case in holdout:
                self.assertTrue(all(cell == 0 or cell >= 5 for row in case['input'] for cell in row))
            for condition, arm in run['arms'].items():
                queried = {event['case_id'] for event in arm['archive']}
                self.assertLessEqual(queried, {case['id'] for case in acquisition})
                for row in self.report['rows']:
                    if row['run_id'] == run['run_id'] and row['condition'] == condition:
                        state = arm['prefixes'][row['prefix'] - 1]
                        self.assertEqual(row['hypotheses_sha256'], state['hypotheses_sha256'])
                        self.assertIs(row['result']['test_verified'], False)

    def test_every_prefix_records_the_same_queries_once_with_actual_work(self):
        config = self.report['config']
        expected = {(i, condition, prefix, j) for i in range(config['paired_runs'])
                    for condition in c.CONDITIONS for prefix in range(1, config['rounds'] + 1)
                    for j in range(config['confirmation_cases_per_run'])}
        self.assertEqual(len(self.report['rows']), len(expected))
        self.assertEqual({(r['run_index'], r['condition'], r['prefix'], r['query_index'])
                          for r in self.report['rows']}, expected)
        for run in self.report['runs']:
            for condition in c.CONDITIONS:
                arm_rows = [r for r in self.report['rows']
                            if r['run_index'] == run['run_index'] and r['condition'] == condition]
                self.assertEqual(c._add_work(*(r['work'] for r in arm_rows)),
                                 run['arms'][condition]['evaluation_work'])
                for j in range(config['confirmation_cases_per_run']):
                    current = [r for r in arm_rows if r['query_index'] == j]
                    self.assertEqual(len({r['id'] for r in current}), 1)
                    self.assertEqual(len({c._digest(r['expected']) for r in current}), 1)
        self.assertEqual(self.report['summary']['primary_endpoint'], 'mean_prefix_accuracy')
        self.assertTrue(self.report['summary']['final_gain_descriptive_only'])

    def test_evaluation_predictions_and_verdicts_cannot_steer_later_acquisition(self):
        abstention = {'status': 'ambiguous', 'predictions': None, 'test_verified': False}
        with patch.object(c, '_predict', return_value=abstention), \
                patch.object(c, 'exact_success', return_value=False):
            changed = c.run_benchmark(development_config())
        for actual, original in zip(changed['runs'], self.report['runs']):
            for condition in c.CONDITIONS:
                self.assertEqual(actual['arms'][condition]['archive'], original['arms'][condition]['archive'])
                self.assertEqual(actual['arms'][condition]['survivors'], original['arms'][condition]['survivors'])
        self.assertTrue(all(row['result']['predictions'] is None for row in changed['rows']))

    def test_journal_records_selection_before_evidence_and_does_not_change_outputs(self):
        events = self.journal.events
        for i, event in enumerate(events):
            if event['kind'] == 'curriculum_selection':
                self.assertEqual(events[i+1]['kind'], 'curriculum_evidence')
                self.assertEqual(events[i+1]['case_id'], event['case_id'])
                self.assertNotIn('queried_label', event)
        self.assertEqual(len([e for e in events if e['kind'] == 'curriculum_external_result']),
                         len(self.report['rows']))
        for run in self.report['runs']:
            for condition in c.CONDITIONS:
                current = [e for e in events if e.get('run_id') == run['run_id'] and e.get('condition') == condition]
                for i, event in enumerate(current):
                    if event['kind'] == 'curriculum_selection' and event['round'] > 0:
                        self.assertEqual(current[i - 1]['kind'], 'curriculum_external_result')
                        self.assertEqual(current[i - 1]['prefix'], event['round'])

    def test_audit_rejects_outputs_truth_cost_selection_and_coverage_tampering(self):
        mutations = {
            'success': lambda r: r['rows'][0].update(success=not r['rows'][0]['success']),
            'truth': lambda r: r['rows'][0]['expected'][0][0].__setitem__(0, 9),
            'actor_authority': lambda r: r['rows'][0]['result'].update(test_verified=True),
            'work': lambda r: r['runs'][0]['arms']['adaptive']['work'].update(used=0),
            'opportunities': lambda r: r['runs'][0]['arms']['random']['opportunities'].update(teacher_queries=0),
            'selection': lambda r: r['runs'][0]['arms']['adaptive']['archive'][0].update(selected_index=999),
            'prediction': lambda r: r['rows'][0]['result'].update(predictions=[[[9]]]),
            'row_duplicate': lambda r: r['rows'].__setitem__(1, copy.deepcopy(r['rows'][0])),
            'row_missing': lambda r: r['rows'].pop(),
            'prefix_identity': lambda r: r['rows'][0].update(prefix=0),
            'prefix_state': lambda r: r['runs'][0]['arms']['random']['prefixes'][0].update(survivors=[]),
            'prefix_cost': lambda r: r['runs'][0]['arms']['adaptive']['prefixes'][0]['work'].update(used=0),
            'summary': lambda r: r['summary']['totals']['adaptive'].update(successes=999),
            'utility': lambda r: r['summary']['utility_totals']['adaptive'].update(mean_utility=9),
            'curve': lambda r: r['summary']['curves'][0]['totals']['random'].update(accuracy=9),
            'gates': lambda r: r['gates'].update(scientific_success=True),
            'contract': lambda r: r.update(contract_sha256='0' * 64),
            'sources': lambda r: r.update(sources={}),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                damaged = copy.deepcopy(self.report)
                mutate(damaged)
                with self.assertRaises(ValueError):
                    c.audit_report(damaged)

    def test_one_run_advantage_does_not_become_many_independent_observations(self):
        result = c.paired_uncertainty([1.0] + [0.0] * 31, [1] + [0] * 31,
                                      seed=401, samples=128, relative_cost_deltas=[.01] + [0.] * 31)
        self.assertEqual(result['paired_runs'], 32)
        self.assertEqual(result['wins'], 1)
        self.assertEqual(result['one_sided_sign_p'], 0.5)
        self.assertEqual(result['accuracy_delta_ci95'][0], 0.0)
        self.assertEqual(result['mean_accuracy_delta'], 1/32)
        self.assertEqual(result['unit'], 'independent_acquisition_run')

    def test_ties_have_no_evidence_of_superiority_and_joint_cost_ci_is_deterministic(self):
        kwargs = dict(seed=501, samples=128, relative_cost_deltas=[.06] * 32)
        result = c.paired_uncertainty([0.] * 32, [100] * 32, **kwargs)
        self.assertEqual(result, c.paired_uncertainty([0.] * 32, [100] * 32, **kwargs))
        self.assertEqual(result['one_sided_sign_p'], 1.0)
        self.assertEqual(result['accuracy_delta_ci95'], [0., 0.])
        self.assertEqual(result['total_work_delta_ci95'], [100., 100.])
        self.assertGreater(result['relative_total_work_overhead_ci95'][1], .05)

    def test_regressions_and_cost_overhead_cannot_hide_in_accuracy_total(self):
        summary = copy.deepcopy(self.report['summary'])
        for comparison in summary['comparisons'].values():
            comparison.update(case_regressions=1, losses=1)
        for comparison in summary['utility_comparisons'].values():
            comparison.update(prefix_case_regressions=1, mean_relative_total_work_overhead=.06,
                              relative_total_work_overhead_ci95=[.04, .08],
                              maximum_relative_total_work_overhead=.09)
        gates = c._gates(self.report['config'], self.report['runs'], summary)
        self.assertFalse(gates['no_prefix_case_regressions_vs_random'])
        self.assertFalse(gates['no_final_case_regressions'])
        self.assertFalse(gates['no_final_run_regressions'])
        self.assertFalse(gates['bounded_total_cost_overhead'])
        self.assertFalse(gates['scientific_success'])


class CurriculumUtilityTests(unittest.TestCase):
    def test_utility_can_improve_with_equal_final_accuracy_without_relabelling_it(self):
        profiles = {'sequential': [[True, True]] * 3, 'adaptive': [[True, True]] * 3,
                    'random': [[False, False], [True, True], [True, True]]}
        config, runs, rows = analytic_curves(profiles)
        summary = c._summarize(config, runs, rows)
        comparison = summary['utility_comparisons']['adaptive_vs_random']
        self.assertAlmostEqual(comparison['mean_utility_delta'], 1 / 3)
        self.assertEqual(comparison['wins'], 32)
        self.assertEqual(comparison['paired_runs'], 32)
        self.assertGreater(comparison['utility_delta_ci95'][0], 0)
        self.assertLess(comparison['one_sided_sign_p'], .05)
        self.assertEqual(summary['comparisons']['adaptive_vs_random']['mean_accuracy_delta'], 0)
        self.assertEqual(summary['totals']['random']['cases'], 64)
        self.assertEqual([curve['totals']['random']['accuracy'] for curve in summary['curves']], [0, 1, 1])
        gates = c._gates(config, runs, summary)
        for name in ('meaningful_utility_gain_vs_random', 'multiple_independent_wins',
                     'paired_uncertainty_positive', 'paired_sign_test', 'adaptive_final_accuracy',
                     'no_prefix_case_regressions_vs_random', 'no_final_case_regressions',
                     'sequential_noninferiority', 'bounded_total_cost_overhead'):
            self.assertTrue(gates[name], name)
        # An arithmetic fixture is never confirmation or a valid ledger.
        self.assertFalse(gates['scientific_success'])

    def test_case_regression_at_a_prefix_cannot_be_hidden_by_positive_auc(self):
        profiles = {'sequential': [[True, False], [True, True], [True, True]],
                    'adaptive': [[True, False], [True, True], [True, True]],
                    'random': [[False, True], [False, False], [True, True]]}
        config, runs, rows = analytic_curves(profiles)
        summary = c._summarize(config, runs, rows)
        comparison = summary['utility_comparisons']['adaptive_vs_random']
        self.assertGreater(comparison['mean_utility_delta'], .1)
        self.assertEqual(comparison['prefix_case_regressions_by_prefix'], [32, 0, 0])
        gates = c._gates(config, runs, summary)
        self.assertFalse(gates['no_prefix_case_regressions_vs_random'])
        self.assertTrue(gates['no_final_case_regressions'])
        self.assertFalse(gates['scientific_success'])

    def test_sequential_safeguard_is_mean_utility_plus_final_regressions(self):
        profiles = {'sequential': [[False, True], [True, True], [True, True]],
                    'adaptive': [[True, False], [True, True], [True, True]],
                    'random': [[False, False], [False, False], [True, True]]}
        config, runs, rows = analytic_curves(profiles)
        summary = c._summarize(config, runs, rows)
        self.assertGreater(summary['utility_comparisons']['adaptive_vs_sequential']['prefix_case_regressions'], 0)
        gates = c._gates(config, runs, summary)
        self.assertTrue(gates['sequential_noninferiority'])
        self.assertTrue(gates['no_final_case_regressions'])

    def test_one_winning_run_stays_one_despite_multiple_prefixes_and_cases(self):
        profiles = {'sequential': [[True, True]] * 3, 'adaptive': [[True, True]] * 3,
                    'random': [[False, False], [False, False], [True, True]]}
        config, runs, rows = analytic_curves(profiles)
        for row in rows:
            if row['run_index'] > 0 and row['condition'] == 'random':
                row['result'] = {'status': 'solved', 'predictions': [[[1]]], 'test_verified': False}
        comparison = c._summarize(config, runs, rows)['utility_comparisons']['adaptive_vs_random']
        self.assertEqual(comparison['wins'], 1)
        self.assertEqual(comparison['paired_runs'], 32)
        self.assertEqual(comparison['unit'], 'independent_acquisition_run')
        self.assertEqual(comparison['one_sided_sign_p'], .5)
        self.assertAlmostEqual(comparison['mean_utility_delta'], 2 / (3 * 32))


if __name__ == '__main__':
    unittest.main()
