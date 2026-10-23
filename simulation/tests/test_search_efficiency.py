"""Safety of resource-aware search, including counterexamples to unsafe pruning."""
import unittest
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from echo5.solver import solve
from echo5.budget import Budget
from echo5.programs import execute


class InputOnly(dict):
    def __getitem__(self, key):
        if key != 'input':
            raise AssertionError('query truth read')
        return super().__getitem__(key)


def config(geometry, *, depth=2, strategy='certified', **kwargs):
    return {'max_depth': depth, 'beam_width': 24, 'max_candidates': 12000,
            'grammar': {'geometry': geometry}, 'strategy': strategy, **kwargs}


class EfficientSearchTests(unittest.TestCase):
    def test_same_dimensions_do_not_prune_intermediate_resize(self):
        # Downsampling then upsampling changes content while preserving final shape.
        a = [[1, 2, 3, 4], [2, 1, 4, 3], [5, 6, 7, 8], [6, 5, 8, 7]]
        b = [[2, 3, 4, 5], [3, 2, 5, 4], [6, 7, 8, 9], [7, 6, 9, 8]]
        program = {'steps': [{'op': 'down2'}, {'op': 'up2'}]}
        def output(g):
            return [list(r) for r in execute(program, g)]
        task = {'train': [{'input': a, 'output': output(a)}],
                'test': [InputOnly(input=b, output='forbidden')]}
        result = solve(task, synthesis=config(['down2', 'up2']), cache_policy='interned')
        self.assertEqual(result['status'], 'solved')
        self.assertEqual(result['predictions'], [output(b)])
        self.assertFalse(result['test_verified'])

    def test_first_fit_does_not_hide_late_disagreement(self):
        task = {'train': [{'input': [[2]], 'output': [[2]]}],
                'test': [InputOnly(input=[[1, 2], [3, 4]])]}
        result = solve(task, synthesis=config(['identity', 'up2', 'rot90'], depth=1))
        self.assertEqual(result['status'], 'ambiguous')
        self.assertGreaterEqual(result['metrics']['unique_predictions'], 2)
        self.assertEqual(result['predictions'], [])

    def test_unfinished_consensus_abstains_even_after_first_fit(self):
        task = {'train': [{'input': [[2]], 'output': [[2]]}],
                'test': [InputOnly(input=[[1, 2], [3, 4]])]}
        result = solve(task, synthesis=config(['identity', 'rot90'], depth=1, max_candidates=1))
        self.assertEqual(result['status'], 'search_exhausted')
        self.assertEqual(result['predictions'], [])
        self.assertFalse(result['metrics']['complete'])

    def test_all_modes_agree_on_completed_tier(self):
        task = {'train': [{'input': [[0, 0, 0], [0, 2, 3], [0, 0, 0]],
                           'output': [[2, 3]]}],
                'test': [InputOnly(input=[[0, 0, 0], [0, 4, 5], [0, 0, 0]])]}
        results = [solve(task, synthesis=config(['identity', 'rot90', 'crop', 'up2'],
                         strategy=s), cache_policy='interned')
                   for s in ('baseline', 'memoized', 'certified')]
        self.assertEqual(results[0]['status'], 'solved')
        for result in results[1:]:
            self.assertEqual(result['status'], results[0]['status'])
            self.assertEqual(result['predictions'], results[0]['predictions'])
            self.assertTrue(result['metrics']['complete'])
            self.assertEqual(result['metrics']['used'], sum(result['metrics']['counts'].values()))

    def test_query_undefined_is_not_dropped_from_consensus(self):
        # down2 is defined on train, undefined on a too-small query.
        task = {'train': [{'input': [[2, 2], [2, 2]], 'output': [[2]]}],
                'test': [InputOnly(input=[[2]])]}
        result = solve(task, synthesis=config(['down2'], depth=1))
        self.assertEqual(result['status'], 'ambiguous')
        self.assertGreater(result['metrics']['query_undefined'], 0)

    def test_work_exhaustion_never_returns_a_prediction(self):
        task = {'train': [{'input': [[2]], 'output': [[2]]}], 'test': [{'input': [[3]]}]}
        result = solve(task, synthesis=config(['identity']), budget=30)
        self.assertEqual(result['status'], 'budget_exhausted')
        self.assertEqual(result['predictions'], [])
        self.assertLessEqual(result['metrics']['used'], 30)

    def test_partial_signature_pass_reports_only_paid_operator_checks(self):
        task = {'train': [{'input': [[2]], 'output': [[2]]}], 'test': [{'input': [[3]]}]}
        for limit in (35, 36):
            result = solve(task, synthesis=config(['identity', 'rot90'], depth=1), budget=limit)
            metrics = result['metrics']
            self.assertEqual(metrics['operator_slots_checked'], metrics['counts'].get('signature_operator_checks', 0))

    def test_invalid_strategy_fails_closed(self):
        result = solve({}, synthesis=config(['identity'], strategy='first_fit'))
        self.assertEqual(result['status'], 'invalid_search')

    def test_memoized_execution_preserves_search_candidates_and_answers(self):
        from test_transfer import three_step_task, tiny_search
        cfg = tiny_search()
        baseline = solve(three_step_task(), synthesis=cfg, budget=2000000, cache_policy='interned')
        cached = solve(three_step_task(), synthesis={**cfg, 'strategy': 'memoized'},
                       budget=2000000, cache_policy='interned')
        for key in ('status', 'predictions', 'program', 'hypothesis'):
            self.assertEqual(cached[key], baseline[key])
        for key in ('candidates', 'tier', 'beam_pruned', 'semantic_duplicates'):
            self.assertEqual(cached['metrics'][key], baseline['metrics'][key])

    def test_cache_limit_fallback_does_not_merge_unknown_ids(self):
        from echo5.search_cache import SearchCache
        from echo5.programs import Step
        cache = SearchCache(Budget(1000000), max_entries=1, max_cells=8)
        first, second = ((1, 2), (3, 4)), ((5, 6), (7, 8))
        op = Step('rot90')
        self.assertEqual(cache.step(op, first), ((3, 1), (4, 2)))
        self.assertEqual(cache.step(op, second), ((7, 5), (8, 6)))
        self.assertNotEqual(cache.signature((first,)), cache.signature((second,)))
        self.assertLessEqual(cache.cells, 8)

    def test_zero_cache_retention_includes_nested_analysis(self):
        from echo5.search_cache import SearchCache
        from echo5.programs import Step
        cache = SearchCache(Budget(100000), max_entries=0, max_cells=0)
        result = cache.step(Step('relate', role='largest', relation='all', effect='extract'),
                            ((0, 0, 0), (0, 2, 0), (0, 0, 0)))
        self.assertEqual(result, ((2,),))
        self.assertEqual(cache.analysis.entry_count, 0)
        self.assertEqual(cache.total_retained_cells, 0)

    def test_palette_pruning_does_not_invent_a_color(self):
        task = {'train': [{'input': [[1, 2], [3, 4]], 'output': [[9]]}],
                'test': [InputOnly(input=[[1, 2], [3, 4]])]}
        result = solve(task, synthesis=config(['identity', 'rot90', 'up2']))
        self.assertEqual(result['status'], 'unsolved')
        self.assertEqual(result['predictions'], [])
        self.assertGreater(result['metrics']['signature_pruned'], 0)
        self.assertNotIn('execution_steps', result['metrics']['counts'])

    def test_hash_collision_is_not_grid_equivalence(self):
        from echo5.search_cache import SearchCache
        from echo5.programs import Step
        cache = SearchCache(Budget(100000))
        first, second = ((1, 2), (3, 4)), ((5, 6), (7, 8))
        with patch('echo5.search_cache.hash', return_value=7, create=True):
            self.assertNotEqual(cache.identifier(first), cache.identifier(second))
            self.assertEqual(cache.step(Step('rot90'), first), ((3, 1), (4, 2)))
            self.assertEqual(cache.step(Step('rot90'), second), ((7, 5), (8, 6)))

    def test_new_color_producing_operator_has_no_palette_proof(self):
        from echo5.search_cache import palette_preserving
        from echo5.programs import Step
        self.assertFalse(palette_preserving((Step('paint_constant'),)))
        self.assertFalse(palette_preserving((Step('object', role='largest', effect='new_color'),)))

    def test_alias_pruning_checks_query_bindings_too(self):
        from echo5.search_cache import SearchCache, prune_binding_aliases
        from echo5.programs import expand
        a = {'steps': [{'op': 'relate', 'role': 'largest', 'relation': 'all', 'effect': 'extract'}]}
        b = {'steps': [{'op': 'relate', 'role': 'leftmost', 'relation': 'all', 'effect': 'extract'}]}
        train = ((0, 0, 0, 0, 0, 0, 0), (0, 2, 2, 0, 0, 3, 0),
                 (0, 2, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0, 0))
        query = ((0, 0, 0, 0, 0, 0, 0), (0, 3, 0, 0, 2, 2, 0),
                 (0, 0, 0, 0, 2, 0, 0), (0, 0, 0, 0, 0, 0, 0))
        ledger = Budget(100000)
        cache = SearchCache(ledger)
        compiled = [(p, expand(p, budget=ledger)) for p in (a, b)]
        same, _ = prune_binding_aliases(compiled, (train,), (train,), cache)
        different, _ = prune_binding_aliases(compiled, (train,), (query,), cache)
        self.assertEqual(len(same), 1)
        self.assertEqual(len(different), 2)

    def test_all_326_operators_keep_identical_defined_behaviors_after_pruning(self):
        from echo5.search_cache import SearchCache, prune_binding_aliases
        from echo5.programs import expand, synthesis_atoms, apply_step
        rows = ((0, 0, 0, 0, 0, 0, 0), (0, 2, 2, 0, 0, 3, 0),
                (0, 2, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0, 0))
        query = tuple(tuple(reversed(row)) for row in rows)
        ledger = Budget(10000000)
        compiled = [(p, expand(p, budget=ledger)) for p in synthesis_atoms()]
        kept, discarded = prune_binding_aliases(compiled, (rows,), (query,), SearchCache(ledger))
        def behaviors(candidates):
            results = set()
            for _, (step,) in candidates:
                try:
                    train = apply_step(step, rows, budget=ledger)
                except ValueError:
                    continue
                try:
                    pred = apply_step(step, query, budget=ledger)
                except ValueError:
                    pred = None
                results.add((train, pred))
            return results
        self.assertEqual(behaviors(compiled), behaviors(kept))
        self.assertEqual(len(compiled), len(kept)+len(discarded))
        self.assertLess(len(kept), len(compiled))

    def test_partial_loss_bound_preserves_the_retained_frontier(self):
        from test_transfer import three_step_task, tiny_search
        from echo5.search_diagnostics import _Tap
        cfg = {**tiny_search(), 'beam_width': 2, 'strategy': 'certified'}
        results, traces = [], []
        for enabled in (False, True):
            trace = _Tap(None)
            result = solve(three_step_task(), synthesis={**cfg, 'ranking_bound': enabled},
                           budget=2000000, cache_policy='interned', diagnostic=True, journal=trace)
            results.append(result)
            traces.append([e['retained'] for e in trace.events if e['kind'] == 'synthesis_selection'])
        self.assertNotEqual(results[0]['status'], 'invalid_search')
        self.assertEqual(traces[0], traces[1])
        for key in ('status','predictions','program'):
            self.assertEqual(results[0][key], results[1][key])
        self.assertGreater(results[1]['metrics']['ranking_bound_pruned'], 0)

    def test_cli_exposes_opt_in_strategy_and_real_trace(self):
        from echo5.cli import main
        from echo5.trace import verify_journal
        task = {'train': [{'input': [[1, 2], [3, 4]], 'output': [[3, 1], [4, 2]]}],
                'test': [{'input': [[5, 6], [7, 8]]}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'task.json'
            path.write_text(json.dumps(task))
            trace = Path(directory)/'thought.jsonl'
            output = StringIO()
            with redirect_stdout(output):
                code = main(['solve', str(path), '--synthesis-strategy', 'certified', '--trace', str(trace)])
            self.assertEqual(code, 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result['metrics']['search_strategy'], 'certified')
            self.assertEqual(result['status'], 'solved')
            self.assertGreater(verify_journal(trace)['events'], 0)


if __name__ == '__main__':
    unittest.main()
