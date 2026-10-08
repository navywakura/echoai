import unittest
from seed import s6b6 as s


class DecisionSitePrompts(unittest.TestCase):
    def test_equal_budget_mechanics_and_no_reserved_or_manual_evidence(self):
        rows = [{"index": i, "levels": i, "sites": {}, "site_counts": {"set_future_wait": i},
                 "remaining_wait_histogram": {}} for i in range(5)]
        fixed = s.requests("fijo", 1, rows)
        echo = s.requests("echo", 1, rows)
        for req in fixed + echo:
            self.assertIn("STRICTLY BELOW", req["prompt"])
            self.assertNotIn("hold20_after_level", req["prompt"])
            self.assertNotIn("24320", req["prompt"])
        self.assertEqual(len(fixed), len(echo))
        self.assertIn('"levels":4', echo[0]["prompt"])
        self.assertNotIn('"levels":4', fixed[0]["prompt"])

    def test_new_protected_cohort_and_closed_exam(self):
        self.assertEqual(len(s.B), 40)
        self.assertTrue(set(x[1] for x in s.B).isdisjoint(x[1] for x in s.old.B))
        self.assertFalse(s.config()["exam_opened"])
        self.assertEqual(s.config()["model_calls_with_calibration"], 14)


if __name__ == "__main__":
    unittest.main()
