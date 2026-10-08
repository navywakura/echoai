"""MAINT-B/C/D: observation-only control, physical predictions and custody.

These tests use development bodies only. D is a separate source-locked exam.
"""
import ast
import copy
from dataclasses import replace
from itertools import product
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from echoai.echo4 import maintain_continuity as c
from echoai.echo4 import maintain_final as bench
from echoai.echo4 import maintain_model as m
from echoai.echo4.continuity import canonical
from echoai.echo4.maintain_control import MaintainControl
from echoai.echo4.maintain_world import MaintenanceEnv, FAULTS
from echoai.echo4.world import Body
from echoai.nexus0.encoder import encode_cell
from echoai.nexus0.env import KIND_OBJECT


def packet(h=80, t=72):
    return encode_cell(0, KIND_OBJECT, vitality=h, temperature=t, temperature_bands=8)


def restored(run):
    raw = run.dumps()
    return c.loads(raw, expected_sha256=bench.sha(raw))


def contains(box, h, t, fault, heat, spares):
    return (box[0] <= h <= box[1] and box[2] <= t <= box[3]
            and box[4:] == (fault, heat, spares))


class ModelPhysics(unittest.TestCase):
    def test_singleton_forecasts_match_sealed_physics_at_boundaries(self):
        count = 0
        for h, t, fault, heat, spares, progress, action in product(
                (1, 3, 6, 9, 10, 16, 64, 126, 127), (1, 4, 16, 17, 64, 111, 123, 126),
                range(3), (0, 2, 4), (0, 1, 3), (0, 2), range(3)):
            env = MaintenanceEnv(Body(h, t), fault=FAULTS[fault], spares=spares, external_heat=heat)
            env._progress = progress  # Private mechanics fixture, not agent input.
            env.advance(action)
            predicted = m.project((h, h, t, t, fault, heat, spares), action, progress)
            expected = (env.body.h, env.body.h, env.body.temperature, env.body.temperature,
                        FAULTS.index(env._fault), heat, env._spares)
            self.assertEqual(set(predicted), {expected})
            count += 1
        self.assertEqual(count, 11664)

    def test_rectangles_overapproximate_every_represented_native_transition(self):
        for box in ((1, 12, 1, 19, 1, 4, 1), (6, 14, 109, 126, 0, 2, 2),
                    (120, 127, 15, 20, 2, 4, 3), (6, 14, 60, 67, 1, 0, 1)):
            for action, progress in product(range(3), range(3)):
                predicted = m.project(box, action, progress)
                for h, t in product(range(box[0], box[1]+1), range(box[2], box[3]+1)):
                    env = MaintenanceEnv(Body(h, t), fault=FAULTS[box[4]],
                                         spares=box[6], external_heat=box[5])
                    env._progress = progress
                    env.advance(action)
                    self.assertTrue(any(contains(b, env.body.h, env.body.temperature,
                                                 FAULTS.index(env._fault), box[5], env._spares)
                                        for b in predicted))

    def test_prior_is_uncertain_and_contains_actual_world_not_its_label(self):
        belief = m.prior(packet())
        self.assertEqual(len(belief), 60)
        self.assertEqual({b[4] for b in belief}, {0, 1, 2})
        self.assertEqual({b[5] for b in belief}, set(range(5)))
        self.assertEqual({b[6] for b in belief}, set(range(4)))
        self.assertTrue(all(b[:4] == m.bands(packet()) for b in belief))

    def test_quantized_packets_do_not_reveal_exact_registers(self):
        self.assertEqual(packet(80, 72), packet(79, 71))
        self.assertEqual(m.prior(packet(80, 72)), m.prior(packet(79, 71)))

    def test_bad_semantic_context_and_noninteger_inputs_fail(self):
        bad = bytearray(packet())
        bad[0] ^= 1
        for wsp in (bytes(bad), b"", bytearray(packet()), packet()[:-1]):
            with self.subTest(wsp=wsp), self.assertRaises(ValueError):
                m.MaintainModel(wsp)
        for value in (True, 1.0, -1, 4):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.prior(packet(), value)

    def test_no_unsupported_mode_or_action_q(self):
        with self.assertRaises(ValueError):
            m.MaintainModel(packet(), mode="omniscient")
        model = m.MaintainModel(packet())
        for q, proposed in (((0, 0), 1), ((True, 0, 0), 1), ((0, 0, 128), 1), ((0, 0, 0), True)):
            with self.assertRaises(ValueError):
                model.choose(packet(), q, proposed)

    def test_stale_or_unexecuted_forecast_is_not_evidence(self):
        model = m.MaintainModel(packet())
        with self.assertRaises(ValueError):
            model.choose(packet(100, 100), (0, 0, 0), 0)
        with self.assertRaises(RuntimeError):
            model.observe(packet(), 1, packet(77, 68), False)
        model.prepare(packet(), 1, 0)
        with self.assertRaises(RuntimeError):
            model.prepare(packet(), 1, 0)
        with self.assertRaises(RuntimeError):
            model.choose(packet(), (0, 0, 0), 0)
        with self.assertRaises(ValueError):
            model.observe(packet(), 2, packet(), False)
        self.assertEqual(model.steps, 0)

    def test_one_uncertain_hypothesis_can_block_an_unsafe_action(self):
        good = (60, 70, 60, 70, 0, 0, 3)
        self.assertTrue(m.safe((good,)))
        for bad in ((0, 4, 60, 70, 1, 0, 1), (40, 50, 0, 5, 0, 4, 2),
                    (40, 50, 125, 127, 2, 4, 0)):
            self.assertFalse(m.safe((good, bad)))

    def test_fixed_and_no_repair_do_not_claim_adaptive_evidence(self):
        for mode, wanted in (("adaptive", False), ("no_history", False),
                             ("no_repair", False), ("fixed", True)):
            model = m.MaintainModel(packet(), mode=mode)
            model.choose(packet(), (0, 0, 0), 1)
            self.assertEqual(model.last_choice[1:3], (False, wanted))

    def test_budget_latches_without_executing(self):
        model = m.MaintainModel(packet())
        model.steps = m.LIMIT
        with self.assertRaises(m.MaintainStop):
            model.choose(packet(), (0, 0, 0), 1)
        self.assertEqual(model.stopped, "budget")
        self.assertIsNone(model.pending)

    def test_no_hidden_executor_import_or_float_constant_in_model(self):
        tree = ast.parse((bench.ROOT / "echo4/maintain_model.py").read_text())
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertFalse(names & {"MaintenanceEnv", "ServiceReceipt", "eval", "exec"})
        self.assertFalse(any(isinstance(node, ast.Constant) and isinstance(node.value, float)
                             for node in ast.walk(tree)))


