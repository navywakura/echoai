"""Small development checks; no sealed tasks or benchmark artifacts."""
from contextlib import ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import unittest
from unittest.mock import patch

from echo5 import curriculum, grounding, programs, solver, transfer
from echo5.budget import Budget
from echo5 import transfer_independent as independent


def fixture_scene():
    # A solid 3x3 with a one-cell tail, and two separated L distractors.
    return {'height': 9, 'width': 10, 'objects': [
        {'color': 2, 'cells': [[1, 1], [1, 2], [1, 3], [2, 1], [2, 2],
                               [2, 3], [3, 1], [3, 2], [3, 3], [4, 1]]},
        {'color': 4, 'cells': [[1, 6], [2, 6], [2, 7]]},
        {'color': 6, 'cells': [[6, 1], [6, 2], [7, 2]]}]}


def connected(cells):
    pending = set(map(tuple, cells))
    seen = {pending.pop()}
    frontier = list(seen)
    while frontier:
        y, x = frontier.pop()
        for cell in ((y-1, x), (y+1, x), (y, x-1), (y, x+1)):
            if cell in pending:
                pending.remove(cell)
                seen.add(cell)
                frontier.append(cell)
    return not pending


class OracleTests(unittest.TestCase):
    def test_literal_outline_and_fill_examples(self):
        scene = fixture_scene()
        original = deepcopy(scene)
        self.assertEqual(independent.oracle_output(scene, 'outline_extract_scale'), [
            [2, 2, 2, 2, 2, 2], [2, 2, 2, 2, 2, 2],
            [2, 2, 0, 0, 2, 2], [2, 2, 0, 0, 2, 2],
            [2, 2, 2, 2, 2, 2], [2, 2, 2, 2, 2, 2],
            [2, 2, 0, 0, 0, 0], [2, 2, 0, 0, 0, 0]])
        self.assertEqual(independent.oracle_output(scene, 'fill_extract_tile'),
                         [[2, 2, 2, 2, 2, 2] for _ in range(4)])
        self.assertEqual(scene, original)

    def test_literal_relation_and_packing_compositions(self):
        scene = {'height': 7, 'width': 10, 'objects': [
            {'color': 2, 'cells': [[1, 4], [2, 4], [2, 5], [3, 4]]},
            {'color': 3, 'cells': [[1, 1], [2, 1], [2, 2]]},
            {'color': 4, 'cells': [[4, 8], [5, 8]]}]}
        self.assertEqual(independent.oracle_output(scene, 'right_erase_crop_rotate'),
                         [[0, 3, 3], [0, 3, 0], [0, 0, 0], [2, 2, 2], [0, 2, 0]])
        self.assertEqual(independent.oracle_output(scene, 'pack_reflect'),
                         [[4, 0, 0, 3, 0, 0, 2],
                          [4, 0, 3, 3, 0, 2, 2],
                          [0, 0, 0, 0, 0, 0, 2]])
        reflected = independent.oracle_output(scene, 'below_recolor_reflect')
        self.assertEqual(reflected[4], [0, 2, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(reflected[5], [0, 2, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(reflected[1][8], 3)

    def test_inside_means_strict_box_even_for_an_open_container(self):
        # Open U: the inside target is not topologically enclosed.
        scene = {'height': 8, 'width': 9, 'objects': [
            {'color': 2, 'cells': [[y, 1] for y in range(1, 6)]
             + [[y, 5] for y in range(1, 6)] + [[5, x] for x in (2, 3, 4)]},
            {'color': 3, 'cells': [[3, 3]]},
            {'color': 4, 'cells': [[2, 7], [3, 7], [3, 8]]}]}
        self.assertEqual(independent.oracle_output(scene, 'inside_erase_crop'), [
            [0, 0, 0, 2, 0, 0, 0, 2], [0, 4, 0, 2, 0, 0, 0, 2],
            [4, 4, 0, 2, 0, 0, 0, 2], [0, 0, 0, 2, 0, 0, 0, 2],
            [0, 0, 0, 2, 2, 2, 2, 2]])

    def test_generation_and_oracle_cannot_call_actor_or_old_generator(self):
        with ExitStack() as stack:
            for module, names in (
                (programs, ('execute', 'apply_step', 'expand')),
                (grounding, ('ground', 'select', 'targets', 'apply_relation',
                             'transform_object', 'pack_objects')),
                (solver, ('solve',)),
                (curriculum, ('_scene',)),
                (transfer, ('make_case', '_morphology_example', '_packing_example',
                            '_containment_example', '_control_example'))):
                for name in names:
                    stack.enter_context(patch.object(module, name,
                        side_effect=AssertionError('oracle/actor coupling: ' + name)))
            for family in independent.FAMILIES:
                case = independent.make_case(81, family)
                self.assertEqual(len(case['expected']), 2)
                self.assertGreater(case['costs']['oracle']['used'], 0)

    def test_supported_witnesses_agree_with_already_constructed_truth(self):
        # Execution is a test of compatibility, never a source of oracle labels.
        for family in independent.SUPPORTED_FAMILIES:
            case = independent.make_case(19, family)
            pairs = case['task']['train'] + [
                {'input': row['input'], 'output': output}
                for row, output in zip(case['task']['test'], case['expected'])]
            for pair in pairs:
                with self.subTest(family=family):
                    actual = programs.execute(case['witness'], pair['input'])
                    self.assertEqual([list(row) for row in actual], pair['output'])


class GeneratorTests(unittest.TestCase):
    def test_every_family_varies_object_counts_and_has_irregular_components(self):
        for family in independent.FAMILIES:
            case = independent.make_case(47, family)
            scenes = case['scenes']
            self.assertEqual({len(s['objects']) for s in scenes}, {3, 4, 5, 6})
            for scene, pair in zip(scenes, case['task']['train'] + case['task']['test']):
                objects = scene['objects']
                actual = grounding.ground(pair['input'], Budget(100_000))
                self.assertEqual(len(actual.objects), len(objects))
                self.assertEqual(actual.background, 0)
                for obj in objects:
                    self.assertTrue(connected(obj['cells']))
                    ys, xs = zip(*obj['cells'])
                    self.assertLess(len(obj['cells']),
                                    (max(ys)-min(ys)+1) * (max(xs)-min(xs)+1))

    def test_repeatable_detached_and_no_global_rng_side_effects(self):
        before = random.getstate()
        case = independent.make_case(29, 'fill_extract_tile')
        copy = independent.make_case(29, 'fill_extract_tile')
        self.assertEqual(case, copy)
        self.assertEqual(random.getstate(), before)
        self.assertNotEqual(case['sha256'], independent.make_case(30, 'fill_extract_tile')['sha256'])
        public = independent.public_task(case)
        self.assertEqual(set(public), {'train', 'test'})
        self.assertTrue(all(set(row) == {'input'} for row in public['test']))
        public['train'][0]['output'][0][0] = 9
        public['test'][0]['input'][0][0] = 8
        case['scenes'][0]['objects'][0]['cells'][0][0] = 99
        self.assertEqual(case['task'], copy['task'])
        self.assertEqual(case['expected'], copy['expected'])
        self.assertIsNot(case['task']['train'][0]['output'][0],
                         case['task']['train'][0]['output'][1])
        train = {json.dumps(p['input']) for p in case['task']['train']}
        self.assertTrue(all(json.dumps(p['input']) not in train for p in case['task']['test']))

    def test_no_mutable_aliases_anywhere_in_a_generated_case(self):
        case = independent.make_case(17, 'ambiguous_reflection')
        seen = set()

        def visit(value):
            if isinstance(value, (dict, list)):
                self.assertNotIn(id(value), seen, 'two receipt paths share a mutable object')
                seen.add(id(value))
                for child in value.values() if isinstance(value, dict) else value:
                    visit(child)

        visit(case)

    def test_directional_tasks_include_targets_and_nontarget_distractors(self):
        for family in ('right_erase_crop_rotate', 'below_recolor_reflect', 'inside_erase_crop'):
            case = independent.make_case(82, family)
            for scene in case['scenes']:
                source = max(scene['objects'], key=lambda o: len(o['cells']))
                ys, xs = zip(*source['cells'])
                flags = []
                for obj in scene['objects']:
                    if obj is source:
                        continue
                    oy, ox = zip(*obj['cells'])
                    flags.append(min(ox) > max(xs) if family.startswith('right') else
                                 min(oy) > max(ys) if family.startswith('below') else
                                 min(ys) < min(oy) <= max(oy) < max(ys)
                                 and min(xs) < min(ox) <= max(ox) < max(xs))
                self.assertIn(True, flags)
                self.assertIn(False, flags)

    def test_ambiguous_and_unsupported_controls_have_distinct_evidence(self):
        case = independent.make_case(10, 'ambiguous_reflection')
        self.assertEqual(case['category'], 'ambiguous_control')
        for pair in case['task']['train']:
            self.assertEqual(pair['input'], pair['output'])
            self.assertEqual(pair['input'], [r[::-1] for r in pair['input']])
        for pair, expected in zip(case['task']['test'], case['expected']):
            self.assertNotEqual(pair['input'], expected)
        case = independent.make_case(10, 'unsupported_new_color')
        self.assertEqual(case['category'], 'unsupported_control')
        for pair in case['task']['train']:
            self.assertNotIn(9, {c for row in pair['input'] for c in row})
            self.assertIn(9, {c for row in pair['output'] for c in row})

    def test_strict_arguments(self):
        for seed in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                independent.make_case(seed, 'fill_extract_tile')
        with self.assertRaises(ValueError):
            independent.make_case(1, 'not_a_family')
        for args in ({'cases_per_family': 0}, {'budget': True}, {'budget': -1}):
            with self.assertRaises(ValueError):
                independent.run_benchmark(**args)


class BenchmarkTests(unittest.TestCase):
    def test_tiny_real_run_receipts_costs_and_unpaired_comparator(self):
        report = independent.run_benchmark(seed=31, cases_per_family=1, budget=1)
        self.assertEqual(report['schema'], 'echo5.transfer_independent.v1')
        self.assertTrue(report['instrument_valid'])
        self.assertEqual(report['comparison']['design'], 'independent_samples_not_paired')
        self.assertEqual(set(report['independent']['families']), set(independent.FAMILIES))
        self.assertEqual(set(report['template']['families']), set(independent.COMPARABLE_FAMILIES))
        self.assertEqual(report['independent']['solver_settings'], report['template']['solver_settings'])
        for arm in ('independent', 'template'):
            for family, totals in report[arm]['families'].items():
                self.assertEqual(totals['cases'], 1)
                self.assertEqual(totals['exact'] + totals['abstention'] + totals['wrong'], 1)
                self.assertEqual(totals['abstention'], 1)
            for receipt in report[arm]['receipts']:
                self.assertEqual(receipt['result']['status'], 'budget_exhausted')
                self.assertEqual(receipt['outcome'], 'abstention')
                self.assertEqual(receipt['costs']['solve']['used'],
                                 receipt['result']['metrics']['used'])
                for ledger in receipt['costs'].values():
                    if ledger is not None:
                        self.assertEqual(sum(ledger['counts'].values()), ledger['used'])
                self.assertIn('expected', receipt['case'])
                self.assertNotIn('output', receipt['case']['task']['test'][0])
        self.assertTrue(report['sources']['files'])
        groups = report['independent']['by_category']
        self.assertEqual(groups['supported']['cases'], len(independent.SUPPORTED_FAMILIES))
        self.assertEqual(groups['ambiguous_control']['cases'], 1)
        self.assertEqual(groups['unsupported_control']['cases'], 1)
        self.assertEqual(groups['unsupported_control']['control_pass'], 0)
        json.dumps(report, allow_nan=False)

    def test_fresh_process_replays_entire_small_report_with_different_hash_seeds(self):
        # One unit of solve work per case; no full research run in this test.
        src = str(Path(__file__).resolve().parents[1] / 'src')
        code = (f'import sys; sys.path.insert(0, {src!r}); '
                'import json; from echo5.transfer_independent import run_benchmark; '
                'print(json.dumps(run_benchmark(seed=2400000, cases_per_family=1, budget=1), '
                'sort_keys=True, separators=(",", ":")))')
        outputs = [subprocess.check_output([sys.executable, '-B', '-c', code],
                   env={**os.environ, 'PYTHONHASHSEED': str(seed), 'PYTHONDONTWRITEBYTECODE': '1'},
                   timeout=20) for seed in (7, 991)]
        self.assertEqual(outputs[0], outputs[1])

    def test_actor_boundary_excludes_metadata_and_does_not_share_objects(self):
        calls = []
        real_solve = solver.solve

        def observing_solve(task, **options):
            self.assertEqual(set(task), {'train', 'test'})
            self.assertTrue(all(set(p) == {'input', 'output'} for p in task['train']))
            self.assertTrue(all(set(p) == {'input'} for p in task['test']))
            self.assertFalse(options['learn'])
            self.assertIsNone(options['library'])
            result = real_solve(task, **options)
            task['train'][0]['input'][0][0] = 9
            calls.append(options)
            return result

        with patch.object(solver, 'solve', side_effect=observing_solve):
            report = independent.run_benchmark(seed=5, cases_per_family=1, budget=1)
        self.assertEqual(len(calls), len(independent.FAMILIES) + len(independent.COMPARABLE_FAMILIES))
        for arm in ('independent', 'template'):
            self.assertTrue(all(r['case']['task']['train'][0]['input'][0][0] == 0
                                for r in report[arm]['receipts']))

    def test_scoring_distinguishes_wrong_predictions_and_control_lucky_guesses(self):
        case = independent.make_case(2, 'fill_extract_tile')
        answer = {'status': 'solved', 'predictions': deepcopy(case['expected']),
                  'test_verified': False}
        self.assertEqual(independent.score_result(case, answer)['outcome'], 'exact')
        answer['predictions'][0][0][0] = 0
        self.assertEqual(independent.score_result(case, answer)['outcome'], 'wrong')
        answer['predictions'] = [case['expected'][0]]
        self.assertEqual(independent.score_result(case, answer)['outcome'], 'wrong')
        control = independent.make_case(2, 'ambiguous_reflection')
        answer['predictions'] = deepcopy(control['expected'])
        score = independent.score_result(control, answer)
        self.assertEqual(score['outcome'], 'exact')
        self.assertFalse(score['control_pass'])
        self.assertTrue(score['false_commitment'])
        score = independent.score_result(control, {'status': 'ambiguous', 'predictions': []})
        self.assertEqual(score['outcome'], 'abstention')
        self.assertTrue(score['control_pass'])
        score = independent.score_result(control, {'status': 'budget_exhausted', 'predictions': []})
        self.assertFalse(score['control_pass'])
        with self.assertRaises(RuntimeError):
            independent.score_result(case, {'status': 'invalid_task', 'predictions': []})

    def test_scoring_rejects_boolean_pixels_and_predictions_during_abstention(self):
        case = {'category': 'supported', 'expected': [[[1]]]}
        result = {'status': 'solved', 'predictions': [[[True]]], 'test_verified': False}
        self.assertEqual(independent.score_result(case, result)['outcome'], 'wrong')
        with self.assertRaises(RuntimeError):
            independent.score_result(case, {'status': 'unsolved', 'predictions': [[[1]]]})


if __name__ == '__main__':
    unittest.main()
