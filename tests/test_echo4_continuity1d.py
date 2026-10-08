"""CONT-D: A-only preparation, source-lock protocol, independent audit negatives.

Mocked protocol fixtures are not physical experiments. Reserved B/C recipes
execute only in the source-locked final campaign, not in these unit tests.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from echoai.echo4 import continuity_final_audit as audit
from echoai.echo4 import continuity_final_cases as cases


class TestDevelopmentRecipes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = {name: cases.prepared("A", name)[0] for name in cases.CASES}
        cls.control = cases.controls("A")
        cls.mutants = cases.mutant_suite("A")

    def test_all_23_A_recipes_roundtrip_exactly(self):
        self.assertEqual(len(self.runs), 23)
        for name, run in self.runs.items():
            with self.subTest(case=name):
                self.assertEqual(cases.clone(run).dumps(), run.dumps())

    def test_ambiguous_stays_unconfirmed_and_cannot_authorize(self):
        run = cases.clone(self.runs["ambiguous"])
        self.assertFalse(run.session.diagnosis()["confirmed"])
        raw = run.dumps()
        with self.assertRaises(ValueError):
            run.start_recovery(restored=True, same_context=True)
        self.assertEqual(run.dumps(), raw)
        self.assertEqual(cases.trajectory(run, 5)["events"], [])

    def test_native_terminal_witnesses_do_not_revive(self):
        for name in ("nominal_terminal", "terminal", "terminal_fork"):
            run = cases.clone(self.runs[name])
            self.assertTrue(run.agent.episode_terminal)
            self.assertEqual(cases.trajectory(run, 5)["events"], [])

    def test_stops_and_cancel_preserve_abstention(self):
        for name in ("cancelled", "veto", "stopped"):
            run = cases.clone(self.runs[name])
            self.assertEqual(cases.trajectory(run, 5)["events"], [])

    def test_forks_same_physics_different_scopes(self):
        left, right = (cases.clone(self.runs[n]) for n in ("fork_left", "fork_right"))
        self.assertNotEqual(left.scope, right.scope)
        self.assertEqual(cases.physical(cases.trajectory(left, 3)),
                         cases.physical(cases.trajectory(right, 3)))

    def test_quarantine_is_not_inherited_permission(self):
        for name in ("body_quarantine", "descendant_quarantine"):
            run = cases.clone(self.runs[name])
            self.assertIsNone(run.agent.self_model)
            result = cases.trajectory(run, 3)
            self.assertTrue(result["quarantined"])
            self.assertEqual([r["event"] for r in result["events"]], ["quarantine_block"])

    def test_rebound_body_needs_its_own_confirmed_model(self):
        for name in ("body_active", "descendant_active", "reuse_body_active"):
            run = self.runs[name]
            self.assertTrue(run.active.session.diagnosis()["confirmed"])
            self.assertEqual(run.agent.life_turns, 0)
            if name == "reuse_body_active":
                self.assertTrue(run.agent.trial_active)
                self.assertTrue(run.agent.sensation.frozen)
                self.assertFalse(run.agent.self_model.observe_step(0, 0, 0))
            else:
                self.assertIs(run.agent.self_model.agent, run.agent)

    def test_history_loss_changes_learning_without_claiming_action_gain(self):
        control = self.control
        self.assertTrue(control["checks"]["history_state_loss_detected"])
        self.assertTrue(control["checks"]["history_learning_loss_detected"])
        self.assertEqual(control["history"]["action_differences"], 0)
        self.assertEqual(control["history"]["prediction_differences"], 0)
        self.assertNotEqual(*control["history"]["rows"][-1]["pattern_observations"])

    def test_remainder_control_is_explicit_synthetic_arithmetic(self):
        remainder = self.control["remainder"]
        self.assertTrue(remainder["not_world_reward"])
        self.assertEqual(remainder["native_nonzero_entries"], 0)
        self.assertEqual(remainder["synthetic_reward"], 1)
        self.assertTrue(self.control["checks"]["remainder_update_loss_detected"])
        for row in remainder["rows"]:
            self.assertEqual(row["kept"], row["direct"])
            self.assertEqual(row["kept"], row["resumed"])

    def test_ten_mutants_rejected_without_changing_originals(self):
        self.assertEqual(set(self.mutants["rejected"]), set(cases.MUTANTS))
        self.assertEqual(len(self.mutants["rejected"]), 10)
        self.assertTrue(self.mutants["passed"])
        self.assertTrue(self.mutants["origins_unchanged"])

    def test_real_fresh_process_continuation_and_checkpoint_reconstruction(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "checkpoint.json"
            row = audit.evaluate("A", "selective", path)
            self.assertTrue(row["equal"])
            self.assertTrue(row["roundtrip_exact"])
            self.assertEqual(row, audit.evaluate("A", "selective", path, checking=True))
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "checkpoint differs"):
                audit.evaluate("A", "selective", path, checking=True)

    def test_recipes_reject_unknown_inputs(self):
        for stage, name in (("X", "nominal0"), ("A", "unknown")):
            with self.assertRaises(ValueError):
                cases.prepared(stage, name)

    def test_reserved_stage_bodies_and_horizons_are_distinct(self):
        self.assertEqual(list(cases.STAGES), ["A", "B", "C"])
        bodies = [body for values in cases.STAGES.values() for body in values[0]]
        self.assertEqual(len(set(bodies)), 6)
        self.assertEqual([v[2] for v in cases.STAGES.values()], [5, 6, 7])


class TestLockProtocol(unittest.TestCase):
    def protocol(self, failures=(), *, smoke=False, sources=None):
        seen = []

        def stage(name, *args, **kwargs):
            seen.append("run_" + name)
            return {"passed": name not in failures}

        def emit(row):
            seen.append(row["event"])

        with patch.object(audit, "stage", side_effect=stage), \
                patch.object(audit, "sources", side_effect=sources or (lambda: {"source": "hash"})), \
                patch.object(audit, "parents", return_value={"parent": "hash"}):
            report = audit.campaign(Path("unused"), emit, lambda _: None, smoke=smoke)
        return report, seen

    def test_lock_precedes_B_and_campaign_never_grants_green(self):
        report, seen = self.protocol()
        self.assertEqual(seen, ["run_A", "freeze_before_B", "run_B", "run_C"])
        self.assertTrue(report["closure_eligible"])
        self.assertFalse(report["continuity1_green"])

    def test_red_A_does_not_open_B(self):
        report, seen = self.protocol(("A",))
        self.assertEqual(seen, ["run_A"])
        self.assertFalse(report["closure_eligible"])

    def test_red_B_does_not_open_C(self):
        report, seen = self.protocol(("B",))
        self.assertEqual(seen, ["run_A", "freeze_before_B", "run_B"])
        self.assertFalse(report["closure_eligible"])

    def test_red_C_is_not_closure(self):
        report, _ = self.protocol(("C",))
        self.assertFalse(report["closure_eligible"])

    def test_smoke_never_opens_B_or_becomes_eligible(self):
        report, seen = self.protocol(smoke=True)
        self.assertEqual(seen, ["run_A"])
        self.assertFalse(report["closure_eligible"])

    def test_source_change_before_lock_rejects_campaign(self):
        with self.assertRaisesRegex(ValueError, "changed before lock"):
            self.protocol(sources=[{"source": "old"}, {"source": "new"}])

    def test_source_change_after_lock_rejects_campaign(self):
        with self.assertRaisesRegex(ValueError, "lock changed"):
            self.protocol(sources=[{"source": "old"}, {"source": "old"}, {"source": "new"}])

    def test_recipe_error_produces_red_stage(self):
        rows = []
        with patch.object(audit, "evaluate", side_effect=AssertionError("no confirmed witness")), \
                patch.object(cases, "controls", return_value={"passed": True}), \
                patch.object(cases, "mutant_suite", return_value={"passed": True}):
            result = audit.stage("A", Path("unused"), rows.append, lambda _: None)
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["cases"]), 1)
        self.assertIn("no confirmed witness", rows[0]["row"]["error"])

    def test_real_sources_and_parent_certificates_intact(self):
        manifest = audit.sources()
        for path in ("echo4/continuity_final_audit.py", "echo4/continuity_final_cases.py",
                     "docs/ECHO4-CONTINUITY1-D-DESIGN.md", "docs/ECHO4-CONTINUITY1-D-PREFLIGHT.md",
                     "tests/test_echo4_continuity1d.py"):
            self.assertIn(path, manifest)
        self.assertEqual(set(audit.parents()), set(audit.PARENTS))


class TestReconstructiveAudit(unittest.TestCase):
    """Tiny mocked replay to exercise artifact verification, not physical success."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / "fixture"
        self.manifest, self.ancestry = {"source": "hash"}, {"parent": "hash"}
        self.template = {"schema": audit.SCHEMA, "profile": "smoke", "scope": cases.SCOPE,
                         "sources": self.manifest, "parents": self.ancestry,
                         "closure_eligible": False, "continuity1_green": False}

        def campaign(directory, emit, progress, **kwargs):
            emit({"event": "unit_fixture"})
            return copy.deepcopy(self.template)

        for name, value in (("sources", lambda: self.manifest), ("parents", lambda: self.ancestry),
                            ("campaign", campaign)):
            p = patch.object(audit, name, value)
            p.start()
            self.addCleanup(p.stop)
        audit.record(self.folder, smoke=True)

    def change_report(self, **changes):
        path = self.folder / "report.json"
        report = json.loads(path.read_bytes())
        report.update(changes)
        path.write_bytes(cases.a.canonical(report))

    def assert_rejected(self, message):
        result = audit.verify(self.folder)
        self.assertFalse(result["valid"])
        self.assertFalse(result["continuity1_green"])
        self.assertIsNone(result["reproduction_sha256"])
        self.assertIn(message, result["findings"][0])

    def test_valid_smoke_cannot_certify_green(self):
        result = audit.verify(self.folder)
        self.assertTrue(result["valid"])
        self.assertFalse(result["continuity1_green"])

    def test_existing_evidence_is_never_overwritten(self):
        with self.assertRaises(FileExistsError):
            audit.record(self.folder, smoke=True)

    def test_missing_checkpoint_journal_content_rejected(self):
        (self.folder / "traces.jsonl").write_bytes(b"")
        self.assert_rejected("journal differs")

    def test_changed_journal_rejected(self):
        (self.folder / "traces.jsonl").write_bytes(b'{"event":"forged"}\n')
        self.assert_rejected("journal differs")

    def test_extra_journal_rejected(self):
        path = self.folder / "traces.jsonl"
        path.write_bytes(path.read_bytes() + b"{}\n")
        self.assert_rejected("trailing journal")

    def test_forged_closure_rejected(self):
        self.change_report(closure_eligible=True)
        self.assert_rejected("report differs")

    def test_boolean_integer_type_substitution_rejected(self):
        self.change_report(continuity1_green=0)
        self.assert_rejected("report differs")

    def test_source_substitution_rejected(self):
        self.change_report(sources={})
        self.assert_rejected("source/parent mismatch")

    def test_parent_substitution_rejected(self):
        self.change_report(parents={})
        self.assert_rejected("source/parent mismatch")

    def test_duplicate_keys_rejected(self):
        (self.folder / "report.json").write_bytes(b'{"schema":"x","schema":"y"}')
        self.assert_rejected("duplicate")

    def test_float_rejected(self):
        (self.folder / "report.json").write_bytes(b'{"value":1.5}')
        result = audit.verify(self.folder)
        self.assertFalse(result["valid"])
        self.assertFalse(result["continuity1_green"])


if __name__ == "__main__":
    unittest.main()
