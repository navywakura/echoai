"""SELF-B conditional attribution, prequential probes and honest unknowns."""
from dataclasses import replace
import ast
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.echo4 import self_attribution as module
from echoai.echo4.boundary_world import Experiment, packet, run_pair
from echoai.echo4.self_attribution import CATALOG, H_CODES, T_CODES, ProbePlan, SelfAttributor, forecast
from echoai.echo4.self_probe_audit import calibrate, record, run_condition, verify
from echoai.echo4.self_probe_world import run_probe
from echoai.echo4.self_probe_agent import SelfProbeAgent
from echoai.echo4.self_agent import SelfAgent
from echoai.echo4.self_audit import cam_hash
from echoai.echo4.world import Body


class TestAttribution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.body = Body(37, 65)
        cls.reference, cls.nominal = calibrate(cls.body)

    def model(self, long_reference=True):
        return SelfAttributor(self.reference, packet(self.body), self.nominal if long_reference else None)

    def test_prior_starts_ambiguous_not_true_parameters(self):
        model = self.model()
        self.assertEqual(model.diagnosis()["label"], "unknown")
        self.assertEqual(model.diagnosis()["possible"], ("nominal", "own", "external", "mixed"))
        self.assertGreater(len(model.t_candidates), 1)
        self.assertLessEqual(len(model.h_candidates), 64)
        self.assertLessEqual(len(model.t_candidates), 160)

    def test_old_four_way_witness_resolved(self):
        for hc, heat, label in ((True, 0, "nominal"), (False, 0, "own"),
                                (True, 4, "external"), (False, 4, "mixed")):
            with self.subTest(label=label):
                result = run_condition(self.model(), self.body, hc, True, heat, mode="active")
                self.assertEqual(result["diagnosis"]["label"], label)
                self.assertTrue(result["truth_retained"])
                self.assertEqual(result["terminalities"], 0)

    def test_temperature_only_fault_and_negative_pulse(self):
        result = run_condition(self.model(), self.body, True, False, -16, mode="active")
        self.assertEqual(result["diagnosis"]["label"], "mixed")

    def test_short_reference_keeps_unresolved_causes(self):
        result = run_condition(self.model(False), self.body, True, True, 4, mode="active")
        self.assertEqual(result["diagnosis"]["label"], "unknown")
        self.assertTrue(result["truth_retained"])

    def test_wait_alone_does_not_identify_actuation(self):
        result = run_condition(self.model(), self.body, False, True, 0, mode="wait_only")
        self.assertEqual(result["diagnosis"]["label"], "unknown")

    def test_prediction_precedes_every_physical_step(self):
        model = self.model()
        plan = model.choose(18)
        frozen = copy.deepcopy(model.pending)
        seen = []

        def before_step(tick, action):
            self.assertEqual(model.pending, frozen)
            seen.append(tick)

        trace, _ = run_probe(self.body, plan, before_step=before_step)
        self.assertEqual(len(seen), len(plan.actions))
        model.consume(trace)
        self.assertIsNone(model.pending)

    def test_reference_cam_unchanged_during_diagnosis(self):
        before = self.reference.model_hash(), cam_hash(self.reference.boundary.cam)
        run_condition(self.model(), self.body, False, False, 16, mode="active")
        self.assertEqual((self.reference.model_hash(), cam_hash(self.reference.boundary.cam)), before)

    def test_tokens_do_not_encode_cause_or_change_plan(self):
        a, b = self.model(), self.model()
        self.assertEqual(a.choose(18).index, b.choose(99999).index)
        self.assertEqual(a.h_candidates, b.h_candidates)

    def test_invalid_token_no_mutation(self):
        for token in (True, 0, 17, -1, 1 << 31, 18.0):
            model = self.model()
            before = copy.deepcopy(vars(model))
            with self.assertRaises(ValueError):
                model.choose(token)
            self.assertEqual(vars(model), before)

    def test_pending_and_repeated_receipt_rejected(self):
        model = self.model()
        with self.assertRaises(RuntimeError):
            model.consume(None)
        plan = model.choose(18)
        with self.assertRaises(RuntimeError):
            model.choose(19)
        trace = run_probe(self.body, plan)[0]
        model.consume(trace)
        with self.assertRaises(RuntimeError):
            model.consume(trace)
        with self.assertRaises(ValueError):
            model.choose(18)

    def test_unexpected_real_heat_detects_model_contradiction(self):
        body = Body(30, 50)
        ref, nominal = calibrate(body)
        model = SelfAttributor(ref, packet(body), nominal)
        plan = model.choose(18)
        trace, _ = run_probe(body, plan, heat=32)
        self.assertFalse(any(trace.terminal))
        result = model.consume(trace)
        self.assertEqual((result["label"], result["reason"]), ("unknown", "model_contradiction"))
        self.assertIsNone(model.choose(19))

    def test_invalid_receipts_fail_closed_not_body_failure(self):
        prototype = self.model()
        plan = prototype.choose(18)
        trace = run_probe(self.body, plan)[0]
        bad = [None, replace(trace, token=19), replace(trace, restored=False),
               replace(trace, restored=1), replace(trace, same_context=False),
               replace(trace, packets=trace.packets[:-1]),
               replace(trace, packets=(bytes(15),) + trace.packets[1:]),
               replace(trace, packets=(trace.packets[0],) * len(trace.packets)),
               replace(trace, ticks=(0,) * len(trace.ticks)),
               replace(trace, applied=(None,) + trace.applied[1:]),
               replace(trace, applied=(True,) + trace.applied[1:]),
               replace(trace, gates=(2,) + trace.gates[1:]),
               replace(trace, proposed=(0,) + trace.proposed[1:]),
               replace(trace, terminal=(False,) * (len(trace.terminal) - 1) + (True,))]
        for receipt in bad:
            model = copy.deepcopy(prototype)
            result = model.consume(receipt)
            self.assertEqual(result["label"], "unknown")
            self.assertIsNone(model.choose(19))

    def test_semantic_and_e_range_corruption_abstain(self):
        for index, value in ((0, 47), (8, 127)):
            model = self.model()
            plan = model.choose(18)
            trace = run_probe(self.body, plan)[0]
            raw = bytearray(trace.packets[1])
            raw[index] = value
            trace = replace(trace, packets=(trace.packets[0], bytes(raw)) + trace.packets[2:])
            self.assertEqual(model.consume(trace)["reason"], "invalid_execution_receipt")

    def test_original_gate_stops_probe_at_veto(self):
        model = self.model()
        plan = model.choose(18)
        trace, private = run_probe(self.body, plan, veto_at=2)
        self.assertEqual(len(trace.applied), 2)
        self.assertEqual(trace.applied[-1], 2)
        self.assertEqual(trace.gates[-1], 2)
        self.assertEqual(model.consume(trace)["label"], "unknown")
        self.assertEqual(len(private["states"]), 3)

    def test_unsafe_for_one_hypothesis_means_no_probe(self):
        model = self.model()
        model.t_candidates = ((126, False, 0),)
        self.assertIsNone(model.choose(18))
        self.assertEqual(len(model.used), 0)

    def test_safety_checks_whole_sequence_not_first_tick(self):
        model = self.model()
        model.h_candidates = ((2, False),)
        self.assertIsNone(model.choose(18))  # first wait viable, second terminal

    def test_budget_no_repeat_or_unbounded_history(self):
        outcome = run_condition(self.model(False), self.body, True, True, 4, mode="active")
        indices = [p["before_execution"]["plan"]["index"] for p in outcome["probes"]]
        self.assertEqual(len(indices), len(set(indices)))
        self.assertLessEqual(len(indices), 6)
        self.assertLessEqual(outcome["diagnosis"]["executed_ticks"], 48)
        self.assertEqual(outcome["resources"]["retained_traces"], 0)

    def test_constructor_requires_valid_measured_nominal_data(self):
        for nominal in (False, replace(self.nominal, restored=False),
                        replace(self.nominal, same_context=False)):
            with self.assertRaises(ValueError):
                SelfAttributor(self.reference, packet(self.body), nominal)
        with self.assertRaises(ValueError):
            SelfAttributor(self.reference, packet(Body(90, 64)), self.nominal)
        with self.assertRaises(ValueError):
            SelfAttributor(None, packet(self.body), None)

    def test_same_prior_functions_match_private_executor_single_steps(self):
        for thermal in (False, True):
            for value in range(1, 127 if thermal else 128):
                for coupled in (False, True):
                    for heat in ((-16, -4, 0, 4, 16) if thermal else (0,)):
                        candidate = (value, coupled, heat) if thermal else (value, coupled)
                        for action in range(3):
                            body = Body(64, value) if thermal else Body(value, 64)
                            trace, truth = run_probe(body, ProbePlan(1, 0, (action,), 0, 0),
                                                     h_coupled=coupled if not thermal else True,
                                                     temperature_coupled=coupled if thermal else True, heat=heat)
                            prediction = forecast(candidate, (action,), thermal=thermal)
                            if trace.terminal[-1]:
                                self.assertIsNone(prediction)
                            else:
                                state = truth["states"][-1]
                                expected = T_CODES[state["temperature"]] if thermal else H_CODES[state["h"]]
                                self.assertEqual(prediction, (expected,))

    def test_runtime_cannot_import_judge_or_private_executor(self):
        tree = ast.parse(Path(module.__file__).read_text())
        allowed = {"__future__", "dataclasses", "echoai.echo4.boundary", "echoai.echo4.self_model",
                   "echoai.echo4.sensation", "echoai.echo4.world", "echoai.nexus0.encoder", "echoai.nexus0.env"}
        self.assertTrue(all(n.module in allowed for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)))
        self.assertFalse(any(isinstance(n, ast.Div) or isinstance(n, ast.Constant) and type(n.value) is float
                             for n in ast.walk(tree)))


