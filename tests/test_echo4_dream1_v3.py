"""DREAM-v3 fixtures stay outside prospective H65..96; no real LLM here."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.echo4.continuity import canonical
from echoai.echo4.continuity_final_audit import file_hash
from echoai.echo4.dream_history import sha
from echoai.echo4 import dream_v3_profile as p
from echoai.echo4 import dream_v3 as v
from echoai.echo4 import dream_v3_bench as bench
from echoai.echo4 import self_attribution as original
from echoai.echo4.self_probe_world import run_probe
from echoai.echo4.world import Body


def receipt(data, turn, model_sha, policies=(p.Policy(),)):
    response = {"content": json.dumps({"candidates": [q.data() for q in policies]}),
                "tokens_evaluated": 1000, "tokens_predicted": 250,
                "truncated": False, "stopped_limit": False}
    row = {"request": v.payload(data, turn), "raw_response": json.dumps(response),
           "transport_error": "", "elapsed_ms": 1, "model_sha256": model_sha}
    row["sha256"] = sha(canonical(row))
    return row


class TestPolicy(unittest.TestCase):
    def test_profile_roundtrip_and_identity(self):
        q = p.Policy()
        self.assertEqual(p.Policy.from_data(q.data()), q)
        self.assertEqual(p.parse_candidates(json.dumps({"candidates": [q.data()]})), (q,))
        self.assertEqual(len(q.identity), 64)

    def test_rejects_invalid_policies(self):
        for data in ({"version": 1}, {"order": [0] * 8}, {"order": list(range(7))},
                     {"order": [True] + list(range(1, 8))}, {"enabled": [2] * 8},
                     {"enabled": [1.0] * 8}, {"step_budget": 13}, {"step_budget": True},
                     {"shell": "echo forbidden"}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                p.Policy.from_data({**p.Policy().data(), **data})

    def test_rejects_duplicate_json_keys_and_executable_output(self):
        for raw in ('{"candidates":[],"candidates":[]}', 'print(1)', 'x' * 9000,
                    '{"candidates":[]}', '{"candidates":NaN}'):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                p.parse_candidates(raw)

    def test_proposal_limit(self):
        with self.assertRaises(ValueError):
            p.parse_candidates(json.dumps({"candidates": [p.Policy().data()] * 5}))

    def test_original_catalog_unchanged_and_extended(self):
        self.assertEqual(p.CATALOG[:6], original.CATALOG)
        self.assertEqual(len(original.CATALOG), 6)
        self.assertEqual(len(p.CATALOG), 8)
        self.assertTrue(all(len(a) <= 8 for a in p.CATALOG))

    def test_starter_budget(self):
        self.assertEqual(len(set(v.starters())), 8)
        self.assertTrue(all(q.step_budget == 12 for q in v.starters()))


class TestProbeAndArchive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = Body(56, 52)
        cls.prepared = p.prepare(cls.body)
        cls.condition = (True, True, -16)
        cls.archive = p.collect(cls.body, cls.condition, cls.prepared)
        cls.row = (cls.body, cls.condition, cls.prepared, cls.archive)

    def model(self):
        return p.model_for(self.body, self.prepared)

    def test_first_six_forecasts_equal_original(self):
        a = self.model()
        b = original.SelfAttributor(self.prepared[0], a.initial, self.prepared[1])
        for i in range(6):
            self.assertEqual(a._prediction(i), b._prediction(i))

    def test_unsafe_root_becomes_safe_only_after_observed_short_probe(self):
        m = self.model()
        self.assertIsNone(p.request_plan(m, 6, 18))
        self.assertEqual(m.last_token, 17)
        plan = p.request_plan(m, 2, 18)
        m.consume(p.native(self.body, self.condition, plan))
        self.assertIsNotNone(p.request_plan(m, 6, 19))
        paths = [r["path"] for r in self.archive._data["branches"]]
        self.assertNotIn([6], paths)
        self.assertIn([2, 6], paths)

    def test_safety_is_for_all_remaining_hypotheses(self):
        m = self.model()
        for i, actions in enumerate(p.CATALOG):
            safe = all(original.forecast(c, actions, thermal=False) is not None for c in m.h_candidates)
            safe &= all(original.forecast(c, actions, thermal=True) is not None for c in m.t_candidates)
            self.assertEqual(m._prediction(i) is not None, safe)

    def test_pending_and_stale_tokens_rejected(self):
        m = self.model()
        with self.assertRaises(ValueError):
            p.request_plan(m, 2, 17)
        p.request_plan(m, 2, 18)
        with self.assertRaises(RuntimeError):
            p.request_plan(m, 0, 19)

    def test_original_model_not_accepted_by_new_interpreter(self):
        m = original.SelfAttributor(self.prepared[0], self.model().initial, self.prepared[1])
        with self.assertRaises(ValueError):
            p.request_plan(m, 2, 18)
        with self.assertRaises(RuntimeError):
            self.model().choose(18)

    def test_native_replay_parity_for_every_starter(self):
        for q in v.starters():
            self.assertEqual(v.evaluate(q, [self.row]), v.evaluate(q, [self.row], replay=True))

    def test_adaptive_and_random_parity(self):
        for options in ({"active": True}, {"random_seed": 12}):
            self.assertEqual(v.evaluate(p.Policy(), [self.row], **options),
                             v.evaluate(p.Policy(), [self.row], replay=True, **options))

    def test_replay_never_calls_executor(self):
        with patch("echoai.echo4.self_probe_world.run_probe", side_effect=AssertionError("physics")):
            result = v.evaluate(v.starters()[5], [self.row], replay=True)
        self.assertEqual(result[0]["terminalities"], 0)

    def test_archive_custody_roundtrip(self):
        raw = self.archive.dumps()
        self.assertEqual(p.Archive.loads(raw, sha(raw)).dumps(), raw)
        with self.assertRaises(ValueError):
            p.Archive.loads(raw + b' ', sha(raw))

    def test_archive_rejects_profile_and_catalog_mismatch(self):
        for field in ("profile", "catalog_sha256", "initial"):
            data = copy.deepcopy(self.archive._data)
            data[field] = "bad"
            with self.assertRaises(ValueError):
                p.Archive(data)

    def test_orphan_and_duplicate_branches_rejected(self):
        data = copy.deepcopy(self.archive._data)
        data["branches"] = [r for r in data["branches"] if r["path"] != [2]]
        with self.assertRaises(ValueError):
            p.Archive(data)
        data = copy.deepcopy(self.archive._data)
        data["branches"].append(data["branches"][0])
        with self.assertRaises(ValueError):
            p.Archive(data)

    def test_corrupt_and_cross_context_receipts_rejected(self):
        for field, value in (("token", 99), ("restored", False), ("same_context", False),
                             ("gates", [1] * 8), ("ticks", [0] * 9)):
            data = copy.deepcopy(self.archive._data)
            data["branches"][0]["receipt"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                p.Archive(data)

    def test_missing_root_does_not_reveal_conditional_child(self):
        session = self.archive.replay()
        missing = original.ProbePlan(18, 6, p.CATALOG[6], 0, 0)
        self.assertIsNone(session.request(missing))
        self.assertEqual(session.view()["observed"], [])
        self.assertEqual(session.steps, 0)
        with self.assertRaises(RuntimeError):
            session.request(original.ProbePlan(19, 0, p.CATALOG[0], 0, 0))

    def test_empty_history_remains_unknown_and_charges_budget(self):
        data = copy.deepcopy(self.archive._data)
        data["branches"] = []
        out = p.run_policy(self.model(), p.Policy(), p.Archive(data).replay().request)
        self.assertEqual(out["diagnosis"]["label"], "unknown")
        self.assertEqual(out["steps"], 0)
        self.assertEqual(out["reserved_steps"], 12)
        self.assertTrue(all(e["status"] == "unknown" for e in out["events"]))

    def test_repeated_branch_and_token_rejected(self):
        session = self.archive.replay()
        session.request(original.ProbePlan(18, 2, p.CATALOG[2], 0, 0))
        for plan in (original.ProbePlan(19, 2, p.CATALOG[2], 0, 0),
                     original.ProbePlan(18, 6, p.CATALOG[6], 0, 0)):
            with self.assertRaises(ValueError):
                session.request(plan)

    def test_veto_stops_before_second_probe(self):
        def request(plan):
            return run_probe(self.body, plan, veto_at=1)[0]
        out = p.run_policy(self.model(), v.starters()[5], request)
        self.assertEqual(out["queries"], 1)
        self.assertEqual(out["steps"], 1)
        self.assertEqual(out["diagnosis"]["label"], "unknown")
        self.assertEqual(out["diagnosis"]["reason"], "invalid_execution_receipt")

    def test_operator_stop_no_execution(self):
        with patch.object(p, "native", side_effect=AssertionError("execution")):
            out = p.run_policy(self.model(), p.Policy(), p.native, stopped=lambda: True)
        self.assertEqual(out["reason"], "operator_stop")
        self.assertEqual(out["steps"], 0)

    def test_malformed_receipt_stops_without_claiming_execution(self):
        out = p.run_policy(self.model(), p.Policy(), lambda _: {"fake": "receipt"})
        self.assertEqual(out["queries"], 1)
        self.assertEqual(out["steps"], 0)
        self.assertEqual(out["diagnosis"]["reason"], "invalid_execution_receipt")

    def test_public_judge_not_a_policy_input(self):
        evaluator = v.ReplayEvaluator([[self.row]])
        chosen, before = evaluator.select(p.Policy(), v.starters())
        for groups in evaluator.cache.values():
            for group in groups:
                for row in group:
                    row["correct"], row["wrong"], row["truth_retained"] = False, True, False
        selected, after = evaluator.select(p.Policy(), v.starters())
        self.assertEqual(chosen, selected)
        self.assertEqual(before, after)

    def test_small_budget_and_disabled_experiments(self):
        for q in (p.Policy(step_budget=4), p.Policy(enabled=(0,) * 8)):
            out = v.evaluate(q, [self.row])[0]
            self.assertLessEqual(out["reserved_steps"], q.step_budget)
            self.assertTrue(out["reference_preserved"])
            self.assertEqual(out["cam_facts"], 0)
            self.assertEqual(out["destroyed"], 0)

    def test_prompt_never_exports_hidden_context(self):
        evaluator = v.ReplayEvaluator([[self.row]])
        raw = json.dumps(v.context(evaluator, p.Policy(), (p.Policy(),)))
        for field in ("private_context", "truth_retained", "correct", "packets", "reference_sha256"):
            self.assertNotIn(field, raw)
        with patch.object(evaluator, "public", side_effect=AssertionError("history")):
            empty = v.context(evaluator, p.Policy(), empty=True)
        self.assertEqual(empty["observed_schedules"], [])

    def test_selector_ignores_private_judge_and_retains_ties(self):
        evaluator = v.ReplayEvaluator([[self.row]])
        before = evaluator.public(p.Policy())
        evaluator.cache[p.Policy().identity][0][0]["correct"] = False
        self.assertEqual(before, evaluator.public(p.Policy()))
        chosen, _ = evaluator.select(p.Policy(), (p.Policy(),))
        self.assertEqual(chosen, p.Policy())


class TestQwen(unittest.TestCase):
    def test_real_receipt_schema_and_limits_with_synthetic_transport(self):
        backend = object.__new__(v.Qwen)
        backend.calls, backend.metadata = 0, {"model_sha256": "a" * 64}
        raw = receipt({}, 0, "a" * 64)["raw_response"].encode()
        with patch.object(backend, "_request", return_value=raw):
            for i in range(15):
                row = backend.propose({}, i)
                proposals, cost, error = v.read_proposal(row, {}, i, "a" * 64)
                self.assertEqual(proposals, (p.Policy(),))
                self.assertEqual(cost["calls"], 1)
                self.assertEqual(error, "")
            with self.assertRaises(RuntimeError):
                backend.propose({}, 15)

    def test_tampered_request_and_wrong_model_rejected(self):
        row = receipt({}, 0, "a" * 64)
        with self.assertRaises(ValueError):
            v.read_proposal(row, {"future": 1}, 0, "a" * 64)
        with self.assertRaises(ValueError):
            v.read_proposal(row, {}, 0, "b" * 64)

    def test_transport_failure_recorded(self):
        backend = object.__new__(v.Qwen)
        backend.calls, backend.metadata = 0, {"model_sha256": "a" * 64}
        with patch.object(backend, "_request", side_effect=TimeoutError):
            row = backend.propose({}, 0)
        self.assertEqual(v.read_proposal(row, {}, 0, "a" * 64)[2], "TimeoutError")

    def test_token_overflow_or_truncation_not_candidates(self):
        for changes in ({"tokens_predicted": 641}, {"truncated": True}, {"stopped_limit": True}):
            row = receipt({}, 0, "a" * 64)
            response = json.loads(row["raw_response"])
            response.update(changes)
            row["raw_response"] = json.dumps(response)
            row.pop("sha256")
            row["sha256"] = sha(canonical(row))
            self.assertEqual(v.read_proposal(row, {}, 0, "a" * 64)[0], ())


class TestCampaign(unittest.TestCase):
    def test_fixture_freeze_no_future_feedback_reconstruction_and_tamper(self):
        body = Body(56, 52)
        prep = p.prepare(body)
        condition = (True, True, 0)
        group = [(body, condition, prep, p.collect(body, condition, prep))]
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(bench, "sources", return_value={"fixture": "a" * 64}), \
             patch.object(bench, "binding", return_value={"fixture": "b" * 64}), \
             patch.object(bench, "development_binding", return_value={"fixture": "c" * 64}), \
             patch.object(bench, "load_history", return_value=([group], [])), \
             patch.object(bench, "exam_bodies", return_value=(((57, 52),), ((58, 52),), ((59, 52),))), \
             patch.object(v, "CONDITIONS", ((True, True, 0), (False, True, 4))):
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
                return receipt(data, turn, metadata["model_sha256"], (p.Policy(),) * 4)
            with patch.object(bench, "cases", side_effect=guarded_cases):
                report = bench.build(directory, metadata, propose)
            self.assertEqual(len(seen), 15)
            self.assertTrue(seen[1]["feedback"])
            self.assertFalse(seen[2]["feedback"])
            self.assertEqual(seen[3]["observed_schedules"], [])
            self.assertEqual([c["selection"]["history_contexts"] for c in report["cycles"]], [1, 3, 5])
            self.assertTrue(all(c["checks"]["online_replay_equal"] for c in report["cycles"]))
            self.assertFalse(report["dream1_green"])
            for cycle in report["cycles"]:
                self.assertTrue(all(r["slots"] == 8 for r in cycle["selection"]["candidate_counts"].values()))
            bench.persist(directory, "report.json", report, False)
            with patch.object(v.Qwen, "propose", side_effect=AssertionError("LLM")):
                self.assertTrue(bench.verify(directory)["valid"])
            path = directory / "selection-0.json"
            saved = path.read_bytes()
            path.write_bytes(b'{}')
            self.assertFalse(bench.verify(directory)["valid"])
            path.write_bytes(saved)
            report["criteria_passed"] = True
            report.pop("reproduction_sha256")
            report["reproduction_sha256"] = sha(canonical(report))
            (directory / "report.json").write_bytes(canonical(report))
            self.assertFalse(bench.verify(directory)["valid"])

    def test_missing_evidence_never_green(self):
        with tempfile.TemporaryDirectory() as folder:
            result = bench.verify(Path(folder) / "missing")
        self.assertFalse(result["valid"])
        self.assertFalse(result["dream1_green"])

    def test_parent_sources_still_intact(self):
        self.assertIn("report.json", v.binding())
        self.assertTrue(set(bench.inherited_sources()).issubset(bench.sources()))


if __name__ == "__main__":
    unittest.main()
