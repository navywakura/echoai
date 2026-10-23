"""New discrete regressions and runner contract tests; never launch SITL.

These tests are written for the parent's later background test phase. Fake
telemetry exercises gates only; a fake receipt must remain invalid for SITL.
"""

from copy import deepcopy
import json
import math
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from echo5.budget import Budget
from echo5.legacy import module
from echo5.mission import (
    MissionBridge, MissionExecutor, PLAN_SCHEMA, _health, digest, goal_request,
    audit_report, _audit_episode, normalize_config, run_benchmark, synthetic_models, validate_goal, validate_raw,
)
from echo5 import sitl
from echo5.interaction import HypothesisAgent
from echo5.mission_reasoning import (MissionReasoner, ENGINE, OUTCOME_SCHEMA, EFFECT_PRIOR,
                                     audit_reasoning, validate_outcome)


def raw_frame(*, now=10_000_000_000, position=(0, 0, 0), remaining=950, marker=False):
    """Explicit public synthetic rays, not a Gazebo or camera receipt."""
    angles = [round(-math.pi*1000+i*2*math.pi*1000/360) for i in range(360)]
    rays = dict(capture_ns=now, delivered_ns=now, angles_mrad=angles, ranges_mm=[9000]*360)
    return dict(now_ns=now,
                estimate=dict(position_mm=[position[0]*3000, position[1]*3000, 2500],
                              yaw_mrad=0, received_ns=now, px4_boot_ms=now//1_000_000,
                              tilt_mrad=0, speed_mm_s=0),
                lidar=rays, depth=[deepcopy(rays) for _ in range(4)],
                rgb=dict(capture_ns=now, delivered_ns=now, width=8, height=8,
                         pixels_hex=("00ff00" if marker else "000000")*64),
                battery=dict(capture_ns=now, delivered_ns=now, voltage_mv=12000+remaining*4,
                             empty_mv=12000, full_mv=16000))


def health_at(position, stamp, **changes):
    health = _health(raw_frame(position=position, now=stamp))
    health["frame"].update(changes)
    return health


