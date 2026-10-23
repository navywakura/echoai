"""The model's source is interpreted data, never executable host Python."""
import importlib
from pathlib import Path
import unittest
from echoai.tests.test_echo58_crece_f0 import RuntimeTests


class LanguageTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'echo58/crece/language.py'
        self.assertTrue(path.exists(), 'restricted interpreter missing')
        self.lang = importlib.import_module('echoai.echo58.crece.language')
        fixture = RuntimeTests()
        fixture.setUp()
        self.r = fixture.rt
        self.a, self.p = fixture.agent(lambda m, v, c: ())
        self.v = self.a._view(fixture.obs, fixture.world, self.p)
        self.c = self.r.Context()

    def test_integer_piece_returns_valid_effect(self):
        source = 'def piece(moment, v, c):\n    if moment == DROP and v.hand:\n        return (NOTE(0, HAND),)\n    return ()\n'
        f = self.lang.Program(source)
        self.assertEqual(f(self.r.DROP, self.v, self.c), (self.r.NOTE(0, self.r.HAND),))
        self.assertEqual(f(self.r.DECIDE, self.v, self.c), ())

    def test_untrusted_capabilities_rejected_before_execution(self):
        for body in ('import os', 'return open("/etc/passwd")', 'return v.__class__',
                     'return getattr(v, "hand")', 'v.hand = 1', 'while True: pass',
                     'return piece(moment, v, c)', 'return 1 / 2', 'return 0.5'):
            with self.subTest(body=body), self.assertRaises(self.lang.InvalidProgram):
                self.lang.Program('def piece(moment, v, c):\n    ' + body + '\n')

    def test_operation_budget_applies_to_every_real_invocation(self):
        f = self.lang.Program('def piece(moment, v, c):\n    n = 0\n    for a in range(256):\n        for b in range(256):\n            n += 1\n    return ()\n')
        for _ in range(2):
            with self.assertRaises(self.lang.LimitExceeded):
                f(0, self.v, self.c)

    def test_integer_and_collection_bombs_bounded_before_allocation(self):
        for expr in ('2147483647 + 1', '(1,) * 2147483647', 'range(257)'):
            f = self.lang.Program('def piece(moment, v, c):\n    x = ' + expr + '\n    return ()\n')
            with self.subTest(expr=expr), self.assertRaises(self.lang.LimitExceeded):
                f(0, self.v, self.c)

    def test_nested_collection_size_counts_descendants(self):
        f = self.lang.Program('def piece(moment, v, c):\n    a = (1,) * 128\n    b = (a,) * 128\n    return ()\n')
        with self.assertRaises(self.lang.LimitExceeded):
            f(0, self.v, self.c)

    def test_lambda_is_only_a_direct_selection_key_not_storable_data(self):
        for body in ('a = (lambda x: x)', 'return (lambda x: x,)',
                     'return (lambda x: x) == (lambda x: x)'):
            with self.subTest(body=body), self.assertRaises(self.lang.InvalidProgram):
                self.lang.Program('def piece(moment, v, c):\n    ' + body + '\n')

    def test_bounded_comprehensions_and_sorted_keys(self):
        f = self.lang.Program('def piece(moment, v, c):\n    cells = tuple(p for p in v.reach() if p != v.pos)\n    if cells:\n        target = min(cells, key=lambda p: (v.visits(p), p))\n        return (GOTO(target),)\n    return ()\n')
        self.assertEqual(f(0, self.v, self.c), (self.r.GOTO((1, 2)),))


if __name__ == '__main__':
    unittest.main()
