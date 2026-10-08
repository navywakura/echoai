"""SELF-A tests, not a substitute for attribution and behavioral recovery."""
from __future__ import annotations

import ast
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.core.cam import Cam
from echoai.core.wsp import pack
from echoai.echo4 import self_model as module
from echoai.echo4.boundary import ALL, MASK, BoundaryMap
from echoai.echo4.boundary_world import Experiment, run_pair
from echoai.echo4.self_agent import SelfAgent
from echoai.echo4.self_audit import cam_hash, census, check_witness, normalized, record, verify
from echoai.echo4.self_model import Change, SelfChangeMonitor, signature
from echoai.echo4.sensation_agent import SensationAgent
from echoai.echo4.world import Body


def nominal(identifier=1, action=0, initial=Body(30, 50)):
    return run_pair(Experiment(initial, action), identifier)[0]


def monitor(*, initial=Body(30, 50), samples=8, seal=True):
    model = SelfChangeMonitor(BoundaryMap(Cam()))
    for i in range(1, samples + 1):
        model.calibrate(nominal(i, initial=initial))
    if seal:
        model.seal()
    return model


def snapshot(model):
    return model.model_hash(), cam_hash(model.boundary.cam)


class TestChangeMonitor(unittest.TestCase):
    def test_same_boundary_cam_and_no_new_bus(self):
        boundary = BoundaryMap(Cam())
        model = SelfChangeMonitor(boundary)
        self.assertIs(model.boundary, boundary)
        self.assertFalse(hasattr(model, "cam"))
        self.assertEqual(model.resources()["retained_pairs"], 0)

    def test_no_comparison_before_sealing(self):
        model = monitor(seal=False)
        with self.assertRaises(RuntimeError):
            model.compare(nominal())

    def test_insufficient_calibration_abstains(self):
        model = monitor(samples=7)
        self.assertEqual(model.compare(nominal()).known, 0)
        self.assertEqual(model.compare(nominal()).unknown, ALL)

    def test_nominal_match_is_not_no_physical_change(self):
        model = monitor(initial=Body(38, 50))
        hidden_change = run_pair(Experiment(Body(38, 50), 0, h_coupled=False), 9)[0]
        result = model.compare(hidden_change)
        self.assertEqual((result.reason, result.attribution), ("matches_reference", "unknown"))
        self.assertEqual(result.known, MASK)

    def test_change_channels_checked_by_hand(self):
        model = monitor()
        changed = run_pair(Experiment(Body(30, 50), 0, h_coupled=False), 9)[0]
        result = model.compare(changed)
        self.assertEqual((result.reference_changed, result.action_effect_changed), (0, 256))
        self.assertEqual((result.reason, result.attribution), ("observed_change", "unknown"))

    def test_external_heat_also_changes_action_contrast_under_quantization(self):
        model = monitor()
        external = run_pair(Experiment(Body(30, 50), 0, heat=16), 9)[0]
        result = model.compare(external)
        self.assertEqual((result.reference_changed, result.action_effect_changed), (512, 512))
        self.assertEqual(result.attribution, "unknown")  # not a spurious mixed/body diagnosis

    def test_two_distinct_causes_have_identical_complete_public_receipts(self):
        initial = Body(38, 50)
        for action in (0, 1):
            own, truth_own, _ = run_pair(Experiment(initial, action, h_coupled=False), 1)
            external, truth_external, _ = run_pair(Experiment(initial, action, heat=4), 2)
            self.assertEqual(normalized(own), normalized(external))
            self.assertNotEqual(truth_own["states"], truth_external["states"])

    def test_conflicting_nominal_reference_is_not_averaged_away(self):
        model = monitor(seal=False)
        p = run_pair(Experiment(Body(30, 50), 0, heat=16), 9)[0]
        model.calibrate(p)
        model.seal()
        self.assertEqual(model.compare(p).reason, "conflicting_reference")

    def test_different_execution_timing_abstains(self):
        model = monitor()
        delayed = run_pair(Experiment(Body(30, 50), 0, delay=2), 9)[0]
        self.assertEqual(model.compare(delayed).reason, "different_execution_timing")

    def test_delayed_reference_ignores_pre_application_contrast(self):
        delayed = run_pair(Experiment(Body(30, 50), 0, delay=2), 1)[0]
        applied_at, values = signature(delayed)
        self.assertEqual(applied_at, 2)
        self.assertEqual(values[4:6], (0, 0))

    def test_unknown_context_never_allocates(self):
        model = monitor()
        before = snapshot(model)
        result = model.compare(nominal(9, initial=Body(90, 50)))
        self.assertEqual(result, Change())
        self.assertEqual(snapshot(model), before)

    def test_bad_inputs_do_not_mutate_reference_or_cam(self):
        model = monitor(seal=False)
        p = nominal(9)
        altered = bytes([0]) + p.treatment.packets[1][1:]
        invalid = [None, replace(p, restored=False), replace(p, common_schedule=False),
                   replace(p, treatment=replace(p.treatment, token=99)),
                   replace(p, treatment=replace(p.treatment, applied=(None, 2))),
                   replace(p, treatment=replace(p.treatment, applied=(True, 2))),
                   replace(p, treatment=replace(p.treatment, gates=(2, 0))),
                   replace(p, treatment=replace(p.treatment, ticks=(0, 0, 2))),
                   replace(p, treatment=replace(p.treatment, packets=(bytes(15),) * 3)),
                   replace(p, treatment=replace(p.treatment, terminal=(False, True, False))),
                   replace(p, treatment=replace(p.treatment, packets=(p.treatment.packets[0], altered, altered)))]
        before = snapshot(model)
        for bad in invalid:
            with self.assertRaises(ValueError):
                model.calibrate(bad)
            self.assertEqual(snapshot(model), before)
        model.seal()
        before = snapshot(model)
        for bad in invalid:
            self.assertEqual(model.compare(bad).unknown, ALL)
            self.assertEqual(snapshot(model), before)

    def test_duplicates_and_budget_fail_atomically(self):
        model = monitor(seal=False)
        before = snapshot(model)
        with self.assertRaises(ValueError):
            model.calibrate(nominal(8))
        self.assertEqual(snapshot(model), before)
        model.boundary.pairs = 4096
        before = snapshot(model)
        with self.assertRaises(OverflowError):
            model.calibrate(nominal(9))
        self.assertEqual(snapshot(model), before)

    def test_reference_capacity_and_full_cam(self):
        model = SelfChangeMonitor(BoundaryMap(Cam(), capacity=1))
        model.calibrate(nominal())
        before = snapshot(model)
        with self.assertRaises(OverflowError):
            model.calibrate(nominal(2, action=1))
        self.assertEqual(snapshot(model), before)
        empty = SelfChangeMonitor(BoundaryMap(Cam()))
        empty.boundary.cam.used = 4096
        before = snapshot(empty)
        with self.assertRaises(OverflowError):
            empty.calibrate(nominal())
        self.assertEqual(snapshot(empty), before)

    def test_many_queries_do_not_consume_samples_or_rewrite_memory(self):
        model = monitor()
        before = snapshot(model)
        for i in range(9, 73):
            model.compare(run_pair(Experiment(Body(30, 50), 0, heat=16), i)[0])
        self.assertEqual(snapshot(model), before)
        self.assertEqual(model.boundary.pairs, 8)
        self.assertTrue(all(row.samples == 8 for row in model.references.values()))
        self.assertTrue(all(not s.has_fact for s in model.boundary.cam.slot if s.occupied))

    def test_seal_prevents_nominal_updates(self):
        model = monitor()
        before = snapshot(model)
        with self.assertRaises(RuntimeError):
            model.calibrate(nominal(9))
        self.assertEqual(snapshot(model), before)

    def test_invalid_constructor_and_existing_boundary_capacity(self):
        with self.assertRaises(ValueError):
            SelfChangeMonitor(None)
        boundary = BoundaryMap(Cam())
        boundary.freeze()
        with self.assertRaises(ValueError):
            SelfChangeMonitor(boundary)

    def test_out_of_range_wsp_component_rejected(self):
        model = monitor(seal=False)
        p = nominal(9)
        raw = bytearray(p.treatment.packets[1])
        raw[8] = 127
        bad = replace(p, treatment=replace(p.treatment, packets=(p.treatment.packets[0], bytes(raw), bytes(raw))))
        before = snapshot(model)
        with self.assertRaises(ValueError):
            model.calibrate(bad)
        self.assertEqual(snapshot(model), before)
        model.seal()
        self.assertEqual(model.compare(bad).known, 0)

    def test_uncertain_boundary_fails_closed(self):
        model = monitor()
        from echoai.echo4.boundary import Estimate
        with patch.object(model.boundary, "estimate", return_value=Estimate()):
            self.assertEqual(model.compare(nominal()).reason, "uncertain_boundary")

    def test_no_private_physics_or_float_in_runtime(self):
        tree = ast.parse(Path(module.__file__).read_text())
        self.assertTrue(all(n.module in {"__future__", "dataclasses", "echoai.echo4.boundary"}
                            for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)))
        self.assertTrue(all(alias.name in {"hashlib", "json"} for n in ast.walk(tree)
                            if isinstance(n, ast.Import) for alias in n.names))
        self.assertFalse(any(isinstance(n, ast.Div) or isinstance(n, ast.Constant) and type(n.value) is float
                             for n in ast.walk(tree)))