class TestIntegration(unittest.TestCase):
    def test_factory_attaches_without_changing_normal_policy(self):
        agent, original = SelfProbeAgent(), SelfAgent()
        for tick in range(8):
            self.assertEqual(agent.turn(tick), original.turn(tick))
            self.assertEqual(agent.last_sensation, original.last_sensation)
        self.assertEqual(agent.sensation.model_hash(), original.sensation.model_hash())
        self.assertEqual(agent.metrics.cortex_calls, 0)
        self.assertEqual(agent.metrics.false_facts, 0)
        body = Body(37, 65)
        probe_agent = SelfProbeAgent(initial=body)
        for action in (0, 1):
            for i in range(1, 9):
                probe_agent.calibrate_self_reference(run_pair(Experiment(body, action), 8 * action + i)[0])
        probe_agent.seal_self_reference()
        nominal = run_probe(body, ProbePlan(17, 0, CATALOG[0], 0, 0))[0]
        self.assertIs(probe_agent.self_change.boundary.cam, probe_agent.cam)
        self.assertIs(probe_agent.sensation.world, probe_agent.t)
        self.assertEqual(probe_agent.new_self_diagnosis(packet(body), nominal).diagnosis()["label"], "unknown")

    def test_executor_never_acts_after_terminality(self):
        trace, truth = run_probe(Body(1, 64), ProbePlan(1, 0, (2, 2, 2), 0, 0))
        self.assertEqual(len(trace.applied), 1)
        self.assertTrue(trace.terminal[-1])
        self.assertEqual(len(truth["states"]), 2)


class TestAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temp.name) / "evidence"
        cls.report = record(cls.directory, quick=True)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_smoke_counts_and_full_self_not_green(self):
        self.assertTrue(self.report["diagnostic_checks_passed"])
        self.assertFalse(self.report["self1_green"])
        for controller in self.report["controllers"].values():
            self.assertEqual(controller["total"], 120)
            self.assertEqual(controller["wrong"], 0)

    def test_fresh_replay(self):
        result = verify(self.directory)
        self.assertTrue(result["valid"])
        self.assertFalse(result["self1_green"])

    def test_no_overwrite(self):
        with self.assertRaises(FileExistsError):
            record(self.directory, quick=True)

    def test_tampered_report(self):
        path = self.directory / "report.json"
        raw = path.read_bytes()
        try:
            altered = json.loads(raw)
            altered["self1_green"] = True
            path.write_text(json.dumps(altered))
            self.assertFalse(verify(self.directory)["valid"])
        finally:
            path.write_bytes(raw)

    def test_tampered_execution_and_trailing_data(self):
        path = self.directory / "traces.jsonl"
        raw = path.read_bytes()
        try:
            path.write_bytes(raw.replace(b'"restored":true', b'"restored":false', 1))
            self.assertFalse(verify(self.directory)["valid"])
            path.write_bytes(raw + b"{}\n")
            self.assertFalse(verify(self.directory)["valid"])
        finally:
            path.write_bytes(raw)

    def test_missing_artifact_or_changed_source(self):
        self.assertFalse(verify(Path(self.temp.name) / "absent")["valid"])
        with patch("echoai.echo4.self_probe_audit.sources", return_value={}):
            self.assertFalse(verify(self.directory)["valid"])


if __name__ == "__main__":
    unittest.main()
