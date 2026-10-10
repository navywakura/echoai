"""Log boundary checks: split writes, replacement, tampering, no actor input."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai import observe
from echo_arc.observe import Journal, ObservedAgent


class ObserveTests(unittest.TestCase):
    def test_relational_v3_diary_renders_its_actual_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal.jsonl"
            journal = Journal(path)
            journal.write(kind="observation", agent="echo45-relational-v3", origin="DEVELOPMENT",
                          context="multiple", action="search_first", policy_scores=[3, 7], budget=500000)
            journal.write(kind="result", agent="echo45-relational-v3", origin="DEVELOPMENT",
                          status="NO_PROGRAM", metrics={"work": 499800, "trials": 420,
                                                         "verified_programs": 0, "budget_exhausted": True})
            journal.close()
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertIn("search_first", " ".join(observe.render(rows[0])))
            self.assertIn("499800", " ".join(observe.render(rows[1])))
            rows[1]["metrics"]["work"] = 1
            with self.assertRaisesRegex(ValueError, "hash"):
                observe.render(rows[1])

    def test_attaching_to_old_diary_skips_history_but_preserves_split_last_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal.jsonl"
            path.write_bytes(b'{"old":1}\n' * 1000 + b'{"new":')
            tail = observe.Tail(path)
            with patch.object(observe.json, "loads", side_effect=AssertionError("archive must not be decoded")):
                tail.skip_history()
            self.assertEqual(tail.read(), [])
            with path.open("ab") as f:
                f.write(b'2}\n{"new":3}\n')
            self.assertEqual(tail.read(), [{"new": 2}, {"new": 3}])
            path.write_bytes(b'{"rotated":4}\n')
            self.assertEqual(tail.read(), [{"rotated": 4}])

    def test_history_decodes_only_requested_records_and_then_follows_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal.jsonl"
            path.write_bytes(b'{"old":1}\n' * 1000 + b'{"last":2}\n{"next":')
            tail = observe.Tail(path)
            with patch.object(observe.json, "loads", wraps=json.loads) as decode:
                self.assertEqual(tail.read(history=2), [{"old": 1}, {"last": 2}])
                self.assertEqual(decode.call_count, 2)
            with path.open("ab") as f:
                f.write(b'3}\n')
            self.assertEqual(tail.read(), [{"next": 3}])

    def test_tail_waits_for_complete_line_and_handles_rotation_and_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "thought.jsonl"
            path.write_bytes(b'{"turn":1')
            tail = observe.Tail(path)
            self.assertEqual(tail.read(), [])
            with path.open("ab") as f:
                f.write(b'}\n{"turn":2}\n')
            self.assertEqual(tail.read(), [{"turn": 1}, {"turn": 2}])
            self.assertEqual(tail.read(), [])
            path.write_bytes(b'{"turn":3}\n')
            self.assertEqual(tail.read(), [{"turn": 3}])
            replacement = Path(tmp) / "replacement"
            replacement.write_bytes(b'{"turn":4}\n')
            replacement.replace(path)
            self.assertEqual(tail.read(), [{"turn": 4}])

    def test_invalid_json_is_an_error_and_terminal_control_sequences_are_removed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "broken.jsonl"
            p.write_text('{"turn":1}\nno-json\n')
            with self.assertRaisesRegex(ValueError, "JSON ilegible"):
                observe.Tail(p).read()
        self.assertNotIn("\x1b", observe.clean("\x1b[2J fake\ntext"))

    def test_arc_records_are_chained_and_tampered_values_cannot_be_narrated(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "arc-decisions.jsonl"
            journal = Journal(p)
            journal.write(kind="end", status="complete")
            journal.write(kind="end", status="complete")
            journal.close()
            rows = [json.loads(line) for line in p.read_text().splitlines()]
            self.assertEqual(rows[0]["prev"], "0" * 64)
            self.assertEqual(rows[1]["prev"], rows[0]["hash"])
            self.assertEqual(rows[1]["index"], 1)
            self.assertIn("complete", observe.render(rows[1])[0])
            rows[1]["status"] = "green"
            with self.assertRaisesRegex(ValueError, "hash"):
                observe.render(rows[1])
            with self.assertRaises(FileExistsError):
                Journal(p)

    def test_reading_a_core_diary_preserves_bytes(self):
        from echoai.nexus0 import talk
        from echoai.nexus0.loop import Agent
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {"NAVI_THOUGHT_LOG": ""}):
            p = Path(tmp) / "thought.jsonl"
            control = Agent(cortex=False, ask=False)
            recorded = Agent(cortex=False, ask=False, thought_log=str(p))
            for turn in range(32):
                self.assertEqual(recorded.turn(turn), control.turn(turn))
            self.assertEqual(recorded.q.q, control.q.q)
            self.assertEqual(recorded.metrics.as_dict(), control.metrics.as_dict())
            before = hashlib.sha256(p.read_bytes()).hexdigest()
            rows = [json.loads(line) for line in p.read_text().splitlines()]
            self.assertEqual(len(rows), 32)
            for row in rows:
                talk.validate(row)
                self.assertTrue(observe.render(row))
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), before)

    def test_proxy_forwards_runner_assignments_and_never_passes_diary_to_actor(self):
        class Actor:
            def __init__(self):
                self.level_actions = []
            def choose(self, state):
                self.chosen_state = state
                return ("K", 1, None)
            def learn(self, *args):
                self.learned = args
        with tempfile.TemporaryDirectory() as tmp:
            actor = Actor()
            journal = Journal(Path(tmp) / "test.jsonl")
            proxy = ObservedAgent(actor, journal)
            proxy.level_start = "observed-start"
            proxy.level_actions.append(("K", 2, None))
            self.assertEqual(proxy.choose("observed-state"), ("K", 1, None))
            proxy.learn("a", ("K", 1, None), "b", False, False)
            journal.close()
            self.assertEqual(actor.level_start, "observed-start")
            self.assertEqual(actor.chosen_state, "observed-state")
            self.assertEqual(actor.learned[-2:], (False, False))
            self.assertFalse(any(k.startswith("_journal") for k in vars(actor)))


if __name__ == "__main__":
    unittest.main()
