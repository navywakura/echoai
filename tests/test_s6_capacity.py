import copy
import unittest

from seed import s6_capacity as control


class Metrics(unittest.TestCase):
    def example(self):
        rows = [{"version": 3, "seed": i, "rep": 0, "budget": 2000,
                 "levels_completed": 3, "score": 20., "patch_hits": [0],
                 "actions": [["K", 1, None]], "frames": ["frame"]} for i in range(2)]
        return {"levels": 6, "rows": rows, "trace_digest": "before"}

    def test_aggregate_gain_cannot_hide_individual_score_or_level_regression(self):
        before = self.example()
        after = copy.deepcopy(before)
        after["levels"] = 8
        after["rows"][0].update(levels_completed=6, patch_hits=[7])
        after["rows"][1].update(levels_completed=2, score=19.)
        report = control.result(before, after)
        self.assertEqual(report["gain"], 2)
        self.assertEqual(report["loss_indices"], [1])
        self.assertFalse(control.b4.no_regressions(before, after))
        after["rows"][1].update(levels_completed=3, score=19.)
        self.assertFalse(control.b4.no_regressions(before, after))

    def test_activated_does_not_imply_changed_action_or_improvement(self):
        before = self.example()
        after = copy.deepcopy(before)
        after["rows"][0]["patch_hits"] = [5]
        report = control.result(before, after)
        self.assertEqual(report["activated_games"], 1)
        self.assertEqual(report["activation_count"], 5)
        self.assertEqual(report["changed_action_games"], 0)
        self.assertEqual(report["gain"], 0)
        after["rows"][0]["actions"] = [["K", 2, None]]
        self.assertEqual(control.result(before, after)["changed_action_games"], 1)

    def test_unpaired_games_rejected(self):
        before = self.example()
        after = copy.deepcopy(before)
        after["rows"].reverse()
        with self.assertRaises(AssertionError):
            control.result(before, after)

    def test_behavior_parity_detects_model_or_action_change(self):
        before = {k: [] for k in control.BEHAVIOR_KEYS}
        before["model"] = {"rule": [(1, 2)]}
        after = copy.deepcopy(before)
        after["model"]["rule"] = [[1, 2]]
        self.assertTrue(control.same_behavior(before, after))
        after["model"]["rule"] = [[1, 3]]
        self.assertFalse(control.same_behavior(before, after))
        after = copy.deepcopy(before)
        after["actions"] = [["R", 0, None]]
        self.assertFalse(control.same_behavior(before, after))


if __name__ == "__main__":
    unittest.main()