class ControlledLife(unittest.TestCase):
    def test_initial_proposal_identical_with_different_private_causes(self):
        decisions, priors = set(), set()
        for fault, spares, heat in product(FAULTS, (0, 3), (0, 4)):
            a = MaintainControl(MaintenanceEnv(Body(80, 72), fault=fault,
                                              spares=spares, external_heat=heat))
            priors.add(a.maintenance.boxes)
            a.turn(0)
            decisions.add(a.last_proposed_action)
        self.assertEqual(len(priors), 1)
        self.assertEqual(len(decisions), 1)

    def test_private_audit_is_never_read_by_agent(self):
        a = MaintainControl(MaintenanceEnv(Body(80, 72), fault="clogged", spares=3))
        with patch.object(a.env, "audit_state", side_effect=AssertionError("private truth")):
            for tick in range(16):
                a.turn(tick)
        self.assertEqual(a.env.repairs, 1)
        self.assertIs(a.sensation.cam, a.cam)
        self.assertIs(a.sensation.world, a.t)
        self.assertIs(a.boundary.cam, a.cam)
        self.assertIsNone(a.self_model)
        self.assertEqual((a.metrics.cortex_calls, a.metrics.false_facts, a.cam.destroyed), (0, 0, 0))
        self.assertGreater(a.metrics.deltas, 0)

    def test_service_cost_and_recovery_are_actually_executed(self):
        row = bench.episode((80, 72), "clogged", "adaptive", horizon=32)
        self.assertTrue(row["invariants"])
        self.assertEqual(row["ledger"]["repairs"], 1)
        self.assertEqual(row["confirmed_recoveries"], 1)
        self.assertEqual(row["ledger"]["service_resource_used"], 6)
        self.assertEqual(row["ledger"]["spares"], 2)
        self.assertEqual(row["ledger"]["resets"], 0)

    def test_baseline_ablations_do_not_complete_service(self):
        for mode in ("no_repair", "no_history"):
            row = bench.episode((80, 72), "clogged", mode, horizon=64)
            self.assertEqual(row["ledger"]["services_paid"], 0)
            self.assertEqual(row["ledger"]["repairs"], 0)
            self.assertTrue(row["invariants"])

    def test_irreparable_can_cost_without_success(self):
        row = bench.episode((80, 72), "irreparable", "adaptive", horizon=128)
        self.assertEqual(row["ledger"]["repairs"], 0)
        self.assertGreater(row["ledger"]["services_paid"], 0)
        self.assertFalse(row["terminal"])
        self.assertTrue(row["stopped"])

    def test_recurrence_does_not_reset_body_or_replenish_consumables(self):
        row = bench.episode((80, 72), "recurrent_mixed", "adaptive")
        self.assertTrue(row["complete"])
        self.assertEqual(row["ledger"]["repairs"], 3)
        self.assertEqual(row["confirmed_recoveries"], 3)
        self.assertEqual(row["ledger"]["spares"], 0)
        self.assertTrue(row["invariants"])
        self.assertGreater(row["conflicts"], 0)

    def test_veto_consumes_wait_not_proposal_then_halts(self):
        run = bench.prepared((80, 72), "clogged", veto_at=2)
        run.step()
        event = run.step()
        self.assertEqual((event["proposed"], event["applied"], event["gate"]), (1, 2, 2))
        self.assertEqual(run.agent.maintenance.progress, 0)
        self.assertEqual(run.agent.env.services_paid, 0)
        self.assertEqual(run.agent.maintenance.stopped, "gate_veto")
        before = run.dumps()
        with self.assertRaises(m.MaintainStop):
            run.step()
        self.assertEqual(run.dumps(), before)

    def test_operator_stop_preserves_body_and_prevents_mutation(self):
        run = bench.prepared((80, 72), "clogged")
        run.step()
        body = run.agent.env.body
        run.stop()
        self.assertEqual(run.agent.env.body, body)
        raw = run.dumps()
        with self.assertRaises(m.MaintainStop):
            run.step()
        self.assertEqual(run.dumps(), raw)
        with self.assertRaises(RuntimeError):
            run.agent.respawn()
        with self.assertRaises(RuntimeError):
            run.agent.env.reset()

    def test_safe_halt_has_no_physical_tick(self):
        run = bench.prepared((1, 124), "clogged")
        event = run.step()
        self.assertEqual(event["event"], "stop")
        self.assertEqual(run.next_turn, 0)
        self.assertEqual(run.agent.env.body, Body(1, 124))
        self.assertEqual(restored(run).agent.maintenance.stopped, "no_safe_action")

    def test_private_calendar_only_adds_ordered_faults(self):
        for events in ([], ((1, "healthy"),), ((1, "clogged"), (1, "seized")),
                       ((True, "clogged"),), ((512, "clogged"),)):
            with self.assertRaises(ValueError):
                c.checked_events(events)

    def test_failed_operation_cannot_be_checkpointed_or_retried(self):
        run = c.MaintainRun(MaintainControl(MaintenanceEnv(Body(80, 72), fault="seized")),
                            events=((0, "clogged"),))
        with self.assertRaises(ValueError):
            run.step()
        with self.assertRaises(ValueError):
            run.dumps()
        with self.assertRaises(RuntimeError):
            run.step()


