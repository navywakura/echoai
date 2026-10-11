"""Sampling and missing-evidence regressions; these are not flight evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest

from echo5.sitl_truth import PoseRecorder, audit_pose_stream, instrument_backend


class PoseRecorderTests(unittest.TestCase):
    def capture(self, stamps):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            recorder = PoseRecorder(path, "test-run", period_ns=10_000_000)
            for stamp in stamps:
                recorder.capture((stamp, 0., 0., 2.5, 0., 0., 0.), stamp+5_000_000)
            receipt = recorder.close()
            raw = (path/"private-poses.jsonl").read_bytes()
            self.assertEqual(receipt["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(receipt, json.loads((path/"private-poses-receipt.json").read_text()))
            rows = [json.loads(line) for line in raw.splitlines()]
            return rows, receipt

    def audit(self, rows, receipt):
        return audit_pose_stream(rows, receipt, nonce="test-run",
                                 source_sha256=receipt["source_sha256"],
                                 max_gap_ns=100_000_000)

    def test_capture_uses_original_pose_time_and_drains_on_close(self):
        rows, receipt = self.capture(range(1_000_000, 401_000_000, 1_000_000))
        self.assertEqual([r["now_ns"] for r in rows], list(range(1_000_000, 401_000_000, 10_000_000)))
        self.assertEqual(rows[0]["delivered_clock_ns"], 6_000_000)
        self.assertEqual(receipt["callbacks"], 400)
        self.assertEqual(receipt["sampled_out"], 360)
        self.assertEqual(self.audit(rows, receipt), [])

    def test_gap_is_preserved_not_interpolated_or_relabelled(self):
        rows, receipt = self.capture([10_000_000, 20_000_000, 121_000_000])
        self.assertEqual(len(rows), 3)
        self.assertIn("truth_coverage", self.audit(rows, receipt))

    def test_regression_cannot_be_silently_sorted(self):
        rows, receipt = self.capture([10_000_000, 30_000_000, 20_000_000, 40_000_000])
        self.assertEqual(receipt["regressions"], 1)
        self.assertIn("truth_capture_errors", self.audit(rows, receipt))

    def test_missing_rows_and_forged_capture_timestamp_fail(self):
        rows, receipt = self.capture([10_000_000, 20_000_000, 30_000_000])
        self.assertIn("truth_record_count", self.audit(rows[:-1], receipt))
        changed = deepcopy(rows); changed[1]["body"][0] += 1
        self.assertIn("truth_capture_binding", self.audit(changed, receipt))
        changed = deepcopy(rows); changed[1]["sequence"] = 9
        self.assertIn("truth_sequence", self.audit(changed, receipt))

    def test_wrong_run_incomplete_writer_and_overflow_fail(self):
        rows, receipt = self.capture([10_000_000, 20_000_000, 30_000_000])
        for field, value, finding in (("nonce", "other", "truth_identity"),
                                       ("complete", False, "truth_writer_incomplete"),
                                       ("dropped", 1, "truth_capture_errors")):
            changed = dict(receipt, **{field:value})
            self.assertIn(finding, self.audit(rows, changed))

    def test_capture_coverage_must_span_the_supervised_episode(self):
        rows, receipt = self.capture([10_000_000, 20_000_000, 30_000_000])
        findings = audit_pose_stream(rows, receipt, nonce="test-run",
                                    source_sha256=receipt["source_sha256"], max_gap_ns=100_000_000,
                                    start_ns=15_000_000, end_ns=131_000_000)
        self.assertIn("truth_episode_coverage", findings)

    def test_backend_callback_is_recorded_without_polling(self):
        class Backend:
            def __init__(self, world):
                self.lock = threading.Lock(); self.body_seen = 0; self.body = None
            def _dyn_pose(self, message):
                if message:
                    with self.lock:
                        self.body = message; self.body_seen += 1
            def now_ns(self):
                return 80_000_000
        with tempfile.TemporaryDirectory() as directory:
            recorder = PoseRecorder(Path(directory), "test-run")
            Wrapped = instrument_backend(Backend, recorder)
            backend = Wrapped("sim3")
            for stamp in (10_000_000, 20_000_000, 30_000_000):
                backend._dyn_pose((stamp, 0., 0., 2.5, 0., 0., 0.))
            backend._dyn_pose(None)
            self.assertEqual(recorder.close()["records"], 3)

    def test_invalid_pose_fails_receipt_without_mutating_backend(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = PoseRecorder(Path(directory), "test-run")
            recorder.capture((10_000_000, float("nan"), 0., 0., 0., 0., 0.), 10_000_000)
            receipt = recorder.close()
            self.assertEqual(receipt["invalid"], 1)
            self.assertEqual(receipt["records"], 0)
