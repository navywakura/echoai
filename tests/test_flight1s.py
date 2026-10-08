#!/usr/bin/env python3
"""FLIGHT-1S unit bank: worlds, envelope, protocol, ordering, boundary.

Everything here runs without PX4, without Gazebo and without a network.
The backend bank is separate (`test_flight1s_backend.py`) so that nothing
in this file can be mistaken for evidence that anything flew. The two
synthetic traces below are labelled fixtures: they exercise the
evaluator's arithmetic and they never reach a report.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from echoai.nexus0.sim3.canon import Sim3Error, loads_strict, sha256_bytes
from echoai.nexus0.sim3.generate import generate_suite, rehearsal_assignment
from echoai.nexus0.sim3.pkg import load_protocol as load_world_protocol
from echoai.nexus0.sim3.sdfprof import parse_bytes
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from echoai.nexus0.flight1s import evaluate, mutants, protocol as protomod, worldbuild
from echoai.nexus0.flight1s.bench import FAMILY, WORLD_PROTOCOL, condition_order
from echoai.nexus0.flight1s.session import Episode

ECHOAI = ROOT / "echoai"
EXAMPLE_WORLD = ECHOAI / "docs" / "examples" / "sim3" / "world.sdf"
SLICE = ECHOAI / "docs" / "examples" / "echo3-slices" / "flight1s.json"


def _suite(tmp: Path):
    proto = load_world_protocol(WORLD_PROTOCOL)
    return proto, generate_suite(tmp, proto, REHEARSAL_SECRET,
                                 rehearsal_assignment())


class TestEffectiveWorld(unittest.TestCase):
    def setUp(self) -> None:
        self.source = EXAMPLE_WORLD.read_bytes()
        self.eff = worldbuild.build_effective(self.source,
                                              sha256_bytes(self.source))

    def test_source_bytes_are_untouched(self) -> None:
        self.assertEqual(EXAMPLE_WORLD.read_bytes(), self.source)
        self.assertEqual(self.eff.source_sha256, sha256_bytes(self.source))
        self.assertNotEqual(self.eff.sha256, self.eff.source_sha256)

    def test_every_fixed_system_is_present(self) -> None:
        for _, cls in worldbuild.WORLD_SYSTEMS + worldbuild.FLIGHT_SYSTEMS:
            self.assertIn(cls.encode(), self.eff.data)
        self.assertIn(b"<magnetic_field>", self.eff.data)
        self.assertIn(b"<spherical_coordinates>", self.eff.data)

    def test_the_sim3_profile_refuses_the_effective_world(self) -> None:
        # Source is data, the running copy carries code. Different gates.
        with self.assertRaises(Sim3Error):
            parse_bytes(self.eff.data)

    def test_world_name_is_the_same_everywhere(self) -> None:
        self.assertEqual(self.eff.world_name, "sim3")


class TestEnvelope(unittest.TestCase):
    def test_all_twelve_rehearsal_worlds_hold_an_x500(self) -> None:
        body = protomod.body_with_placement()
        with tempfile.TemporaryDirectory() as tmp:
            _, packages = _suite(Path(tmp))
            self.assertEqual(len(packages), 12)
            for gen in packages:
                env = worldbuild.check_envelope(gen.package, gen.package_id, body)
                with self.subTest(package=gen.package_id):
                    self.assertTrue(env.ok, env.as_dict())
                    self.assertGreaterEqual(env.wall_margin_mm, 0)
                    self.assertEqual(env.required_radius_mm, 1500)

    def test_a_tighter_body_requirement_is_refused_not_ignored(self) -> None:
        body = dict(protomod.body_with_placement())
        body["clearance_mm"] = 5000          # absurd: nothing can hold it
        with tempfile.TemporaryDirectory() as tmp:
            _, packages = _suite(Path(tmp))
            env = worldbuild.check_envelope(packages[0].package,
                                            packages[0].package_id, body)
            self.assertFalse(env.ok)
            self.assertFalse(env.floor_covers)

    def test_spawn_pose_comes_from_the_world_and_the_floor(self) -> None:
        body = protomod.body_with_placement()
        with tempfile.TemporaryDirectory() as tmp:
            _, packages = _suite(Path(tmp))
            pose, xyz = worldbuild.spawn_pose(packages[0].package, body)
            spawn = packages[0].package.spawn_mm
            floor_top = packages[0].package.aabb_of(
                packages[0].package.floor).hi[2]
            self.assertEqual(xyz, (spawn[0], spawn[1],
                                   floor_top + body["spawn_clearance_mm"]))
            self.assertTrue(pose.endswith(",0,0,0"))


class TestProtocol(unittest.TestCase):
    def test_frozen_instance_loads_and_pins_px4(self) -> None:
        proto = protomod.load()
        self.assertEqual(proto["dataset_kind"], "rehearsal")
        self.assertEqual(proto["episodes"], 48)
        self.assertEqual(proto["conditions"], ["nominal", "perturbed"])
        self.assertEqual(proto["body"]["px4_commit"], protomod.PX4_COMMIT)
        self.assertEqual(proto["stages"]["takeoff_alt_mm"], 1500)
        self.assertEqual(proto["bands"]["recovery_hold_ms"], 3000)

    def test_it_points_at_the_worlds_it_was_frozen_against(self) -> None:
        proto = protomod.load()
        self.assertEqual(load_world_protocol(WORLD_PROTOCOL).sha256,
                         proto["worlds"]["protocol_sha256"])
        self.assertEqual(sha256_bytes(FAMILY.read_bytes()),
                         proto["worlds"]["family_sha256"])

    def test_unknown_field_is_refused(self) -> None:
        data = loads_strict(protomod.DEFAULT_PATH.read_bytes())
        data["room_id"] = "C"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "protocol.json"
            path.write_text(json.dumps(data))
            with self.assertRaises(Sim3Error) as cm:
                protomod.load(path)
            self.assertEqual(cm.exception.code, "flight_protocol_schema")

    def test_a_different_px4_commit_is_refused(self) -> None:
        data = loads_strict(protomod.DEFAULT_PATH.read_bytes())
        data["body"]["px4_commit"] = "0" * 40
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "protocol.json"
            path.write_text(json.dumps(data))
            with self.assertRaises(Sim3Error) as cm:
                protomod.load(path)
            self.assertEqual(cm.exception.code, "protocol_px4_commit")

    def test_freeze_refuses_to_overwrite(self) -> None:
        with self.assertRaises(Sim3Error) as cm:
            protomod.freeze(1, {}, {}, worlds={}, order_seed=0)
        self.assertEqual(cm.exception.code, "protocol_exists")


class TestConditionOrder(unittest.TestCase):
    def test_order_is_derived_reproducible_and_balanced(self) -> None:
        proto = protomod.load()
        order = condition_order(int(proto["order_seed"]), 24)
        self.assertEqual(len(order), 48)
        self.assertEqual(order.count("nominal"), 24)
        self.assertEqual(order.count("perturbed"), 24)
        self.assertEqual(order, condition_order(int(proto["order_seed"]), 24))

    def test_a_different_seed_gives_a_different_order(self) -> None:
        a = condition_order(1, 24)
        b = condition_order(2, 24)
        self.assertNotEqual(a, b)

    def test_every_slot_is_a_pair(self) -> None:
        order = condition_order(7, 24)
        for i in range(0, len(order), 2):
            self.assertEqual(sorted(order[i:i + 2]), ["nominal", "perturbed"])


class TestBoundary(unittest.TestCase):
    """What crosses into the container, and what must never."""

    def test_config_carries_no_room_identity(self) -> None:
        proto = protomod.load()
        with tempfile.TemporaryDirectory() as tmp:
            _, packages = _suite(Path(tmp))
            configs = [mutants.container_config(g.package, proto.data, c)
                       for g in packages for c in ("nominal", "perturbed")]
        for cfg in configs:
            with self.subTest(pose=cfg["spawn_pose"]):
                self.assertTrue(mutants.inspect_config(cfg)["ok"],
                                mutants.inspect_config(cfg))
        varying = {k for k in configs[0]
                   if any(c[k] != configs[0][k] for c in configs)}
        self.assertLessEqual(varying, {"spawn_pose", "condition", "disturbance"})

    def test_an_injected_room_key_is_caught(self) -> None:
        proto = protomod.load()
        with tempfile.TemporaryDirectory() as tmp:
            _, packages = _suite(Path(tmp))
            cfg = mutants.container_config(packages[0].package, proto.data,
                                           "nominal")
        self.assertTrue(mutants.inspect_config(cfg)["ok"])
        for key, value in (("split", "C"), ("package_id", "abc"),
                           ("station_mm", [1, 2, 3])):
            with self.subTest(key=key):
                dirty = dict(cfg)
                dirty[key] = value
                self.assertFalse(mutants.inspect_config(dirty)["ok"])

    def test_the_runner_never_reads_a_manifest(self) -> None:
        source = (ECHOAI / "nexus0" / "flight1s" / "assets"
                  / "flightrunner.py").read_text()
        for needle in ("manifest", "package_id", "roles", "split"):
            self.assertNotIn(needle, source.split('"""', 2)[2])


