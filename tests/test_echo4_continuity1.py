"""CONT-A persistence tests; these do not close full E4-CONTINUITY-1."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.echo4 import continuity as c
from echoai.echo4.continuity_bench import prepared, resumed, trajectory
from echoai.echo4.self_agent import SelfAgent
from echoai.echo4.self_recovery_agent import SelfRecoveryAgent
from echoai.echo4.world import Body


def signed_load(value):
    raw = c.canonical(value)
    return c.loads(raw, expected_sha256=hashlib.sha256(raw).hexdigest())


class TestContinuity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = prepared(60, 46, 2, 5)
        cls.raw = cls.base.dumps()
        cls.digest = hashlib.sha256(cls.raw).hexdigest()

    def restored(self):
        return c.loads(self.raw, expected_sha256=self.digest)

    def changed(self, tag, name, value):
        data = json.loads(self.raw)
        record = next(r for r in data["state"]["objects"] if r["type"] == tag)
        record["fields"][name] = value
        return data

    def test_canonical_roundtrip_covers_all_fields(self):
        self.assertEqual(self.restored().dumps(), self.raw)

    def test_single_cam_t_and_boundary_references(self):
        agent = self.restored().agent
        self.assertIs(agent.cam, agent.sensation.cam)
        self.assertIs(agent.cam, agent.boundary.cam)
        self.assertIs(agent.t, agent.sensation.world)
        self.assertIs(agent.boundary, agent.self_change.boundary)
        self.assertIsNot(agent.cam, self.base.agent.cam)

    def test_native_decisions_and_learning_match_every_step(self):
        reference = copy.deepcopy(self.base)
        self.assertEqual(trajectory(reference, 12), trajectory(self.restored(), 12))

    def test_fresh_process_resume(self):
        run = copy.deepcopy(self.base)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            digest = run.save(path)
            self.assertEqual(trajectory(run, 8), resumed(path, digest, 8))

    def test_reference_boundary_and_temporal_learning_preserved(self):
        agent = self.restored().agent
        self.assertTrue(agent.self_change.sealed)
        self.assertTrue(agent.self_change.references)
        self.assertTrue(agent.sensation.contexts)
        self.assertGreater(agent.sensation.memory.size, 0)
        self.assertEqual(agent.self_change.model_hash(), self.base.agent.self_change.model_hash())
        self.assertEqual(agent.sensation.history.snapshot(), self.base.agent.sensation.history.snapshot())

    def test_integer_q_remainders_are_not_discarded(self):
        run = copy.deepcopy(self.base)
        slot = run.agent.cam.get(run.agent.sensation.history.snapshot()[-16:])
        run.agent.q.update(slot, 0, 1, slot)
        self.assertNotEqual(run.agent.q.rem[slot][0], 0)
        raw = run.dumps()
        restored = c.loads(raw, expected_sha256=hashlib.sha256(raw).hexdigest())
        self.assertEqual(restored.agent.q.rem, run.agent.q.rem)
        self.assertEqual(trajectory(restored, 4), trajectory(run, 4))

    def test_all_supported_history_depths(self):
        for depth in (0, 2, 4):
            with self.subTest(depth=depth):
                run = c.ContinuityRun(SelfAgent(initial=Body(63, 71), depth=depth))
                for _ in range(3):
                    run.step()
                raw = run.dumps()
                restored = c.loads(raw, expected_sha256=hashlib.sha256(raw).hexdigest())
                self.assertEqual(trajectory(run, 3), trajectory(restored, 3))

    def test_initial_state(self):
        run = c.ContinuityRun(SelfAgent())
        restored = signed_load(run.snapshot())
        self.assertEqual(restored.next_turn, 0)
        self.assertEqual(trajectory(run, 3), trajectory(restored, 3))

    def test_terminal_snapshot_does_not_resurrect(self):
        run = c.ContinuityRun(SelfAgent(initial=Body(1, 126)))
        run.step()
        self.assertTrue(run.agent.episode_terminal)
        restored = signed_load(run.snapshot())
        before = restored.state_hash()
        with self.assertRaises(RuntimeError):
            restored.step()
        self.assertEqual(restored.state_hash(), before)
        self.assertEqual(restored.agent.env.resets, 0)

    def test_corruption_rejected_with_original_digest(self):
        for raw in (self.raw[:-1], self.raw + b" ", b"{}", b""):
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
                c.loads(raw, expected_sha256=self.digest)

    def test_custody_digest_is_required_and_external(self):
        for digest in ("0" * 64, "", None, 1):
            with self.assertRaises(ValueError):
                c.loads(self.raw, expected_sha256=digest)
        with self.assertRaises(TypeError):
            c.loads(self.raw)

    def test_unknown_version_and_profile(self):
        for key in ("schema", "profile"):
            data = json.loads(self.raw)
            data[key] = "unknown"
            with self.assertRaises(ValueError):
                signed_load(data)

    def test_source_change_requires_explicit_migration(self):
        data = json.loads(self.raw)
        data["sources"]["echo4/continuity.py"] = "0" * 64
        with self.assertRaises(ValueError):
            signed_load(data)

    def test_unknown_class_never_imported_or_executed(self):
        data = json.loads(self.raw)
        data["state"]["objects"][0]["type"] = "os.system"
        with self.assertRaises(ValueError):
            signed_load(data)

    def test_missing_and_extra_fields_rejected(self):
        for missing in (True, False):
            data = json.loads(self.raw)
            fields = data["state"]["objects"][0]["fields"]
            if missing:
                del fields["q"]
            else:
                fields["custom_hook"] = None
            with self.assertRaises(ValueError):
                signed_load(data)

    def test_invalid_reference(self):
        data = self.changed("agent", "cam", {"ref": 99999})
        with self.assertRaises(ValueError):
            signed_load(data)

    def test_duplicate_json_keys(self):
        raw = b'{"schema":1,"schema":2}'
        with self.assertRaises(ValueError):
            c.loads(raw, expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_float_nan_and_excessively_nested_json_rejected(self):
        for raw in (b'{"x":1.2}', b'{"x":NaN}', b"[" * 2000 + b"]" * 2000):
            with self.assertRaises(ValueError):
                c.loads(raw, expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_byte_budget(self):
        with patch.object(c, "MAX_BYTES", len(self.raw) - 1):
            with self.assertRaises(ValueError):
                self.restored()

    def test_body_clock_and_resource_corruption(self):
        for tag, name, value in (("agent", "H", 0), ("agent", "life_turns", 0),
                                 ("env", "resource_in", 999), ("env", "resets", 1),
                                 ("agent", "episode_terminal", True)):
            with self.subTest(name=name), self.assertRaises(ValueError):
                signed_load(self.changed(tag, name, value))

    def test_boolean_is_not_a_clock(self):
        data = json.loads(self.raw)
        data["next_turn"] = True
        with self.assertRaises(ValueError):
            signed_load(data)

    def test_cortex_and_external_logs_rejected(self):
        for key, val in (("cortex_enabled", True), ("thought_log", "/tmp/not-written"),
                         ("plan_depth", 2), ("oracle", "untrusted")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                signed_load(self.changed("agent", key, val))

    def test_pending_forecast_cannot_be_hidden(self):
        run = copy.deepcopy(self.base)
        run.agent.sensation.anticipate(0)
        before = copy.deepcopy(run.agent.sensation.pending)
        with self.assertRaises(ValueError):
            run.dumps()
        self.assertEqual(run.agent.sensation.pending, before)

    def test_extra_runtime_fields_and_aliased_arrays_fail_closed(self):
        run = copy.deepcopy(self.base)
        run.agent.surprise_hook = 1
        with self.assertRaises(ValueError):
            run.dumps()
        del run.agent.surprise_hook
        run.agent.q.q[1] = run.agent.q.q[0]
        with self.assertRaises(ValueError):
            run.dumps()

    def test_does_not_claim_active_recovery_support(self):
        with self.assertRaises(ValueError):
            c.ContinuityRun(SelfRecoveryAgent())

    def test_incomplete_turn_poisoned_even_after_pending_is_cleared(self):
        run = copy.deepcopy(self.base)
        with patch.object(SelfAgent, "turn", side_effect=RuntimeError("interrupted")):
            with self.assertRaises(RuntimeError):
                run.step()
        with self.assertRaises(ValueError):
            run.dumps()
        with self.assertRaises(RuntimeError):
            run.step()

    def test_save_never_overwrites_and_cleans_own_temporary_file(self):
        run = copy.deepcopy(self.base)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "checkpoint.json"
            digest = run.save(path)
            run.step()
            with self.assertRaises(FileExistsError):
                run.save(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
            self.assertEqual(len(list(Path(directory).iterdir())), 1)
            self.assertEqual(c.load(path, expected_sha256=digest).dumps(), self.raw)

    def test_snapshot_readonly_and_original_isolated(self):
        before = self.base.state_hash()
        run = self.restored()
        run.step()
        self.assertEqual(self.base.state_hash(), before)
        self.assertNotEqual(run.state_hash(), before)

    def test_gate_inhibit_survives_resume(self):
        from echoai.core.qn import SLOT_FLAG_INHIBIT
        run = copy.deepcopy(self.base)
        slot = run.agent.cam.get(run.agent.sensation.history.snapshot()[-16:])
        run.agent.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
        restored = signed_load(run.snapshot())
        self.assertEqual(run.step(), restored.step())
        self.assertEqual(restored.agent.last_gate_decision, 2)
        self.assertEqual(restored.state_hash(), run.state_hash())


if __name__ == "__main__":
    unittest.main()
