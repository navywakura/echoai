"""Private evaluator instrumentation; never imported or exposed to the actor.

Keep original Gazebo pose stamps in a bounded callback queue. The main runner's
poll frequency cannot discard intermediate poses. No interpolation, coordinate
transformation or control command is performed here. The historical backend is
subclassed at launch; its on-disk bytes remain untouched.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import threading


SCHEMA = "echo5.sitl.private-poses.v1"


class PoseRecorder:
    def __init__(self, output, nonce, *, period_ns=10_000_000, capacity=16384):
        self.output = Path(output)
        self.nonce, self.period_ns = nonce, period_ns
        self.queue = queue.Queue(maxsize=capacity)
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.closed = False
        self.last_seen = self.last_kept = -1
        self.callbacks = self.sampled_out = self.duplicates = self.regressions = 0
        self.invalid = self.dropped = self.enqueued = self.written = 0
        self.errors = []
        self.stream = (self.output/"private-poses.jsonl").open("xb")
        self.hasher = hashlib.sha256()
        self.thread = threading.Thread(target=self._write, name="private-pose-writer", daemon=True)
        self.thread.start()

    def capture(self, body, delivered_clock_ns):
        with self.lock:
            if self.closed:
                return
            self.callbacks += 1
            if (not isinstance(body, (tuple, list)) or len(body) != 7
                    or type(body[0]) is not int or body[0] < 0
                    or type(delivered_clock_ns) is not int or delivered_clock_ns < 0
                    or any(type(v) not in (int, float) or not math.isfinite(v) for v in body[1:])):
                self.invalid += 1
                return
            stamp = body[0]
            if stamp < self.last_seen:
                self.regressions += 1
                return
            if stamp == self.last_seen:
                self.duplicates += 1
                return
            self.last_seen = stamp
            if self.last_kept >= 0 and stamp-self.last_kept < self.period_ns:
                self.sampled_out += 1
                return
            record = dict(sequence=self.enqueued, now_ns=stamp, body=list(body),
                          delivered_clock_ns=delivered_clock_ns)
            try:
                self.queue.put_nowait(record)
            except queue.Full:
                self.dropped += 1
                return
            self.enqueued += 1
            self.last_kept = stamp

    def _write(self):
        try:
            while not self.stop.is_set() or not self.queue.empty():
                try:
                    row = self.queue.get(timeout=.05)
                except queue.Empty:
                    continue
                data = (json.dumps(row, sort_keys=True, allow_nan=False)+"\n").encode()
                self.stream.write(data)
                self.hasher.update(data)
                self.written += 1
            self.stream.flush()
            os.fsync(self.stream.fileno())
        except Exception as exc:
            self.errors.append(type(exc).__name__+": "+str(exc))
        finally:
            self.stream.close()

    def close(self):
        with self.lock:
            if self.closed:
                raise RuntimeError("Private pose recorder already closed")
            self.closed = True
            self.stop.set()
        self.thread.join(5)
        receipt = dict(schema=SCHEMA, nonce=self.nonce, period_ns=self.period_ns,
                       source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                       complete=not self.thread.is_alive() and not self.errors,
                       records=self.written, enqueued=self.enqueued, callbacks=self.callbacks,
                       sampled_out=self.sampled_out, duplicates=self.duplicates,
                       regressions=self.regressions, invalid=self.invalid, dropped=self.dropped,
                       errors=list(self.errors), sha256=self.hasher.hexdigest())
        with (self.output/"private-poses-receipt.json").open("x") as stream:
            json.dump(receipt, stream, sort_keys=True, allow_nan=False)
        return receipt


def instrument_backend(base, recorder):
    class RecordedBackend(base):
        def __init__(self, *args, **kwargs):
            self._pose_recorder_lock = threading.Lock()
            super().__init__(*args, **kwargs)

        def _dyn_pose(self, message):
            # Serialize callbacks without holding the inherited lock while its
            # own implementation runs. Record only a newly observed body pose.
            with self._pose_recorder_lock:
                before = self.body_seen
                super()._dyn_pose(message)
                with self.lock:
                    body, after = self.body, self.body_seen
                if after > before:
                    recorder.capture(body, self.now_ns())
    return RecordedBackend


def audit_pose_stream(rows, receipt, *, nonce, source_sha256, max_gap_ns,
                      start_ns=None, end_ns=None):
    findings = []
    def require(value, name):
        if not value and name not in findings:
            findings.append(name)
    require(receipt.get("schema") == SCHEMA and receipt.get("nonce") == nonce
            and receipt.get("source_sha256") == source_sha256, "truth_identity")
    require(receipt.get("complete") is True, "truth_writer_incomplete")
    require(not receipt.get("errors") and all(receipt.get(k) == 0 for k in
            ("invalid", "dropped", "regressions")), "truth_capture_errors")
    require(len(rows) >= 3 and len(rows) == receipt.get("records") == receipt.get("enqueued"),
            "truth_record_count")
    require([r.get("sequence") for r in rows] == list(range(len(rows))), "truth_sequence")
    valid = all(isinstance(r.get("body"), list) and len(r["body"]) == 7
                and type(r.get("now_ns")) is int and r["now_ns"] >= 0
                and type(r["body"][0]) is int and r["now_ns"] == r["body"][0]
                and type(r.get("delivered_clock_ns")) is int and r["delivered_clock_ns"] >= 0
                and all(type(v) in (int, float) and math.isfinite(v) for v in r["body"][1:])
                for r in rows)
    require(valid, "truth_capture_binding")
    if valid and rows:
        stamps = [r["now_ns"] for r in rows]
        require(all(a < b for a, b in zip(stamps, stamps[1:])), "advancing_sim_clock")
        require(all(b-a <= max_gap_ns for a, b in zip(stamps, stamps[1:])), "truth_coverage")
        require((start_ns is None or stamps[0] <= start_ns+max_gap_ns)
                and (end_ns is None or stamps[-1] >= end_ns-max_gap_ns), "truth_episode_coverage")
    return findings
