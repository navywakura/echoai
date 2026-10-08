"""CONT-C lineage, quarantine and custody tests; no full-phase green."""
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from echoai.echo4 import continuity_active_bench as previous
from echoai.echo4 import continuity_lineage as c
from echoai.echo4 import continuity_lineage_bench as bench
from echoai.echo4.world import Body


def restore(raw):
    return c.loads(raw, expected_sha256=hashlib.sha256(raw).hexdigest())


def rehash(value):
    return restore(c.b.base.canonical(value))


class TestLineage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = bench.wrap(previous.prepared("recovery_learned"))
        cls.raw = cls.parent.dumps()
        cls.child = cls.parent.allocate_body(Body(60, 46), body_id="body-2", token="new-body")
        cls.child_raw = cls.child.dumps()
        cls.pairs, cls.nominal = bench.calibration(Body(60, 46))
        cls.commissioned = restore(cls.child_raw)
        cls.commissioned.commission(cls.pairs, cls.nominal, scope=cls.commissioned.scope)
        cls.commissioned_raw = cls.commissioned.dumps()

    def test_exact_resume_identity_clocks_and_permissions(self):
        run = restore(self.raw)
        self.assertEqual(run.dumps(), self.raw)
        self.assertEqual(run.identity, self.parent.identity)
        self.assertEqual(run.scope, self.parent.scope)
        self.assertIs(run.agent.self_model.agent, run.agent)
        self.assertEqual(bench.trajectory(run, 2), bench.trajectory(restore(self.raw), 2))

    def test_shared_references_inside_not_between_agents(self):
        run = restore(self.raw)
        self.assertIs(run.agent.cam, run.agent.sensation.cam)
        self.assertIs(run.agent.cam, run.agent.boundary.cam)
        self.assertIs(run.agent.t, run.agent.sensation.world)
        self.assertIs(run.agent.boundary, run.agent.self_change.boundary)
        self.assertIsNot(run.agent.cam, self.parent.agent.cam)

    def test_forks_identical_native_state_distinct_scopes(self):
        left, right = self.parent.fork("left", "right")
        self.assertEqual(left.active.dumps(), right.active.dumps())
        self.assertEqual(left.agent.env.body, self.parent.agent.env.body)
        self.assertNotEqual(left.scope, right.scope)
        self.assertNotEqual(left.scope, self.parent.scope)
        self.assertEqual(left.ancestry[-1]["parent_sha256"], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(self.parent.dumps(), self.raw)

    def test_mutable_fork_isolation(self):
        left, right = self.parent.fork("left", "right")
        right_raw = right.dumps()
        left.step()
        self.assertEqual(right.dumps(), right_raw)
        self.assertEqual(self.parent.dumps(), self.raw)
        left.agent.q.q[0][0] += 1
        self.assertNotEqual(left.agent.q.q[0][0], right.agent.q.q[0][0])

    def test_fork_duplicate_or_invalid_label_is_atomic(self):
        for labels in (("same", "same"), ("ok", "../bad"), ("ok", "")):
            with self.assertRaises(ValueError):
                self.parent.fork(*labels)
        self.assertEqual(self.parent.dumps(), self.raw)

    def test_pending_probe_and_inbox_cannot_branch_or_rebind(self):
        for case in ("pending", "inbox"):
            run = bench.wrap(previous.prepared(case))
            raw = run.dumps()
            for operation in (lambda run=run: run.fork("a", "b"),
                              lambda run=run: run.allocate_body(Body(), body_id="next", token="x")):
                with self.assertRaises(ValueError):
                    operation()
            self.assertEqual(run.dumps(), raw)

    def test_cancelled_pending_can_fork_without_reauthorizing(self):
        run = bench.wrap(previous.prepared("pending"))
        run.cancel()
        child = run.fork("a", "b")[0]
        with self.assertRaises(ValueError):
            child.start_recovery(scope=child.scope, restored=True, same_context=True)

    def test_body_retains_memory_and_global_not_life_clock(self):
        child = restore(self.child_raw)
        self.assertEqual(c.memory_hash(child.agent), c.memory_hash(self.parent.agent))
        self.assertEqual(child.agent.metrics.turns, self.parent.agent.metrics.turns)
        self.assertEqual(child.agent.life_turns, 0)
        self.assertEqual(child.identity["individual"], self.parent.identity["individual"])
        self.assertEqual(child.identity["branch"], self.parent.identity["branch"])
        self.assertEqual(child.identity["epoch"], 1)
        self.assertEqual(child.ancestry[-1]["allocation"]["external_h"], 60)
        self.assertEqual(child.agent.env.resource_in, 0)

    def test_descendant_inherits_memory_not_personal_turns(self):
        child = self.parent.allocate_body(Body(60, 46), body_id="baby-body", token="born", individual="echo-2")
        self.assertEqual(c.memory_hash(child.agent), c.memory_hash(self.parent.agent))
        self.assertEqual(child.agent.metrics.turns, 0)
        self.assertEqual(child.agent.life_turns, 0)
        self.assertEqual(child.identity["generation"], 1)
        self.assertEqual(child.identity["epoch"], 0)
        self.assertNotEqual(child.identity["branch"], self.parent.identity["branch"])

    def test_all_body_bound_evidence_revoked(self):
        child = restore(self.child_raw)
        a = child.agent
        self.assertIsNone(child.active)
        self.assertIsNone(a.recovery)
        self.assertIsNone(a.self_model)
        self.assertIsNone(a.prev_slot)
        self.assertFalse(a.self_change.sealed)
        self.assertEqual(a.self_change.references, {})
        self.assertEqual(a.boundary.rows, {})
        self.assertEqual(a.sensation.history.steps, 0)
        self.assertTrue(a.sensation.frozen)
        self.assertEqual(self.parent.dumps(), self.raw)

    def test_quarantine_cannot_act_or_diagnose(self):
        child = restore(self.child_raw)
        for operation in (lambda: child.step(), lambda: child.choose_probe(18),
                          lambda: child.start_recovery(scope=child.scope, restored=True, same_context=True)):
            with self.assertRaises(RuntimeError):
                operation()
        self.assertEqual(child.dumps(), self.child_raw)

    def test_calibration_atomic_failure_wrong_scope_missing_bad_receipt(self):
        child = restore(self.child_raw)
        bad_pairs = self.pairs[:-1] + (replace(self.pairs[-1], restored=False),)
        cases = ((self.pairs, self.nominal, self.parent.scope),
                 (self.pairs, None, child.scope), (self.pairs[:8], self.nominal, child.scope),
                 (bad_pairs, self.nominal, child.scope),
                 (self.pairs, replace(self.nominal, restored=False), child.scope))
        for pairs, nominal, scope in cases:
            with self.subTest(scope=scope, count=len(pairs)):
                with self.assertRaises(ValueError):
                    child.commission(pairs, nominal, scope=scope)
                self.assertEqual(child.dumps(), self.child_raw)

    def test_recommission_needs_fresh_confirmation(self):
        child = restore(self.commissioned_raw)
        self.assertFalse(child.active.session.diagnosis()["confirmed"])
        with self.assertRaises(ValueError):
            bench.authorize(child)
        bench.finish_diagnosis(child)
        self.assertTrue(child.active.session.diagnosis()["confirmed"])
        self.assertEqual(child.active.session.diagnosis()["label"], "nominal")
        bench.authorize(child)
        child.step()
        self.assertEqual(child.agent.metrics.turns, 4)
        self.assertEqual(child.agent.life_turns, 1)
        self.assertTrue(child.agent.env.balanced)
        self.assertEqual(restore(child.dumps()).dumps(), child.dumps())

    def test_calibration_does_not_teach_inherited_t_q_pattern(self):
        before, after = self.child.agent, self.commissioned.agent
        self.assertEqual(vars(before.q), vars(after.q))
        self.assertEqual(vars(before.t), vars(after.t))
        self.assertEqual(vars(before.sensation.memory), vars(after.sensation.memory))
        self.assertEqual(before.sensation.contexts, after.sensation.contexts)

    def test_wrong_branch_receipt_even_when_token_and_wsp_match(self):
        left, right = self.commissioned.fork("left", "right")
        self.assertEqual(left.choose_probe(18), right.choose_probe(18))
        receipt = previous.physical_receipt(left.active)
        before = right.dumps()
        with self.assertRaises(ValueError):
            right.queue_receipt(receipt, scope=left.scope)
        self.assertEqual(right.dumps(), before)
        right.queue_receipt(receipt, scope=right.scope)  # separate trusted execution attestation
        right.consume_receipt()

    def test_identical_observation_does_not_inherit_permission(self):
        child = self.parent.allocate_body(self.parent.agent.env.body, body_id="alias-body", token="alias")
        self.assertEqual(child.agent.observation(child.agent.env.cell()),
                         self.parent.agent.observation(self.parent.agent.env.cell()))
        self.assertIsNone(child.agent.self_model)
        self.assertIsNone(child.active)
        with self.assertRaises(ValueError):
            child.commission(self.pairs, self.nominal, scope=self.parent.scope)

    def test_reuse_rebinding_revokes_trial_and_freeze(self):
        parent = bench.wrap(previous.prepared("reuse_done"))
        child = parent.allocate_body(Body(60, 46), body_id="next", token="replace")
        self.assertEqual(child.agent.trial_token, 0)
        self.assertEqual(child.agent.trial_phase, "")
        self.assertFalse(child.agent.trial_active)
        self.assertEqual(child.agent.metrics.turns, 25)
        child.commission(self.pairs, self.nominal, scope=child.scope)
        bench.finish_diagnosis(child)
        bench.authorize(child)
        child.step()
        self.assertEqual(child.agent.metrics.turns, 26)
        self.assertEqual(child.agent.life_turns, 1)
        with self.assertRaises(RuntimeError):
            child.step()

    def test_terminal_cannot_rebody_but_can_have_separate_descendant(self):
        terminal = bench.wrap(previous.prepared("terminal"))
        raw = terminal.dumps()
        with self.assertRaises(ValueError):
            terminal.allocate_body(Body(), body_id="next", token="revive")
        for run in (restore(raw), terminal.fork("left", "right")[0]):
            self.assertTrue(run.agent.episode_terminal)
            with self.assertRaises(RuntimeError):
                run.step()
        child = terminal.allocate_body(Body(), body_id="next", token="descend", individual="echo-2")
        self.assertFalse(child.agent.episode_terminal)
        self.assertEqual(child.agent.metrics.turns, 0)
        self.assertIsNone(child.active)
        self.assertEqual(terminal.dumps(), raw)

    def test_new_body_labels_and_live_allocation_required(self):
        for kwargs in ({"body_id": "body-1"}, {"body_id": "new", "individual": "echo-1"},
                       {"body_id": "new", "hc": 1}, {"body_id": "new", "heat": 128}):
            with self.assertRaises(ValueError):
                self.parent.allocate_body(Body(), token="bad", **kwargs)
        with self.assertRaises(ValueError):
            self.parent.allocate_body(Body(0, 64), body_id="dead", token="bad")
        self.assertEqual(self.parent.dumps(), self.raw)

    def test_scope_and_chain_survive_second_body_and_fork(self):
        run = bench.prepared("second_body")
        self.assertEqual(run.identity["epoch"], 2)
        fork = run.fork("a", "b")[0]
        self.assertEqual(restore(fork.dumps()).dumps(), fork.dumps())
        with self.assertRaises(ValueError):
            fork.queue_receipt(self.nominal, scope=self.commissioned.scope)

    def test_metadata_mutants_and_receipt_rewrites_rejected(self):
        for field, value in (("parent_sha256", "0" * 64), ("parent_turns", 0), ("memory_sha256", "0" * 64)):
            data = json.loads(self.child_raw)
            data["ancestry"][-1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                rehash(data)
        for field, value in (("individual", "forged"), ("branch", "0" * 64), ("epoch", 0), ("generation", 2)):
            data = json.loads(self.child_raw)
            edge = data["ancestry"][-1]
            edge["identity"][field] = value
            c._seal(edge)  # also challenge semantic checks, not only digest
            with self.subTest(field=field), self.assertRaises(ValueError):
                rehash(data)

    def test_quarantine_mutants_memory_permissions_and_context(self):
        for tag, field, value in (("recovery_agent", "prev_slot", 0), ("sensation", "frozen", False),
                                  ("self", "sealed", True), ("recovery_agent", "life_turns", 1)):
            data = json.loads(self.child_raw)
            record = next(r for r in data["quarantine"]["objects"] if r["type"] == tag)
            record["fields"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                rehash(data)
        run = restore(self.child_raw)
        run.agent.q.q[0][0] += 1
        with self.assertRaises(ValueError):
            run.dumps()

    def test_false_commission_and_forged_calibration_rejected(self):
        for value in (None, {}, {"scope": self.parent.scope, "pairs": self.commissioned.commissioning["pairs"]}):
            data = json.loads(self.commissioned_raw)
            data["commissioning"] = value
            with self.assertRaises(ValueError):
                rehash(data)
        data = json.loads(self.commissioned_raw)
        pair = next(r for r in data["commissioning"]["pairs"]["objects"] if r["type"] == "Pair")
        pair["fields"]["restored"] = False
        with self.assertRaises(ValueError):
            rehash(data)

    def test_source_schema_digest_and_unknown_fields_rejected(self):
        with self.assertRaises(ValueError):
            c.loads(self.raw, expected_sha256="0" * 64)
        for key, value in (("schema", "unknown"), ("sources", {}), ("extra", True)):
            data = json.loads(self.raw)
            data[key] = value
            with self.assertRaises(ValueError):
                rehash(data)
        with self.assertRaises(ValueError):
            restore(self.parent.active.dumps())
        with self.assertRaises(ValueError):
            c.b.loads(self.raw, expected_sha256=hashlib.sha256(self.raw).hexdigest())

    def test_invalid_json_graph_and_chain_limits(self):
        for raw in (b"{}", b"[]", b"{", b'{"x":1,"x":2}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                restore(raw)
        data = json.loads(self.raw)
        data["ancestry"] *= 33
        with self.assertRaises(ValueError):
            rehash(data)
        with patch.object(c, "MAX_LINKS", 1), self.assertRaises(ValueError):
            self.parent.fork("a", "b")

    def test_failed_native_operation_cannot_branch(self):
        run = restore(self.raw)
        with patch.object(run.agent, "turn", side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            run.step()
        with self.assertRaises(ValueError):
            run.dumps()
        with self.assertRaises(ValueError):
            run.fork("a", "b")

    def test_atomic_save_no_overwrite_and_fresh_process(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            sha256 = self.commissioned.save(path)
            with self.assertRaises(FileExistsError):
                self.commissioned.save(path)
            expected = bench.trajectory(restore(self.commissioned_raw), 2)
            self.assertEqual(bench.resumed(path, sha256, 2), expected)
            self.assertEqual(path.read_bytes(), self.commissioned_raw)

    def test_two_measured_goals_produce_divergent_branches(self):
        left, right = bench.prepared("fork_goal0"), bench.prepared("fork_goal1")
        self.assertNotEqual(left.step(), right.step())
        self.assertNotEqual(left.agent.env.body, right.agent.env.body)
        self.assertTrue(left.agent.env.balanced and right.agent.env.balanced)

    def test_every_development_case_roundtrips(self):
        for case in bench.CASES:
            with self.subTest(case=case):
                run = bench.prepared(case)
                raw = run.dumps()
                self.assertEqual(restore(raw).dumps(), raw)

    def test_verifier_rejects_invalid_report(self):
        with patch.object(Path, "read_bytes", return_value=b"{}"):
            result = bench.verify("unused")
        self.assertFalse(result["valid"])
        self.assertFalse(result["continuity1_green"])


if __name__ == "__main__":
    unittest.main()
