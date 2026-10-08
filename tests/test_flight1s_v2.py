#!/usr/bin/env python3
"""FLIGHT-1S v2 unit bank: the repair, the rules, and v1 left alone.

No PX4 and no Gazebo here. The flight itself is v1's and is tested by
the v1 banks; what this file checks is the thing v2 actually changed —
that one number became three verdicts that cannot pay for each other,
that the numbers behind them come from rules fixed in advance, and that
none of it disturbed the red result it repairs.

The synthetic episodes are labelled fixtures. They never reach a report.
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from echoai.nexus0.sim3.canon import Sim3Error, loads_strict, sha256_bytes
from echoai.nexus0.flight1s import protocol as v1proto
from echoai.nexus0.flight1s.runtime import code_inventory as v1_code_inventory
from echoai.nexus0.flight1s.session import Episode
from echoai.nexus0.flight1s.v2 import (
    V1_CODE_SHA256,
    V1_PROTOCOL_SHA256,
    V1_REPORT_SHA256,
)
from echoai.nexus0.flight1s.v2 import calibrate, evaluate as v2eval
from echoai.nexus0.flight1s.v2 import mutants as v2mut
from echoai.nexus0.flight1s.v2 import protocol as protomod
from echoai.nexus0.flight1s.v2 import runtime as v2rt

ECHOAI = ROOT / "echoai"
V1_PROTOCOL = ECHOAI / "docs" / "examples" / "flight1s" / "protocol.json"
V1_REPORT = ECHOAI / "lab" / "echo3_flight1s_report.json"
V2_SCHEMA = (ECHOAI / "docs" / "schemas" / "flight1s-v2"
             / "flight1s-protocol-v2.schema.json")


class TestV1Untouched(unittest.TestCase):
    """The whole point: v2 must not move the evidence it repairs."""

    def test_v1_code_inventory_is_byte_identical(self) -> None:
        entries, sha = v1_code_inventory()
        self.assertEqual(sha, V1_CODE_SHA256)
        self.assertEqual(len(entries), 15)

    def test_v2_lives_outside_the_v1_glob(self) -> None:
        paths = {e["path"] for e in v1_code_inventory()[0]}
        self.assertFalse(any("/v2/" in p for p in paths), sorted(paths))
        self.assertFalse(any("flight1s-v2" in p for p in paths), sorted(paths))

    def test_v1_protocol_bytes_are_unchanged(self) -> None:
        self.assertEqual(sha256_bytes(V1_PROTOCOL.read_bytes()),
                         V1_PROTOCOL_SHA256)

    @unittest.skipUnless(V1_REPORT.exists(), "no v1 report on disk")
    def test_v1_report_is_still_red_and_still_forty_eight(self) -> None:
        d = loads_strict(V1_REPORT.read_bytes())
        self.assertIs(d["flight1s_green"], False)
        self.assertEqual(d["report_sha256"], V1_REPORT_SHA256)
        self.assertEqual(len(d["episodes"]), 48)

    def test_preflight_records_and_checks_v1(self) -> None:
        state = v2rt.check_v1_undisturbed()
        self.assertTrue(state["ok"], state)
        self.assertEqual(state["expected"], V1_CODE_SHA256)


class TestFrozenRules(unittest.TestCase):
    """The numbers come from rules written before anything was measured."""

    def test_margin_is_derived_from_declared_quantities_only(self) -> None:
        m = protomod.exit_margin_mm()
        d = m["derivation"]
        self.assertEqual(d["blind_spot_mm"],
                         -(-d["speed_ceiling_mm_s"]
                           * d["sample_interval_ceiling_ms"] // 1000))
        self.assertGreaterEqual(m["exit_margin_mm"],
                                d["blind_spot_mm"] + d["reference_error_mm"])
        self.assertEqual(m["exit_margin_mm"] % d["rounding_mm"], 0)

    def test_the_speed_ceiling_is_above_the_free_delta_v(self) -> None:
        d = protomod.exit_margin_mm()["derivation"]
        self.assertGreater(d["speed_ceiling_mm_s"], protomod.free_delta_v_mm_s())

    def test_radius_never_drops_below_v1(self) -> None:
        self.assertEqual(protomod.recovery_radius_mm(10.0),
                         protomod.V1_RECOVERY_RADIUS_MM)
        self.assertEqual(protomod.recovery_radius_mm(159.3), 200)
        self.assertEqual(protomod.recovery_radius_mm(201.0), 250)

    def test_the_impulse_floor_only_moves_away_from_the_controls(self) -> None:
        quiet = protomod.impulse_floor_ppk([15, 12, 18, 14])
        self.assertEqual(quiet["min_impulse_ratio_ppk"],
                         protomod.IMPULSE_FLOOR_PPK)
        loud = protomod.impulse_floor_ppk([400, 420, 460, 500])
        self.assertGreater(loud["min_impulse_ratio_ppk"],
                           protomod.IMPULSE_FLOOR_PPK)

    def test_commanded_impulse_arithmetic(self) -> None:
        self.assertEqual(protomod.commanded_impulse_mn_s(5000, 600), 3000)
        self.assertEqual(protomod.free_delta_v_mm_s(5000, 600), 1453)

    def test_calibration_order_is_derived_and_balanced(self) -> None:
        order = calibrate.episode_order(calibrate.CALIBRATION_ORDER_SEED, 8)
        self.assertEqual(len(order), 16)
        self.assertEqual(order.count("nominal"), 8)
        self.assertEqual(order, calibrate.episode_order(
            calibrate.CALIBRATION_ORDER_SEED, 8))
        self.assertNotEqual(order, calibrate.episode_order(1, 8))


def _valid_instance() -> dict:
    """A schema-valid v2 instance built from the frozen rules."""
    margin = protomod.exit_margin_mm()
    return {
        "schema_version": 2,
        "scope": "flight_software_in_the_loop",
        "dataset_kind": "rehearsal",
        "profile": "flight1s-x500-v2",
        "supersedes": {"version": 1, "protocol_sha256": V1_PROTOCOL_SHA256,
                       "report_sha256": V1_REPORT_SHA256, "verdict": "red",
                       "defect": "excursion floor on a closed-loop outcome"},
        "units": protomod.UNITS,
        "worlds": {"source": "sim3-rehearsal", "family_sha256": "a" * 64,
                   "protocol_sha256": "b" * 64, "n_packages": 12,
                   "splits": {"A": [0, 1, 2, 3], "B": [4, 5, 6, 7],
                              "C": [8, 9, 10, 11]}},
        "body": dict(protomod.BODY),
        "stages": dict(protomod.STAGES),
        "conditions": ["nominal", "perturbed"],
        "repeats": 2, "episodes": 48,
        "disturbance": {"kind": "backend_link_wrench",
                        "link": "x500_0::base_link", "frame": "world",
                        "axis": [1, 0, 0], "force_mn": 5000,
                        "publications": 1, "require_clear": True,
                        "swept_on_split": "A"},
        "stimulus": {"min_impulse_ratio_ppk": 500,
                     "max_impulse_ratio_ppk": 1500,
                     "commanded_impulse_mn_s": 3000,
                     "free_delta_v_mm_s": 1453,
                     "measurement": protomod.MEASUREMENT_NOTE},
        "challenge": {"recovery_radius_mm": 200,
                      "exit_margin_mm": margin["exit_margin_mm"],
                      "margin_derivation": margin["derivation"]},
        "recovery": {"radius_mm": 200, "hold_ms": 3000, "timeout_ms": 10000,
                     "measured_from": "end_of_disturb_window"},
        "hover_bands": {"horiz_rms_mm": 100, "horiz_max_mm": 200,
                        "vert_max_mm": 210, "attitude_max_mdeg": 25000},
        "tolerances": {"paired_hover_rms_mm": 200, "paired_recovery_ms": 5000,
                       "clock_drift_max_ms": 100},
        "timeouts": dict(protomod.TIMEOUTS),
        "rates": dict(protomod.RATES),
        "order_seed": 20260912,
    }


class TestSchemaAndDispatch(unittest.TestCase):
    def test_a_valid_instance_loads(self) -> None:
        proto = protomod.load_from_dict(_valid_instance())
        self.assertEqual(proto.version, 2)

    def test_unknown_field_is_refused(self) -> None:
        bad = _valid_instance()
        bad["room_id"] = "C"
        with self.assertRaises(Sim3Error) as cm:
            protomod.load_from_dict(bad)
        self.assertEqual(cm.exception.code, "flight_protocol_v2_schema")

    def test_recovery_measured_from_is_pinned(self) -> None:
        bad = _valid_instance()
        bad["recovery"]["measured_from"] = "start_of_disturb_window"
        with self.assertRaises(Sim3Error) as cm:
            protomod.load_from_dict(bad)
        self.assertEqual(cm.exception.code, "flight_protocol_v2_schema")

    def test_the_two_radii_must_agree(self) -> None:
        bad = _valid_instance()
        bad["challenge"]["recovery_radius_mm"] = 150
        with self.assertRaises(Sim3Error) as cm:
            protomod.load_from_dict(bad)
        self.assertEqual(cm.exception.code, "protocol_radius_disagreement")

    def test_the_v1_loader_refuses_a_v2_instance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "protocol.json"
            path.write_text(json.dumps(_valid_instance()))
            with self.assertRaises(Sim3Error):
                v1proto.load(path)

    def test_the_v2_loader_refuses_the_v1_instance(self) -> None:
        with self.assertRaises(Sim3Error) as cm:
            protomod.load(V1_PROTOCOL)
        self.assertEqual(cm.exception.code, "protocol_not_v2")


class TestThreeVerdictsAreSeparate(unittest.TestCase):
    """A failure in one question must not be paid for by another."""

    def _episode(self, *, kick_mm_s: float, force_n: float,
                 publications: int = 1, cleared: bool = True,
                 pin_after_hover: bool = False) -> Episode:
        step = 20_000_000
        samples = []
        t = 0
        x = 0
        for i in range(1000):
            if 400 <= i < 430:
                x += int(kick_mm_s * 1000 * (step / 1e9))
            elif i >= 430:
                x = int(x * 0.94)
            samples.append([t, 0 if pin_after_hover and i >= 400 else x,
                            0, 1_500_000, 0, 0, 0,
                            1 if 400 <= i < 430 else 0])
            t += step
        plan = [["climb", 0, 100 * step], ["stabilize", 100 * step, 200 * step],
                ["hover", 200 * step, 400 * step],
                ["disturb", 400 * step, 430 * step],
                ["recover", 430 * step, 999 * step]]
        ep = Episode(ok=True, condition="perturbed", label="fixture")
        ep.samples = samples
        ep.sample_columns = ["sim_time_ns", "x_um", "y_um", "z_um", "roll_mdeg",
                             "pitch_mdeg", "yaw_mdeg", "wrench"]
        ep.stage_marks = {"rest_z_um": 0, "armed_ns": 0, "takeoff_ns": 0,
                          "disarmed_ns": t, "landed_ns": t, "plan": plan}
        ep.force_n = [force_n, 0.0, 0.0]
        ep.wrench_published = publications
        ep.events = [{"ev": "wrench_applied", "sim_time_ns": 401 * step,
                      "force_n": ep.force_n}]
        if cleared:
            ep.events.append({"ev": "wrench_cleared", "published": publications,
                              "sim_time_ns": 430 * step})
        ep.driver_events = [{"event": "armed"}, {"event": "mode_auto_takeoff"}]
        ep.px4_tail = ["INFO  [commander] Armed by external command"]
        ep.ulog_sha256 = "a" * 64
        ep.ulog_bytes = 5_000_000
        return ep

    def setUp(self) -> None:
        self.proto = protomod.load_from_dict(_valid_instance()).data
        self.proto["body"]["spawn_clearance_mm"] = 250

    def test_a_healthy_episode_passes_all_three(self) -> None:
        m = v2eval.episode_metrics(self._episode(kick_mm_s=1400.0,
                                                 force_n=5.0), self.proto)
        self.assertTrue(m["stimulus"]["ok"], m["stimulus"])
        self.assertTrue(m["challenge"]["ok"], m["challenge"])
        self.assertTrue(m["recovery_verdict"]["ok"], m["recovery_verdict"])

    def test_no_force_fails_stimulus_only(self) -> None:
        m = v2eval.episode_metrics(self._episode(kick_mm_s=5.0, force_n=5.0),
                                   self.proto)
        self.assertFalse(m["stimulus"]["ok"])
        self.assertLess(m["impulse"]["ratio_ppk"],
                        self.proto["stimulus"]["min_impulse_ratio_ppk"])

    def test_an_accumulated_wrench_fails_stimulus(self) -> None:
        m = v2eval.episode_metrics(
            self._episode(kick_mm_s=1400.0, force_n=5.0, publications=10),
            self.proto)
        self.assertFalse(m["stimulus"]["ok"])
        self.assertEqual(m["stimulus"]["wrench_publications"], 10)

    def test_a_wrench_never_withdrawn_fails_stimulus(self) -> None:
        m = v2eval.episode_metrics(
            self._episode(kick_mm_s=1400.0, force_n=5.0, cleared=False),
            self.proto)
        self.assertFalse(m["stimulus"]["ok"])
        self.assertFalse(m["stimulus"]["cleared_at_window_end"])

    def test_never_leaving_the_band_fails_challenge_not_recovery(self) -> None:
        m = v2eval.episode_metrics(
            self._episode(kick_mm_s=1400.0, force_n=5.0, pin_after_hover=True),
            self.proto)
        self.assertFalse(m["challenge"]["ok"])
        self.assertEqual(m["recovery_verdict"]["status"], "recovered")
        self.assertTrue(m["recovery_verdict"]["ok"])

    def test_the_v1_failing_excursions_now_meet_the_challenge(self) -> None:
        """Documented consequence, not the reason the rule was chosen.

        The threshold is radius plus a margin derived from sampling
        resolution. What that implies for the two v1 episodes is checked
        here after the fact, so the implication is on the record.
        """
        threshold = (self.proto["challenge"]["recovery_radius_mm"]
                     + self.proto["challenge"]["exit_margin_mm"])
        self.assertEqual(threshold, 250)
        for v1_excursion in (389.388, 291.697):
            self.assertGreater(v1_excursion, threshold)
        self.assertLess(195.387, threshold)      # the v1 nominal maximum

    def test_a_nominal_episode_is_expected_to_stay_inside(self) -> None:
        ep = self._episode(kick_mm_s=1.0, force_n=0.0)
        ep.condition = "nominal"
        ep.wrench_published = 0
        ep.events = []
        m = v2eval.episode_metrics(ep, self.proto)
        self.assertTrue(m["stimulus"]["ok"])          # not applicable
        self.assertEqual(m["stimulus"]["status"], "not_applicable")
        self.assertTrue(m["challenge"]["stayed_inside"])


class TestBoundary(unittest.TestCase):
    def test_the_v2_config_carries_no_room_identity(self) -> None:
        proto = protomod.load_from_dict(_valid_instance()).data
        proto["body"]["spawn_clearance_mm"] = 250
        from echoai.nexus0.sim3.generate import generate_suite, rehearsal_assignment
        from echoai.nexus0.sim3.pkg import load_protocol as lwp
        from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
        from echoai.nexus0.flight1s.bench import WORLD_PROTOCOL
        with tempfile.TemporaryDirectory() as tmp:
            packages = generate_suite(Path(tmp), lwp(WORLD_PROTOCOL),
                                      REHEARSAL_SECRET, rehearsal_assignment())
            configs = [v2mut.container_config(g.package, proto, c)
                       for g in packages for c in ("nominal", "perturbed")]
        for cfg in configs:
            self.assertTrue(v2mut.inspect_config(cfg)["ok"],
                            v2mut.inspect_config(cfg))
        varying = {k for k in configs[0]
                   if any(c[k] != configs[0][k] for c in configs)}
        self.assertLessEqual(varying, {"spawn_pose", "condition"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
