"""STREAM-1: external chunks stay outside WSP while alias stays visible."""
from __future__ import annotations

import inspect
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from echoai.nexus0 import stream1


class TestStream1Processor(unittest.TestCase):
    def test_ingest_api_has_no_chunk_or_frame(self):
        self.assertEqual(list(inspect.signature(stream1.StreamProcessor.ingest).parameters),
                         ["self", "wsp", "action", "next_wsp"])

    def test_equal_packets_share_cam_across_external_chunks(self):
        processor = stream1.StreamProcessor()
        source = stream1.external_stream()
        first = source[0]
        last_same = next(row for row in reversed(source)
                         if row.wsp == first.wsp and row.action == first.action)
        processor.ingest(first.wsp, first.action, first.next_wsp)
        processor.ingest(last_same.wsp, last_same.action, last_same.next_wsp)
        self.assertEqual(sum(slot.occupied != 0 for slot in processor.agent.cam.slot), 2)
        self.assertEqual(processor.dynamic_alias(), [])

    def test_changed_physics_is_an_alias_not_a_new_packet(self):
        clean = stream1.external_stream()
        altered = stream1.external_stream(altered_chunks=(stream1.CHUNKS // 2,))
        self.assertEqual({row.wsp for row in clean}, {row.wsp for row in altered})
        processor = stream1.StreamProcessor()
        processor.ingest_all(altered)
        self.assertEqual(len(processor.dynamic_alias()), 1)
        self.assertGreater(processor.agent.t.conflicts, 0)

    def test_rejects_non_wsp_input(self):
        processor = stream1.StreamProcessor()
        with self.assertRaises(ValueError):
            processor.ingest(b"bad", 0, stream1.packet_of(0))
        with self.assertRaises(ValueError):
            processor.ingest(stream1.packet_of(0), 0, bytearray(16))


class TestStream1Experiment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = stream1.experiment()

    def test_long_stream_and_alias_control(self):
        r = self.report
        self.assertTrue(stream1.green(r))
        self.assertGreater(r["stream_frames"], 256)
        self.assertEqual(r["sequence_last"], r["stream_frames"] - 1)
        self.assertEqual(r["coherent"]["dynamic_alias"], 0)
        self.assertEqual(r["alias_control"]["dynamic_alias"], 1)

    def test_packet_contract_and_fast_locks(self):
        r = self.report
        for name in ("coherent_packet_contract", "aliased_packet_contract"):
            contract = r[name]
            self.assertEqual(contract["packet_bytes"], [16])
            self.assertTrue(contract["domain_zero"])
            self.assertTrue(contract["style_zero"])
            self.assertTrue(contract["seq_local"])
        self.assertEqual((r["cortex_calls"], r["destroyed"]), (0, 0))
        self.assertFalse(r["chunk_in_wsp"])

    def test_green_rejects_alias_hiding_and_headline_lies(self):
        for key, bad in (
            ("chunk_in_wsp", True), ("cortex_calls", 1),
            ("stream_frames", 256),
        ):
            self.assertFalse(stream1.green(dict(self.report, **{key: bad})), key)
        changed = dict(self.report)
        changed["alias_control"] = dict(changed["alias_control"], dynamic_alias=0)
        self.assertFalse(stream1.green(changed))

    def test_runner_writes_a_separate_report(self):
        with tempfile.TemporaryDirectory() as td:
            fake_module = Path(td) / "nexus0" / "stream1.py"
            fake_module.parent.mkdir()
            fake_module.touch()
            with mock.patch.object(stream1, "__file__", str(fake_module)):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(stream1.main([]), 0)
            written = json.loads((Path(td) / "lab" / "echo2_stream1_report.json")
                                 .read_text(encoding="utf-8"))
            self.assertTrue(written["green"])


if __name__ == "__main__":
    unittest.main()

