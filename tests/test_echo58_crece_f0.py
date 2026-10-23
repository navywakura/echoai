"""F0: exact development replay and adversarial plug boundary checks."""
import ast
import importlib
import json
import unittest
from collections import Counter
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

from echoai.echo58.acumula3 import bench as B3
from echoai.echo58.memx.world import Obs

ROOT = Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((ROOT / 'echo58/crece/runtime.py').exists(), 'F0 runtime is missing')
        self.rt = importlib.import_module('echoai.echo58.crece.runtime')
        self.obs = Obs(((9, 9, 9, 9), (9, 1, 1, 9), (9, 1, 2, 9), (9, 9, 9, 9)),
                       (1, 1), 0, 2, 0, False, False)
        self.world = SimpleNamespace(absolute=False, acts=('ENTER', 'PICK', 'TOGGLE'), reset=lambda: self.obs)

    def agent(self, fn, hook=None):
        r = self.rt
        p = r.Plug('test', fn, frozenset({r.DROP if hook is None else hook}))
        a = r.HAgent(plugs=(p,))
        a.run(self.world, max_steps=0)
        a._scan(self.obs.grid)
        a.cur_hand = self.obs.hand
        a.E[(1, 'ENTER', 0)] = [1, 0, 0, 0, 0, 0]
        return a, p

    def test_native_pieces_cannot_be_enabled(self):
        with self.assertRaises(ValueError):
            self.rt.HAgent(pieces={'clear'})
        a = self.rt.HAgent()
        with self.assertRaises(ValueError):
            a.pieces = {'clear'}
        self.assertEqual(a.pieces, frozenset())

    def test_hand_notes_survive_switches_and_reset_between_episodes(self):
        r = self.rt
        a, p = self.agent(lambda moment, v, c: (r.NOTE(0, r.HAND),))
        for hand in (2, 2, 1, 2):
            a._dispatch(r.DROP, replace(self.obs, hand=hand), self.world, r.Context())
        self.assertEqual(a._view(self.obs, self.world, p).note(0, r.HAND), 3)
        self.assertEqual(a._view(replace(self.obs, hand=1), self.world, p).note(0, r.HAND), 1)
        a.run(self.world, max_steps=0)
        a._scan(self.obs.grid)
        self.assertEqual(a._view(self.obs, self.world, p).note(0, r.HAND), 0)

    def test_invalid_output_abstains_atomically(self):
        r = self.rt
        def boom(moment, v, c):
            raise ValueError('bad piece')
        for fn in (boom, lambda m, v, c: 'garbage',
                   lambda m, v, c: (r.NOTE(0, r.HAND), r.GOTO((0, 0)))):
            a, p = self.agent(fn)
            self.assertIsNone(a._dispatch(r.DROP, self.obs, self.world, r.Context()))
            self.assertEqual(len(a.plug_errors), 1)
            self.assertEqual(a._view(self.obs, self.world, p).note(0, r.HAND), 0)

    def test_view_is_deeply_read_only_and_does_not_query_live_memory(self):
        from echoai.echo58.acumula.config import ConfMemory, Config
        r = self.rt
        a, p = self.agent(lambda m, v, c: ())
        a.source = ConfMemory(Config())
        for _ in range(3):
            a.source.observe(2, a.sig(2), 'ENTER', 0, 'HURT')
        before = (a.source.queries, dict(a.answers), dict(a.why), dict(a.belief_cache))
        v = a._view(self.obs, self.world, p)
        self.assertEqual(v.belief(2, r.ENTER, 0), r.HURT)
        self.assertEqual(before, (a.source.queries, a.answers, a.why, a.belief_cache))
        with self.assertRaises((AttributeError, TypeError)):
            v.hand = 7
        with self.assertRaises(TypeError):
            v.grid[0][0] = 7
        with self.assertRaises(AttributeError):
            v.reach().add((0, 0))

    def test_ban_only_restricts_and_expires_with_progress(self):
        r = self.rt
        a, p = self.agent(lambda m, v, c: (r.BAN_UNTIL_PROGRESS(2, r.ENTER),), r.OUTCOME)
        a.E[(2, 'ENTER', 0)] = [0, 0, 1, 0, 0, 0]
        before = a.belief(2, 'ENTER', 0)
        self.assertEqual(before, 'HURT')
        a._dispatch(r.OUTCOME, self.obs, self.world, r.Context())
        self.assertEqual(a.belief(2, 'ENTER', 0), 'NOOP')
        a.progress += 1
        self.assertEqual(a.belief(2, 'ENTER', 0), before)

    def test_order_first_action_wins_notes_continue(self):
        r = self.rt
        calls = []
        a, p = self.agent(lambda m, v, c: (r.NOTE(0),), r.DECIDE)
        def ban(m, v, c):
            calls.append('ban')
            return (r.BAN(2, r.PICK, r.ANY),)
        def last(m, v, c):
            calls.append('last')
            return ()
        a.plugs += (r.Plug('ban', ban, frozenset({r.DECIDE})),
                    r.Plug('last', last, frozenset({r.DECIDE})))
        a._dispatch(r.DECIDE, self.obs, self.world, r.Context())
        self.assertEqual(calls, ['ban'])
        self.assertEqual(a._view(self.obs, self.world, p).note(0), 1)
        self.assertEqual(a.belief(2, 'PICK', 0), 'NOOP')

    def test_clear_counts_failed_search_and_stops_after_eighth(self):
        self.assertTrue((ROOT / 'echo58/crece/pieces_b3.py').exists(), 'external pieces are missing')
        pieces = importlib.import_module('echoai.echo58.crece.pieces_b3')
        r = self.rt
        self.obs = replace(self.obs, grid=((9, 9, 9, 9, 9), (9, 1, 1, 1, 9), (9, 9, 9, 9, 9)))
        a, p = self.agent(pieces.clear)
        a._notes = {'test': {(0, 2): 7}}
        self.assertEqual(a._dispatch(r.DROP, self.obs, self.world, r.Context()), r.GOTO((2, 1)))
        self.assertIsNone(a._dispatch(r.DROP, self.obs, self.world, r.Context()))
        self.assertEqual(a._view(self.obs, self.world, p).note(0, r.HAND), 9)

    def test_later_bans_cannot_weaken_any_or_other_hands(self):
        r = self.rt
        sequence = iter((r.ANY, r.HAND))
        a, p = self.agent(lambda m, v, c: (r.BAN(1, r.ENTER, next(sequence)),), r.DECIDE)
        for _ in range(2):
            a._dispatch(r.DECIDE, self.obs, self.world, r.Context())
        a.cur_hand = 0
        self.assertEqual(a.belief(1, 'ENTER', 0), 'NOOP')
        a, p = self.agent(lambda m, v, c: (r.BAN(1, r.ENTER, r.HAND),), r.DECIDE)
        for hand in (2, 9):
            a.cur_hand = hand
            a._dispatch(r.DECIDE, replace(self.obs, hand=hand), self.world, r.Context())
        for hand in (2, 9):
            a.cur_hand = hand
            self.assertEqual(a.belief(1, 'ENTER', 0), 'NOOP')
        a.cur_hand = 0
        self.assertEqual(a.belief(1, 'ENTER', 0), 'PASS')