class MissionTests(unittest.TestCase):
    def actor(self, target=(1, 0, 0), **kwargs):
        return MissionBridge(goal_request(target), budget=Budget(1_000_000), **kwargs)

    def test_imports_full_mission_agent_power_and_composer(self):
        actor = self.actor()
        self.assertIsInstance(actor.agent, module("nexus0.drone3.agent").MissionAgent)
        self.assertIsInstance(actor.agent.guard, module("nexus0.power1.core").Guard)
        self.assertIsInstance(actor.agent.composer, module("nexus0.compose1_v3.controller").Composer)

    def test_goal_plan_power_action_return_and_stop(self):
        actor = self.actor()
        before = actor.agent.fingerprint()
        first = actor.decide(raw_frame(), sequence=0, now_ns=10_000_000_000)
        self.assertEqual((first["action"], first["prediction"]), (0, [1, 0, 0]))
        self.assertEqual(first["power"]["reason"], "continue")
        self.assertTrue(first["energy_check"]["allowed"])
        self.assertEqual(first["plan"][0], 0)
        back = actor.decide(raw_frame(now=10_100_000_000, position=(1, 0, 0), remaining=935, marker=True),
                            sequence=1, now_ns=10_100_000_000)
        self.assertEqual((back["action"], back["prediction"], back["return_reason"]),
                         (1, [0, 0, 0], "goal_reached"))
        stop = actor.decide(raw_frame(now=10_200_000_000, remaining=920), sequence=2, now_ns=10_200_000_000)
        self.assertEqual(stop["action"], 6)
        self.assertEqual(actor.agent.fingerprint(), before)
        self.assertEqual(actor.agent.composer.model.cam.destroyed, 0)
        self.assertEqual(actor.agent.composer.imagined_writes, 0)

    def test_goal_coordinate_alone_is_not_a_fact(self):
        actor = self.actor()
        response = actor.decide(raw_frame(position=(1, 0, 0)), sequence=0, now_ns=10_000_000_000)
        self.assertEqual(response["status"], "inspect_target")
        self.assertFalse(response["reached"])
        self.assertFalse(response["has_fact"])

    def test_reasoning_plan_is_used_but_never_a_cam_fact(self):
        actor = self.actor()
        before = actor.agent.fingerprint()
        plan = dict(schema=PLAN_SCHEMA, goal_id="mission", based_on_sequence=0,
                    start_cell=[0, 0, 0], actions=[2])
        response = actor.decide(raw_frame(), sequence=0, now_ns=10_000_000_000, plan=plan)
        self.assertEqual((response["action"], response["prediction"]), (2, [0, 1, 0]))
        self.assertEqual(response["plan_source"], "reasoning_hypothesis")
        self.assertEqual(actor.agent.fingerprint(), before)
        self.assertNotIn("search", actor.agent.composer.__dict__)

    def test_plan_cannot_authorize_unknown_or_mismatched_state(self):
        for actions, sequence, start in (([0], 2, [0, 0, 0]), ([True], 0, [0, 0, 0]),
                                         ([0], 0, [1, 0, 0]), ([0]*5, 0, [0, 0, 0])):
            actor = self.actor()
            plan = dict(schema=PLAN_SCHEMA, goal_id="mission", based_on_sequence=sequence,
                        start_cell=start, actions=actions)
            out = actor.decide(raw_frame(), sequence=0, now_ns=10_000_000_000, plan=plan)
            self.assertEqual(out["action"], 6)
            self.assertEqual(actor.agent.turn, 0)
        actor = self.actor()
        raw = raw_frame()
        raw["lidar"]["ranges_mm"] = [-1]*360
        plan = dict(schema=PLAN_SCHEMA, goal_id="mission", based_on_sequence=0, start_cell=[0, 0, 0], actions=[0])
        out = actor.decide(raw, sequence=0, now_ns=raw["now_ns"], plan=plan)
        self.assertEqual(out["action"], 6)

    def test_private_bad_and_stale_sensor_inputs_stop_before_agent(self):
        changes = [lambda r: r.update(world={"hidden": 1}),
                   lambda r: r["estimate"].update(speed_mm_s=True),
                   lambda r: r["lidar"].update(capture_ns=r["now_ns"]-250_000_001),
                   lambda r: r["depth"][0].update(delivered_ns=r["now_ns"]+1),
                   lambda r: r["rgb"].update(width=1000000),
                   lambda r: r["battery"].update(voltage_mv=65535),
                   lambda r: r["lidar"]["ranges_mm"].append(9000),
                   lambda r: r["rgb"].update(pixels_hex="gg"*192)]
        for mutate in changes:
            actor = self.actor()
            raw = raw_frame()
            mutate(raw)
            out = actor.decide(raw, sequence=0, now_ns=raw["now_ns"])
            self.assertEqual(out["action"], 6)
            self.assertEqual(actor.agent.turn, 0)
            self.assertIsNone(out["prediction"])
            self.assertEqual(module("nexus0.drone3.contract").intention(out["wsp"]), ("stop", 6))

    def test_raw_ttl_inclusive_and_never_refresh_capture(self):
        raw = raw_frame()
        original = deepcopy(raw)
        validate_raw(raw, raw["now_ns"]+250_000_000)
        self.assertEqual(raw, original)
        with self.assertRaises(ValueError):
            validate_raw(raw, raw["now_ns"]+250_000_001)

    def test_repeated_sequence_latches_stop(self):
        actor = self.actor()
        actor.decide(raw_frame(), sequence=0, now_ns=10_000_000_000)
        out = actor.decide(raw_frame(now=10_100_000_000), sequence=0, now_ns=10_100_000_000)
        self.assertEqual(out["action"], 6)
        again = actor.decide(raw_frame(now=10_200_000_000), sequence=1, now_ns=10_200_000_000)
        self.assertEqual(again["status"], out["status"])

    def test_low_energy_power_guard_prevents_outbound_mission(self):
        actor = self.actor((4, 0, 0))
        out = actor.decide(raw_frame(remaining=150), sequence=0, now_ns=10_000_000_000)
        self.assertEqual(out["action"], 6)
        self.assertEqual(out["power"]["reason"], "land_home")
        self.assertGreater(out["power"]["mission_required"], 150)

    def test_budget_exhaustion_precedes_decision(self):
        actor = self.actor()
        actor.budget.consume("test_spent", actor.budget.remaining)
        out = actor.decide(raw_frame(), sequence=0, now_ns=10_000_000_000)
        self.assertEqual((out["action"], out["status"]), (6, "budget_exhausted"))
        self.assertEqual(actor.agent.turn, 0)

    def test_controls_keep_full_power_and_safety_path(self):
        for mode in ("one_step", "conventional"):
            actor = self.actor(mode=mode)
            self.assertEqual(actor.agent.composer.mode, mode)
            out = actor.decide(raw_frame(), sequence=0, now_ns=10_000_000_000)
            self.assertEqual(out["action"], 0)
            self.assertTrue(out["energy_check"]["allowed"])
            if mode == "one_step":
                self.assertLessEqual(len(out["plan"]), 1)

    def test_ack_does_not_mean_arrival_and_duplicate_samples_do_not_count(self):
        actor = self.actor()
        raw = raw_frame()
        out = actor.decide(raw, sequence=0, now_ns=raw["now_ns"])
        executor = MissionExecutor(actor.power_model, budget=Budget(100000))
        self.assertTrue(executor.submit(out, raw, _health(raw))["allowed"])
        stamp = raw["now_ns"]+10_000_000
        self.assertTrue(executor.acknowledge(dict(system=1, component=1, command=192, result=0, received_ns=stamp), stamp))
        self.assertEqual(executor.supervisor.gateway.state, "executing")
        h = health_at((1, 0, 0), stamp+1)
        for _ in range(5):
            self.assertEqual(executor.observe(h), "executing")
        self.assertEqual(executor.supervisor.gateway.samples, 1)
        self.assertEqual(executor.observe(health_at((1, 0, 0), stamp+2)), "executing")
        self.assertEqual(executor.observe(health_at((1, 0, 0), stamp+3)), "complete")

    def test_gateway_rejects_hallucinated_prediction_and_stale_source_binding(self):
        for change in (lambda r: r.update(prediction=[0, 1, 0]),
                       lambda r: r.update(raw_sha256="0"*64)):
            actor = self.actor()
            raw = raw_frame()
            out = actor.decide(raw, sequence=0, now_ns=raw["now_ns"])
            change(out)
            executor = MissionExecutor(actor.power_model, budget=Budget(100000))
            self.assertFalse(executor.submit(out, raw, _health(raw))["allowed"])
            self.assertTrue(executor.supervisor.tripped)

    def test_fresh_raw_unknown_target_cannot_reuse_cached_admission(self):
        actor = self.actor()
        raw = raw_frame()
        out = actor.decide(raw, sequence=0, now_ns=raw["now_ns"])
        raw["lidar"]["ranges_mm"] = [-1]*360
        out["raw_sha256"] = digest(raw)
        executor = MissionExecutor(actor.power_model, budget=Budget(100000))
        decision = executor.submit(out, raw, _health(raw))
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["reason"], "epistemic_block")

    def test_safe_sensor_and_authority_loss_are_latched(self):
        for fault in ("sensor", "authority", "worker"):
            _, power = synthetic_models()
            executor = MissionExecutor(power, budget=Budget(100000))
            raw = raw_frame()
            health = _health(raw)
            if fault == "sensor":
                health["sensor_ns"] -= 250_000_001
            elif fault == "authority":
                health["frame"]["authority"] = False
            else:
                health["worker_alive"] = False
            self.assertEqual(executor.observe(health), "fault")
            self.assertEqual(executor.observe(_health(raw)), "fault")

    def test_goal_cannot_disable_return_marker_or_allow_hardware_coordinates(self):
        for change in ({"target_cell": [5, 0, 0]}, {"target_cell": [0, 0, 1]},
                       {"return_home": False}, {"require_marker": False}, {"target_cell": [True, 0, 0]},
                       {"max_decisions": 65}, {"command": "arm"}):
            value = goal_request((1, 0, 0))
            value.update(change)
            with self.assertRaises(ValueError):
                validate_goal(value)

    def test_journal_copies_actual_decisions_and_cannot_mutate_policy(self):
        class HostileObserver:
            def write(self, **event):
                event.clear()
        with_journal = self.actor(journal=HostileObserver())
        without = self.actor()
        raw = raw_frame()
        self.assertEqual(with_journal.decide(raw, sequence=0, now_ns=raw["now_ns"]),
                         without.decide(raw, sequence=0, now_ns=raw["now_ns"]))

    def test_software_denominator_costs_and_exact_replay_are_not_sitl(self):
        config = dict(seed=51601, cases=2, budget=1000000, max_decisions=4)
        first = run_benchmark(config)
        second = run_benchmark(config)
        self.assertEqual(first, second)
        self.assertEqual(len(first["rows"]), 6)
        self.assertFalse(first["gates"]["sitl_valid"])
        self.assertFalse(first["gates"]["condition_coverage"])
        self.assertEqual(sum(r["cost"] for r in first["rows"]), first["costs"]["used"])
        self.assertTrue(all(r["evidence"] == "software_fixture" for r in first["rows"]))

    def test_zero_budget_and_invalid_confirmation_do_not_hide_failures(self):
        report = run_benchmark(dict(cases=1, budget=0))
        self.assertEqual(len(report["rows"]), 3)
        self.assertTrue(all(r["budget_exhausted"] and not r["success"] for r in report["rows"]))
        with self.assertRaises(ValueError):
            run_benchmark(dict(phase="confirmation", seed=51601))


class MissionAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Short new software fixture; its negative completion result is honest.
        cls.report = run_benchmark(dict(seed=51601, cases=1, budget=1000000, max_decisions=2))

    def test_explicit_auditor_reconstructs_and_replays_in_a_new_process(self):
        result = audit_report(self.report)
        self.assertTrue(result["valid"], result["findings"])
        self.assertTrue(result["replay"]["exact"])
        self.assertNotEqual(result["replay"]["process_id"], os.getpid())
        self.assertFalse(result["gates"]["sitl_valid"])
        self.assertFalse(result["gates"]["software_correctness"])

    def test_external_judge_rejects_a_claim_even_if_fake_replay_agrees(self):
        report = deepcopy(self.report)
        report["rows"][0]["success"] = True
        # Deliberately not real replay evidence: the external consequence judge
        # must refuse even an agreeing producer/mocked replay.
        fake = SimpleNamespace(returncode=0, stderr="", stdout=json.dumps(dict(pid=os.getpid()+10000, report=report)))
        with patch("echo5.mission.subprocess.run", return_value=fake):
            result = audit_report(report)
        self.assertFalse(result["valid"])
        self.assertTrue(any("claimed_metric:success" in reason for reason in result["findings"]))

    def test_external_world_rejects_fabricated_motion_without_running_the_actor(self):
        row = deepcopy(self.report["rows"][0])
        step = next(event for event in row["trace"] if event["kind"] == "mission_software_step")
        step["consequence"]["after"] = [99, 99, 0]
        with self.assertRaisesRegex(ValueError, "external_action_consequence"):
            _audit_episode(row, self.report["config"], 0, "echo32")

    def test_reduced_denominator_and_invented_reserve_fail(self):
        report = deepcopy(self.report)
        report["rows"].pop()
        with patch("echo5.mission.subprocess.run") as process:
            result = audit_report(report)
        self.assertFalse(result["valid"])
        process.assert_not_called()
        row = deepcopy(self.report["rows"][0])
        row["final_reserve"] += 1
        with self.assertRaisesRegex(ValueError, "claimed_metric:final_reserve"):
            _audit_episode(row, self.report["config"], 0, "echo32")

    def test_zero_budget_is_an_auditable_negative_not_a_missing_case(self):
        report = run_benchmark(dict(cases=1, budget=0))
        for index, mode in enumerate(("echo32", "one_step", "conventional")):
            row = _audit_episode(report["rows"][index], report["config"], 0, mode)
            self.assertFalse(row["success"])
            self.assertTrue(row["budget_exhausted"])


