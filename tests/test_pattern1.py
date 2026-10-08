"""PATTERN-1: learned invariance without id/pose/context leakage."""
from __future__ import annotations

import inspect
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from echoai.nexus0 import pattern1


class TestPattern1Memory(unittest.TestCase):
    def test_api_cannot_receive_exam_answer_or_metadata(self):
        self.assertEqual(list(inspect.signature(
            pattern1.InvariantPatternMemory.observe).parameters),
            ["self", "signature", "outcome"])
        self.assertEqual(list(inspect.signature(
            pattern1.InvariantPatternMemory.predict).parameters),
            ["self", "signature"])

    def test_near_signatures_join_only_with_compatible_dynamics(self):
        mem = pattern1.InvariantPatternMemory(min_hits=2)
        a = 0xF0C3
        same = a ^ 0x0001
        incompatible = a ^ 0x400C
        self.assertEqual(mem.observe(a, 16), 0)
        self.assertEqual(mem.observe(same, 16), 0)
        self.assertEqual(mem.observe(incompatible, -16), 1)
        self.assertEqual(mem.size, 2)
        self.assertGreater(mem.incompatible_near, 0)

    def test_frozen_prediction_and_ambiguous_refusal(self):
        mem = pattern1.InvariantPatternMemory(max_hamming=2, min_hits=2)
        for _ in range(2):
            mem.observe(0x0000, 16)
            mem.observe(0x0003, -16)
        before = (mem.snapshot_hash(), mem.observations)
        self.assertIsNone(mem.predict(0x0001))  # distance one from both
        self.assertEqual((mem.snapshot_hash(), mem.observations), before)

    def test_fixed_capacity_drops_without_overwrite(self):
        mem = pattern1.InvariantPatternMemory(capacity=1, max_hamming=0)
        mem.observe(0x0000, 0)
        before = (mem.prototype[:], mem.outcome[:], mem.hits[:])
        self.assertIsNone(mem.observe(0xFFFF, 16))
        self.assertEqual(mem.dropped, 1)
        self.assertEqual((mem.prototype, mem.outcome, mem.hits), before)

    def test_integer_input_contract(self):
        mem = pattern1.InvariantPatternMemory()
        for bad in (-1, 65536, 1.5, True):
            with self.assertRaises(ValueError):
                mem.predict(bad)
        for bad in (-128, 128, 1.5, True):
            with self.assertRaises(ValueError):
                mem.observe(1, bad)


class TestPattern1Experiment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = pattern1.experiment()

    def test_unseen_objects_views_contexts_and_positions(self):
        r = self.report
        self.assertTrue(pattern1.green(r))
        self.assertEqual(r["recognized"], r["exam_samples"])
        self.assertEqual(r["outcome_hits"], r["exam_samples"])
        self.assertEqual(r["family_hits"], r["exam_samples"])
        self.assertEqual(r["exact_hits"], 0)
        self.assertGreater(r["gain_over_exact"], 0)

    def test_near_but_incompatible_objects_stay_apart(self):
        r = self.report
        self.assertTrue(r["incompatible_split"])
        self.assertGreater(r["incompatible_near"], 0)
        self.assertNotEqual(r["category_family"]["resource"],
                            r["category_family"]["mimic_hazard"])

    def test_exam_is_frozen_and_fast_only(self):
        r = self.report
        self.assertEqual(r["observations_before_exam"],
                         r["observations_after_exam"])
        self.assertEqual(r["hash_before_exam"], r["hash_after_exam"])
        self.assertEqual((r["cortex_calls"], r["destroyed"]), (0, 0))

    def test_green_fails_closed_on_headline_mutations(self):
        for key, bad in (
            ("outcome_hits", 0), ("family_hits", 0), ("exact_hits", 32),
            ("gain_over_exact", 0), ("incompatible_near", 0),
            ("incompatible_split", False), ("dropped", 1),
            ("object_id_used_by_learner", True), ("cortex_calls", 1),
        ):
            changed = dict(self.report, **{key: bad})
            self.assertFalse(pattern1.green(changed), key)

    def test_runner_writes_its_own_report(self):
        with tempfile.TemporaryDirectory() as td:
            fake_module = Path(td) / "nexus0" / "pattern1.py"
            fake_module.parent.mkdir()
            fake_module.touch()
            with mock.patch.object(pattern1, "__file__", str(fake_module)):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(pattern1.main([]), 0)
            report_path = Path(td) / "lab" / "echo2_pattern1_report.json"
            written = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(written["green"])


if __name__ == "__main__":
    unittest.main()
