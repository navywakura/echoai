"""Small synthetic parity and work-accounting checks; no solver or campaigns."""
import hashlib
import json
import sys
import unittest
from unittest.mock import patch

from echo5 import grounding as g, programs as p
from echo5.budget import Budget, BudgetExceeded


def fixtures():
    distinct = ((0, 0, 0, 0, 0, 0, 0),
                (0, 2, 2, 0, 4, 0, 0),
                (0, 2, 2, 0, 4, 0, 0),
                (0, 0, 0, 0, 0, 0, 0),
                (0, 0, 6, 0, 0, 0, 0),
                (0, 0, 0, 0, 0, 0, 0))
    tied = ((0, 0, 0, 0, 0), (0, 2, 0, 3, 0), (0, 0, 0, 0, 0))
    ring = ((0, 0, 0, 0, 0, 0, 0),
            (0, 2, 2, 2, 2, 2, 0),
            (0, 2, 0, 0, 0, 2, 0),
            (0, 2, 0, 3, 0, 2, 0),
            (0, 2, 0, 0, 0, 2, 0),
            (0, 2, 2, 2, 2, 2, 0),
            (0, 0, 0, 0, 0, 0, 0))
    return (distinct, tied, ring, ((0, 0), (0, 0)), ((0, 1), (1, 0)),
            (), ((),), ((0,), (0, 1)), ((False, 0),), ((0.0, 0),),
            ((10,),), ((0,) * 31,), ((0,),) * 31)


def atoms():
    return tuple(p.Step(**item['steps'][0]) for item in p.synthesis_atoms())


def extra_fixtures():
    # A unique L among repeated singletons exercises successful contextual
    # roles, row/column relations and stamping near the output boundary.
    rows = [[0] * 8 for _ in range(7)]
    for y, x in ((1, 1), (2, 1), (2, 2)):
        rows[y][x] = 2
    rows[1][5] = rows[5][1] = rows[6][7] = 4
    original = tuple(map(tuple, rows))
    recolored = tuple(tuple({2: 9, 4: 6}.get(v, v) for v in row) for row in rows)
    wide = ((0,) * 18, (0,) + (2,) * 16 + (0,), (0,) * 18,
            (0,) + (4,) * 15 + (0, 0), (0,) * 18)
    return original, recolored, wide


def outcome(function):
    try:
        return ('ok', function())
    except ValueError as exc:
        return ('error', type(exc).__name__, str(exc))


def run_atoms(rows, budget, **kwargs):
    # The public grid boundary precedes already-validated apply_step, as in solver.
    return [outcome(lambda step=step: p.apply_step(
        step, g.grid(rows, budget, **kwargs), budget=budget, **kwargs))
        for step in atoms()]


def legacy_digest(**kwargs):
    records = []
    for rows in fixtures():
        budget = Budget(10**8)
        records.append((run_atoms(rows, budget, **kwargs), budget.counts))
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()


