"""DREAM B/C/D infrastructure; never opens the frozen campaign partitions."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.echo4.continuity import canonical
from echoai.echo4.dream_history import sha
from echoai.echo4.dream_policy import Policy, parse_candidates, promotion, request_plan, run_policy, select
from echoai.echo4.dream_probe import ProbeArchive, collect, model_for, native, prepare
from echoai.echo4.dream_qwen import LocalQwen, payload, read_proposal
from echoai.echo4.world import Body


class TestPolicy(unittest.TestCase):
    def test_roundtrip(self):
        policy = Policy((3, 2, 1, 0, 4, 5))
        raw = json.dumps({"candidates": [policy.data()]})
        self.assertEqual(parse_candidates(raw), (policy,))

    def test_closed_schema(self):
        for field, value in (("shell", "echo hi"), ("version", 2), ("version", True),
                             ("step_budget", 13), ("step_budget", 3), ("step_budget", 12.0),
                             ("order", [0] * 6), ("order", [False, 1, 2, 3, 4, 5]),
                             ("enabled", [1] * 5), ("enabled", [2] * 6)):
            data = Policy().data()
            data[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                parse_candidates(json.dumps({"candidates": [data]}))

    def test_duplicate_keys_and_nonsense(self):
        for raw in ('{"candidates":[],"candidates":[]}', 'null', '[]', '{}',
                    '__import__("os")', '```json\n{}\n```', 'x' * 8193):
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                parse_candidates(raw)

    def test_candidate_quota(self):
        for count in (0, 5):
            with self.assertRaises(ValueError):
                parse_candidates(json.dumps({"candidates": [Policy().data()] * count}))

    def test_fixed_incumbent_wins_ties(self):
        incumbent, other = Policy(), Policy((5, 4, 3, 2, 1, 0))
        rows = [{"diagnosis": {"label": "own"}, "steps": 8}]
        chosen, scores = select(incumbent, [other, incumbent], lambda _: rows)
        self.assertEqual(chosen, incumbent)
        self.assertEqual(len(scores), 2)

    def test_selector_can_improve_without_private_truth(self):
        incumbent, other = Policy(), Policy((5, 4, 3, 2, 1, 0))
        def evaluate(policy):
            return [{"diagnosis": {"label": "unknown" if policy == incumbent else "own"}, "steps": 8}]
        self.assertEqual(select(incumbent, [other], evaluate)[0], other)

    def test_promotion_rollback_stop_and_insufficient_evidence(self):
        incumbent, other = Policy(), Policy((5, 4, 3, 2, 1, 0))
        good = {"diagnosis": {"label": "own"}, "steps": 8, "wrong": False, "terminalities": 0}
        bad = {**good, "diagnosis": {"label": "unknown"}}
        self.assertEqual(promotion(incumbent, other, [good], [bad]), (incumbent, "rollback_regression"))
        self.assertEqual(promotion(incumbent, other, [good], [good]), (other, "accepted"))
        self.assertEqual(promotion(incumbent, other, [good], [], stopped=True)[1], "operator_stop")
        self.assertEqual(promotion(incumbent, other, [good], [])[1], "insufficient_evidence")
        for mutation in ({"wrong": True}, {"terminalities": 1}):
            self.assertEqual(promotion(incumbent, other, [good], [{**good, **mutation}])[1], "safety_rejection")


class TestProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = Body(77, 50)  # not a campaign case
        cls.prepared = prepare(cls.body)
        cls.condition = (False, True, 4)
        cls.archive = collect(cls.body, cls.condition, cls.prepared)

    def model(self):
        return model_for(self.body, self.prepared)

    def test_archive_roundtrip(self):
        raw = self.archive.dumps()
        self.assertEqual(ProbeArchive.loads(raw, sha(raw)).dumps(), raw)
        with self.assertRaises(ValueError):
            ProbeArchive.loads(raw + b' ', sha(raw))

    def test_source_receipts_reconstruct(self):
        self.assertEqual(collect(self.body, self.condition, self.prepared).dumps(), self.archive.dumps())

    def test_online_offline_equal_every_rotation(self):
        from echoai.echo4.dream_bench import rotations
        for policy in rotations():
            online = run_policy(self.model(), policy, lambda p: native(self.body, self.condition, p))
            replay = run_policy(self.model(), policy, self.archive.replay().request)
            self.assertEqual(online, replay)

    def test_replay_never_runs_physics_or_model(self):
        with patch("echoai.echo4.self_probe_world.run_probe", side_effect=AssertionError("physics")), \
             patch.object(LocalQwen, "propose", side_effect=AssertionError("LLM")):
            result = run_policy(self.model(), Policy(), self.archive.replay().request)
        self.assertGreater(result["queries"], 0)

    def test_unrevealed_future_cannot_change_view(self):
        data = json.loads(self.archive.dumps())
        before = self.archive.replay().view()
        data["branches"] = []
        self.assertEqual(before, ProbeArchive(data).replay().view())
        self.assertEqual(set(before), {"initial", "observed", "queries", "represented_steps", "replay_native_steps", "replay_llm_calls"})

    def test_unknown_is_not_predicted_or_free_budget(self):
        data = json.loads(self.archive.dumps())
        data["branches"] = []
        result = run_policy(self.model(), Policy(), ProbeArchive(data).replay().request)
        self.assertEqual(result["diagnosis"]["label"], "unknown")
        self.assertEqual(result["steps"], 0)
        self.assertGreater(result["reserved_steps"], 0)
        self.assertTrue(all(e["status"] == "unknown" for e in result["events"]))

    def test_view_is_copied_and_sessions_isolated(self):
        first, second = self.archive.replay(), self.archive.replay()
        plan = request_plan(self.model(), 0, 18)
        first.request(plan)
        view = first.view()
        view["observed"].clear()
        self.assertEqual(len(first.view()["observed"]), 1)
        self.assertEqual(second.view()["observed"], [])

    def test_repeated_request_unknown(self):
        session = self.archive.replay()
        plan = request_plan(self.model(), 0, 18)
        self.assertIsNotNone(session.request(plan))
        self.assertIsNone(session.request(plan))
        self.assertEqual(session.steps, 8)

    def test_invalid_archive_rejected(self):
        base = json.loads(self.archive.dumps())
        mutations = []
        for field, value in (("native_steps", 99), ("experiment", True)):
            data = copy.deepcopy(base)
            data["branches"][0][field] = value
            mutations.append(data)
        data = copy.deepcopy(base)
        data["branches"].append(data["branches"][0])
        mutations.append(data)
        data = copy.deepcopy(base)
        data["body"] = {"h": 77}
        mutations.append(data)
        data = copy.deepcopy(base)
        data["branches"][0]["receipt"]["terminal"][-1] = True
        mutations.append(data)
        for data in mutations:
            with self.assertRaises(ValueError):
                ProbeArchive(data)

    def test_stop_before_any_effect(self):
        called = []
        result = run_policy(self.model(), Policy(), called.append, stopped=lambda: True)
        self.assertEqual(called, [])
        self.assertEqual(result["reason"], "operator_stop")

    def test_disabled_quota_never_requested(self):
        called = []
        result = run_policy(self.model(), Policy(enabled=(0,) * 6), called.append)
        self.assertEqual(called, [])
        self.assertEqual(result["steps"], 0)

    def test_budget_and_unique_experiments(self):
        for cap in (4, 8, 12):
            result = run_policy(self.model(), Policy(step_budget=cap), self.archive.replay().request)
            self.assertLessEqual(result["steps"], cap)
            indices = [r["experiment"] for r in result["events"]]
            self.assertEqual(len(indices), len(set(indices)))

    def test_veto_abstains_and_stops(self):
        from echoai.echo4.self_probe_world import run_probe
        result = run_policy(self.model(), Policy(), lambda p: run_probe(self.body, p, veto_at=1)[0])
        self.assertEqual(result["diagnosis"]["label"], "unknown")
        self.assertEqual(result["queries"], 1)

    def test_unsafe_all_hypotheses_filter(self):
        model = self.model()
        model.h_candidates = ((2, False),)
        called = []
        self.assertEqual(run_policy(model, Policy(), called.append)["queries"], 0)
        self.assertEqual(called, [])

    def test_non_catalog_request_rejected_before_budget(self):
        session = self.archive.replay()
        plan = request_plan(self.model(), 0, 18)
        with self.assertRaises(ValueError):
            session.request(replace(plan, actions=(0,)))
        self.assertEqual(session.queries, 0)


class TestQwen(unittest.TestCase):
    def receipt(self, content=None):
        response = {"tokens_evaluated": 400, "tokens_predicted": 100,
                    "content": content or json.dumps({"candidates": [Policy().data()]}),
                    "stopped_limit": False, "truncated": False}
        row = {"request": payload([], 0), "raw_response": json.dumps(response),
               "transport_error": "", "elapsed_ms": 1, "model_sha256": "a" * 64}
        row["sha256"] = sha(canonical(row))
        return row

    def test_receipt_and_cost(self):
        candidates, cost, error = read_proposal(self.receipt(), [], 0, "a" * 64)
        self.assertEqual(candidates, (Policy(),))
        self.assertEqual(cost["generated_tokens"], 100)
        self.assertEqual(error, "")

    def test_prompt_not_allowed_to_contain_holdout(self):
        receipt = self.receipt()
        with self.assertRaises(ValueError):
            read_proposal(receipt, [{"new": 1}], 0, "a" * 64)

    def test_tampered_receipt_and_model_rejected(self):
        receipt = self.receipt()
        receipt["elapsed_ms"] = 0
        with self.assertRaises(ValueError):
            read_proposal(receipt, [], 0, "a" * 64)
        with self.assertRaises(ValueError):
            read_proposal(self.receipt(), [], 0, "b" * 64)

    def test_invalid_completion_retains_no_candidates(self):
        candidates, cost, error = read_proposal(self.receipt("__import__('os')"), [], 0, "a" * 64)
        self.assertEqual(candidates, ())
        self.assertTrue(error)
        self.assertEqual(cost["calls"], 1)

    def test_timeout_rejection(self):
        receipt = self.receipt()
        receipt["transport_error"] = "TimeoutError"
        receipt["raw_response"] = ""
        receipt.pop("sha256")
        receipt["sha256"] = sha(canonical(receipt))
        self.assertEqual(read_proposal(receipt, [], 0, "a" * 64)[0], ())

    def test_budget_and_truncation(self):
        for mutation in ({"tokens_predicted": 513}, {"tokens_evaluated": 8193},
                         {"tokens_predicted": True}, {"truncated": True}, {"stopped_limit": True}):
            receipt = self.receipt()
            response = json.loads(receipt["raw_response"])
            response.update(mutation)
            receipt["raw_response"] = json.dumps(response)
            receipt.pop("sha256")
            receipt["sha256"] = sha(canonical(receipt))
            self.assertEqual(read_proposal(receipt, [], 0, "a" * 64)[0], ())

    def test_missing_or_legacy_model_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                LocalQwen(Path(d) / "missing", Path(d) / "Qwen.gguf", d)
            with self.assertRaises(ValueError):
                LocalQwen(Path(d) / "echo-discord/server", Path(d) / "Qwen.gguf", d)


class TestCampaignAudit(unittest.TestCase):
    def test_small_fixture_reconstructs_and_detects_tampering_without_llm(self):
        from echoai.echo4 import dream_bench as bench
        from echoai.echo4.continuity_final_audit import file_hash
        # Test-only data, never the declared WORLD-1 exam. Synthetic completion
        # exercises plumbing; this is not evidence of Qwen performance.
        with tempfile.TemporaryDirectory() as d, \
             patch.object(bench, "TRAIN", ((76, 51),)), \
             patch.object(bench, "EXAMS", (((78, 52),), ((79, 53),), ((80, 54),))), \
             patch.object(bench, "CONDITIONS", ((False, True, 4), (True, True, 0))):
            directory = Path(d)
            metadata = {"model": __file__, "model_sha256": file_hash(__file__),
                        "server": __file__, "server_sha256": file_hash(__file__), "weights_updated": False}

            def proposer(history, cycle):
                row = TestQwen().receipt()
                row["request"] = payload(history, cycle)
                row["model_sha256"] = metadata["model_sha256"]
                row.pop("sha256")
                row["sha256"] = sha(canonical(row))
                return row

            report = bench.build(directory, metadata, proposer)
            bench.persist(directory, "report.json", report, False)
            with patch.object(LocalQwen, "propose", side_effect=AssertionError("network")):
                verified = bench.verify(directory)
            self.assertTrue(verified["valid"], verified)
            self.assertFalse(verified["dream1_green"])
            self.assertEqual(report["cycles"][0]["selection"]["history_contexts"], 2)
            self.assertEqual(report["cycles"][1]["selection"]["history_contexts"], 4)
            self.assertEqual(report["cycles"][2]["selection"]["history_contexts"], 6)
            self.assertTrue(all(c["checks"]["online_replay_equal"] for c in report["cycles"]))
            path = directory / "version-0.json"
            saved = path.read_bytes()
            path.write_bytes(b'{}')
            self.assertFalse(bench.verify(directory)["valid"])
            path.write_bytes(saved)
            # Even a self-consistent recomputed report hash cannot manufacture
            # approval: the auditor reconstructs metric values and decisions.
            report["criteria_passed"] = True
            report.pop("reproduction_sha256")
            report["reproduction_sha256"] = sha(canonical(report))
            (directory / "report.json").write_bytes(canonical(report))
            result = bench.verify(directory)
            self.assertFalse(result["valid"])
            self.assertFalse(result["dream1_green"])


if __name__ == "__main__":
    unittest.main()
