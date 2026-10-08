import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from seed import arc_comparison as c
from seed.final_arc import accounting


def grid_row(tid, correct=False):
    return {'task': tid, 'correct': correct, 'public_sha256': tid, 'budget': 400,
            'result': {'expansions': 10, 'test_ok': None}}


def arc_row(game='game', actions=2):
    row = {'game': game, 'actions': [['K', 1, None]] * actions,
           'frames': ['frame'] * (actions + 1), 'levels': [0] * actions + [1],
           'resets': 0, 'automatic_reset_indices': [], 'actions_per_level': [actions],
           'levels_completed': 1, 'win_levels': 2, 'baseline': [1, 1], 'budget': 2000,
           'sdk_counter_verified': True, 'contract_score': 100 * (1 / actions) ** 2 / 3}
    row['accounting'] = accounting(row)
    return row


class ComparisonTests(unittest.TestCase):
    def test_zero_baseline_is_not_infinite_or_one_hundred_percent(self):
        result = c.delta(0, 3, 120)
        self.assertIsNone(result['relative_percent'])
        self.assertEqual(result['percentage_points'], 2.5)
        self.assertEqual(c.delta(20, 31, 400)['relative_percent'], 55)

    def test_invalid_counts_and_denominators_are_rejected(self):
        for args in [(0, 1, 0), (False, 1, 2), (1, 3, 2), (-1, 1, 2)]:
            with self.assertRaises(ValueError):
                c.delta(*args)

    def test_paired_grid_changes_keep_losses_visible(self):
        before = [grid_row('a', True), grid_row('b')]
        after = [grid_row('b', True), grid_row('a')]
        result = c.compare_grid_rows(before, after, ['a', 'b'], {'a': ['objects'], 'b': ['relations']})
        self.assertEqual(result['overall']['absolute'], 0)
        self.assertEqual(result['gained'], ['b'])
        self.assertEqual(result['lost'], ['a'])
        self.assertEqual(result['by_capability']['objects']['absolute'], -1)

    def test_missing_duplicate_different_input_or_budget_never_compares(self):
        before = [grid_row('a'), grid_row('b')]
        bad_cases = [before[:1], [before[0], before[0]], [dict(before[0], budget=401), before[1]],
                     [dict(before[0], public_sha256='other'), before[1]]]
        leaked = copy.deepcopy(before)
        leaked[0]['result']['test_ok'] = False
        bad_cases.append(leaked)
        over = copy.deepcopy(before)
        over[0]['result']['expansions'] = 401
        bad_cases.append(over)
        for after in bad_cases:
            with self.subTest(after=after), self.assertRaises(ValueError):
                c.compare_grid_rows(before, after, ['a', 'b'])

    def test_arc_weighted_score_and_action_regression(self):
        result = c.compare_arc_rows([arc_row()], [arc_row(actions=4)], ['game'])
        self.assertEqual(result['levels']['absolute'], 0)
        self.assertLess(result['score_delta'], 0)
        self.assertEqual(result['games_losing_score'], ['game'])
        altered = arc_row()
        altered['contract_score'] += 0.01
        with self.assertRaisesRegex(ValueError, 'score'):
            c.arc_totals([altered])

    def test_arc_automatic_reset_accounting_cannot_be_falsified(self):
        altered = arc_row()
        altered['accounting']['total_actions'] += 1
        with self.assertRaisesRegex(ValueError, 'accounting'):
            c.arc_totals([altered])

    def test_frozen_sources_are_verified_without_refreezing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'agent.py'
            source.write_text('x = 1\n')
            profile = root / 'profile.json'
            profile.write_text(json.dumps({'sources': {'agent.py': c.file_sha(source)}}))
            before = profile.read_bytes()
            c.freeze_guard(root, ['profile.json'])
            source.write_text('x = 2\n')
            with self.assertRaisesRegex(ValueError, 'protected source changed'):
                c.freeze_guard(root, ['profile.json'])
            self.assertEqual(profile.read_bytes(), before)

    def release(self):
        strategies = {name: {'format': 'local', 'program': {'patches': []}}
                      for name in ('echo', 'fijo', 'semilla', 'sinfiltro')}
        profile = {'sources': {'agent.py': 'digest'}}
        checks = {k: True for k in ('B1', 'B2', 'B3', 'B4', 'B5')}
        closed = {'result': 'EXAM_CLOSED', 's6_green': True, 'exam_opened': True, 'checks': checks}
        completed = {'sources': profile['sources'], 'profile_sha256': c.digest(profile),
                     'strategies_sha256': c.digest(strategies)}
        audit = dict(completed, green=True, checks=checks, training_audit=True, model_payload_audit=True,
                     replays={k: True for k in strategies})
        return closed, audit, completed, strategies, profile

    def test_candidate_needs_all_five_criteria_and_bound_policy(self):
        args = self.release()
        self.assertEqual(c.validate_release(*args), args[3]['echo'])
        for location, field, value in [(0, 's6_green', False), (1, 'training_audit', False),
                                       (1, 'strategies_sha256', 'changed')]:
            changed = copy.deepcopy(args)
            changed[location][field] = value
            with self.assertRaises(ValueError):
                c.validate_release(*changed)
        for criterion in ('B1', 'B2', 'B3', 'B4', 'B5'):
            changed = copy.deepcopy(args)
            changed[1]['checks'][criterion] = False
            with self.assertRaises(ValueError):
                c.validate_release(*changed)

    def test_pending_s6_cannot_open_a_followup_or_load_runtime(self):
        with patch.object(c, 'prepared', return_value={}), patch.object(c, 'candidate_available', return_value=False):
            with self.assertRaisesRegex(ValueError, 'pending or red'):
                c.freeze_candidate(Path('/nonexistent/preparation'))


class ArcAdapterTests(unittest.TestCase):
    def test_empty_b11_policy_preserves_native_actor_on_development_game(self):
        try:
            import arc_agi
        except ImportError:
            self.skipTest('managed ARC runtime required')
        from seed.final_arc import one
        game = 'bp35-0a0ad940'
        a = one(game, {'kind': 'base'}, budget=40)
        b = c.arc_one(game, {'format': 'local', 'program': {'patches': []}}, budget=40)
        for field in ('actions', 'frames', 'levels', 'accounting', 'model', 'contract_score'):
            self.assertEqual(c.digest(a[field]), c.digest(b[field]), field)


if __name__ == '__main__':
    unittest.main()
