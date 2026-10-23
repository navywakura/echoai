"""Fresh CPU integration cases; none load a historical campaign or exam."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from echo5.robotics import RoboticsBridge, observation_from_scan, run_benchmark
from echo5.budget import Budget, BudgetExceeded
from echo5.legacy import module


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def reseal(observation):
    observation["sha256"] = digest({k: v for k, v in observation.items() if k != "sha256"})
    return observation


def frame(*, now=1_000_000_000, position=(0, 0, 0), station=False, energy=240):
    packet = module("nexus0.fusion1.core").packet
    return dict(now_ns=now, odometry=list(position), station_observed=station,
                energy=energy, cells=[dict(position=list(p), depth=packet(0, 40).hex(),
                                          lidar=packet(0, 40).hex())
                                      for p in ((0, 0, 0), (1, 0, 0))])


class RoboticsTests(unittest.TestCase):
    def bridge(self, **kwargs):
        return RoboticsBridge([1, 0, 0], budget=Budget(100_000), **kwargs)

    def test_real_controller_predicts_executes_and_requires_observed_station(self):
        actor = self.bridge()
        self.assertIsInstance(actor.controller, module("nexus0.compose1_v3.controller").Composer)
        before = actor.controller.model.fingerprint()
        first = actor.decide(observation_from_scan(frame(), sequence=0), now_ns=1_000_000_000)
        self.assertEqual((first["action"], first["prediction"], first["status"]),
                         (0, [1, 0, 0], "moving"))
        self.assertEqual(module("nexus0.drone3.contract").intention(first["wsp"]), ("move", 0))
        self.assertEqual(len(bytes.fromhex(first["gate"]["belief"])), 16)
        second = actor.decide(observation_from_scan(frame(now=1_025_000_000,
                              position=(1, 0, 0), station=True, energy=236), sequence=1),
                              now_ns=1_025_000_000)
        self.assertEqual((second["action"], second["status"]), (6, "reached"))
        self.assertEqual(second["prediction_errors"], 0)
        self.assertEqual(actor.controller.model.fingerprint(), before)
        self.assertEqual(actor.controller.model.cam.destroyed, 0)

    def test_goal_coordinate_without_marker_does_not_certify_arrival(self):
        actor = self.bridge()
        response = actor.decide(observation_from_scan(frame(position=(1, 0, 0)), sequence=0),
                                now_ns=1_000_000_000)
        self.assertNotEqual(response["status"], "reached")

    def test_fusion_blocks_single_family_conflicting_and_skewed_evidence(self):
        fusion = module("nexus0.fusion1.core")
        for kind in ("camera_only", "conflict", "skew"):
            with self.subTest(kind=kind):
                obs = observation_from_scan(frame(), sequence=0)
                for cell in obs["cells"]:
                    for record in cell["sources"]:
                        if record["source"] == "lidar":
                            if kind == "camera_only":
                                record["source"] = "rgb"
                            elif kind == "conflict":
                                record["wsp"] = fusion.packet(1, 40).hex()
                            else:
                                record["capture_ns"] -= 150_000_000
                        record["raw_sha256"] = digest(dict(position=cell["position"],
                            **{k: v for k, v in record.items() if k != "raw_sha256"}))
                response = self.bridge().decide(reseal(obs), now_ns=1_000_000_000)
                self.assertEqual(response["action"], 6)
                self.assertNotEqual(response["status"], "rejected")

    def test_malformed_provenance_private_fields_and_stale_input_stop_before_controller(self):
        changes = [
            ("private", lambda o: o.update(world={"secret": "map"})),
            ("body type", lambda o: o.update(energy=True)),
            ("body hash", lambda o: o.update(sha256="0" * 64)),
            ("source hash", lambda o: o["cells"][0]["sources"][0].update(raw_sha256="0" * 64)),
            ("unknown source", lambda o: o["cells"][0]["sources"][0].update(source="oracle")),
            ("bad wsp", lambda o: o["cells"][0]["sources"][0].update(wsp="00")),
            ("stale", lambda o: o.update(capture_ns=0)),
            ("future", lambda o: o.update(delivered_ns=1_000_000_001)),
            ("bounds", lambda o: o.update(odometry=[10**20, 0, 0])),
            ("duplicate cell", lambda o: o["cells"].append(copy.deepcopy(o["cells"][0]))),
            ("oversize", lambda o: o.update(cells=[o["cells"][0]] * 257)),
        ]
        for name, change in changes:
            with self.subTest(name=name):
                actor = self.bridge()
                obs = observation_from_scan(frame(), sequence=0)
                change(obs)
                if name != "body hash":
                    reseal(obs)
                result = actor.decide(obs, now_ns=1_000_000_000)
                self.assertEqual((result["status"], result["action"]), ("rejected", 6))
                self.assertEqual(actor.controller.turns, 0)
                self.assertFalse(actor.controller.cells)

    def test_replayed_frame_and_expired_sensor_are_not_refreshed(self):
        actor = self.bridge()
        obs = observation_from_scan(frame(), sequence=0)
        actor.decide(obs, now_ns=1_000_000_000)
        result = actor.decide(obs, now_ns=1_025_000_000)
        self.assertEqual((result["action"], result["status"]), (6, "rejected"))
        fresh = observation_from_scan(frame(now=1_300_000_000), sequence=1)
        fresh["cells"] = copy.deepcopy(obs["cells"])
        result = actor.decide(reseal(fresh), now_ns=1_300_000_000)
        self.assertEqual((result["action"], result["status"]), (6, "rejected"))
        self.assertEqual(actor.controller.turns, 1)

    def test_budget_exhaustion_never_runs_controller(self):
        actor = self.bridge()
        actor.budget.consume("test_spent", actor.budget.limit - actor.budget.used)
        result = actor.decide(observation_from_scan(frame(), sequence=0), now_ns=1_000_000_000)
        self.assertEqual((result["status"], result["action"]), ("budget_exhausted", 6))
        self.assertEqual(actor.controller.turns, 0)
        self.assertEqual(actor.budget.used, actor.budget.limit)
        with self.assertRaises(BudgetExceeded):
            RoboticsBridge([1, 0, 0], budget=Budget(0))

    def test_prediction_error_is_measured_from_next_public_odometry(self):
        actor = self.bridge()
        actor.decide(observation_from_scan(frame(), sequence=0), now_ns=1_000_000_000)
        result = actor.decide(observation_from_scan(frame(now=1_025_000_000), sequence=1),
                              now_ns=1_025_000_000)
        self.assertEqual(result["prediction_errors"], 1)
        self.assertGreaterEqual(result["plan_invalidations"], 1)

    def test_low_energy_retains_controller_reserve_stop(self):
        actor = self.bridge()
        result = actor.decide(observation_from_scan(frame(energy=10), sequence=0),
                              now_ns=1_000_000_000)
        self.assertEqual((result["action"], result["status"]), (6, "abandoned_at_home"))

    def test_gate_vetoes_cached_free_target_missing_from_current_observation(self):
        actor = self.bridge()
        actor.decide(observation_from_scan(frame(), sequence=0), now_ns=1_000_000_000)
        scan = frame(now=1_025_000_000)
        scan["cells"] = scan["cells"][:1]
        result = actor.decide(observation_from_scan(scan, sequence=1), now_ns=1_025_000_000)
        self.assertEqual((result["action"], result["status"]), (6, "vetoed"))
        self.assertEqual(result["prediction"], [0, 0, 0])
        self.assertEqual(result["proposed_prediction"], [1, 0, 0])

    def test_wrong_wsp_predicate_is_not_normalized_into_free_barrier_evidence(self):
        actor = self.bridge()
        obs = observation_from_scan(frame(), sequence=0)
        cell = obs["cells"][1]
        record = cell["sources"][0]
        record["wsp"] = module("nexus0.fusion1.core").packet(0, 40, predicate=2).hex()
        record["raw_sha256"] = digest(dict(position=cell["position"],
            **{k: v for k, v in record.items() if k != "raw_sha256"}))
        result = actor.decide(reseal(obs), now_ns=1_000_000_000)
        self.assertEqual((result["action"], result["status"]), (6, "rejected"))
        self.assertEqual(actor.controller.turns, 0)

    def test_receiver_clock_enforces_exact_freshness_boundary(self):
        obs = observation_from_scan(frame(), sequence=0)
        accepted = self.bridge().decide(obs, now_ns=1_250_000_000)
        rejected = self.bridge().decide(obs, now_ns=1_250_000_001)
        self.assertEqual(accepted["action"], 0)
        self.assertEqual((rejected["action"], rejected["status"]), (6, "rejected"))

    def test_turn_limit_is_a_fail_closed_mission_bound(self):
        actor = self.bridge()
        for index in range(64):
            now = 1_000_000_000 + index * 25_000_000
            actor.decide(observation_from_scan(frame(now=now), sequence=index), now_ns=now)
        result = actor.decide(observation_from_scan(frame(now=3_000_000_000), sequence=64),
                              now_ns=3_000_000_000)
        self.assertEqual((result["action"], result["status"]), (6, "rejected"))
        self.assertEqual(actor.controller.turns, 64)

    def test_trace_uses_existing_recorder_without_changing_decisions(self):
        from echo5.trace import Recorder, verify_journal
        obs = observation_from_scan(frame(), sequence=0)
        expected = self.bridge().decide(obs, now_ns=1_000_000_000)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "robotics.jsonl"
            with Recorder(path) as recorder:
                result = self.bridge(journal=recorder).decide(obs, now_ns=1_000_000_000)
            self.assertEqual(result, expected)
            self.assertEqual(verify_journal(path)["events"], 2)
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(rows[0]["observation"], obs)
            self.assertEqual(rows[1]["response"]["action"], 0)

    def test_integer_benchmark_budget_is_per_case_per_mode(self):
        report = run_benchmark(seed=7, cases=1, budget=100)
        self.assertEqual(report["costs"]["per_case_per_mode_limit"], 100)
        self.assertLessEqual(report["costs"]["used"], 300)
        for rows in [report["cases"], *(r["cases"] for r in report["controls"].values())]:
            self.assertEqual(len(rows), 1)
            self.assertGreater(rows[0]["cost"], 50)

    def test_shared_ledger_is_charged_before_observer_sees_action(self):
        budget = Budget(6000)
        used_at_observation = []

        class Observer:
            def write(self, **event):
                if event["kind"] == "robotics_observation":
                    used_at_observation.append(budget.used)

        run_benchmark(seed=7, cases=1, budget=budget, journal=Observer())
        self.assertTrue(used_at_observation)
        self.assertGreater(used_at_observation[0], 0)

    def test_benchmark_reuses_simulation_and_reports_control_denominators(self):
        report = run_benchmark(seed=20261010, cases=4, budget=200_000)
        json.dumps(report, allow_nan=False)
        self.assertEqual(report["denominator"], 4)
        self.assertEqual(report["simulator"], "nexus0.compose1_v3.space.Space")
        self.assertFalse(report["sitl_executed"])
        self.assertGreater(report["successes"], 0)
        self.assertEqual(report["collisions"], 0)
        self.assertEqual(report["reserve_violations"], 0)
        self.assertEqual(set(report["controls"]), {"one_step", "conventional"})
        for control in report["controls"].values():
            self.assertEqual(control["denominator"], 4)
        for rows in [report["cases"], *(r["cases"] for r in report["controls"].values())]:
            for row in rows:
                arrived = (row["status"] == "reached" and row["final_position"] == row["goal"]
                           and row["station_observed"] is True and row["collisions"] == 0
                           and row["reserve_violations"] == 0)
                self.assertEqual(row["success"], arrived)
                self.assertEqual(sum(row["costs"].values()), row["cost"])
                self.assertLessEqual(row["cost"], row["budget_limit"])
        self.assertGreater(report["costs"]["used"], 0)
        self.assertEqual(sum(report["costs"]["counts"].values()), report["costs"]["used"])
        self.assertTrue(all(r["model_unchanged"] for r in report["cases"]))

    def test_zero_benchmark_budget_keeps_requested_denominators(self):
        report = run_benchmark(seed=1, cases=3, budget=0)
        self.assertEqual((report["successes"], report["denominator"]), (0, 3))
        self.assertEqual(report["budget_exhausted"], 3)
        self.assertEqual(report["costs"]["used"], 0)
        self.assertEqual(len(report["cases"]), 3)
        for row in report["cases"]:
            self.assertIsNone(row["final_position"])
            self.assertIsNone(row["goal"])
            self.assertIsNone(row["station_observed"])
            self.assertIsNone(row["model_unchanged"])

    def test_clean_restart_is_deterministic_and_does_not_load_campaigns(self):
        root = Path(__file__).resolve().parents[1]
        code = """import json, sys
sys.dont_write_bytecode = True
sys.path.insert(0, sys.argv[1])
from echo5.robotics import run_benchmark
r = run_benchmark(seed=20261010, cases=4, budget=200000)
print(json.dumps({'report': r, 'campaigns': sorted(n for n in sys.modules
    if any(s in n for s in ('campaign', 's6b24', 'echo_discord', 'exam')))}, sort_keys=True))
"""
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        first, second = [subprocess.check_output([sys.executable, "-I", "-B", "-c", code,
                          str(root / "src")], cwd="/tmp", env=env, text=True, timeout=60)
                         for _ in range(2)]
        self.assertEqual(json.loads(first), json.loads(second))
        self.assertEqual(json.loads(first)["campaigns"], [])


if __name__ == "__main__":
    unittest.main()
