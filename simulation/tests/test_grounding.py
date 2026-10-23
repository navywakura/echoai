"""Hand checked scenes: ties, contextual roles, and relative transfer."""
import unittest

from echo5.budget import Budget, BudgetExceeded
from echo5 import grounding as g
from echo5.legacy import module


def scene_fixture(color=2, other=4, dy=0, dx=0):
    rows = [[0] * 12 for _ in range(10)]
    # Unique L shape; two identical singletons, one to its right and one below.
    for y, x in ((2, 2), (3, 2), (3, 3)):
        rows[y + dy][x + dx] = color
    rows[2 + dy][7 + dx] = other
    rows[6 + dy][2 + dx] = other
    return rows


class GroundingTests(unittest.TestCase):
    def test_reuses_canonical_objects(self):
        scene = g.ground(scene_fixture(), Budget(10000))
        self.assertIsInstance(scene, module('seed.relational_dsl').Scene)
        self.assertIsInstance(scene.objects[0], module('seed.relational_dsl').Object)

    def test_distinctive_shape_survives_color_and_layout_change(self):
        for color, other, dy, dx in ((2, 4, 0, 0), (9, 6, 1, 2)):
            budget = Budget(10000)
            scene = g.ground(scene_fixture(color, other, dy, dx), budget)
            obj = g.select(scene, 'unique_shape', budget)
            self.assertEqual(obj.color, color)
            self.assertEqual(obj.shape, ((0, 0), (1, 0), (1, 1)))

    def test_strict_direction_is_from_source_to_target(self):
        budget = Budget(10000)
        scene = g.ground(scene_fixture(), budget)
        obj = g.select(scene, 'largest', budget)
        self.assertEqual([o.anchor for o in g.targets(scene, obj, 'right', budget)], [(2, 7)])
        self.assertEqual([o.anchor for o in g.targets(scene, obj, 'below', budget)], [(6, 2)])
        right = g.targets(scene, obj, 'right', budget)[0]
        self.assertIn(obj, g.targets(scene, right, 'left', budget))
        lower = g.targets(scene, obj, 'below', budget)[0]
        self.assertIn(obj, g.targets(scene, lower, 'above', budget))

    def test_ties_abstain_and_cost_work(self):
        budget = Budget(10000)
        scene = g.ground(scene_fixture(), budget)
        before = budget.used
        for role in ('smallest', 'topmost'):
            with self.assertRaises(ValueError):
                g.select(scene, role, budget)
        self.assertGreater(budget.used, before)

    def test_multiple_distinctive_shapes_are_not_a_unique_role(self):
        budget = Budget(10000)
        scene = g.ground([[0, 0, 0, 0, 0], [0, 2, 0, 3, 0], [0, 2, 0, 0, 0], [0]*5], budget)
        with self.assertRaises(ValueError):
            g.select(scene, 'unique_shape', budget)

    def test_contextual_shape_role_is_not_an_alias_for_largest(self):
        rows = [[0]*12 for _ in range(10)]
        for y, x in ((2, 2), (3, 2), (3, 3)):
            rows[y][x] = 8
        for y, x in ((2, 7), (2, 8), (3, 7), (3, 8), (6, 7), (6, 8), (7, 7), (7, 8)):
            rows[y][x] = 3
        budget = Budget(10000)
        scene = g.ground(rows, budget)
        with self.assertRaises(ValueError):
            g.select(scene, 'largest', budget)
        self.assertEqual(g.select(scene, 'unique_shape', budget).color, 8)

    def test_recolor_reads_source_color_without_mutating_input(self):
        rows = scene_fixture(9, 6, 1, 2)
        out = g.apply_relation(rows, role='unique_shape', relation='right', effect='recolor', budget=Budget(10000))
        self.assertEqual(out[3][9], 9)
        self.assertEqual(out[7][4], 6)
        self.assertEqual(rows[3][9], 6)

    def test_background_tie_and_invalid_cells_are_rejected(self):
        for rows in ([[0, 1], [1, 0]], [[False, 0]], [[10]], [[0], [0, 1]]):
            with self.assertRaises(ValueError):
                g.ground(rows, Budget(10000))

    def test_budget_stops_before_segmentation(self):
        with self.assertRaises(BudgetExceeded):
            g.ground(scene_fixture(), Budget(1))


if __name__ == '__main__':
    unittest.main()
