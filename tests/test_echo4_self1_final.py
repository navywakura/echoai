"""Final SELF-1 confirmation, model limits, native controls and evidence custody."""
import ast
import copy
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.echo4 import self_final as runtime
from echoai.echo4.boundary_world import packet
from echoai.echo4.self_attribution import ProbePlan
from echoai.echo4.self_final import SelfSession, SCOPE
from echoai.echo4.self_final_world import novel_probe
from echoai.echo4.self_final_audit import (
    GRIDS, NEGATIVES, campaign, diagnose, model_hash, native_veto, record, verify,
)
from echoai.echo4.self_probe_world import run_probe
from echoai.echo4.self_recovery import RecoveryBelief
from echoai.echo4 import self_recovery_audit as lives
from echoai.echo4 import self_reuse_audit as reuse
from echoai.echo4.world import Body


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = Body(60, 46)  # A only; no B/C outcomes inspected in tests.
        cls.base, cls.nominal, _ = reuse.school(cls.body)

    def session(self):
        return SelfSession(self.base.new_self_diagnosis(packet(self.body), self.nominal))


class TestSession(Fixture):
    def test_new_model_is_not_an_authorized_cause(self):
        session = self.session()
        self.assertEqual(session.diagnosis()["label"], "unknown")
        self.assertEqual(session.diagnosis()["scope"], SCOPE)
        with self.assertRaises(ValueError):
            session.authorized_model()

    def test_consensus_needs_confirmation(self):
        session = self.session()
        for token in range(18, 24):
            plan = session.choose(token)
            session.consume(run_probe(self.body, plan)[0])
            if session.model.diagnosis()["label"] != "unknown":
                break
        self.assertEqual(session.model.diagnosis()["label"], "nominal")
        self.assertEqual(session.diagnosis()["label"], "unknown")
        with self.assertRaises(ValueError):
            session.authorized_model()
        self.assertIsNotNone(session.choose(token + 1))
        self.assertEqual(session.challenge_probes, 1)

    def test_full_confirmation_reuses_the_original_diagnostic_model(self):
        session, result = diagnose(self.base, self.nominal, self.body)
        self.assertEqual(result["diagnosis"]["label"], "nominal")
        self.assertIs(session.authorized_model(), session.model)
        self.assertEqual(len(session.model.used), 6)
        self.assertLessEqual(result["physical_steps"], 48)
        self.assertGreater(session.challenge_probes, 0)
        self.assertTrue(result["truth_retained"])

    def test_contradiction_after_consensus_revokes_authority(self):
        session, result = diagnose(self.base, self.nominal, self.body, fault="late_change")
        self.assertEqual(result["diagnosis"]["label"], "unknown")
        self.assertGreater(session.challenge_probes, 0)
        with self.assertRaises(ValueError):
            RecoveryBelief(session.model, restored=True, same_context=True)

    def test_confirmation_precedes_physics_and_preserves_reference(self):
        before = model_hash(self.base)
        session = self.session()
        seen = []
        for token in range(18, 25):
            plan = session.choose(token)
            if plan is None:
                break
            pending = copy.deepcopy(session.model.pending)

            def inspect(tick, action):
                self.assertEqual(session.model.pending, pending)
                seen.append(tick)

            receipt, _ = run_probe(self.body, plan, before_step=inspect)
            session.consume(receipt)
        self.assertTrue(seen)
        self.assertEqual(before, model_hash(self.base))

    def test_cancel_pending_has_no_authority(self):
        session = self.session()
        session.choose(18)
        session.cancel()
        self.assertEqual(session.diagnosis()["label"], "unknown")
        self.assertIsNone(session.model.pending)
        with self.assertRaises(ValueError):
            session.authorized_model()

    def test_invalid_ids_do_not_mutate(self):
        session = self.session()
        before = copy.deepcopy(vars(session.model))
        for token in (0, 17, -1, True, 18.0, 1 << 31):
            with self.assertRaises(ValueError):
                session.choose(token)
        self.assertEqual(vars(session.model), before)

    def test_pending_duplicate_and_finished_consume_rejected(self):
        session = self.session()
        plan = session.choose(18)
        with self.assertRaises(RuntimeError):
            session.choose(19)
        receipt = run_probe(self.body, plan)[0]
        session.consume(receipt)
        with self.assertRaises(RuntimeError):
            session.consume(receipt)
        session.cancel()
        with self.assertRaises(RuntimeError):
            session.consume(receipt)

    def test_no_safe_probe_does_not_invent_action(self):
        session = self.session()
        session.model.h_candidates = ((2, False),)
        self.assertIsNone(session.choose(18))
        self.assertTrue(session.finished)
        self.assertEqual(session.diagnosis()["label"], "unknown")
        self.assertEqual(session.model.executed_ticks, 0)

    def test_no_alias_of_existing_or_pending_session(self):
        with self.assertRaises(ValueError):
            SelfSession(None)
        session = self.session()
        session.choose(18)
        with self.assertRaises(ValueError):
            SelfSession(session.model)

    def test_no_private_fields_executor_or_float(self):
        tree = ast.parse(Path(runtime.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, ("echoai.echo4.boundary", "echoai.echo4.self_attribution"))
            if isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, ("env", "body", "H", "temperature", "_hc", "_tc", "_heat"))
            self.assertFalse(isinstance(node, ast.Div))
            self.assertFalse(isinstance(node, ast.Constant) and type(node.value) is float)