class GroundingCacheTests(unittest.TestCase):
    def cache(self, budget, **kwargs):
        self.assertTrue(hasattr(g, 'AnalysisCache'), 'per-solve AnalysisCache API is missing')
        return g.AnalysisCache(budget, **kwargs)

    def test_historical_outputs_errors_and_costs(self):
        self.assertEqual(len(atoms()), 326)
        self.assertEqual(legacy_digest(), '81b86d43476e28c07a375a510d6f4a89afee70c8e1dd23a3b98d47a26d556c68')

    def test_explicit_none_keeps_historical_costs(self):
        self.cache(Budget(1))
        self.assertEqual(legacy_digest(analysis=None), legacy_digest())

    def test_all_primitives_match_cold_warm_and_saturated_contexts(self):
        for rows in (*fixtures(), *extra_fixtures()):
            expected = run_atoms(rows, Budget(10**8))
            for limits in ({}, {'max_entries': 0}, {'max_cells': 0},
                           {'max_entries': 5, 'max_cells': 100}):
                with self.subTest(rows=rows, limits=limits):
                    budget = Budget(10**8)
                    analysis = self.cache(budget, **limits)
                    self.assertEqual(run_atoms(rows, budget, analysis=analysis), expected)
                    self.assertEqual(run_atoms(rows, budget, analysis=analysis), expected)
                    self.assertLessEqual(analysis.entry_count, analysis.max_entries)
                    self.assertLessEqual(analysis.retained_cells, analysis.max_cells)

    def test_fewer_real_segmentations_and_total_units(self):
        rows = fixtures()[0]
        plain = Budget(10**8)
        with patch.object(g._rel, 'objects', wraps=g._rel.objects) as segment:
            expected = run_atoms(rows, plain)
            plain_calls = segment.call_count
        budget = Budget(10**8)
        analysis = self.cache(budget)
        with patch.object(g._rel, 'objects', wraps=g._rel.objects) as segment:
            self.assertEqual(run_atoms(rows, budget, analysis=analysis), expected)
            self.assertEqual(segment.call_count, 1)
        self.assertEqual(plain_calls, 314)
        self.assertLess(budget.used, plain.used)
        self.assertEqual(budget.counts['segment_cells'], 42)
        for kind in ('analysis_key_units', 'analysis_lookups', 'analysis_writes',
                     'analysis_retained_cells'):
            self.assertGreater(budget.counts.get(kind, 0), 0, kind)
        self.assertEqual(budget.counts['analysis_retained_cells'], analysis.retained_cells)

    def test_features_roles_targets_and_canonical_relations_are_reused(self):
        budget = Budget(10**6)
        analysis = self.cache(budget)
        scene = g.ground(fixtures()[0], budget, analysis=analysis)
        source = g.select(scene, 'largest', budget, analysis=analysis)
        boxes = g._features(scene, budget, analysis=analysis)
        with self.assertRaises(TypeError):
            boxes[source] = (99, 99, 99, 99)
        before = budget.counts['feature_cells']
        with patch.object(g._rel, 'relate', wraps=g._rel.relate) as relate:
            for role in g.ROLES:
                for _ in range(2):
                    bound = outcome(lambda: g.select(scene, role, budget, analysis=analysis))
                    if bound[0] == 'ok':
                        g.targets(scene, bound[1], 'same_row', budget, analysis=analysis)
            self.assertEqual(relate.call_count, 1)
        self.assertEqual(budget.counts['feature_cells'], before)
        source = g.select(scene, 'largest', budget, analysis=analysis)
        expected = g.targets(scene, source, 'right', Budget(10000))
        first = g.targets(scene, source, 'right', budget, analysis=analysis)
        pairs = budget.counts['object_pairs']
        self.assertIs(g.targets(scene, source, 'right', budget, analysis=analysis), first)
        self.assertEqual(first, expected)
        self.assertEqual(budget.counts['object_pairs'], pairs)

    def test_value_errors_are_cached_without_tracebacks(self):
        budget = Budget(10**6)
        analysis = self.cache(budget)
        rows = fixtures()[3]  # Valid immutable grid without objects.
        with patch.object(g._rel, 'objects', wraps=g._rel.objects) as segment:
            errors = []
            for _ in range(2):
                try:
                    g.ground(rows, budget, analysis=analysis)
                except ValueError as exc:
                    errors.append(exc)
            self.assertEqual(segment.call_count, 1)
        self.assertEqual([str(exc) for exc in errors], ['need one to 32 objects'] * 2)
        self.assertIsNot(errors[0], errors[1])
        scene = g.ground(fixtures()[1], budget, analysis=analysis)
        with patch.object(g, '_features', wraps=g._features) as features:
            with self.assertRaisesRegex(ValueError, 'source role is ambiguous'):
                g.select(scene, 'largest', budget, analysis=analysis)
            calls = features.call_count
            self.assertGreater(calls, 0)
            with self.assertRaisesRegex(ValueError, 'source role is ambiguous'):
                g.select(scene, 'largest', budget, analysis=analysis)
            self.assertEqual(features.call_count, calls)
        for owner, value in analysis._entries.values():
            self.assertNotIsInstance(owner, BaseException)
            self.assertNotIsInstance(value, BaseException)

    def test_mutable_rows_and_equal_invalid_types_never_hit_old_validation(self):
        budget = Budget(10**6)
        analysis = self.cache(budget)
        rows = [list(row) for row in fixtures()[0]]
        step = p.Step('relate', role='largest', relation='all', effect='extract')
        first = p.apply_step(step, rows, budget=budget, analysis=analysis)
        rows[1][1] = rows[1][2] = rows[2][1] = rows[2][2] = 8
        second = p.apply_step(step, rows, budget=budget, analysis=analysis)
        self.assertNotEqual(first, second)
        self.assertEqual(second, p.apply_step(step, rows, budget=Budget(10000)))
        g.grid(((0, 0),), budget, analysis=analysis)
        for value in (False, 0.0):
            for invalid in ([[value, 0]], ((value, 0),)):
                with self.assertRaisesRegex(ValueError, 'integer colors'):
                    g.grid(invalid, budget, analysis=analysis)
        mixed = ([0, 0, 0], [0, 2, 0], [0, 0, 0])
        g.ground(mixed, budget, analysis=analysis)
        mixed[1][1] = False
        with self.assertRaisesRegex(ValueError, 'integer colors'):
            g.ground(mixed, budget, analysis=analysis)

    def test_identity_keys_retain_inputs_and_hash_collisions_are_not_matches(self):
        budget = Budget(10**6)
        analysis = self.cache(budget)
        left, right = fixtures()[:2]
        refs = sys.getrefcount(left)
        # Distinct integers with identical Python hashes exercise dict collision equality.
        with patch.object(g, 'id', lambda obj: 17 if obj is left else 17 + sys.hash_info.modulus,
                          create=True):
            self.assertEqual(g.grid(left, budget, analysis=analysis), left)
            self.assertGreater(sys.getrefcount(left), refs)
            self.assertEqual(g.grid(right, budget, analysis=analysis), right)
            self.assertEqual(g.grid(left, budget, analysis=analysis), left)
        self.assertGreaterEqual(analysis.retained_cells, sum(map(len, left)) + sum(map(len, right)) + 2)

    def test_bounds_include_identity_references_and_fallback_keeps_work_real(self):
        rows = fixtures()[0]
        area = sum(map(len, rows))
        for limits in ({'max_entries': 0}, {'max_cells': area}):
            budget = Budget(10**6)
            analysis = self.cache(budget, **limits)
            with patch.object(g._rel, 'objects', wraps=g._rel.objects) as segment:
                for _ in range(2):
                    g.ground(rows, budget, analysis=analysis)
                self.assertEqual(segment.call_count, 2)
            self.assertEqual(analysis.entry_count, 0)
            self.assertEqual(analysis.retained_cells, 0)

    def test_budget_exceeded_is_never_cached_or_written_after_failure(self):
        budget = Budget(10**6)
        analysis = self.cache(budget)
        rows = fixtures()[0]
        with patch.object(g._rel, 'objects', side_effect=BudgetExceeded('injected')) as segment:
            for _ in range(2):
                with self.assertRaises(BudgetExceeded):
                    g.ground(rows, budget, analysis=analysis)
            self.assertEqual(segment.call_count, 2)
        self.assertEqual(g.ground(rows, budget, analysis=analysis), g.ground(rows, Budget(10000)))
        entries, cells = analysis.entry_count, analysis.retained_cells
        budget.limit = budget.used
        with self.assertRaises(BudgetExceeded):
            g.ground(rows, budget, analysis=analysis)
        self.assertEqual((analysis.entry_count, analysis.retained_cells), (entries, cells))

    def test_context_is_local_and_bound_to_one_budget(self):
        rows = fixtures()[0]
        with patch.object(g._rel, 'objects', wraps=g._rel.objects) as segment:
            for _ in range(2):
                budget = Budget(10**6)
                analysis = self.cache(budget)
                g.ground(rows, budget, analysis=analysis)
            self.assertEqual(segment.call_count, 2)
        with self.assertRaisesRegex(ValueError, 'budget'):
            g.ground(rows, Budget(10000), analysis=analysis)

    def test_invalid_immutable_grids_reuse_errors_but_not_equal_valid_grids(self):
        budget = Budget(10**6)
        analysis = self.cache(budget)
        for rows in fixtures()[5:]:
            expected = outcome(lambda: g.grid(rows, Budget(10000)))
            self.assertEqual(outcome(lambda: g.grid(rows, budget, analysis=analysis)), expected)
            before = budget.counts.get('validate_cells', 0)
            self.assertEqual(outcome(lambda: g.grid(rows, budget, analysis=analysis)), expected)
            if len(rows) <= 30 and all(len(row) <= 30 for row in rows):
                self.assertEqual(budget.counts.get('validate_cells', 0), before)
        # An error under bool/float must not poison a distinct tuple of ints.
        self.assertEqual(g.grid(((0, 0),), budget, analysis=analysis), ((0, 0),))

    def test_external_scenes_and_equal_source_objects_remain_safe(self):
        budget = Budget(10**6)
        analysis = self.cache(budget)
        scene = g.ground(fixtures()[0], budget, analysis=analysis)
        source = g.select(scene, 'largest', budget, analysis=analysis)
        clone = g.Object(source.color, source.cells)
        self.assertIsNot(clone, source)
        for relation in g.ALL_RELATIONS:
            expected = g.targets(scene, clone, relation, Budget(10000))
            self.assertEqual(g.targets(scene, clone, relation, budget, analysis=analysis), expected)
        # Scene is frozen only shallowly; public constructors can hold lists.
        objects = list(scene.objects)
        external = g.Scene(scene.grid, scene.background, objects)
        self.assertEqual(g.select(external, 'largest', budget, analysis=analysis), source)
        objects.remove(source)
        self.assertEqual(g.select(external, 'largest', budget, analysis=analysis),
                         g.select(external, 'largest', Budget(10000)))

    def test_scene_aliases_are_charged_and_bounded(self):
        rows = fixtures()[0]
        budget = Budget(10**6)
        cache = self.cache(budget)
        scene = g.ground(rows, budget, analysis=cache)
        self.assertEqual(cache.entry_count, 3)  # Grid, grounding, scene alias.
        footprint = 2 * sum(map(len, rows)) + sum(len(o.cells) for o in scene.objects)
        self.assertEqual(cache.retained_cells, footprint + 3)
        for limits in ({'max_entries': 2}, {'max_cells': footprint + 2}):
            budget = Budget(10**6)
            cache = self.cache(budget, **limits)
            scene = g.ground(rows, budget, analysis=cache)
            self.assertEqual(cache.entry_count, 2)
            before = cache.entry_count, cache.retained_cells
            for _ in range(2):
                g.select(scene, 'largest', budget, analysis=cache)
            self.assertEqual((cache.entry_count, cache.retained_cells), before)
            self.assertEqual(budget.counts['feature_cells'], 2 * sum(len(o.cells) for o in scene.objects))

    def test_exhaustion_during_cache_retention_does_not_publish_partial_entries(self):
        budget = Budget(10**6)
        cache = self.cache(budget)
        consume = budget.consume
        def fail_retention(kind, amount=1):
            if kind == 'analysis_retained_cells':
                raise BudgetExceeded('retention unavailable')
            consume(kind, amount)
        with patch.object(budget, 'consume', side_effect=fail_retention):
            with self.assertRaises(BudgetExceeded):
                g.grid(fixtures()[0], budget, analysis=cache)
        self.assertEqual((cache.entry_count, cache.retained_cells), (0, 0))
        self.assertEqual(g.grid(fixtures()[0], budget, analysis=cache), fixtures()[0])

    def test_small_real_budgets_recover_without_poisoning_analysis(self):
        rows = fixtures()[0]
        step = p.Step('relate', role='largest', relation='right', effect='recolor')
        expected = p.apply_step(step, rows, budget=Budget(10000))
        for limit in range(0, 400, 7):
            budget = Budget(limit)
            cache = self.cache(budget)
            try:
                result = p.apply_step(step, rows, budget=budget, analysis=cache)
            except BudgetExceeded:
                self.assertLessEqual(budget.used, limit)
            else:
                self.assertEqual(result, expected)
            budget.limit = 10000
            self.assertEqual(p.apply_step(step, rows, budget=budget, analysis=cache), expected)

    def test_alias_roles_and_relations_share_one_canonical_map_and_render(self):
        rows = fixtures()[0]
        for effect in g.EFFECTS:
            budget = Budget(10**6)
            cache = self.cache(budget)
            relations = ('all',) * 3 if effect == 'extract' else ('right', 'right', 'same_row')
            steps = [p.Step('relate', role=role, relation=relation, effect=effect)
                     for role, relation in zip(('largest', 'leftmost', 'largest'), relations)]
            expected = p.apply_step(steps[0], rows, budget=Budget(10000))
            with self.subTest(effect=effect), \
                 patch.object(g._rel, 'map_objects', wraps=g._rel.map_objects) as mapping, \
                 patch.object(g._rel, 'render', wraps=g._rel.render) as render:
                outputs = [p.apply_step(step, rows, budget=budget, analysis=cache) for step in steps]
                self.assertEqual(outputs, [expected] * 3)
                self.assertIs(outputs[0], outputs[1])
                self.assertEqual(mapping.call_count, 1)
                self.assertEqual(render.call_count, 1)
                self.assertEqual(budget.counts['render_cells'], sum(map(len, expected)))
                self.assertEqual(budget.counts['role_attempts'], 3)

    def test_object_alias_roles_share_cell_edits_and_render(self):
        rows = fixtures()[0]
        for effect in g.OBJECT_EFFECTS:
            budget = Budget(10**6)
            cache = self.cache(budget)
            with self.subTest(effect=effect), patch.object(g._rel, 'render', wraps=g._rel.render) as render:
                outputs = [g.transform_object(rows, role=role, effect=effect, budget=budget, analysis=cache)
                           for role in ('largest', 'leftmost')]
                self.assertEqual(outputs[0], outputs[1])
                self.assertIs(outputs[0], outputs[1])
                self.assertEqual(render.call_count, 1)
                self.assertEqual(budget.counts['object_cell_index'], 4)
                self.assertEqual(budget.counts['render_cells'], sum(map(len, rows)))

    def test_alias_binding_failures_reuse_real_map_and_render_errors(self):
        cases = ((fixtures()[0], ('largest', 'leftmost'), 'same_shape', 'recolor', 'no target binding', 0),
                 (extra_fixtures()[0], ('largest', 'unique_shape'), 'right', 'stamp', 'edit outside grid', 1))
        for rows, roles, relation, effect, error, render_calls in cases:
            budget = Budget(10**6)
            cache = self.cache(budget)
            with self.subTest(error=error), \
                 patch.object(g._rel, 'map_objects', wraps=g._rel.map_objects) as mapping, \
                 patch.object(g._rel, 'render', wraps=g._rel.render) as render:
                for role in roles:
                    with self.assertRaisesRegex(ValueError, error):
                        g.apply_relation(rows, role=role, relation=relation, effect=effect,
                                         budget=budget, analysis=cache)
                self.assertEqual(mapping.call_count, 1)
                self.assertEqual(render.call_count, render_calls)
        budget = Budget(10**6)
        cache = self.cache(budget)
        for role in ('largest', 'leftmost'):
            with self.assertRaisesRegex(ValueError, 'fill would overwrite another object'):
                g.transform_object(fixtures()[2], role=role, effect='fill_box', budget=budget, analysis=cache)
        self.assertEqual(budget.counts['fill_box_cells'], 25)

    def test_render_exhaustion_is_never_reused_as_a_binding_failure(self):
        rows = fixtures()[0]
        budget = Budget(10**6)
        cache = self.cache(budget)
        with patch.object(g._rel, 'render', side_effect=BudgetExceeded('render budget')) as render:
            for role in ('largest', 'leftmost'):
                with self.assertRaises(BudgetExceeded):
                    g.apply_relation(rows, role=role, relation='right', effect='recolor',
                                     budget=budget, analysis=cache)
            self.assertEqual(render.call_count, 2)
        expected = g.apply_relation(rows, role='largest', relation='right', effect='recolor', budget=Budget(10000))
        with patch.object(g._rel, 'render', wraps=g._rel.render) as render:
            for role in ('largest', 'leftmost'):
                self.assertEqual(g.apply_relation(rows, role=role, relation='right', effect='recolor',
                                                 budget=budget, analysis=cache), expected)
            self.assertEqual(render.call_count, 1)

    def test_binding_key_hashes_and_retains_each_target_reference(self):
        rows = fixtures()[0]
        budget = Budget(10**6)
        cache = self.cache(budget)
        scene = g.ground(rows, budget, analysis=cache)
        source = g.select(scene, 'largest', budget, analysis=cache)
        deltas = {}
        for relation in ('right', 'all'):
            selected = g.targets(scene, source, relation, budget, analysis=cache)
            retained, entries = cache.retained_cells, cache.entry_count
            g.apply_relation(rows, role='largest', relation=relation, effect='recolor', budget=budget, analysis=cache)
            self.assertEqual(cache.entry_count, entries + 1)
            self.assertEqual(cache.retained_cells - retained, sum(map(len, rows)) + 1 + len(selected))
            before = dict(budget.counts)
            g.apply_relation(rows, role='largest', relation=relation, effect='recolor', budget=budget, analysis=cache)
            deltas[relation] = {key: value - before.get(key, 0) for key, value in budget.counts.items()}
            self.assertEqual(deltas[relation]['analysis_binding_refs'], 1 + len(selected))
            self.assertEqual(deltas[relation]['render_cells'], 0)
            self.assertEqual(deltas[relation]['analysis_writes'], 0)
        self.assertEqual(deltas['all']['analysis_key_units'] - deltas['right']['analysis_key_units'], 1)

    def test_render_cache_saturation_falls_back_without_unaccounted_retention(self):
        rows = fixtures()[0]
        for cap in ('max_cells', 'max_entries'):
            budget = Budget(10**6)
            cache = self.cache(budget)
            scene = g.ground(rows, budget, analysis=cache)
            source = g.select(scene, 'largest', budget, analysis=cache)
            g.select(scene, 'leftmost', budget, analysis=cache)
            selected = g.targets(scene, source, 'right', budget, analysis=cache)
            retained, entries = cache.retained_cells, cache.entry_count
            if cap == 'max_cells':
                # The grid fits, but the source/target identity retention does not.
                cache.max_cells = retained + sum(map(len, rows)) + len(selected)
            else:
                cache.max_entries = entries
            with patch.object(g._rel, 'render', wraps=g._rel.render) as render:
                results = [g.apply_relation(rows, role=role, relation='right', effect='recolor',
                                            budget=budget, analysis=cache)
                           for role in ('largest', 'leftmost')]
                self.assertEqual(results[0], results[1])
                self.assertEqual(render.call_count, 2)
            self.assertEqual((cache.retained_cells, cache.entry_count), (retained, entries))

    def test_binding_cache_keeps_checks_and_distinguishes_colliding_target_ids(self):
        rows = fixtures()[0]
        budget = Budget(10**6)
        cache = self.cache(budget)
        scene = g.ground(rows, budget, analysis=cache)
        identities = {id(obj): 17 + i * sys.hash_info.modulus for i, obj in enumerate(scene.objects)}
        real_id = id
        with patch.object(g, 'id', lambda obj: identities.get(real_id(obj), real_id(obj)), create=True), \
             patch.object(g._rel, 'render', wraps=g._rel.render) as render:
            outputs = [g.apply_relation(rows, role='largest', relation=relation, effect='recolor',
                                        budget=budget, analysis=cache) for relation in ('right', 'below')]
            self.assertNotEqual(outputs[0], outputs[1])
            self.assertEqual(render.call_count, 2)
        g.apply_relation(rows, role='largest', relation='all', effect='extract', budget=budget, analysis=cache)
        for role, relation, error in (('topmost', 'all', 'source role is ambiguous'),
                                      ('largest', 'right', 'extract uses the source')):
            with self.assertRaisesRegex(ValueError, error):
                g.apply_relation(rows, role=role, relation=relation, effect='extract', budget=budget, analysis=cache)

    def test_limits_are_nonnegative_integers(self):
        for name in ('max_entries', 'max_cells'):
            for value in (-1, False, 1.5):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    self.cache(Budget(10000), **{name: value})


if __name__ == '__main__':
    unittest.main()
