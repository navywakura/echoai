"""Structural transfer, complete bounded tiers and independently checked receipts.

Written before evaluation. These tests deliberately use development seeds only.
"""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from echo5.budget import Budget, BudgetExceeded
from echo5.concepts import Library
from echo5 import grounding as g, programs as p
from echo5.solver import solve
from echo5 import transfer as t


class InputOnly(dict):
    def __getitem__(self, key):
        if key != 'input':
            raise AssertionError('hidden query label read')
        return super().__getitem__(key)

    def get(self, key, *default):
        return self[key]

    def __iter__(self):
        raise AssertionError('query mapping inspected')

    items = keys = values = __iter__


def padded(color):
    return [[0]*5, [0, color, 2, 0, 0], [0, 3, 0, 0, 0], [0]*5]


def target(color):
    return [[color, color, 2, 2]*2, [color, color, 2, 2]*2,
            [3, 3, 0, 0]*2, [3, 3, 0, 0]*2]


def three_step_task():
    return {'train': [{'input': padded(c), 'output': target(c)} for c in (1, 4)],
            'test': [InputOnly(input=padded(7), output='forbidden')]}


def tiny_search(depth=3):
    return {'max_depth': depth, 'beam_width': 32, 'max_candidates': 1000,
            'grammar': {'geometry': ['crop', 'up2', 'tile1x2'], 'roles': [],
                        'relations': [], 'effects': [], 'object_effects': [],
                        'pack_axes': []}}


class StructuralGroundingTests(unittest.TestCase):
    def test_outline_removes_only_interior_and_keeps_other_objects(self):
        rows = [[0]*8 for _ in range(7)]
        for y in range(1, 5):
            for x in range(1, 5):
                rows[y][x] = 2
        rows[5][6] = 4
        expected = deepcopy(rows)
        for y in (2, 3):
            for x in (2, 3):
                expected[y][x] = 0
        out = p.execute({'steps': [{'op': 'object', 'role': 'largest', 'effect': 'outline'}]}, rows)
        self.assertEqual([list(r) for r in out], expected)
        self.assertEqual(rows[2][2], 2)

    def test_fill_refuses_to_overwrite_another_object(self):
        rows = [[0]*7, [0, 2, 2, 2, 2, 2, 0], [0, 2, 0, 0, 0, 2, 0],
                [0, 2, 0, 5, 0, 2, 0], [0, 2, 2, 2, 2, 2, 0], [0]*7]
        budget = Budget(100000)
        with self.assertRaises(ValueError):
            p.execute({'steps': [{'op': 'object', 'role': 'largest', 'effect': 'fill_box'}]}, rows, budget=budget)
        scene = g.ground(rows, budget)
        source = g.select(scene, 'largest', budget)
        self.assertEqual([o.color for o in g.targets(scene, source, 'inside', budget)], [5])

    def test_pack_orders_by_area_and_refuses_ties(self):
        rows = [[0]*9, [0, 3, 0, 0, 2, 2, 0, 0, 0],
                [0, 0, 0, 0, 2, 0, 0, 0, 0], [0]*9]
        program = {'steps': [{'op': 'pack', 'axis': 'row'}]}
        self.assertEqual(p.execute(program, rows), ((2, 2, 0, 3), (2, 0, 0, 0)))
        with self.assertRaises(ValueError):
            p.execute(program, [[0]*5, [0, 2, 0, 3, 0], [0]*5])

    def test_new_ops_reject_authority_and_invalid_parameters(self):
        for step in ({'op': 'pack', 'axis': 'diagonal'},
                     {'op': 'object', 'role': 'largest', 'effect': 'outline', 'verified': True}):
            with self.assertRaises(ValueError):
                p.parse_program({'steps': [step]}, budget=Budget(10000))


