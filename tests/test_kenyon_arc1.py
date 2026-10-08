"""Outcome isolation and regression accounting for the development runner."""
import unittest

from echoai.seed.kenyon_arc1 import ARMS, stable, totals, solver_input


class ComparisonTests(unittest.TestCase):
    def test_public_input_strips_test_output(self):
        task = {"train": [{"input": [[1]], "output": [[2]]}],
                "test": [{"input": [[3]], "output": [[4]]}]}
        self.assertEqual(solver_input(task)["test"], [{"input": [[3]]}])

    def test_gains_cannot_hide_an_individual_loss(self):
        rows = []
        for tid, correct in (("a", {"base": True, "guide640": True, "guide500k": False}),
                             ("b", {"base": False, "guide640": False, "guide500k": True})):
            for arm in ARMS:
                rows.append({"task": tid, "arm": arm, "correct": correct[arm],
                             "result": {"expansions": 1}, "applications": 2,
                             "primitive_steps_upper_count": 2,
                             "cost": {"cpu_seconds": 0.1, "wall_seconds": 0.2}})
        result = totals(rows)
        self.assertEqual(result["guide500k"]["gained"], ["b"])
        self.assertEqual(result["guide500k"]["lost"], ["a"])
        with self.assertRaises(AssertionError):
            totals(rows[:-1])

    def test_replay_ignores_only_descriptive_timing(self):
        a = {"result": {"program": [["rot90"]]}, "applications": 3, "cost": {"cpu_seconds": 1}}
        b = {**a, "cost": {"cpu_seconds": 2}}
        self.assertEqual(stable(a), stable(b))
        self.assertNotEqual(stable(a), stable({**b, "applications": 4}))


if __name__ == "__main__":
    unittest.main()