class TestFalsification(Fixture):
    def test_all_negative_mechanisms_and_receipts_abstain(self):
        before = model_hash(self.base)
        for fault in NEGATIVES:
            with self.subTest(fault=fault):
                _, result = diagnose(self.base, self.nominal, self.body, fault=fault)
                self.assertEqual(result["diagnosis"]["label"], "unknown")
                self.assertTrue(result["authorization_denied"])
                self.assertTrue(result["bounded"])
                self.assertTrue(result["balanced"])
        self.assertEqual(before, model_hash(self.base))

    def test_partial_reference_can_stay_ambiguous(self):
        body = Body(37, 65)
        base, _ = lives.school(body)
        _, result = diagnose(base, None, body, heat=4)
        self.assertEqual(result["diagnosis"]["label"], "unknown")
        self.assertTrue(result["authorization_denied"])

    def test_gate_is_physical_and_not_a_fabricated_packet(self):
        _, result = diagnose(self.base, self.nominal, self.body, fault="veto")
        self.assertEqual(result["physical_steps"], 2)
        receipt = result["traces"][0]["physical_receipt"]
        self.assertEqual(receipt["gates"][-1], 2)
        self.assertEqual(receipt["applied"][-1], 2)
        base, _ = lives.school(self.body)
        session, _ = diagnose(self.base, self.nominal, self.body)
        self.assertTrue(native_veto(base, session.authorized_model(), self.body)["passed"])

    def test_externally_cancelled_action_is_not_identifiable(self):
        _, bodily = diagnose(self.base, self.nominal, self.body, False, False)
        _, external = diagnose(self.base, self.nominal, self.body, fault="external_mimic")
        self.assertEqual([t["physical_receipt"] for t in bodily["traces"]],
                         [t["physical_receipt"] for t in external["traces"]])
        self.assertEqual(bodily["diagnosis"], external["diagnosis"])
        self.assertEqual(external["diagnosis"]["scope"], SCOPE)
        # Identical conditional labels do NOT identify the private true cause.

    def test_novel_dynamics_resource_balance_and_terminality(self):
        plan = ProbePlan(1, 0, (0, 1, 2), 0, 0)
        for mechanism in ("persistent_heat", "delayed_heat", "reversed_cooling", "external_mimic"):
            receipt, private = novel_probe(self.body, plan, mechanism)
            self.assertEqual(len(receipt.applied), 3)
            self.assertTrue(all(row["balanced"] for row in private["resource_ledger"]))
        receipt, _ = novel_probe(Body(1, 64), replace(plan, actions=(2, 2)), "persistent_heat")
        self.assertEqual(len(receipt.applied), 1)
        self.assertTrue(receipt.terminal[-1])

    def test_new_BC_states_disjoint_without_executing_them(self):
        sets = {name: {(h, t) for h in grid[0] for t in grid[1]} for name, grid in GRIDS.items() if name != "smoke"}
        self.assertFalse(sets["A"] & sets["B"] or sets["A"] & sets["C"] or sets["B"] & sets["C"])
        self.assertTrue(all(h > 40 for pairs in sets.values() for h, _ in pairs))