class DeeperSynthesisTests(unittest.TestCase):
    def test_discovers_three_primitives_without_proposals_or_query_truth(self):
        result = solve(three_step_task(), synthesis=tiny_search(), cache_policy='interned', budget=2_000_000)
        self.assertEqual(result['status'], 'solved')
        self.assertEqual(result['predictions'], [target(7)])
        self.assertEqual(len(result['program']['steps']), 3)
        self.assertFalse(result['test_verified'])
        shallow = solve(three_step_task(), synthesis=tiny_search(2), budget=2_000_000)
        self.assertNotEqual(shallow['status'], 'solved')

    def test_interned_and_uncached_frontiers_are_identical(self):
        cached = solve(three_step_task(), synthesis=tiny_search(), cache_policy='interned', budget=2_000_000)
        flat = solve(three_step_task(), synthesis=tiny_search(), hierarchical=False, budget=2_000_000)
        for key in ('status', 'predictions', 'program', 'hypothesis'):
            self.assertEqual(cached[key], flat[key])
        for key in ('candidates', 'semantic_duplicates', 'beam_pruned', 'tier'):
            self.assertEqual(cached['metrics'][key], flat['metrics'][key])
        self.assertGreater(cached['metrics']['cache_hits'], 0)
        self.assertEqual(cached['metrics']['counts'].get('cache_key_cells', 0), 0)
        self.assertGreater(cached['metrics']['counts']['cache_input_cells'], 0)
        self.assertGreater(cached['metrics']['counts']['cache_lookups'], 0)

    def test_candidate_exhaustion_never_emits_a_partial_tier_prediction(self):
        search = tiny_search()
        search['max_candidates'] = 1
        result = solve(three_step_task(), synthesis=search, budget=2_000_000)
        self.assertEqual(result['status'], 'search_exhausted')
        self.assertEqual(result['predictions'], [])
        self.assertFalse(result['metrics']['complete'])

    def test_budget_exhaustion_abstains_and_ledger_still_adds_up(self):
        result = solve(three_step_task(), synthesis=tiny_search(), budget=100)
        self.assertEqual(result['status'], 'budget_exhausted')
        self.assertEqual(result['predictions'], [])
        self.assertEqual(sum(result['metrics']['counts'].values()), result['metrics']['used'])

    def test_semantic_dedup_keeps_query_disagreement(self):
        grammar = tiny_search(1)
        grammar['grammar']['geometry'] = ['identity', 'rot90']
        task = {'train': [{'input': [[2]], 'output': [[2]]}],
                'test': [InputOnly(input=[[1, 2], [3, 4]])]}
        result = solve(task, synthesis=grammar, budget=100000)
        self.assertEqual(result['status'], 'ambiguous')
        self.assertEqual(result['metrics']['unique_predictions'], 2)

    def test_snapshot_is_detached_and_rechecks_support_on_next_task(self):
        lib = Library()
        program = {'steps': [{'op': 'crop'}, {'op': 'up2'}, {'op': 'tile1x2'}]}
        lib.acquire('expanded', program, three_step_task()['train'],
                    budget=Budget(500000), provenance={'source': 'hand fixtures'})
        view = lib.verified_view(budget=Budget(500000))
        self.assertEqual(p.execute({'steps': [{'op': 'call', 'name': 'expanded'}]}, padded(7), library=view),
                         tuple(tuple(r) for r in target(7)))
        lib.challenge('expanded', [{'input': padded(7), 'output': padded(7)}],
                      budget=Budget(500000), provenance={'source': 'counterexample'})
        self.assertEqual(view.active_names(), ('expanded',))
        self.assertEqual(lib.verified_view(budget=Budget(500000)).active_names(), ())

    def test_synthesis_acquires_a_parent_with_a_real_child_dependency(self):
        lib = Library()
        child = {'steps': [{'op': 'crop'}, {'op': 'up2'}]}
        evidence = [{'input': padded(c), 'output': [row[:4] for row in target(c)]} for c in (1, 4)]
        lib.acquire('frame', child, evidence, budget=Budget(500000), provenance={'source': 'hand fixtures'})
        result = solve(three_step_task(), library=lib, learn=True, synthesis=tiny_search(2),
                       cache_policy='interned', budget=2_000_000)
        self.assertEqual(result['status'], 'solved')
        self.assertEqual(result['predictions'], [target(7)])
        self.assertEqual(len(result['program']['steps']), 3)
        self.assertIn({'op': 'call', 'name': 'frame'}, result['hypothesis']['steps'])
        parents = [record for record in lib.state()['concepts'] if record['name'] != 'frame']
        self.assertEqual(len(parents), 1)
        self.assertIn('frame', parents[0]['dependencies'])
        self.assertEqual(parents[0]['program'], result['hypothesis'])