class TestSelfIntegration(unittest.TestCase):
    def test_original_agent_actions_and_predictions_unchanged(self):
        self_agent, original = SelfAgent(), SensationAgent()
        self.assertIs(self_agent.self_change.boundary.cam, self_agent.cam)
        self.assertIs(self_agent.sensation.world, self_agent.t)
        for turn in range(8):
            self.assertEqual(self_agent.turn(turn), original.turn(turn))
            self.assertEqual(self_agent.env.body, original.env.body)
            self.assertEqual(self_agent.last_sensation, original.last_sensation)
        self.assertEqual(self_agent.sensation.model_hash(), original.sensation.model_hash())
        self.assertEqual(self_agent.metrics.cortex_calls, 0)
        self.assertEqual(self_agent.metrics.false_facts, 0)
        self.assertEqual(self_agent.cam.destroyed, 0)

    def test_opt_in_calibration_does_not_update_q_or_t(self):
        agent = SelfAgent()
        before = repr(vars(agent.q)), repr(vars(agent.t))
        for i in range(1, 9):
            agent.calibrate_self_reference(nominal(i))
        agent.seal_self_reference()
        result = agent.compare_self_observation(nominal(9))
        self.assertEqual(result.reason, "matches_reference")
        self.assertEqual((repr(vars(agent.q)), repr(vars(agent.t))), before)


class TestSelfAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name) / "evidence"
        cls.report = record(cls.directory, quick=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_smoke_census_complete_and_self_stays_open(self):
        r = self.report
        self.assertEqual((r["conditions"], r["comparisons"], r["calibration_pairs"]), (120, 240, 96))
        self.assertTrue(r["self_a_checks_passed"])
        self.assertFalse(r["self1_green"])
        self.assertLess(r["both_actions"]["forced_classifier_correct_upper_bound"], 120)

    def test_complete_witnesses_replay(self):
        for key in ("single_action", "both_actions"):
            for witness in self.report[key]["witnesses"]:
                self.assertTrue(check_witness(witness, dual=key == "both_actions"))

    def test_valid_reproduction_is_not_self_closure(self):
        result = verify(self.directory)
        self.assertTrue(result["valid"])
        self.assertFalse(result["self1_green"])

    def test_no_overwrite(self):
        with self.assertRaises(FileExistsError):
            record(self.directory, quick=True)

    def test_tampered_report_cannot_promote_green(self):
        path = self.directory / "report.json"
        raw = path.read_bytes()
        try:
            altered = json.loads(raw)
            altered["self1_green"] = True
            path.write_text(json.dumps(altered))
            self.assertFalse(verify(self.directory)["valid"])
        finally:
            path.write_bytes(raw)

    def test_tampered_trace_rejected(self):
        path = self.directory / "traces.jsonl"
        raw = path.read_bytes()
        try:
            path.write_bytes(raw.replace(b'"restored":true', b'"restored":false', 1))
            self.assertFalse(verify(self.directory)["valid"])
            path.write_bytes(raw + b"{}\n")
            self.assertFalse(verify(self.directory)["valid"])
        finally:
            path.write_bytes(raw)

    def test_missing_evidence_or_changed_sources_rejected(self):
        self.assertFalse(verify(Path(self.temp.name) / "absent")["valid"])
        with patch("echoai.echo4.self_audit.sources", return_value={}):
            self.assertFalse(verify(self.directory)["valid"])


if __name__ == "__main__":
    unittest.main()
