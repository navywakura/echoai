from copy import deepcopy
import unittest

from seed.final_audit_recovery import compare


class ReplayComparisonTests(unittest.TestCase):
    def test_json_preserves_tuple_content_without_changing_the_experiment(self):
        rebuilt = {"model": {"hypotheses": [[1, ["entry_order", (2, 3)], "proposed"]]},
                   "actions": [["K", 1, None]], "frames": ["a", "b"], "levels": [0, 1]}
        saved = deepcopy(rebuilt)
        saved["model"]["hypotheses"][0][1][1] = [2, 3]
        compare(rebuilt, saved)
        for key, value in (("actions", [["K", 2, None]]), ("frames", ["a", "c"]),
                           ("levels", [0, 0]), ("model", {"hypotheses": []})):
            changed = dict(saved, **{key: value})
            with self.assertRaises(AssertionError):
                compare(rebuilt, changed)

    def test_numeric_types_and_precision_are_not_erased(self):
        with self.assertRaises(AssertionError):
            compare({"verified": True}, {"verified": 1})
        with self.assertRaises(AssertionError):
            compare({"score": 0.6436787896156994}, {"score": 0.6436788})
        with self.assertRaises(ValueError):
            compare({"score": float("nan")}, {"score": float("nan")})