class TransferEvidenceTests(unittest.TestCase):
    def test_confirmation_overrides_and_overlapping_seeds_are_rejected(self):
        config = t.default_config('confirmation')
        config['work_per_case'] += 1
        with self.assertRaises(ValueError):
            t.normalize_config(config)
        config = t.default_config('development')
        config['seeds'] = [530011]
        with self.assertRaises(ValueError):
            t.normalize_config(config)

    def test_independent_generators_match_executable_witnesses(self):
        for family in t.SUPPORTED_FAMILIES:
            for seed in (61013, 61027):
                case = t.make_case(seed, family, split='development', budget=Budget(1_000_000))
                public = t.public_task(case)
                self.assertEqual(set(public), {'train', 'test'})
                self.assertTrue(all(set(row) == {'input'} for row in public['test']))
                self.assertTrue(t.validate_witness(case, Budget(1_000_000)))
                public['train'][0]['input'][0][0] = 9
                self.assertNotEqual(public['train'], case['task']['train'])

    def test_controls_have_an_oracle_but_no_claimed_executable_witness(self):
        for family in t.CONTROL_FAMILIES:
            case = t.make_case(61013, family, split='development', budget=Budget(1_000_000))
            self.assertIsNone(case['witness'])
            self.assertTrue(case['expected'])

    def test_report_recomputation_detects_forged_success_cost_and_missing_rows(self):
        # Minimal development receipt: training and all controls still present.
        config = t.default_config('development')
        config.update(seeds=[61013], families=['unsupported_color'], work_per_case=50000,
                      training_work_per_case=50000)
        report = t.run_benchmark(config)
        self.assertEqual(set(('schema', 'config', 'rows', 'summary', 'gates')) - set(report), set())
        audit = t.audit_benchmark(report, replay=False)
        self.assertTrue(audit['arithmetic_valid'], audit)
        self.assertFalse(audit['valid'])
        self.assertEqual(audit['summary'], report['summary'])
        replayed = t.audit_report(report)
        self.assertTrue(replayed['valid'])
        self.assertEqual(replayed['replayed_rows'], len(report['rows']))
        self.assertEqual(replayed['replayed_training'], len(report['training']))
        self.assertGreater(report['summary']['arms']['learned']['training_work'], 0)
        self.assertEqual(len(report['libraries']['learned']['concepts']),
                         len(report['libraries']['irrelevant']['concepts']))
        for mutation in ('success', 'cost', 'missing', 'oracle', 'authority', 'gate', 'source',
                         'metametric', 'required_gates', 'reference_role'):
            forged = deepcopy(report)
            if mutation == 'success':
                forged['rows'][0]['success'] = not forged['rows'][0]['success']
            elif mutation == 'cost':
                forged['rows'][0]['work']['used'] += 1
            elif mutation == 'missing':
                forged['rows'].pop()
            elif mutation == 'oracle':
                forged['rows'][0]['expected'] = [[[9]]]
            elif mutation == 'authority':
                forged['rows'][0]['result']['test_verified'] = True
            elif mutation == 'gate':
                forged['gates']['closure_candidate'] = not forged['gates']['closure_candidate']
            elif mutation == 'metametric':
                forged['summary']['metametric_differences']['learned_vs_fixed']['evaluation'] = {
                    'semantic_work': -1, 'metadata_work': 0, 'total_work': -1}
            elif mutation == 'required_gates':
                forged['summary']['required_gates'].remove('fixed_total_cost_noninferiority')
            elif mutation == 'reference_role':
                forged['summary']['condition_roles']['fixed'] = 'ordinary_baseline'
            else:
                forged['sources']['sha256'] = '0'*64
            with self.assertRaises(ValueError, msg=mutation):
                t.audit_benchmark(forged, replay=False)
        self.assertEqual(json.loads(json.dumps(report)), report)


def accounting_ledger(semantic=0, metadata=0):
    """Hand-set accounting units, never generated/evaluated benchmark tasks."""
    return {'limit': 1_000_000, 'used': semantic + metadata,
            'remaining': 1_000_000 - semantic - metadata,
            'counts': {'candidate_attempts': semantic, 'hash_bytes': metadata}}


def accounting_fixture():
    """Small arithmetic fixture for the pure summary primitive, not an audit receipt."""
    config = t.default_config('development')
    config['families'] = ['outline_extract_scale', 'ambiguous_rotation', 'unsupported_color']
    costs = {'learned': 800, 'fixed': 800, 'irrelevant': 1000, 'empty': 1000,
             'empty_uncached': 2000, 'empty_shallow': 500, 'old_representation': 500}
    rows = []
    for condition, cost in costs.items():
        for family in config['families']:
            supported = family == 'outline_extract_scale'
            success = supported and condition not in ('empty_shallow', 'old_representation')
            rows.append({'id': family, 'family': family, 'condition': condition,
                         'supported': supported, 'success': success,
                         'result': {'status': 'solved' if success else 'unsolved',
                                    'predictions': [[[1]]] if success else [],
                                    'program': None, 'hypothesis': None,
                                    'metrics': {'candidates': 1, 'complete': True, 'tier': 1,
                                                'beam_pruned': 0, 'semantic_duplicates': 0}},
                         'work': accounting_ledger(cost), 'judge_work': accounting_ledger()})
    training = [{'work': accounting_ledger(100), 'generator_work': accounting_ledger()}]
    record = {'expanded': {'steps': [{'op': 'identity'}]}}
    libraries = {name: {'concepts': [] if name == 'empty' else [deepcopy(record)]}
                 for name in ('learned', 'fixed', 'irrelevant', 'empty')}
    preparation = {name: accounting_ledger() for name in libraries}
    cases = [{'case': {'public_sha256': family}, 'generator_work': accounting_ledger()}
             for family in config['families']]
    return config, rows, training, libraries, preparation, cases, accounting_ledger()


