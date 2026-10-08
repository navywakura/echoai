"""DREAM-D v2 tests use synthetic scores or bodies outside the exam domain."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.echo4.continuity import canonical
from echoai.echo4.continuity_final_audit import file_hash
from echoai.echo4.dream_bench import evaluate
from echoai.echo4.dream_history import sha
from echoai.echo4.dream_policy import Policy
from echoai.echo4.dream_probe import collect, prepare
from echoai.echo4.dream_qwen import payload, read_proposal
from echoai.echo4 import dream_v2 as v2
from echoai.echo4 import dream_v2_bench as bench
from echoai.echo4.world import Body


def result(resolved=True, steps=8):
    return {"diagnosis": {"label": "nominal" if resolved else "unknown"},
            "steps": steps, "queries": 1, "correct": resolved, "wrong": False,
            "terminalities": 0, "truth_retained": True, "reference_preserved": True,
            "cam_facts": 0, "destroyed": 0, "reserved_steps": steps}


def receipt(data, turn, model_sha, policies=(Policy(),)):
    raw = {"content": json.dumps({"candidates": [p.data() for p in policies]}),
           "tokens_evaluated": 1000, "tokens_predicted": 200,
           "truncated": False, "stopped_limit": False}
    row = {"request": payload(data, turn), "raw_response": json.dumps(raw),
           "transport_error": "", "elapsed_ms": 1, "model_sha256": model_sha}
    row["sha256"] = sha(canonical(row))
    return row


class TestRobustSelection(unittest.TestCase):
    def test_empty_batches_rejected(self):
        for groups in ([], [[]]):
            with self.assertRaises(ValueError):
                v2.ReplayEvaluator(groups)

    def test_worst_batch_before_total(self):
        # Better aggregate but losing in one batch must not win.
        base, fragile, robust = Policy(), Policy((5, 4, 3, 2, 1, 0)), Policy((2, 4, 0, 1, 3, 5))
        groups = [[None] * 10, [None] * 2]
        evaluator = v2.ReplayEvaluator(groups)
        def rows(n, successes):
            return [result(i < successes) for i in range(n)]
        evaluator.cache = {base.identity: [rows(10, 5), rows(2, 1)],
                           fragile.identity: [rows(10, 10), rows(2, 0)],
                           robust.identity: [rows(10, 6), rows(2, 2)]}
        self.assertEqual(evaluator.select(base, (fragile, robust))[0], robust)
        self.assertEqual(evaluator.score(fragile)[0], -500000)

    def test_ties_keep_incumbent(self):
        base, other = Policy(), Policy((1, 0, 2, 3, 4, 5))
        evaluator = v2.ReplayEvaluator([[None]])
        evaluator.cache = {p.identity: [[result()]] for p in (base, other)}
        selected, scores = evaluator.select(base, (other, other, base))
        self.assertEqual(selected, base)
        self.assertEqual(len(scores), 2)

    def test_public_score_ignores_private_truth(self):
        evaluator = v2.ReplayEvaluator([[None]])
        evaluator.cache[Policy().identity] = [[result()]]
        before = evaluator.public(Policy())
        evaluator.cache[Policy().identity][0][0]["correct"] = False
        evaluator.cache[Policy().identity][0][0]["truth_retained"] = False
        self.assertEqual(before, evaluator.public(Policy()))
        self.assertEqual(set(before), {"policy", "score", "batches"})

    def test_replay_cached_and_no_new_execution(self):
        evaluator = v2.ReplayEvaluator([[None]])
        with patch.object(v2, "evaluate", return_value=[result()]) as execute:
            evaluator.public(Policy())
            evaluator.public(Policy())
        execute.assert_called_once_with(Policy(), [None], replay=True)
        self.assertEqual(evaluator.cost(), {"policies": 1, "queries": 1,
                                          "represented_steps": 8, "native_steps": 0, "llm_calls": 0})

    def test_no_history_does_not_query_archive(self):
        with patch.object(v2.ReplayEvaluator, "public", side_effect=AssertionError("history")):
            data = v2.context(None, Policy(), empty=True)
        self.assertEqual(data["observed_schedules"], [])
        self.assertEqual(data["feedback"], [])
        self.assertNotIn("incumbent", data)

    def test_control_budget_unique_and_deterministic(self):
        for cycle in range(3):
            policies = v2.control_candidates(cycle)
            self.assertEqual(len(set(policies)), 8)
            self.assertEqual(policies, v2.control_candidates(cycle))
            self.assertTrue(all(p.step_budget == 12 for p in policies))


class TestPromotion(unittest.TestCase):
    def setUp(self):
        self.base, self.other = Policy(), Policy((2, 4, 0, 1, 3, 5))

    def test_improvement_and_retention(self):
        args = ([result(False)], [result()], [result(False)])
        self.assertEqual(v2.promote(self.base, self.other, *args), (self.other, "accepted"))
        self.assertEqual(v2.promote(self.base, self.base, *args)[1], "incumbent_retained")

    def test_regression_against_original_fixed_is_rejected(self):
        self.assertEqual(v2.promote(self.base, self.other, [result(False)],
                                   [result(False)], [result()]), (self.base, "rollback_fixed"))

    def test_incumbent_regression_rejected(self):
        self.assertEqual(v2.promote(self.base, self.other, [result()],
                                   [result(False)], [result(False)])[1], "rollback_incumbent")

    def test_stop_and_missing_rows(self):
        self.assertEqual(v2.promote(self.base, self.other, [], [], [], stopped=True)[1], "operator_stop")
        self.assertEqual(v2.promote(self.base, self.other, [], [], [result()])[1], "insufficient_evidence")

    def test_invariant_failures_block_promotion(self):
        for field, value in (("wrong", True), ("terminalities", 1), ("truth_retained", False),
                             ("reference_preserved", False), ("cam_facts", 1),
                             ("destroyed", 1), ("reserved_steps", 13)):
            with self.subTest(field=field):
                self.assertEqual(v2.promote(self.base, self.other, [result()],
                                           [{**result(), field: value}], [result()])[1], "safety_rejection")


class TestQwenFeedback(unittest.TestCase):
    def backend(self):
        # No server is launched. The synthetic transport is NOT scientific evidence.
        backend = object.__new__(v2.FeedbackQwen)
        backend.calls = 0
        backend.metadata = {"model_sha256": "a" * 64}
        return backend

    def test_nine_call_limit_and_receipt_compatibility(self):
        backend = self.backend()
        response = receipt({}, 0, "a" * 64)["raw_response"].encode()
        with patch.object(backend, "_request", return_value=response) as transport:
            for turn in range(9):
                row = backend.propose({}, turn)
                candidates, cost, error = read_proposal(row, {}, turn, "a" * 64)
                self.assertEqual(candidates, (Policy(),))
                self.assertEqual(cost["calls"], 1)
                self.assertEqual(error, "")
            with self.assertRaises(RuntimeError):
                backend.propose({}, 9)
        self.assertEqual(transport.call_count, 9)

    def test_transport_failure_recorded(self):
        backend = self.backend()
        with patch.object(backend, "_request", side_effect=TimeoutError):
            row = backend.propose({}, 0)
        policies, cost, error = read_proposal(row, {}, 0, "a" * 64)
        self.assertEqual(policies, ())
        self.assertEqual(error, "TimeoutError")
        self.assertEqual(cost["calls"], 1)


class TestRealHistoryInterface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = Body(56, 52)  # outside the prospective H range
        prepared = prepare(cls.body)
        condition = (False, True, 4)
        cls.row = (cls.body, condition, prepared, collect(cls.body, condition, prepared))

    def test_public_prompt_contains_only_summaries(self):
        evaluator = v2.ReplayEvaluator([[self.row]])
        data = v2.context(evaluator, Policy(), (Policy((2, 4, 0, 1, 3, 5)),))
        self.assertEqual(len(data["feedback"]), 1)
        raw = json.dumps(data)
        for forbidden in ("private_context", "temperature", "truth_retained", "correct", "packets", "reference_sha256"):
            self.assertNotIn(forbidden, raw)

    def test_selection_never_calls_physical_executor(self):
        evaluator = v2.ReplayEvaluator([[self.row]])
        with patch("echoai.echo4.self_probe_world.run_probe", side_effect=AssertionError("physics")), \
             patch.object(v2.FeedbackQwen, "propose", side_effect=AssertionError("LLM")):
            chosen, _ = evaluator.select(Policy(), v2.control_candidates(0))
        self.assertIsInstance(chosen, Policy)

    def test_native_replay_parity_for_selected_policy(self):
        evaluator = v2.ReplayEvaluator([[self.row]])
        chosen, _ = evaluator.select(Policy(), v2.control_candidates(0))
        self.assertEqual(evaluate(chosen, [self.row]), evaluate(chosen, [self.row], replay=True))


class TestCampaign(unittest.TestCase):
    def test_end_to_end_fixture_freeze_feedback_reconstruct_and_tamper(self):
        body = Body(56, 52)
        prepared = prepare(body)
        condition = (True, True, 0)
        initial = [(body, condition, prepared, collect(body, condition, prepared))]
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(bench, "exam_bodies", return_value=(((57, 52),), ((58, 52),), ((59, 52),))), \
             patch.object(bench, "load_history", return_value=([initial], Policy())), \
             patch("echoai.echo4.dream_bench.CONDITIONS", ((True, True, 0), (False, True, 4))):
            directory = Path(folder)
            metadata = {"model": __file__, "model_sha256": file_hash(Path(__file__)),
                        "server": __file__, "server_sha256": file_hash(Path(__file__)), "weights_updated": False}
            seen = []
            original_cases = bench.cases
            def guarded_cases(bodies):
                cycle = len(list(directory.glob("selection-*.json"))) - 1
                self.assertTrue((directory / f"selection-{cycle}.json").exists())
                self.assertTrue((directory / "lock.json").exists())
                return original_cases(bodies)
            def propose(data, turn):
                seen.append(copy.deepcopy(data))
                return receipt(data, turn, metadata["model_sha256"])
            with patch.object(bench, "cases", side_effect=guarded_cases):
                report = bench.build(directory, metadata, propose)
            bench.persist(directory, "report.json", report, False)
            self.assertEqual(len(seen), 9)
            self.assertEqual(len(seen[1]["feedback"]), 1)
            self.assertEqual(seen[2]["observed_schedules"], [])
            self.assertEqual([c["selection"]["history_contexts"] for c in report["cycles"]], [1, 3, 5])
            self.assertTrue(all(c["checks"]["online_replay_equal"] for c in report["cycles"]))
            with patch.object(v2.FeedbackQwen, "propose", side_effect=AssertionError("LLM")):
                verified = bench.verify(directory)
            self.assertTrue(verified["valid"], verified)
            self.assertFalse(verified["dream1_green"])
            path = directory / "selection-0.json"
            saved = path.read_bytes()
            path.write_bytes(b'{}')
            self.assertFalse(bench.verify(directory)["valid"])
            path.write_bytes(saved)
            report["criteria_passed"] = True
            report.pop("reproduction_sha256")
            report["reproduction_sha256"] = sha(canonical(report))
            (directory / "report.json").write_bytes(canonical(report))
            forged = bench.verify(directory)
            self.assertFalse(forged["valid"])
            self.assertFalse(forged["dream1_green"])

    def test_missing_campaign_has_no_green(self):
        with tempfile.TemporaryDirectory() as d:
            result = bench.verify(Path(d) / "missing")
        self.assertFalse(result["valid"])
        self.assertFalse(result["dream1_green"])

    def test_version_one_sources_and_certificate_unchanged(self):
        parents = v2.binding()
        self.assertIn("report.json", parents)
        self.assertIn("audit-receipt.json", parents)
        self.assertTrue(set(bench.v1_sources()).issubset(bench.sources()))


if __name__ == "__main__":
    unittest.main()