class TestEvaluatorArithmetic(unittest.TestCase):
    """Synthetic traces. Labelled fixtures; they never reach a report."""

    def _episode(self, *, kick_mm_s: float, force_n: float) -> Episode:
        step_ns = 20_000_000
        samples = []
        t = 0
        x = 0
        for i in range(1000):
            if 400 <= i < 430:                       # the disturbance window
                x += int(kick_mm_s * 1000 * (step_ns / 1e9))
            elif i >= 430:
                x = int(x * 0.97)                    # PX4 pulls it back
            samples.append([t, x, 0, 1_500_000, 0, 0, 0, 1 if 400 <= i < 430 else 0])
            t += step_ns
        plan = [["climb", 0, 100 * step_ns], ["stabilize", 100 * step_ns,
                200 * step_ns], ["hover", 200 * step_ns, 400 * step_ns],
                ["disturb", 400 * step_ns, 430 * step_ns],
                ["recover", 430 * step_ns, 999 * step_ns]]
        ep = Episode(ok=True, condition="perturbed", label="fixture")
        ep.samples = samples
        ep.sample_columns = ["sim_time_ns", "x_um", "y_um", "z_um", "roll_mdeg",
                             "pitch_mdeg", "yaw_mdeg", "wrench"]
        ep.stage_marks = {"rest_z_um": 0, "armed_ns": 0, "takeoff_ns": 0,
                          "disarmed_ns": t, "landed_ns": t, "plan": plan}
        ep.force_n = [force_n, 0.0, 0.0]
        ep.wrench_published = 1
        ep.driver_events = [{"event": "armed"}, {"event": "mode_auto_takeoff"}]
        ep.px4_tail = ["INFO  [commander] Armed by external command"]
        ep.ulog_sha256 = "a" * 64
        ep.ulog_bytes = 5_000_000
        return ep

    def _protocol(self) -> dict:
        proto = protomod.load().data
        return proto

    def test_impulse_ratio_tracks_the_applied_force(self) -> None:
        proto = self._protocol()
        strong = evaluate.episode_metrics(self._episode(kick_mm_s=1000.0,
                                                        force_n=3.0), proto)
        weak = evaluate.episode_metrics(self._episode(kick_mm_s=10.0,
                                                      force_n=3.0), proto)
        self.assertEqual(strong["impulse"]["status"], "measured")
        self.assertGreater(strong["impulse"]["ratio_ppk"],
                           weak["impulse"]["ratio_ppk"])
        # A wrench that was declared and never applied collapses the ratio.
        self.assertLess(weak["impulse"]["ratio_ppk"], 500)

    def test_recovery_needs_the_hold(self) -> None:
        proto = self._protocol()
        m = evaluate.episode_metrics(self._episode(kick_mm_s=300.0,
                                                   force_n=3.0), proto)
        self.assertEqual(m["recovery"]["status"], "recovered")
        self.assertIsInstance(m["recovery"]["recovery_ms"], int)

    def test_px4_signature_refuses_a_harness(self) -> None:
        proto = self._protocol()
        ep = self._episode(kick_mm_s=300.0, force_n=3.0)
        ep.ulog_sha256 = None
        ep.ulog_bytes = 0
        ep.driver_events = [{"event": "teleport_harness"}]
        ep.px4_tail = []
        m = evaluate.episode_metrics(ep, proto)
        self.assertFalse(m["px4_signature"]["ok"])
        self.assertFalse(m["px4_signature"]["ulog_present"])
        self.assertFalse(m["px4_signature"]["driver_armed"])

    def test_clock_regression_is_counted(self) -> None:
        proto = self._protocol()
        ep = self._episode(kick_mm_s=300.0, force_n=3.0)
        ep.samples[500][0] = ep.samples[499][0] - 1_000_000
        m = evaluate.episode_metrics(ep, proto)
        self.assertGreaterEqual(m["timing"]["clock_regressions"], 1)


class TestSliceManifest(unittest.TestCase):
    def test_slice_manifest_validates(self) -> None:
        from echoai.nexus0.sim3 import declarations
        self.assertTrue(declarations.validate("slice", SLICE)["valid"])

    def test_slice_manifest_declares_the_invariants(self) -> None:
        data = loads_strict(SLICE.read_bytes())
        self.assertEqual(data["slice"], "FLIGHT-1S")
        blob = json.dumps(data, ensure_ascii=False).lower()
        self.assertIn("agent_in_gazebo=false", blob)
        self.assertIn("wsp", blob)


if __name__ == "__main__":
    unittest.main(verbosity=2)
