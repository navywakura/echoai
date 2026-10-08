"""SLEEP-2: bounded consolidation with immutable CAM/T sources."""
from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from echoai.nexus0 import sleep2


class TestConsolidatedRules(unittest.TestCase):
    def test_rule_requires_multiple_origins(self):
        agent, _slots = sleep2.build_day()
        rules, audit = sleep2.consolidate(agent, min_origins=100)
        self.assertEqual(rules.size, 0)
        self.assertGreater(audit["below_support"], 0)

    def test_capacity_is_fixed_and_drops_without_overwrite(self):
        rules = sleep2.ConsolidatedRules(capacity=1)
        a = sleep2.packet_of(0, 0)
        b = sleep2.packet_of(0, 1)
        self.assertTrue(rules.add(a, 0, a, 1, 8, 8))
        before = rules.snapshot_hash()
        self.assertFalse(rules.add(b, 0, b, 1, 8, 8))
        self.assertEqual(rules.size, 1)
        self.assertEqual(rules.dropped, 1)
        self.assertNotEqual(rules.snapshot_hash(), before)  # dropped is counted
        self.assertEqual(rules.current[0], sleep2.template_of(a))

    def test_prediction_is_read_only(self):
        agent, slots = sleep2.build_day()
        rules, _audit = sleep2.consolidate(agent)
        wsp = sleep2.packet_of(0, sleep2.HOLDOUT_STATES[0])
        before = rules.snapshot_hash()
        predicted = rules.predict(wsp, 0)
        self.assertEqual(
            predicted,
            sleep2.packet_of(0, sleep2.HOLDOUT_STATES[0] + 1),
        )
        self.assertEqual(rules.snapshot_hash(), before)

    def test_bad_wsp_is_rejected(self):
        rules = sleep2.ConsolidatedRules()
        for raw in (b"", b"x" * 15, bytearray(16)):
            with self.assertRaises(ValueError):
                rules.predict(raw, 0)


class TestSleep2Experiment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = sleep2.experiment()

    def test_pressure_compression_and_heldout_gain(self):
        r = self.report
        self.assertTrue(sleep2.green(r))
        self.assertGreaterEqual(r["cam_occupied"], r["cam_pressure_min"])
        self.assertGreater(r["compressed_knowledge_after"],
                           r["compressed_knowledge_before"])
        self.assertEqual(r["exam"]["t_hits"], 0)
        self.assertEqual(r["exam"]["rule_hits"], r["exam"]["points"])

    def test_sleep_does_not_modify_source_memories_or_call_cortex(self):
        r = self.report
        self.assertTrue(r["source_unchanged"])
        self.assertEqual(r["source_hash_before"], r["source_hash_after"])
        self.assertEqual((r["destroyed_before"], r["destroyed_after"],
                          r["cortex_calls"]), (0, 0, 0))

    def test_conflicting_regularities_are_refused(self):
        control = self.report["conflict_control"]
        self.assertEqual(control["ambiguous_groups"], sleep2.SEMANTIC_TEMPLATES)
        self.assertEqual(control["world_conflicts"], sleep2.SEMANTIC_TEMPLATES)
        self.assertEqual(control["rules"],
                         sleep2.SEMANTIC_TEMPLATES * (sleep2.N_ACTIONS - 1))
        self.assertLess(control["exam"]["rule_hits"],
                        control["exam"]["points"])

    def test_green_fails_closed_on_core_claims(self):
        for key, bad in (
            ("cam_occupied", 1), ("rules", 0),
            ("compressed_knowledge_after", 0), ("source_unchanged", False),
            ("destroyed_after", 1), ("cortex_calls", 1),
        ):
            self.assertFalse(sleep2.green(dict(self.report, **{key: bad})), key)

    def test_runner_writes_its_own_report(self):
        with tempfile.TemporaryDirectory() as td:
            fake_module = Path(td) / "nexus0" / "sleep2.py"
            fake_module.parent.mkdir()
            fake_module.touch()
            with mock.patch.object(sleep2, "__file__", str(fake_module)):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(sleep2.main([]), 0)
            written = json.loads((Path(td) / "lab" / "echo2_sleep2_report.json")
                                 .read_text(encoding="utf-8"))
            self.assertTrue(written["green"])


if __name__ == "__main__":
    unittest.main()