class TransferV2AccountingTests(unittest.TestCase):
    def test_closure_uses_required_policy_when_strict_oracle_gate_is_false(self):
        fixture = accounting_fixture()
        fixture[0]['phase'] = 'confirmation'
        # Only the frozen-config equality is substituted for this arithmetic
        # fixture. No confirmation inputs, generators or actor calls are used.
        with patch.object(t, 'default_config', return_value=deepcopy(fixture[0])):
            summary, gates = t.recompute_summary(*fixture)
        self.assertFalse(gates['learned_vs_fixed'])
        self.assertTrue(gates['closure_candidate'])
        self.assertIn('fixed_total_cost_noninferiority', summary['required_gates'])

    def test_oracle_noninferiority_does_not_require_old_strict_superiority(self):
        summary, gates = t.recompute_summary(*accounting_fixture())
        self.assertEqual(summary['condition_roles']['fixed'], 'fixed_oracle_reference')
        self.assertEqual(summary['arms']['learned']['total_work'], 2500)
        self.assertEqual(summary['arms']['fixed']['total_work'], 2400)
        self.assertTrue(gates['fixed_accuracy_noninferiority'])
        self.assertTrue(gates['fixed_total_cost_noninferiority'])
        self.assertFalse(gates['learned_vs_fixed'])
        self.assertIn('learned_vs_fixed', summary['descriptive_gates'])
        self.assertNotIn('learned_vs_fixed', summary['required_gates'])
        self.assertFalse(gates['closure_candidate'])  # Development never promotes.
        eligible = dict(gates, confirmatory_config=True)
        self.assertTrue(t._required_gates_pass(eligible, summary['required_gates']))
        for name in summary['required_gates']:
            missing = dict(eligible)
            del missing[name]
            self.assertFalse(t._required_gates_pass(missing, summary['required_gates']), name)
        self.assertFalse(t._required_gates_pass(eligible, []))
        eligible['fixed_accuracy_noninferiority'] = 1
        self.assertFalse(t._required_gates_pass(eligible, summary['required_gates']))

    def test_fixed_cost_tolerance_is_inclusive_and_counts_acquisition(self):
        fixture = accounting_fixture()
        training = fixture[2]
        # Evaluation ties at 2400. Exactly 120 extra acquisition units is 5%.
        training[0]['work'] = accounting_ledger(120)
        self.assertTrue(t.recompute_summary(*fixture)[1]['fixed_total_cost_noninferiority'])
        training[0]['work'] = accounting_ledger(60, 60)
        self.assertTrue(t.recompute_summary(*fixture)[1]['fixed_total_cost_noninferiority'])
        for semantic, metadata in ((121, 0), (0, 121)):
            training[0]['work'] = accounting_ledger(semantic, metadata)
            self.assertFalse(t.recompute_summary(*fixture)[1]['fixed_total_cost_noninferiority'])

    def test_one_fixed_accuracy_regression_fails_even_if_costs_pass(self):
        fixture = accounting_fixture()
        row = next(row for row in fixture[1] if row['condition'] == 'learned' and row['supported'])
        row['success'] = False
        row['result'].update(status='unsolved', predictions=[])
        summary, gates = t.recompute_summary(*fixture)
        self.assertEqual(summary['comparisons']['learned_vs_fixed']['losses'], 1)
        self.assertFalse(gates['fixed_accuracy_noninferiority'])
        self.assertTrue(gates['fixed_total_cost_noninferiority'])

    def test_fixed_comparison_requires_a_present_paired_reference(self):
        fixture = accounting_fixture()
        fixture[0]['conditions'].remove('fixed')
        fixture[1][:] = [row for row in fixture[1] if row['condition'] != 'fixed']
        _, gates = t.recompute_summary(*fixture)
        self.assertFalse(gates['fixed_accuracy_noninferiority'])
        self.assertFalse(gates['fixed_total_cost_noninferiority'])

    def test_metadata_only_saving_cannot_satisfy_memory_improvement(self):
        fixture = accounting_fixture()
        fixture[2][0]['work'] = accounting_ledger()
        for row in fixture[1]:
            if row['condition'] == 'learned':
                row['work'] = accounting_ledger(800)
            elif row['condition'] in ('empty', 'irrelevant'):
                row['work'] = accounting_ledger(800, 200)
        summary, gates = t.recompute_summary(*fixture)
        for control in ('empty', 'irrelevant'):
            name = 'learned_vs_' + control
            self.assertTrue(gates[name])  # The unchanged all-in total criterion.
            self.assertFalse(gates[name + '_semantic'])
            self.assertIn(name + '_semantic', summary['required_gates'])
            diff = summary['metametric_differences'][name]
            self.assertEqual(diff['evaluation'],
                             {'semantic_work': 0, 'metadata_work': -600, 'total_work': -600})
            self.assertTrue(diff['evaluation_saving_is_metadata_only'])

    def test_semantic_saving_cannot_hide_total_cost_regression(self):
        fixture = accounting_fixture()
        for row in fixture[1]:
            if row['condition'] == 'learned':
                row['work'] = accounting_ledger(600, 600)
        _, gates = t.recompute_summary(*fixture)
        for control in ('empty', 'irrelevant'):
            self.assertTrue(gates['learned_vs_' + control + '_semantic'])
            self.assertFalse(gates['learned_vs_' + control])

    def test_fixed_metadata_difference_is_not_reported_as_semantic_saving(self):
        fixture = accounting_fixture()
        for row in fixture[1]:
            if row['condition'] in ('learned', 'fixed'):
                row['work'] = accounting_ledger(100000, 1496 if row['condition'] == 'fixed' else 0)
        summary, gates = t.recompute_summary(*fixture)
        difference = summary['metametric_differences']['learned_vs_fixed']
        self.assertEqual(difference['evaluation'],
                         {'semantic_work': 0, 'metadata_work': -4488, 'total_work': -4488})
        self.assertEqual(difference['total'],
                         {'semantic_work': 100, 'metadata_work': -4488, 'total_work': -4388})
        self.assertTrue(difference['evaluation_saving_is_metadata_only'])
        self.assertFalse(gates['learned_vs_fixed'])

    def test_semantic_threshold_and_all_cost_stages_are_preserved(self):
        fixture = accounting_fixture()
        fixture[2][0]['work'] = accounting_ledger(450)
        # Learned 2400 evaluation + 450 acquisition = 2850, exactly 95% of empty.
        self.assertTrue(t.recompute_summary(*fixture)[1]['learned_vs_empty_semantic'])
        fixture[2][0]['work'] = accounting_ledger(451)
        self.assertFalse(t.recompute_summary(*fixture)[1]['learned_vs_empty_semantic'])
        fixture = accounting_fixture()
        fixture[2][0]['generator_work'] = accounting_ledger(20, 30)
        fixture[4]['learned'] = accounting_ledger(40, 50)
        fixture[5][0]['generator_work'] = accounting_ledger(60, 70)
        fixture[-1].update(accounting_ledger(80, 90))
        summary, _ = t.recompute_summary(*fixture)
        learned = summary['arms']['learned']
        self.assertEqual(learned['cost_breakdown']['training'],
                         {'semantic_work': 120, 'metadata_work': 30, 'total_work': 150})
        self.assertEqual(learned['cost_breakdown']['common'],
                         {'semantic_work': 140, 'metadata_work': 160, 'total_work': 300})
        self.assertEqual(learned['semantic_work'], 2700)
        self.assertEqual(learned['metadata_work'], 240)
        self.assertEqual(learned['total_work'], 2940)
        for arm in summary['arms'].values():
            self.assertEqual(arm['total_work'], arm['semantic_work'] + arm['metadata_work'])

    def test_search_state_hashing_remains_semantic_work(self):
        fixture = accounting_fixture()
        ledger = fixture[1][0]['work']
        ledger['counts'] = {'hash_bytes': 100, 'json_characters': 100, 'json_nodes': 100,
                            'source_read_hash_bytes': 100, 'library_snapshot_records': 100,
                            'state_hash_cells': 200, 'cache_lookups': 100}
        summary, _ = t.recompute_summary(*fixture)
        self.assertEqual(summary['arms']['learned']['cost_breakdown']['evaluation'],
                         {'semantic_work': 1900, 'metadata_work': 500, 'total_work': 2400})

    def test_v1_report_requires_its_archived_auditor(self):
        with self.assertRaises(ValueError):
            t.audit_benchmark({'schema': 'echo5.transfer.v1'}, replay=False)


if __name__ == '__main__':
    unittest.main()