class TestArtifacts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / "evidence"
        cls.report = record(cls.path, quick=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_smoke_cannot_close(self):
        self.assertFalse(self.report["self1_green"])
        self.assertFalse(self.report["closure_eligible"])
        self.assertIsNone(self.report["lock_sha256"])
        self.assertNotIn("B", self.report["stages"])
        result = self.report["stages"]["smoke"]
        self.assertEqual(result["conditions"], 12)
        self.assertTrue(result["checks"]["abstention"])
        self.assertTrue(result["checks"]["invariants"])

    def test_full_smoke_replay_still_not_green(self):
        result = verify(self.path)
        self.assertTrue(result["valid"])
        self.assertFalse(result["self1_green"])

    def test_refuses_overwrite(self):
        with self.assertRaises(FileExistsError):
            record(self.path, quick=True)

    def test_forged_green_or_eligibility_is_rejected(self):
        path = self.path / "report.json"
        raw = path.read_bytes()
        try:
            altered = json.loads(raw)
            altered["self1_green"] = True
            altered["closure_eligible"] = True
            path.write_text(json.dumps(altered))
            self.assertFalse(verify(self.path)["valid"])
        finally:
            path.write_bytes(raw)

    def test_tampered_forecast_and_trailing_trace_rejected(self):
        path = self.path / "traces.jsonl"
        raw = path.read_bytes()
        try:
            path.write_bytes(raw.replace(b'"restored":true', b'"restored":false', 1))
            self.assertFalse(verify(self.path)["valid"])
            path.write_bytes(raw + b"{}\n")
            self.assertFalse(verify(self.path)["valid"])
        finally:
            path.write_bytes(raw)

    def test_parent_or_source_mutation_rejected(self):
        with patch("echoai.echo4.self_final_audit.parents", return_value={}):
            self.assertFalse(verify(self.path)["valid"])
        with patch("echoai.echo4.self_final_audit.sources", return_value={}):
            self.assertFalse(verify(self.path)["valid"])

    def test_malformed_or_missing_report(self):
        self.assertFalse(verify(Path(self.temp.name) / "missing")["valid"])
        path = self.path / "report.json"
        raw = path.read_bytes()
        try:
            for malformed in (b"[]", b"null", b"{broken"):
                path.write_bytes(malformed)
                self.assertFalse(verify(self.path)["valid"])
        finally:
            path.write_bytes(raw)


class TestExamOrder(unittest.TestCase):
    """Mock orchestration only: never inspect actual B/C outcomes before lock."""

    def test_red_development_does_not_open_BC(self):
        with patch("echoai.echo4.self_final_audit.stage", return_value={"passed": False}) as stage:
            result = campaign()
        self.assertEqual([call.args[0] for call in stage.call_args_list], ["A"])
        self.assertFalse(result["closure_eligible"])
        self.assertIsNone(result["lock_sha256"])

    def test_lock_before_B_and_C_still_runs_when_B_is_red(self):
        events = []

        def synthetic_stage(name, emit):
            events.append(name)
            return {"passed": name != "B"}

        with patch("echoai.echo4.self_final_audit.stage", side_effect=synthetic_stage):
            result = campaign(emit=lambda value: events.append(value["phase"]))
        self.assertEqual(events, ["A", "freeze_before_B", "B", "C"])
        self.assertFalse(result["closure_eligible"])
        self.assertFalse(result["self1_green"])

    def test_source_mutation_after_lock_stops_exam(self):
        with patch("echoai.echo4.self_final_audit.stage", return_value={"passed": True}), \
             patch("echoai.echo4.self_final_audit.sources", side_effect=({"source": "a"}, {"source": "b"})):
            with self.assertRaisesRegex(ValueError, "sources changed after lock"):
                campaign()


if __name__ == "__main__":
    unittest.main()