class SITLContractTests(unittest.TestCase):
    def test_launch_is_local_isolated_bounded_and_no_mutable_image_tag(self):
        root = Path("/tmp/echo5-case")
        args = sitl.launch_argv("/usr/bin/podman", root, {"timeouts": {"episode_s": 100}}, "a"*32)
        self.assertIn("--network=none", args)
        self.assertIn("--read-only", args)
        self.assertIn("--pull=never", args)
        self.assertIn("--cap-drop=ALL", args)
        self.assertIn(sitl.IMAGE_ID, args)
        self.assertIn("--timeout", args)
        self.assertNotIn("--privileged", args)
        self.assertNotIn("--network=host", args)
        self.assertFalse(any(a.startswith(("--device", "--publish")) for a in args))

    def test_no_host_or_external_transport_override(self):
        for key in ("host", "port", "device", "backend", "command", "image_id"):
            with self.assertRaises(ValueError):
                sitl._config(dict(output=str(sitl.ROOT/"artifacts/test-new"), **{key: "fake"}))
        with self.assertRaises(ValueError):
            sitl._config(dict(output="/tmp/not-echo5"))

    def test_read_only_availability_never_launches_a_container(self):
        calls = []
        class Result:
            returncode = 0
            stderr = ""
            stdout = sitl.IMAGE_ID+"\n"
        def read(argv, **kwargs):
            calls.append(argv)
            self.assertNotIn("run", argv)
            self.assertNotIn("build", argv)
            self.assertNotIn("pull", argv)
            return Result()
        with patch.object(sitl.shutil, "which", return_value="/usr/bin/podman"), patch.object(sitl, "_command", side_effect=read):
            result = sitl.availability()
        self.assertFalse(result["runtime_probed"])
        self.assertTrue(calls)

    def test_fake_unit_fixture_cannot_be_a_real_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = dict(agent=dict(goal=goal_request((1, 0, 0))), condition="static", mode="echo32",
                          runner=dict(seed=1), nonce="a"*32, imported_sources={})
            (root/"configuration.json").write_text(json.dumps(config))
            (root/"process-receipt.json").write_text(json.dumps(dict(
                schema="echo5.sitl.process.v1", evidence="software_fixture", nonce="a"*32,
                external_pid=None, launcher_pid=1, returncode=0, teardown=True, finished_ns=2, started_ns=1)))
            row = sitl.evaluate_episode(root)
            self.assertFalse(row["valid_receipt"])
            self.assertFalse(row["success"])
            self.assertIn("external_process_receipt", row["findings"])

    def test_missing_mission_process_output_cannot_be_green(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"configuration.json").write_text(json.dumps(dict(
                agent=dict(goal=goal_request((1, 0, 0))), condition="static", mode="echo32", runner=dict(seed=1))))
            row = sitl.evaluate_episode(root)
            self.assertFalse(row["valid_receipt"])
            self.assertFalse(row["success"])
            self.assertIsNone(row["collisions"])

    def test_swept_collision_catches_a_wall_between_safe_endpoints(self):
        self.assertEqual(sitl._segment_box_distance((-3000, 0), (3000, 0), (-1500, -1500), (1500, 1500)), 0)
        self.assertEqual(sitl._segment_box_distance((-3000, 3000), (3000, 3000), (-1500, -1500), (1500, 1500)), 1500)

    def test_contract_coverage_and_external_audit_cannot_be_skipped(self):
        rows = [dict(mode=mode, case_id="one", condition="static", success=True, valid_receipt=True,
                     safety_success=True, returned_home=True, goal_observed=True) for mode in ("echo32", "one_step", "conventional")]
        gates = sitl._campaign_gates(rows, dict(cases=1))
        self.assertTrue(gates["real_receipts"])
        self.assertFalse(gates["condition_coverage"])
        self.assertFalse(gates["sitl_valid"])
        self.assertFalse(gates["independent_audit"])


