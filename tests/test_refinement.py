import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from echoai.seed import refinement as r
from echoai.seed.learn import Library


class HiddenOutput:
    def __deepcopy__(self, memo):
        raise AssertionError("reserved output copied")


class RefinementTests(unittest.TestCase):
    def task(self):
        return {"train": [{"input": [[1, 2, 3], [4, 5, 6]], "output": [[4, 1], [5, 2], [6, 3]]}],
                "test": [{"input": [[7, 8, 9], [0, 1, 2]], "output": HiddenOutput()}]}

    def test_eight_distinct_views_and_inverse_rectangles(self):
        self.assertEqual(len({r.transform(r.PROBE, v) for v in r.VIEWS}), 8)
        for view in r.VIEWS:
            self.assertEqual(r.transform(r.transform(r.PROBE, view), r.inverse(view)), r.PROBE)

    def test_fit_verify_no_hidden_answers_or_library_updates(self):
        library = Library()
        result = r.solve(self.task(), library, max_trials=200, rounds=1)
        self.assertEqual(result["predictions"], [[[0, 7], [1, 8], [2, 9]]])
        self.assertIsNone(result["test_ok"])
        self.assertFalse(result["test_verified"])
        self.assertEqual(result["weight_updates"], 0)
        self.assertEqual(library.concepts, {})
        self.assertLessEqual(result["trials"], 200)

    def test_fitting_programs_disagree_on_test(self):
        task = {"train": [{"input": [[1, 0], [0, 1]], "output": [[1, 0], [0, 1]]}],
                "test": [{"input": [[1, 2], [3, 4]]}]}
        result = r.solve(task, Library(), max_trials=150, rounds=1)
        self.assertEqual(result["status"], "AMBIGUOUS")
        self.assertEqual(len(result["attempts"]), 2)
        self.assertFalse(result["test_verified"])
        self.assertGreater(result["prediction_groups"], 1)

    def test_refines_failed_model_proposal(self):
        task = self.task()
        task["train"][0]["output"] = [[4, 7], [5, 2], [6, 3]]
        result = r.solve(task, Library(), proposals=[[["rot90"]]], views=False,
                         max_trials=3000, beam_width=4, rounds=2, max_depth=2)
        self.assertTrue(result["verified_programs"])
        self.assertEqual(result["predictions"], [[[0, 7], [7, 8], [2, 9]]])

    def test_closed_dsl_rejects_code(self):
        result = r.solve(self.task(), max_trials=10, proposals=["import os", [["open", "/tmp/x"]]])
        self.assertEqual(len(result["rejected_proposals"]), 2)

    def test_relational_operator_generalizes_objects(self):
        task = {"train": [{"input": [[0, 2, 0, 3, 3]], "output": [[0, 2, 0, 2, 2]]}],
                "test": [{"input": [[0, 4, 4, 0, 5, 5, 5]]}]}
        lib = r.RefinementLibrary()
        program = (("recolor_by_size", 0, 2, "largest"),)
        self.assertEqual(r.execute(r.grid(task["train"][0]["input"]), program, lib), r.grid(task["train"][0]["output"]))
        self.assertEqual(r.execute(r.grid(task["test"][0]["input"]), program, lib), r.grid([[0, 4, 4, 0, 2, 2, 2]]))

    def test_observer_does_not_change_result(self):
        class Passive:
            def __init__(self):
                self.rows = []
            def write(self, **row):
                self.rows.append(row)
        journal = Passive()
        args = dict(max_trials=150, rounds=1)
        self.assertEqual(r.solve(self.task(), **args), r.solve(self.task(), journal=journal, **args))
        self.assertTrue(journal.rows)
        self.assertTrue(all(row.get("test_verified", False) is False for row in journal.rows))

    def test_strict_color_bounds(self):
        for value in (10, -1, True, 1.2):
            with self.assertRaises(ValueError):
                r.grid([[value]])


if __name__ == "__main__":
    unittest.main()
