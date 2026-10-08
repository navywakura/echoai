"""DREAM-A: strict custody, partial information, budgets and native evidence."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from echoai.echo4 import dream_history as h
from echoai.echo4 import dream_history_bench as bench


def fixture():
    """Synthetic schema fixture, explicitly not an executed discovery tree."""
    nodes = []
    for index, ancestor, experiment in ((0, None, None), (1, 0, "native"), (2, 0, "greedy"), (3, 1, "native")):
        turn = 0 if ancestor is None else nodes[ancestor]["observation"]["turn"] + 1
        nodes.append({"id": index, "parent": ancestor, "experiment": experiment,
                      "observation": {"wsp": "00" * 16, "turn": turn,
                                      "action": None if index == 0 else 0,
                                      "gate": None if index == 0 else 0,
                                      "reward": 0, "terminal": False},
                      "score": 0, "checkpoint": str(index) * 64,
                      "cost": {"attempts": int(index > 0), "native_steps": int(index > 0), "llm_calls": 0}})
    return {"schema": h.SCHEMA, "profile": h.PROFILE, "sources": {"fixture": "a" * 64},
            "continuity_certificate": "b" * 64, "nodes": nodes}


class TestArchive(unittest.TestCase):
    def test_roundtrip_and_defensive_copy(self):
        data = fixture()
        archive = h.Archive(data)
        raw = archive.dumps()
        data["nodes"][0]["score"] = -16
        self.assertEqual(archive.dumps(), raw)
        self.assertEqual(h.Archive.loads(raw, expected_sha256=h.sha(raw)).dumps(), raw)

    def test_digest_mismatch_rejected(self):
        raw = h.Archive(fixture()).dumps()
        with self.assertRaises(ValueError):
            h.Archive.loads(raw + b" ", expected_sha256=h.sha(raw))

    def test_duplicate_keys_float_nan_and_malformed_json_rejected(self):
        for raw in (b'{"x":0,"x":1}', b'{"x":1.5}', b'{"x":NaN}', b'\xff', b'{'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                h.Archive.loads(raw, expected_sha256=h.sha(raw))

    def test_bad_schema_fields_and_private_observation_rejected(self):
        for key in ("H", "temperature", "checkpoint_path", "future_score"):
            data = fixture()
            data["nodes"][1]["observation"][key] = 60
            with self.subTest(key=key), self.assertRaises(ValueError):
                h.Archive(data)

    def test_cycles_forward_parent_and_bool_ids_rejected(self):
        for value in (1, 2, -1, True, None):
            data = fixture()
            data["nodes"][1]["parent"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                h.Archive(data)

    def test_terminal_cannot_have_children(self):
        data = fixture()
        data["nodes"][0]["observation"]["terminal"] = True
        with self.assertRaises(ValueError):
            h.Archive(data)

    def test_clock_mismatch_rejected(self):
        data = fixture()
        data["nodes"][3]["observation"]["turn"] += 1
        with self.assertRaises(ValueError):
            h.Archive(data)

    def test_mutated_score_and_cost_even_with_new_digest_rejected(self):
        for field in ("attempts", "native_steps", "llm_calls"):
            data = fixture()
            data["nodes"][1]["cost"][field] += 1
            raw = h.canonical(data)
            with self.subTest(field=field), self.assertRaises(ValueError):
                h.Archive.loads(raw, expected_sha256=h.sha(raw))
        data = fixture()
        data["nodes"][1]["score"] = 1
        with self.assertRaises(ValueError):
            h.Archive(data)

    def test_invalid_observation_types_and_ranges(self):
        for key, value in (("wsp", "00" * 17), ("turn", True), ("action", 3),
                           ("gate", 1.0), ("reward", 128), ("terminal", 0)):
            data = fixture()
            data["nodes"][1]["observation"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                h.Archive(data)

    def test_empty_oversized_and_unknown_profile_rejected(self):
        for value in ([], fixture()["nodes"] * h.MAX_NODES):
            data = fixture()
            data["nodes"] = value
            with self.assertRaises(ValueError):
                h.Archive(data)
        raw = b"x" * (h.MAX_BYTES + 1)
        with self.assertRaises(ValueError):
            h.Archive.loads(raw, expected_sha256=h.sha(raw))
        data = fixture()
        data["profile"] = "unsupported"
        with self.assertRaises(ValueError):
            h.Archive(data)


class TestPartialReplay(unittest.TestCase):
    def setUp(self):
        self.archive = h.Archive(fixture())
        self.replay = self.archive.replay(budget=20)

    def test_initial_view_has_only_root_and_no_custody_or_future(self):
        view = self.replay.view()
        self.assertEqual(len(view["nodes"]), 1)
        for key in ("sources", "continuity_certificate", "checkpoint", "total_nodes", "children"):
            self.assertNotIn(key, json.dumps(view))
        self.assertEqual(view["represented_native_steps"], 0)

    def test_handles_do_not_leak_global_creation_order(self):
        first = self.replay.expand(0, "greedy")
        self.assertEqual(first["node"]["id"], 1)  # private index was 2
        second = self.replay.expand(0, "native")
        self.assertEqual(second["node"]["id"], 2)  # private index was 1
        third = self.replay.expand(2, "native")
        self.assertEqual(third["node"]["parent"], 2)

    def test_changing_unseen_future_does_not_change_visible_prefix(self):
        data = fixture()
        data["nodes"][3]["observation"]["reward"] = -16
        data["nodes"][3]["score"] = -16
        data["nodes"][3]["observation"]["terminal"] = True
        other = h.Archive(data).replay(budget=20)
        self.assertEqual(other.view(), self.replay.view())
        self.assertEqual(other.expand(0, "native"), self.replay.expand(0, "native"))
        self.assertEqual(other.view(), self.replay.view())
        self.assertNotEqual(other.expand(1, "native"), self.replay.expand(1, "native"))

    def test_adding_unseen_future_does_not_change_view(self):
        data = fixture()
        child = copy.deepcopy(data["nodes"][-1])
        child.update(id=4, parent=2, experiment="greedy")
        data["nodes"].append(child)
        other = h.Archive(data).replay(budget=20)
        self.assertEqual(self.replay.view(), other.view())
        self.assertEqual(self.replay.expand(0, "native"), other.expand(0, "native"))
        self.assertEqual(self.replay.view(), other.view())

    def test_same_wsp_does_not_merge_distinct_parent_states(self):
        self.replay.batch([(0, "native"), (0, "greedy")])
        self.assertEqual(self.replay.expand(1, "native")["status"], "observed")
        self.assertEqual(self.replay.expand(2, "native")["status"], "unknown")

    def test_missing_branch_is_unknown_not_invented_or_execution(self):
        self.replay.expand(0, "greedy")
        result = self.replay.expand(1, "native")
        self.assertEqual(result, {"status": "unknown", "parent": 1, "experiment": "native"})
        self.assertEqual(self.replay.view()["represented_native_steps"], 1)
        self.assertEqual(self.replay.view()["queries_used"], 2)

    def test_repeat_does_not_return_same_execution_twice(self):
        self.replay.expand(0, "native")
        self.assertEqual(self.replay.expand(0, "native")["status"], "unknown")
        self.assertEqual(self.replay.view()["represented_native_steps"], 1)

    def test_multiple_executed_samples_have_separate_costs(self):
        data = fixture()
        node = copy.deepcopy(data["nodes"][1])
        node["id"] = 4
        data["nodes"].append(node)
        replay = h.Archive(data).replay()
        first = replay.expand(0, "native")
        second = replay.expand(0, "native")
        self.assertNotEqual(first["node"]["id"], second["node"]["id"])
        self.assertEqual(replay.view()["represented_native_steps"], 2)

    def test_terminal_abstains_without_new_cost(self):
        data = fixture()
        data["nodes"] = data["nodes"][:1]
        data["nodes"][0]["observation"]["terminal"] = True
        replay = h.Archive(data).replay()
        self.assertEqual(replay.expand(0, "native")["status"], "terminal")
        self.assertEqual(replay.view()["represented_native_steps"], 0)

    def test_query_budget_is_atomic_and_counts_unknown(self):
        replay = self.archive.replay(budget=1)
        replay.expand(0, "greedy")
        before = replay.view()
        with self.assertRaises(RuntimeError):
            replay.expand(1, "native")
        self.assertEqual(replay.view(), before)
        replay = self.archive.replay(budget=2)
        replay.expand(0, "greedy")
        replay.expand(1, "native")
        self.assertEqual(replay.view()["queries_remaining"], 0)

    def test_invalid_or_future_batch_does_not_partially_apply(self):
        for batch in ([(0, "native"), (1, "native")], [(0, "native"), (0, "native")],
                      [(0, "native"), (0, "unknown")], [(True, "native")], [(0,)]):
            before = self.replay.view()
            with self.subTest(batch=batch), self.assertRaises(ValueError):
                self.replay.batch(batch)
            self.assertEqual(self.replay.view(), before)

    def test_batch_width_and_budget_validate_before_revealing(self):
        for replay, error in ((self.archive.replay(batch_limit=1), ValueError),
                              (self.archive.replay(budget=1), RuntimeError)):
            before = replay.view()
            with self.assertRaises(error):
                replay.batch([(0, "native"), (0, "greedy")])
            self.assertEqual(replay.view(), before)

    def test_empty_batch_and_zero_budget(self):
        replay = self.archive.replay(budget=0)
        before = replay.view()
        self.assertEqual(replay.batch([]), [])
        self.assertEqual(replay.view(), before)
        with self.assertRaises(RuntimeError):
            replay.expand(0, "native")

    def test_views_and_sessions_are_isolated(self):
        other = self.archive.replay(budget=20)
        raw = self.archive.dumps()
        result = self.replay.expand(0, "native")
        result["node"]["observation"]["wsp"] = "ff" * 16
        self.assertEqual(other.view()["queries_used"], 0)
        self.assertNotEqual(self.replay.view()["nodes"][-1]["observation"]["wsp"], "ff" * 16)
        self.assertEqual(raw, self.archive.dumps())

    def test_replay_never_calls_the_native_agent_or_world(self):
        with patch.object(bench.base.ContinuityRun, "step", side_effect=AssertionError("executed")), \
                patch.object(bench.base.SelfAgent, "turn", side_effect=AssertionError("executed")), \
                patch.object(bench.base.DockEnv, "step_homeostatic", side_effect=AssertionError("executed")):
            result = bench.replay_all(self.archive)
        self.assertEqual(result["view"]["represented_native_steps"], 3)
        self.assertEqual(result["view"]["replay_native_steps"], 0)
        self.assertEqual(result["view"]["replay_llm_calls"], 0)


class TestNativeEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name) / "campaign"
        cls.spec = ("native-test", 60, 46, 2, 3, 1)
        with patch.object(bench, "CASES", (cls.spec, ("terminal", 32, 64, 2, 128, 1))):
            cls.report = bench.record(cls.directory)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_agent_archive_matches_fresh_process(self):
        self.assertTrue(self.report["development_passed"])
        row = self.report["trees"][0]
        self.assertEqual(row["native_attempts"], 2)
        self.assertTrue(row["fresh_process_equal"])
        self.assertTrue(row["observed_equal"])
        self.assertTrue(row["parent_unchanged"])
        self.assertFalse(self.report["dream1_green"])
        self.assertFalse(self.report["qwen_implemented"])

    def test_complete_native_reconstruction(self):
        with patch.object(bench, "CASES", (self.spec, ("terminal", 32, 64, 2, 128, 1))):
            receipt = bench.verify(self.directory)
        self.assertTrue(receipt["valid"], receipt)
        self.assertFalse(receipt["dream1_green"])

    def test_checkpoint_corruption_rejected_without_modifying_artifact(self):
        target = self.directory / "native-test/0000.json"
        before = target.read_bytes()
        original = Path.read_bytes

        def altered(path):
            return original(path) + (b" " if path == target else b"")

        with patch.object(Path, "read_bytes", altered), \
                patch.object(bench, "CASES", (self.spec, ("terminal", 32, 64, 2, 128, 1))):
            receipt = bench.verify(self.directory)
        self.assertFalse(receipt["valid"])
        self.assertIn("checkpoint differs", receipt["findings"][0])
        self.assertEqual(before, target.read_bytes())

    def test_cannot_overwrite_evidence(self):
        with self.assertRaises(FileExistsError):
            bench.record(self.directory)

    def test_continuity_certificate_and_sources_unchanged(self):
        self.assertEqual(self.report["parent_binding"], bench.parent_binding())
        self.assertEqual(self.report["sources"], bench.sources())

    def test_forged_report_rejected(self):
        real = bench.parent.read_json

        def altered(path):
            result = real(path)
            if path == self.directory / "report.json":
                result["dream1_green"] = True
            return result

        with patch.object(bench.parent, "read_json", altered), \
                patch.object(bench, "CASES", (self.spec, ("terminal", 32, 64, 2, 128, 1))):
            receipt = bench.verify(self.directory)
        self.assertFalse(receipt["valid"])
        self.assertFalse(receipt["dream1_green"])
        self.assertIn("report differs", receipt["findings"][0])


if __name__ == "__main__":
    unittest.main()
