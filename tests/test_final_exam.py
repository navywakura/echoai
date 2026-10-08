import unittest
from types import SimpleNamespace

from seed.final_eval import solver_input, judge, solve_one
from seed.final_arc import Counter, accounting


class GridTests(unittest.TestCase):
    def test_labels_are_removed_and_inputs_are_independent(self):
        task = {"train": [{"input": [[1, 2]], "output": [[2, 1]]}],
                "test": [{"input": [[3, 4]], "output": [[4, 3]], "private": 99}]}
        public = solver_input(task)
        self.assertEqual(public["test"], [{"input": [[3, 4]]}])
        public["test"][0]["input"][0][0] = 9
        self.assertEqual(task["test"][0]["input"], [[3, 4]])

    def test_real_solver_is_label_blind_and_judge_requires_all_outputs(self):
        task = {"train": [{"input": [[1, 2], [3, 4]], "output": [[2, 1], [4, 3]]}],
                "test": [{"input": [[5, 6], [7, 8]], "output": [[6, 5], [8, 7]]}]}
        result = solve_one(("synthetic", solver_input(task), "S0", {}, {}, 400))["result"]
        self.assertIsNone(result["test_ok"])
        self.assertTrue(judge(task, result))
        task["test"][0]["output"] = [[0]]
        self.assertFalse(judge(task, result))
        result["program"] = None
        self.assertFalse(judge(task, result))


class AccountingTests(unittest.TestCase):
    def test_initial_and_automatic_and_chosen_resets_are_distinct(self):
        class Environment:
            def reset(self):
                return SimpleNamespace(state=SimpleNamespace(name="NOT_FINISHED"))
            def step(self, action, data=None):
                return SimpleNamespace(state=SimpleNamespace(name="GAME_OVER" if action == 1 else "NOT_FINISHED"))
        env = Counter(Environment())
        env.reset()
        self.assertEqual(env.emitted, 0)
        env.step(1)
        env.reset()
        env.reset()
        self.assertEqual(env.automatic, [1])
        self.assertEqual(env.emitted, 3)
        record = {"actions": [["K", 1, None], ["R", 0, None], ["R", 0, None], ["K", 2, None]],
                  "frames": ["a"] * 5, "levels": [0, 0, 0, 0, 1], "resets": 1,
                  "automatic_reset_indices": [1], "budget": 3, "actions_per_level": [3],
                  "levels_completed": 1, "win_levels": 2}
        counts = accounting(record)
        self.assertEqual(counts["complete_per_level"], [4])
        self.assertEqual(counts["chosen_resets"], 1)
        record["automatic_reset_indices"] = [0]
        with self.assertRaises(AssertionError):
            accounting(record)


if __name__ == "__main__":
    unittest.main()
