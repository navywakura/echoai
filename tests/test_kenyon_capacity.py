"""Development-only checks for the optional sparse guide."""
import unittest

from echoai.seed.kenyon_capacity import SparsePrimitiveGuide
from echoai.seed.learn import Library


def task(output):
    return {"train": [{"input": [[1, 2], [3, 4]], "output": output}],
            "test": [{"input": [[5, 6], [7, 8]], "output": [[9]]}]}


class GuideTests(unittest.TestCase):
    def test_capacity_training_and_isolation(self):
        sample = task([[2, 1], [4, 3]])
        guide = SparsePrimitiveGuide()
        self.assertEqual(len(guide.weights), 500_000)
        self.assertEqual(guide.examples, 0)
        library = Library()
        guide.observe(sample, [("fliplr",)], library)
        self.assertEqual(guide.examples, 1)
        self.assertGreater(guide.probs(sample)["fliplr"], 0.05)
        guided = guide.guided_library(sample, library)
        self.assertIsNone(library.guide)
        self.assertGreater(guided.guide["fliplr"], 0.05)

    def test_rejects_unverified_program_without_learning(self):
        guide = SparsePrimitiveGuide()
        with self.assertRaises(ValueError):
            guide.observe(task([[1, 2], [3, 4]]), [("fliplr",)])
        self.assertEqual(guide.examples, 0)
        self.assertFalse(any(guide.weights))

    def test_test_outputs_never_enter_features(self):
        guide = SparsePrimitiveGuide()
        a = task([[2, 1], [4, 3]])
        b = task([[2, 1], [4, 3]])
        b["test"][0]["output"] = [[0, 0]]
        self.assertEqual(guide.features(a), guide.features(b))

    def test_verified_macro_teaches_its_expanded_primitives(self):
        guide = SparsePrimitiveGuide()
        lib = Library({"macro": {"steps": [["fliplr"]]}})
        guide.observe(task([[2, 1], [4, 3]]), ["macro"], lib)
        self.assertGreater(guide.probs(task([[2, 1], [4, 3]]))["fliplr"], 0.05)


if __name__ == "__main__":
    unittest.main()