class MaintenanceContinuity(unittest.TestCase):
    def run_at(self, steps=2, scenario="clogged"):
        run = bench.prepared((80, 72), scenario)
        for _ in range(steps):
            run.step()
        return run

    def test_exact_graph_roundtrip_and_future(self):
        run = self.run_at()
        raw = run.dumps()
        resumed = restored(run)
        self.assertEqual(resumed.dumps(), raw)
        self.assertIs(resumed.agent.sensation.cam, resumed.agent.cam)
        self.assertIs(resumed.agent.sensation.world, resumed.agent.t)
        self.assertIs(resumed.agent.self_change.boundary, resumed.agent.boundary)
        self.assertEqual(resumed.agent.env._progress, 2)
        self.assertEqual(canonical(bench.trajectory(run, 40)), canonical(bench.trajectory(resumed, 40)))

    def test_complete_c_suite_in_fresh_processes_and_mutants(self):
        with tempfile.TemporaryDirectory() as directory:
            result = bench.continuity_suite(Path(directory))
        self.assertTrue(result["passed"], result["checks"])
        self.assertEqual(len(result["rows"]), 12)
        self.assertEqual(len(result["mutants"]), 11)

    def test_ledger_repair_spares_and_q_are_not_rejuvenated(self):
        run = self.run_at(16)
        resumed = restored(run)
        self.assertEqual(resumed.agent.env.audit_state(), run.agent.env.audit_state())
        self.assertEqual(resumed.agent.q.q, run.agent.q.q)
        self.assertEqual(resumed.agent.q.rem, run.agent.q.rem)
        self.assertEqual(resumed.agent.t.n, run.agent.t.n)
        self.assertEqual(resumed.agent.maintenance.boxes, run.agent.maintenance.boxes)
        self.assertGreater(resumed.agent.env.resource_used, 0)

    def test_future_fault_calendar_and_cursor_are_preserved(self):
        run = self.run_at(47, "recurrent")
        resumed = restored(run)
        self.assertEqual(resumed.events, bench.RECURRENCE)
        self.assertEqual(resumed.cursor, 0)
        for _ in range(20):
            self.assertEqual(run.step(), resumed.step())
        self.assertEqual(resumed.cursor, 1)

    def test_terminal_cannot_resurrect_or_be_operator_relabeled(self):
        run = bench.prepared((80, 124), "hot_stress", veto_at=1)
        run.step()
        self.assertTrue(run.agent.episode_terminal)
        raw = run.dumps()
        run.stop()
        self.assertEqual(run.dumps(), raw)
        resumed = restored(run)
        with self.assertRaises(m.MaintainStop):
            resumed.step()
        self.assertEqual(resumed.dumps(), raw)

    def test_invalid_model_and_physical_fields_rejected(self):
        cases = (("maintenance", "progress", True), ("maintenance", "steps", 9),
                 ("maintenance", "pending", ()), ("maintenance", "boxes", ()),
                 ("env", "_spares", 4), ("env", "_external_heat", True),
                 ("env", "service_resource_used", 6), ("env", "resource_used", 0))
        for child, field, value in cases:
            run = self.run_at()
            setattr(getattr(run.agent, child), field, value)
            with self.subTest(field=field), self.assertRaises(ValueError):
                run.dumps()

    def test_physical_receipt_cannot_claim_unperformed_service(self):
        run = self.run_at()
        run.agent.env.last_service = replace(run.agent.env.last_service, service="repaired")
        with self.assertRaises(ValueError):
            run.dumps()

    def test_private_unrecorded_fault_rejected(self):
        run = self.run_at()
        run.agent.env._fault = "seized"
        with self.assertRaises(ValueError):
            run.dumps()

    def test_completed_event_cursor_cannot_skip_a_future_event(self):
        run = self.run_at(47, "recurrent")
        run.cursor = 1
        with self.assertRaises(ValueError):
            run.dumps()

    def test_current_event_not_marked_consumed_without_action_or_stop(self):
        run = self.run_at(48, "recurrent")
        run.cursor = 1
        with self.assertRaises(ValueError):
            run.dumps()

    def test_observed_stop_after_fault_can_be_saved(self):
        run = c.MaintainRun(MaintainControl(MaintenanceEnv(Body(1, 124))),
                            events=((0, "seized"),))
        run.step()
        self.assertEqual(restored(run).cursor, 1)
        self.assertEqual(restored(run).agent.env._fault, "seized")

    def test_unfinished_or_extra_state_not_serialized(self):
        for field in ("_busy", "_failed"):
            run = self.run_at()
            setattr(run, field, True)
            with self.assertRaises(ValueError):
                run.dumps()
        run = self.run_at()
        run.agent.maintenance.hidden_truth = "clogged"
        with self.assertRaises(ValueError):
            run.dumps()

    def test_custody_digest_strict_json_and_profile_rejected(self):
        raw = self.run_at().dumps()
        with self.assertRaises(ValueError):
            c.loads(raw + b" ", expected_sha256=bench.sha(raw))
        for malformed in (raw + b" ", b'{"x":0,"x":1}', b'{"x":1.0}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                c.loads(malformed, expected_sha256=bench.sha(malformed))
        data = json.loads(raw)
        data["schema"] = "nominal"
        wrong = canonical(data)
        with self.assertRaises(ValueError):
            c.loads(wrong, expected_sha256=bench.sha(wrong))

    def test_sources_and_unknown_classes_fail_closed_even_if_resigned(self):
        original = json.loads(self.run_at().dumps())
        for kind in ("sources", "class"):
            data = copy.deepcopy(original)
            if kind == "sources":
                data["sources"] = {}
            else:
                data["state"]["objects"][0]["type"] = "arbitrary.import.Class"
            raw = canonical(data)
            with self.assertRaises(ValueError):
                c.loads(raw, expected_sha256=bench.sha(raw))

    def test_atomic_publication_never_overwrites(self):
        run = self.run_at()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            run.save(path)
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                run.save(path)
            self.assertEqual(path.read_bytes(), before)


class CampaignContract(unittest.TestCase):
    def test_source_lock_precedes_execution_and_red_development_keeps_exams_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)

            def failed_development(bodies, progress):
                self.assertTrue((path / "lock.json").exists())
                self.assertEqual(bodies, bench.DEVELOPMENT)
                return {"totals": {}, "checks": {"synthetic_failure": False}, "passed": False}

            # Synthetic orchestration test, never substituted for an exam.
            with patch.object(bench, "sources", return_value={}), \
                    patch.object(bench, "parent", return_value={}), \
                    patch.object(bench, "exam_bodies", return_value=((), ())), \
                    patch.object(bench, "batch", side_effect=failed_development) as batch, \
                    patch.object(bench, "continuity_suite", return_value={
                        "checks": {}, "mutants": {}, "passed": True}):
                result = bench.campaign(path)
            batch.assert_called_once()
            self.assertFalse(result["criteria_passed"])
            self.assertFalse(result["maintain1_green"])
            self.assertEqual(result["exams"], [])
            self.assertFalse((path / "exam-1.json").exists())

    def test_parent_sources_and_negative_result_are_unchanged(self):
        self.assertTrue(bench.parent())
        receipt = json.loads((bench.PARENT / "audit-receipt.json").read_bytes())
        self.assertFalse(receipt["maintain1_green"])
        self.assertEqual(receipt["reproduction_sha256"], bench.PARENT_DIGEST)

    def test_manifest_covers_new_runtime_and_contract(self):
        manifest = bench.sources()
        for name in ("echo4/maintain_model.py", "echo4/maintain_continuity.py",
                     "tests/test_echo4_maintain1.py", "docs/ECHO4-MAINTAIN1-BCD-DESIGN.md"):
            self.assertIn(name, manifest)
        self.assertEqual(len(manifest), 93)

    def test_no_replay_predictions_are_counted_as_executed_work(self):
        row = bench.episode((80, 72), "nominal", "adaptive", horizon=32)
        self.assertEqual(row["ledger"]["work_done"], sum(e.get("reward") == 16 for e in row["frames"]))
        self.assertGreater(row["model_predictions"], row["ledger"]["steps"])

    def test_missing_or_forged_campaign_cannot_be_green(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            result = bench.verify(p)
            self.assertFalse(result["valid"])
            self.assertFalse(result["maintain1_green"])
            bench.persist(p, "report.json", {"sources": {}, "maintain1_green": True}, False)
            result = bench.verify(p)
            self.assertFalse(result["valid"])
            self.assertFalse(result["maintain1_green"])


if __name__ == "__main__":
    unittest.main()