class NewMissionReasoningTests(unittest.TestCase):
    def actor(self, mode="echo32"):
        return MissionBridge(goal_request((1, 0, 0)), budget=Budget(1_000_000), mode=mode)

    def test_normal_path_calls_shared_new_planner_without_an_external_plan(self):
        actor = self.actor()
        raw = raw_frame()
        old = module("nexus0.compose1_v3.controller").Composer
        with patch.object(actor.reasoner.planner, "plan", wraps=actor.reasoner.planner.plan) as new_plan:
            with patch.object(old, "search", side_effect=AssertionError("legacy search was used")):
                out = actor.decide(raw, sequence=0, now_ns=raw["now_ns"])
        self.assertGreater(new_plan.call_count, 0)
        self.assertEqual(out["plan_source"], "echo5_reasoner")
        self.assertEqual(out["reasoning"]["proposal"]["engine"], ENGINE)
        self.assertTrue(out["reasoning"]["applied"])
        self.assertEqual(out["prediction"], [1, 0, 0])
        frame = module("nexus0.compose1_v3.perception").project({k:v for k,v in raw.items() if k != "battery"}, 240)
        self.assertEqual(audit_reasoning(frame, out, actor.goal, "echo32"), dict(called=1, applied=1))

    def test_conventional_control_never_calls_new_planner(self):
        actor = self.actor("conventional")
        with patch.object(actor.reasoner.planner, "plan", side_effect=AssertionError("control contamination")):
            out = actor.decide(raw_frame(), sequence=0, now_ns=10_000_000_000)
        self.assertEqual(out["plan_source"], "compose")
        self.assertFalse(out["reasoning"]["called"])

    def test_normal_path_projects_once_inside_full_inherited_agent(self):
        actor = self.actor()
        legacy = module("nexus0.drone3.agent")
        perception = module("nexus0.compose1_v3.perception")
        with patch.object(legacy, "project", wraps=legacy.project) as projected:
            with patch.object(perception, "project", side_effect=AssertionError("duplicate bridge projection")):
                out = actor.decide(raw_frame(), sequence=0, now_ns=10_000_000_000)
        self.assertEqual(projected.call_count, 1)
        self.assertTrue(out["reasoning"]["applied"])
        self.assertIsNone(actor.agent.plan_hook)
        self.assertNotIn("search", actor.agent.composer.__dict__)

    def test_power_land_preempts_new_reasoning(self):
        actor = MissionBridge(goal_request((4, 0, 0)), budget=Budget(1_000_000))
        with patch.object(actor.reasoner.planner, "plan", side_effect=AssertionError("POWER bypassed")):
            out = actor.decide(raw_frame(remaining=150), sequence=0, now_ns=10_000_000_000)
        self.assertEqual(out["power"]["reason"], "land_home")
        self.assertFalse(out["reasoning"]["called"])
        self.assertFalse(out["reasoning"]["applied"])

    def test_prior_is_never_fabricated_acquisition_evidence(self):
        planner = HypothesisAgent()
        before = planner.checkpoint()
        observation = dict(schema="echo5.interaction.observation.v1", width=3, height=3,
            walls=[], position=[1, 1], goal=[1, 2], actions=[0, 1, 2, 3], tick=0)
        plan = planner.plan(observation, budget=Budget(10000), max_depth=4, effect_prior=EFFECT_PRIOR)
        self.assertEqual(plan["actions"], [0])
        self.assertEqual(plan["edge_sources"], ["declared_prior"])
        self.assertEqual(planner.checkpoint(), before)
        self.assertEqual(planner.evidence, [])
        self.assertEqual(planner.plan(observation, budget=Budget(10000))["reason"], "no_supported_path")

    @staticmethod
    def scene():
        stamp = 10_000_000_000
        packet = module("nexus0.fusion1.core").packet
        cells = []
        for point, value in (([1,0,0],1), ([0,1,0],0), ([1,1,0],0), ([2,1,0],0), ([2,0,0],0)):
            sources = [dict(source=s, wsp=packet(value, 40).hex(), capture_ns=stamp,
                            delivered_ns=stamp, raw_sha256="0"*64) for s in ("depth", "lidar")]
            cells.append(dict(position=point, sources=sources))
        return dict(physical=True, now_ns=stamp, odometry=[0,0,0], energy=240,
                    station_observed=False, cells=cells)

    def test_projected_obstacle_requires_real_bounded_detour(self):
        actor = MissionReasoner()
        plan = actor.propose(self.scene(), goal_request((2,0,0)), sequence=0,
                             raw_sha256="1"*64, budget=Budget(100000), horizon=4)
        self.assertEqual(plan["actions"], [2,0,0,3])
        self.assertLessEqual(len(plan["targets"]), 8)
        self.assertLessEqual(plan["work"]["used"], 30000)
        self.assertTrue(all([1,0,0] not in c["positions"] for c in plan["candidates"]))

    def test_unknown_or_conflicting_projection_never_becomes_a_path(self):
        frame = self.scene()
        frame["cells"] = []
        plan = MissionReasoner().propose(frame, goal_request((2,0,0)), sequence=0,
                                        raw_sha256="1"*64, budget=Budget(100000))
        self.assertEqual(plan["actions"], [])
        frame = self.scene()
        frame["cells"][1]["sources"][1]["wsp"] = module("nexus0.fusion1.core").packet(1, 40).hex()
        plan = MissionReasoner().propose(frame, goal_request((2,0,0)), sequence=0,
                                        raw_sha256="1"*64, budget=Budget(100000))
        self.assertEqual(plan["actions"], [])

    def test_skipped_stale_proposal_is_not_execution_or_learning(self):
        actor = self.actor()
        out = actor.decide(raw_frame(), sequence=0, now_ns=10_000_000_000)
        visits = deepcopy(actor.reasoner.visits)
        receipt = dict(schema=OUTCOME_SCHEMA, sequence=out["sequence"], raw_sha256=out["raw_sha256"],
            wsp=out["wsp"], prediction=out["prediction"], disposition="not_executed",
            command_seq=None, ack=None, samples=0, estimate=None, reason="age")
        actor.observe_consequence(receipt)
        self.assertEqual(actor.reasoner.visits, visits)
        self.assertEqual(actor.reasoner.planner.evidence, [])
        with self.assertRaises(ValueError):
            actor.observe_consequence(receipt)

    def test_ack_only_cannot_be_a_confirmed_consequence(self):
        actor = self.actor()
        out = actor.decide(raw_frame(), sequence=0, now_ns=10_000_000_000)
        receipt = dict(schema=OUTCOME_SCHEMA, sequence=0, raw_sha256=out["raw_sha256"],
            wsp=out["wsp"], prediction=out["prediction"], disposition="arrived", command_seq=0,
            ack=dict(system=1, component=1, command=192, result=0, received_ns=10_010_000_000),
            samples=1, estimate=dict(position_mm=[3000,0,2500], received_ns=10_030_000_000, speed_mm_s=0),
            reason="gateway_complete")
        with self.assertRaises(ValueError):
            actor.observe_consequence(receipt)
        receipt["samples"] = 3
        actor.observe_consequence(receipt)
        self.assertEqual(actor.reasoner.visits[(1,0,0)], 1)

    def test_independent_auditor_rejects_forged_new_reasoning_attribution(self):
        report = run_benchmark(dict(seed=51601, cases=1, budget=1000000, max_decisions=1))
        row = deepcopy(report["rows"][0])
        event = next(e for e in row["trace"] if e["kind"] == "mission_plan")
        event["response"]["reasoning"] = dict(called=False, applied=False, proposal=None)
        event["response"]["plan_source"] = "compose"
        with self.assertRaisesRegex(ValueError, "new_reasoner_bypassed"):
            _audit_episode(row, report["config"], 0, "echo32")

    def test_independent_auditor_rejects_imagined_as_executed(self):
        report = run_benchmark(dict(seed=51601, cases=1, budget=1000000, max_decisions=1))
        row = deepcopy(report["rows"][0])
        event = next(e for e in row["trace"] if e["kind"] == "mission_execution_outcome")
        event["outcome"]["estimate"]["position_mm"][0] += 1000
        with self.assertRaisesRegex(ValueError, "outcome_arrival_tolerance"):
            _audit_episode(row, report["config"], 0, "echo32")

    def test_reserved_confirmation_intervals_reject_any_intersection(self):
        for seed, cases in ((61703,1), (61714,1), (61702,2), (61608,96)):
            with self.subTest(domain="mission", seed=seed, cases=cases):
                with self.assertRaisesRegex(ValueError, "reserved_confirmation_seed_interval"):
                    normalize_config(dict(seed=seed, cases=cases))
        for seed,cases in ((61607,96), (61715,96)):
            self.assertEqual(normalize_config(dict(seed=seed,cases=cases))["seed"], seed)
        output = str(sitl.ROOT/"artifacts/unexecuted-test")
        for seed,cases in ((861703,1), (861708,1), (861702,2), (861692,12)):
            with self.subTest(domain="sitl", seed=seed, cases=cases):
                with self.assertRaisesRegex(ValueError, "reserved_confirmation_seed_interval"):
                    sitl._config(dict(output=output, seed=seed, cases=cases))
        for seed,cases in ((861691,12), (861709,12)):
            self.assertEqual(sitl._config(dict(output=output,seed=seed,cases=cases))["seed"], seed)
        self.assertEqual(normalize_config(dict(phase="confirmation",seed=61703))["cases"],12)
        confirmation_seed = json.loads(sitl.CONTRACT.read_text())['sitl']['confirmation_seed']
        self.assertEqual(sitl._config(dict(output=output,phase="confirmation",seed=confirmation_seed))["cases"],6)

    def test_public_sitl_outcome_requires_send_ack_and_arrival(self):
        actor = self.actor()
        out = actor.decide(raw_frame(), sequence=0, now_ns=10_000_000_000)
        proposal = dict(kind="proposal",epoch=0,now_ns=10_000_000_000,mono_ns=10_000_000_000,
                        request=dict(seq=1,wsp=out["wsp"],prediction=out["prediction"],published_ns=out["observation_ns"]),
                        decision=dict(allowed=True,target_mm=[3000,0,2500],yaw_mrad=1571))
        ack = dict(system=1,component=1,command=192,result=0,received_ns=10_010_000_000)
        events = [proposal, dict(kind="send",seq=1,target_mm=[3000,0,2500],yaw_mrad=1571,
                                now_ns=10_001_000_000,mono_ns=10_001_000_000),
            dict(kind="ack",epoch=0,accepted=True,ack=ack,now_ns=10_010_000_000,mono_ns=10_010_000_000)]
        for n in (1,2,3):
            stamp = 10_010_000_000+n*10_000_000
            events.append(dict(kind="check",ok=True,state="complete" if n == 3 else "executing",samples=n,
                now_ns=stamp,mono_ns=stamp,health=dict(frame=dict(position_mm=[3000,0,2500],
                received_ns=stamp,speed_mm_s=0,armed=True,authority=True,failsafe=False))))
        events.append(dict(kind="arrival",epoch=0,target_mm=[3000,0,2500],samples=3,
                           now_ns=10_050_000_000,mono_ns=10_050_000_000))
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)/"trace.jsonl"
            path.write_text("".join(json.dumps(e)+"\n" for e in events))
            result = sitl._PublicOutcomes(path).take(0,out)
            self.assertEqual(result["disposition"],"arrived")
            path.write_text("".join(json.dumps(e)+"\n" for e in events if e["kind"] != "ack"))
            with self.assertRaisesRegex(ValueError,"missing_public_execution_outcome"):
                sitl._PublicOutcomes(path).take(0,out)


if __name__ == "__main__":
    unittest.main()