class EquivalenceTests(unittest.TestCase):
    def test_sample_all_configurations_both_memory_protocols(self):
        self.assertTrue((ROOT / 'echo58/crece/equiv.py').exists(), 'equivalence runner is missing')
        eq = importlib.import_module('echoai.echo58.crece.equiv')
        result = eq.run_suite(seeds=(7_000_000,), families=('KeyCorridorS3R2',), max_steps=80)
        self.assertEqual(result['pairs'], 16)
        self.assertTrue(result['identical'], result.get('first_difference'))
        self.assertEqual(result['plug_errors'], 0)

    def test_external_pieces_are_integer_and_do_not_use_native_agent(self):
        path = ROOT / 'echo58/crece/pieces_b3.py'
        self.assertTrue(path.exists(), 'external pieces are missing')
        for n in ast.walk(ast.parse(path.read_text())):
            if isinstance(n, ast.ImportFrom):
                self.assertNotIn('b3', n.module or '')
                self.assertNotIn('PAgent', [a.name for a in n.names])
            if isinstance(n, ast.Attribute):
                self.assertFalse(n.attr.startswith('_'))
            self.assertFalse(isinstance(n, ast.Constant) and isinstance(n.value, float))
            self.assertFalse(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div))

    def test_frozen_sources_match_sealed_preflight(self):
        pf = json.loads((B3.LAB / 'preflight.json').read_text())
        self.assertEqual(B3.frozen_state(), pf['frozen'])


if __name__ == '__main__':
    unittest.main()
