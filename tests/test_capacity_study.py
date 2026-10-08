"""Scientific-integrity checks; no ARC solve, holdout or S6 game is executed."""
import copy
import unittest

from seed import capacity_study as study
from seed.capacity_media import trace_operation
from echoai.seed.kenyon_capacity import SparsePrimitiveGuide
from echoai.seed.kenyon_bench import sample


class CapacityStudyTests(unittest.TestCase):
    def receipt(self):
        return {"result": {"expansions": 400, "test_ok": None, "predictions": [[[1]]]},
                "demonstration_replay": True, "correct": True, "cost": {"cpu_seconds": 4}}

    def test_replay_requires_predictions_not_just_score(self):
        first = self.receipt(); second = copy.deepcopy(first)
        second["result"]["predictions"] = [[[2]]]
        with self.assertRaisesRegex(ValueError, "replay differs"):
            study.check_pair(first, second)

    def test_timing_is_not_deterministic_evidence(self):
        first = self.receipt(); second = copy.deepcopy(first)
        second["cost"]["cpu_seconds"] = 90
        study.check_pair(first, second)

    def test_budget_and_label_leak_fail_closed(self):
        for key, value in (("expansions", 401), ("test_ok", True)):
            row = self.receipt(); row["result"][key] = value
            with self.assertRaises(ValueError): study.check_pair(row, row)

    def test_regressions_are_not_cancelled_by_new_success(self):
        result = study.paired({"a": True, "b": False}, {"a": False, "b": True})
        self.assertEqual(result, {"gained": ["b"], "lost": ["a"], "delta": 0})

    def test_different_cohorts_rejected(self):
        with self.assertRaises(ValueError): study.paired({"a": True}, {"b": True})

    def test_exam_id_rejected_before_read(self):
        with self.assertRaisesRegex(ValueError, "outside declared"):
            study.checked_task("sealed-exam", {"fit": [], "development": []})

    def test_s6_blocked_or_missing_audit_never_starts(self):
        good = {"singles": 200, "replay_failures": [], "exam_opened": False, "B_measured": False}
        self.assertTrue(study.probe_finished({"stage": "DONE"}, good))
        self.assertFalse(study.probe_finished({"stage": "BLOCKED"}, good))
        self.assertFalse(study.probe_finished({"stage": "DONE"}, {}))
        self.assertFalse(study.probe_finished({"stage": "DONE"}, dict(good, replay_failures=[1])))

    def test_tree_values_reproduce_real_guide(self):
        task, name = sample(2)
        guide = SparsePrimitiveGuide(4096)
        guide.observe(task, [(name,)])
        weights_before = bytes(guide.weights)
        trace = trace_operation(guide, task, name)
        self.assertEqual(trace["guide_score"], guide.probs(task)[name])
        self.assertEqual(trace["raw_score"], sum(sum(x["weights"]) for x in trace["branches"]))
        self.assertEqual(bytes(guide.weights), weights_before)
        for b in trace["branches"]:
            self.assertEqual(b["weights"], [guide.weights[i] for i in b["indices"]])

    def test_untrained_tree_has_no_invented_activity(self):
        task, name = sample(2)
        trace = trace_operation(SparsePrimitiveGuide(640), task, name)
        self.assertEqual(trace["nonzero_reads"], 0)
        self.assertEqual(trace["raw_score"], 0)
        self.assertEqual(trace["guide_score"], .05)


if __name__ == "__main__":
    unittest.main()
