"""Seeded metamorphic checks on existing DSL operations, not ARC benchmark tasks."""
from __future__ import annotations

import random
import unittest

from seed import dsl


class GridProperties(unittest.TestCase):
    def setUp(self) -> None:
        rng = random.Random(45001)
        shapes = [(1, 1), (1, 30), (30, 1), (30, 30)]
        shapes += [(rng.randrange(1, 31), rng.randrange(1, 31)) for _ in range(96)]
        self.grids = [dsl.G([[rng.randrange(10) for _ in range(w)] for _ in range(h)]) for h, w in shapes]

    def test_rotation_group(self) -> None:
        for g in self.grids:
            with self.subTest(shape=(len(g), len(g[0]))):
                self.assertEqual(dsl.rot90(dsl.rot90(dsl.rot90(dsl.rot90(g)))), g)
                self.assertEqual(dsl.rot180(g), dsl.rot90(dsl.rot90(g)))
                self.assertEqual(dsl.rot270(g), dsl.rot90(dsl.rot180(g)))

    def test_reflections_and_transpose_are_involutions(self) -> None:
        for g in self.grids:
            for operation in (dsl.flipud, dsl.fliplr, dsl.transpose):
                with self.subTest(operation=operation.__name__, shape=(len(g), len(g[0]))):
                    self.assertEqual(operation(operation(g)), g)

    def test_dimension_and_palette_conservation(self) -> None:
        for g in self.grids:
            for operation in (dsl.rot90, dsl.rot270, dsl.transpose):
                actual = operation(g)
                self.assertEqual((len(actual), len(actual[0])), (len(g[0]), len(g)))
                self.assertEqual(dsl.palette(actual), dsl.palette(g))

    def test_replays_and_input_immutability(self) -> None:
        for g in self.grids[:10]:
            for operation in dsl.NO_ARG:
                before = repr(g)
                outcomes = []
                for _ in range(2):
                    try:
                        outcomes.append(("ok", dsl.apply_step(g, (operation,))))
                    except ValueError as exc:
                        outcomes.append(("invalid", str(exc)))
                with self.subTest(operation=operation):
                    self.assertEqual(outcomes[0], outcomes[1])
                    self.assertEqual(repr(g), before)

    def test_shape_boundary_rejections(self) -> None:
        cases: list[list[list[int]]] = [[], [[]], [[1], [1, 2]], [[1]]*31, [[1]*31]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                dsl.G(rows)
