"""CAPACITY-1: fixed sensory interface, causal controls and certificate."""
from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from echoai.nexus0 import capacity1


class TestCapacity1Units(unittest.TestCase):
    def test_wsp_interface_and_imported_spoke_projection(self):
        raw = capacity1._packet(0, 0)
        self.assertEqual(len(raw), 16)
        self.assertEqual(capacity1.signature_for(raw, capacity1.FEATURE_BLIND), 0)
        self.assertIsInstance(capacity1.signature_for(raw, capacity1.LIF256), int)
        self.assertIsInstance(capacity1.signature_for(raw, capacity1.LIF512), int)
        with self.assertRaises(ValueError):
            capacity1.signature_for(b"short", capacity1.LIF512)

    def test_held_out_packet_is_distinct_but_keeps_shared_vertex(self):
        packets = capacity1._family_packets()
        self.assertEqual(len(packets), capacity1.FAMILIES)
        for family in range(capacity1.FAMILIES):
            self.assertEqual(len(packets[family][0]), 16)
            self.assertNotEqual(packets[family][0], packets[family][1])
            self.assertEqual(capacity1.simhash16(packets[family][0]),
                             capacity1.simhash16(packets[family][1]))

    def test_temporal_head_isolates_adaptation_from_neuron_count(self):
        seed = capacity1.seeds("capacity", "development")[0]
        control = capacity1.temporal_seed(seed, 0, 8)
        adaptive = capacity1.temporal_seed(seed, 4, 8)
        permuted = capacity1.temporal_seed(seed, 4, 8, feature_permuted=True)
        self.assertEqual((control["hits"], control["total"]), (0, 2))
        self.assertEqual((adaptive["hits"], adaptive["total"]), (2, 2))
        self.assertEqual(permuted["hits"], 0)
        self.assertNotEqual(adaptive["normal_signature"],
                            adaptive["anomaly_signature"])


class TestCapacity1Certificate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(capacity1.__file__).resolve().parents[1]
        cls.report = json.loads(
            (root / "lab" / "echo2_capacity1_report.json").read_text())

    def test_report_is_green_and_audited(self):
        self.assertTrue(self.report["green"])
        self.assertTrue(capacity1.green(self.report))
        science = self.report["scientific"]
        self.assertEqual(science["wsp_bytes"], 16)
        self.assertEqual((science["false_facts"], science["destroyed"],
                          science["cortex_calls"]), (0, 0, 0))
        self.assertEqual(science["adaptive_status"], "justified")

    def test_measured_causal_comparisons(self):
        science = self.report["scientific"]
        perception = science["perception"]
        self.assertGreater(perception[capacity1.LIF512]["hits"],
                           perception[capacity1.LIF256]["hits"])
        self.assertEqual(perception[capacity1.LIF512]["incompatible_collisions"], 0)
        self.assertLess(perception[capacity1.FEATURE_PERMUTED]["hits"],
                        perception[capacity1.LIF256]["hits"])
        temporal = science["temporal"]
        self.assertEqual(temporal[capacity1.LIF512_ALIF128]["hits"],
                         temporal[capacity1.LIF512_ALIF128]["total"])
        self.assertEqual(temporal[capacity1.LIF512_LIF128]["hits"], 0)

    def test_auditor_rejects_seed_row_and_green_mutations(self):
        for path, value in (
            (("green",), False),
            (("scientific", "exam_seeds", 0), 0),
            (("scientific", "perception", capacity1.LIF512, "rows", 0,
              "hits"), 0),
        ):
            changed = copy.deepcopy(self.report)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            self.assertFalse(capacity1.green(changed), path)


if __name__ == "__main__":
    unittest.main()
