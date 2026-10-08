"""Adverse checks for S5-F verdicts and reset accounting, without exam worlds."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

PATH = Path(__file__).resolve().parents[1] / "lab/temporal/h1h3-exam-20260927/evaluate.py"
SPEC = importlib.util.spec_from_file_location("h1h3_exam", PATH)
exam = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exam)


class ExamVerdicts(unittest.TestCase):
    def setUp(self):
        families = ["K1", "K2", "K3", "K4", "C1", "C2", "M1"]
        self.validation = {2: {"levels": 300, "solver_levels": 300,
                               "families": {f: 1 for f in families}},
                           3: {"levels": 300, "solver_levels": 300,
                               "families": {f: 1 for f in ["H1", "H2", "H3", "H4"]}}}
        old = {"families": {f: 10 for f in families + ["H1", "H2", "H3", "H4"]},
               "scores": {2: 10, 3: 10}, "levels": 110}
        new = copy.deepcopy(old)
        new["families"].update(H1=15, H3=15)
        new["scores"][3] = 11
        new["levels"] = 120
        self.totals = {"v5.7": old, "v5.8": new, "random": {"levels": 10}}

    def verdict(self, replay=True):
        return exam.checks(self.validation, self.totals, replay)

    def test_gains_in_one_temporal_family_cannot_mask_a_tie_in_the_other(self):
        self.assertTrue(all(self.verdict().values()))
        self.totals["v5.8"]["families"].update(H1=100, H3=10)
        self.assertFalse(self.verdict()["F3"])

    def test_control_family_regression_cannot_hide_behind_other_gains(self):
        self.totals["v5.8"]["families"].update(K1=100, K4=9)
        self.assertFalse(self.verdict()["F4"])
        self.totals["v5.8"]["families"]["K4"] = 10
        self.totals["v5.8"]["scores"][2] = 9.9
        self.assertFalse(self.verdict()["F4"])

    def test_missing_family_or_unsolved_level_prevents_green(self):
        del self.validation[2]["families"]["M1"]
        self.assertFalse(self.verdict()["F1"])
        self.validation[2]["families"]["M1"] = 1
        self.validation[3]["solver_levels"] = 299
        self.assertFalse(self.verdict()["F1"])

    def test_random_limit_score_tie_and_failed_replay_are_not_green(self):
        self.totals["random"]["levels"] = 270
        self.totals["v5.8"]["scores"][3] = 10
        verdict = self.verdict(replay=False)
        self.assertFalse(verdict["F2"])
        self.assertFalse(verdict["F5"])
        self.assertFalse(verdict["F6"])


class ResetAccounting(unittest.TestCase):
    def test_agent_reset_and_automatic_reset_have_distinct_indices(self):
        class Env:
            def reset(self):
                return SimpleNamespace(state=SimpleNamespace(name="NOT_FINISHED"))
            def step(self, action, data=None):
                return SimpleNamespace(state=SimpleNamespace(name=action))
        env = exam.ResetCounter(Env())
        env.reset()  # initial observation is not an action
        env.step("NOT_FINISHED")
        env.reset()  # voluntary reset, including a possible R,0
        env.step("GAME_OVER")
        env.reset()  # automatic reset immediately after GAME_OVER
        self.assertEqual(env.emitted, 4)
        self.assertEqual(env.automatic, [3])


if __name__ == "__main__":
    unittest.main()
