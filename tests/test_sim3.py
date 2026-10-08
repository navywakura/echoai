#!/usr/bin/env python3
"""SIM-3 unit bank: profile, packages, geometry, generator, seal, transport.

Everything here runs without Gazebo, without a container and without a
network. The backend bank is separate (`test_sim3_backend.py`) precisely
so that a machine with no simulator still exercises the parts that do not
need one — and so that nothing in here can be mistaken for evidence that
a world ran.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from echoai.nexus0.sim3 import declarations, metamorph, mutants, seal
from echoai.nexus0.sim3.canon import (
    Sim3Error,
    canonical_bytes,
    canonical_sha256,
    loads_strict,
    safe_child,
    sha256_bytes,
)
from echoai.nexus0.sim3.generate import (
    SplitMix64,
    build_layout,
    generate_suite,
    load_family,
    metres,
    rehearsal_assignment,
)
from echoai.nexus0.sim3.geom import (
    Aabb,
    FreeGrid,
    fingerprint,
    mm,
    planar_equivalent,
    pose6,
    rgba,
)
from echoai.nexus0.sim3.pkg import load_package, load_protocol
from echoai.nexus0.sim3.rig import RIG_MODEL, WORLD_SYSTEMS, build_effective
from echoai.nexus0.sim3.runtime import PROBE, SANDBOX_ARGV, SANDBOX_ENV_EXPECTED
from echoai.nexus0.sim3.sdfprof import parse_bytes, parse_file

ECHOAI = ROOT / "echoai"
EXAMPLE = ECHOAI / "docs" / "examples" / "sim3"
PROTOCOL_PATH = EXAMPLE / "protocol.json"
FAMILY = ECHOAI / "docs" / "examples" / "sim3-families" / "rehearsal-v1.json"
SLICE = ECHOAI / "docs" / "examples" / "echo3-slices" / "sim3.json"
CAMPAIGN = ECHOAI / "docs" / "examples" / "sim3-campaigns" / "sim3-rehearsal-20260910.json"


def _suite(tmp: Path):
    protocol = load_protocol(PROTOCOL_PATH)
    return protocol, generate_suite(tmp, protocol, seal.REHEARSAL_SECRET,
                                    rehearsal_assignment())


class TestCanon(unittest.TestCase):
    def test_duplicate_keys_are_refused(self) -> None:
        with self.assertRaises(Sim3Error) as cm:
            loads_strict(b'{"a":1,"a":2}')
        self.assertEqual(cm.exception.code, "json_duplicate_key")

    def test_non_finite_numbers_are_refused(self) -> None:
        for blob in (b'{"a":NaN}', b'{"a":Infinity}', b'{"a":-Infinity}'):
            with self.subTest(blob=blob):
                with self.assertRaises(Sim3Error):
                    loads_strict(blob)

    def test_canonical_bytes_are_sorted_and_tight(self) -> None:
        self.assertEqual(canonical_bytes({"b": 1, "a": [2, "x"]}),
                         b'{"a":[2,"x"],"b":1}')

    def test_canonical_bytes_refuse_floats(self) -> None:
        with self.assertRaises(Sim3Error):
            canonical_bytes({"a": 1.5})

    def test_world_sdf_is_a_name_not_a_path(self) -> None:
        for bad in ("../world.sdf", "sub/world.sdf", "", ".."):
            with self.subTest(bad=bad):
                with self.assertRaises(Sim3Error):
                    safe_child(EXAMPLE, bad)


class TestMillimetres(unittest.TestCase):
    def test_exact_decimal(self) -> None:
        self.assertEqual(mm("0.1"), 100)
        self.assertEqual(mm("-9.81"), -9810)
        self.assertEqual(mm("12"), 12000)
        self.assertEqual(mm("0"), 0)

    def test_sub_millimetre_is_refused_not_rounded(self) -> None:
        for bad in ("0.0001", "1.2345", "0.05001"):
            with self.subTest(bad=bad):
                with self.assertRaises(Sim3Error):
                    mm(bad)

    def test_exponents_and_specials_are_refused(self) -> None:
        for bad in ("1e3", "NaN", "Infinity", "0x10", ""):
            with self.subTest(bad=bad):
                with self.assertRaises(Sim3Error):
                    mm(bad)

    def test_round_trip_through_metres(self) -> None:
        for value in (-8000, -100, 0, 1, 999, 12000):
            self.assertEqual(mm(metres(value)), value)

    def test_rotation_must_be_zero(self) -> None:
        self.assertEqual(pose6("1 2 3 0 0 0"), (1000, 2000, 3000))
        with self.assertRaises(Sim3Error):
            pose6("1 2 3 0 0 1.57")

    def test_material_must_be_opaque_grey(self) -> None:
        self.assertEqual(rgba("0.3 0.3 0.3 1"), (300, 300, 300, 1000))
        for bad in ("0.3 0.4 0.3 1", "0.3 0.3 0.3 0.5", "1.5 1.5 1.5 1"):
            with self.subTest(bad=bad):
                with self.assertRaises(Sim3Error):
                    rgba(bad)


class TestSdfProfile(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = (EXAMPLE / "world.sdf").read_bytes()

    def test_example_parses(self) -> None:
        world = parse_file(EXAMPLE / "world.sdf")
        self.assertEqual(len(world.models), 3)
        self.assertEqual(world.by_name("m0").aabb.as_list(),
                         [-6000, -6000, -200, 6000, 6000, 0])

    def test_manifest_hash_matches_the_shipped_example(self) -> None:
        manifest = loads_strict((EXAMPLE / "manifest.json").read_bytes())
        self.assertEqual(sha256_bytes(self.raw), manifest["sdf"]["sha256"])

    def test_refusals(self) -> None:
        cases = {
            "sdf_doctype": b'<!DOCTYPE sdf [<!ENTITY x "y">]>' + self.raw,
            "sdf_version": self.raw.replace(b'version="1.8"', b'version="1.9"'),
            "sdf_world_name": self.raw.replace(b'world name="sim3"',
                                               b'world name="other"'),
            "sdf_unsupported_element":
                self.raw.replace(b"  </world>",
                                 b'    <plugin filename="x" name="y"/>\n  </world>'),
            "sdf_gravity": self.raw.replace(b"0 0 -9.81", b"0 0 -1.62"),
            "sdf_max_step_size": self.raw.replace(b"<max_step_size>0.001",
                                                  b"<max_step_size>0.01"),
            "sdf_model_not_static": self.raw.replace(b"<static>true</static>",
                                                     b"<static>false</static>", 1),
            "sdf_visual_collision_mismatch":
                self.raw.replace(b"<size>0.6 0.6 0.2</size>",
                                 b"<size>0.7 0.6 0.2</size>", 1),
            "sdf_pose_not_millimetre":
                self.raw.replace(b"<pose>3 0 0.1", b"<pose>3.00005 0 0.1"),
            "sdf_size_not_millimetre":
                self.raw.replace(b"<size>0.6 0.6 0.2</size>",
                                 b"<size>0.60005 0.6 0.2</size>"),
            "sdf_aabb_out_of_domain":
                self.raw.replace(b"<pose>3 0 0.1", b"<pose>7.9 0 0.1"),
        }
        for expected, blob in cases.items():
            with self.subTest(expected=expected):
                with self.assertRaises(Sim3Error) as cm:
                    parse_bytes(blob)
                self.assertEqual(cm.exception.code, expected)

    def test_duplicate_model_names_are_refused(self) -> None:
        blob = self.raw.replace(b'name="m2"', b'name="m1"')
        with self.assertRaises(Sim3Error) as cm:
            parse_bytes(blob)
        self.assertEqual(cm.exception.code, "sdf_duplicate_model_name")

    def test_processing_instructions_are_refused(self) -> None:
        blob = self.raw.replace(b"<sdf", b"<?leak href='x'?><sdf", 1)
        with self.assertRaises(Sim3Error) as cm:
            parse_bytes(blob)
        self.assertEqual(cm.exception.code, "sdf_processing_instruction")


class TestPackage(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = load_protocol(PROTOCOL_PATH)

    def test_example_package(self) -> None:
        pkg = load_package(EXAMPLE, self.protocol)
        self.assertEqual(pkg.floor, "m0")
        self.assertEqual(pkg.station, "m2")
        self.assertEqual(pkg.barriers, ["m1"])
        self.assertEqual(list(pkg.rig_start_mm), [-3000, 0, 1000])
        # top of the station (200) + probe radius (250) + offset (100)
        self.assertEqual(list(pkg.approach_mm), [3000, 0, 550])

    def test_hash_is_checked_before_the_parser_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "p"
            pkg.mkdir()
            # Bytes that our parser would reject anyway; the hash must
            # fire first, so the observed cause is the mismatch.
            (pkg / "world.sdf").write_bytes(b"<sdf version='1.8'><nope/></sdf>")
            (pkg / "manifest.json").write_bytes(
                (EXAMPLE / "manifest.json").read_bytes())
            with self.assertRaises(Sim3Error) as cm:
                load_package(pkg, self.protocol)
            self.assertEqual(cm.exception.code, "sdf_hash_mismatch")

    def test_protocol_mismatch_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "p"
            pkg.mkdir()
            (pkg / "world.sdf").write_bytes((EXAMPLE / "world.sdf").read_bytes())
            manifest = loads_strict((EXAMPLE / "manifest.json").read_bytes())
            manifest["protocol_sha256"] = "0" * 64
            (pkg / "manifest.json").write_bytes(canonical_bytes(manifest))
            with self.assertRaises(Sim3Error) as cm:
                load_package(pkg, self.protocol)
            self.assertEqual(cm.exception.code, "protocol_mismatch")

    def test_extra_file_in_package_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp) / "p"
            pkg.mkdir()
            for name in ("world.sdf", "manifest.json"):
                (pkg / name).write_bytes((EXAMPLE / name).read_bytes())
            (pkg / "notes.txt").write_text("hi")
            with self.assertRaises(Sim3Error) as cm:
                load_package(pkg, self.protocol)
            self.assertEqual(cm.exception.code, "package_extra_file")


class TestGeometry(unittest.TestCase):
    def test_planar_equivalence_detects_rotation_and_reflection(self) -> None:
        base = [Aabb((0, 0, 0), (1000, 200, 500))]
        rotated = [Aabb((5000, 5000, 0), (5200, 6000, 500))]
        self.assertTrue(planar_equivalent(base, rotated))
        different = [Aabb((0, 0, 0), (1000, 300, 500))]
        self.assertFalse(planar_equivalent(base, different))

    def test_fingerprint_ignores_order(self) -> None:
        a = [{"aabb_mm": [0, 0, 0, 1, 1, 1], "ambient": [1, 1, 1, 1000],
              "diffuse": [1, 1, 1, 1000], "role": "barrier"},
             {"aabb_mm": [2, 2, 2, 3, 3, 3], "ambient": [1, 1, 1, 1000],
              "diffuse": [1, 1, 1, 1000], "role": "floor"}]
        self.assertEqual(canonical_sha256(fingerprint(a)),
                         canonical_sha256(fingerprint(list(reversed(a)))))

    def test_free_grid_blocks_and_connects(self) -> None:
        floor = Aabb((-6000, -6000, -200), (6000, 6000, 0))
        # Tall enough that inflating by the probe radius closes the top of
        # the domain too: a 3 m wall can simply be flown over.
        wall = Aabb((-100, -8000, 0), (100, 8000, 3700))
        grid = FreeGrid.build([floor, wall], 300, 100)
        left = grid.index_of((-3000, 0, 1000))
        right = grid.index_of((3000, 0, 1000))
        self.assertIsNotNone(left)
        self.assertIsNotNone(right)
        # A wall spanning the whole domain separates the two halves.
        self.assertFalse(grid.connected([left], [right]))
        grid_open = FreeGrid.build([floor], 300, 100)
        self.assertTrue(grid_open.connected(
            [grid_open.index_of((-3000, 0, 1000))],
            [grid_open.index_of((3000, 0, 1000))]))


class TestGenerator(unittest.TestCase):
    def test_splitmix64_reference_stream(self) -> None:
        rng = SplitMix64(0)
        self.assertEqual([rng.next_u64() for _ in range(3)],
                         [16294208416658607535, 7960286522194355700,
                          487617019471545679])

    def test_bounded_draws_stay_in_range(self) -> None:
        rng = SplitMix64(12345)
        self.assertTrue(all(0 <= rng.below(7) < 7 for _ in range(500)))
        rng = SplitMix64(99)
        self.assertTrue(all(v % 100 == 0 and -600 <= v <= 600
                            for v in (rng.lattice(-600, 600, 100)
                                      for _ in range(200))))

    def test_suite_is_reproducible_and_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protocol, first = _suite(Path(tmp) / "a")
            second = generate_suite(Path(tmp) / "b", protocol,
                                    seal.REHEARSAL_SECRET,
                                    list(reversed(rehearsal_assignment())))
            by_id = {r.package_id: r.package.package_sha256 for r in second}
            self.assertEqual(len(first), 12)
            for gen in first:
                self.assertEqual(by_id[gen.package_id],
                                 gen.package.package_sha256)
            fps = {g.package.fingerprint_sha256 for g in first}
            self.assertEqual(len(fps), 12)
            splits = {g.split for g in first}
            self.assertEqual(splits, {"A", "B", "C"})

    def test_rendered_world_reparses_to_the_same_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _, results = _suite(Path(tmp))
            for gen in results:
                raw = (gen.path / "world.sdf").read_bytes()
                self.assertEqual(sha256_bytes(raw), gen.package.sdf.sha256)

    def test_declared_family_reproduces_the_published_first_fixture(self) -> None:
        protocol = load_protocol(PROTOCOL_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            generated = generate_suite(Path(tmp), protocol, seal.REHEARSAL_SECRET,
                                       rehearsal_assignment(), family_path=FAMILY)
        self.assertEqual(generated[0].package.package_sha256,
                         "2ba79cdb4ab9d04266f742dceddbee5a99fe997edc66cabe9496bd69163ce906")

    def test_declared_family_bases_are_not_planar_equivalent(self) -> None:
        family = load_family(FAMILY)
        layouts = {name: build_layout(SplitMix64(0), name, family)
                   for name in ("A", "B", "C")}
        boxes = {name: [Aabb.from_pose_size(box.pose, box.size)
                        for box in layout.boxes]
                 for name, layout in layouts.items()}
        self.assertFalse(planar_equivalent(boxes["A"], boxes["B"]))
        self.assertFalse(planar_equivalent(boxes["A"], boxes["C"]))
        self.assertFalse(planar_equivalent(boxes["B"], boxes["C"]))


class TestDeclarations(unittest.TestCase):
    def test_examples_validate(self) -> None:
        for kind, path in (("family", FAMILY), ("slice", SLICE),
                           ("campaign", CAMPAIGN)):
            with self.subTest(kind=kind):
                self.assertTrue(declarations.validate(kind, path)["valid"])

    def test_unknown_declaration_field_is_refused(self) -> None:
        for kind, source in (("family", FAMILY), ("slice", SLICE),
                             ("campaign", CAMPAIGN)):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                bad = json.loads(source.read_text())
                bad["room_id"] = "C"
                path = Path(tmp) / "bad.json"
                path.write_text(json.dumps(bad))
                with self.assertRaises(Sim3Error) as cm:
                    declarations.validate(kind, path)
                self.assertEqual(cm.exception.code, f"{kind}_schema")


class TestMetamorph(unittest.TestCase):
    def test_rename_keeps_the_fingerprint_and_changes_the_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protocol, results = _suite(Path(tmp) / "s")
            gen = results[0]
            renamed = metamorph.renamed(gen.package, Path(tmp) / "r", protocol)
            self.assertEqual(renamed.fingerprint_sha256,
                             gen.package.fingerprint_sha256)
            self.assertNotEqual(renamed.sdf.sha256, gen.package.sdf.sha256)

    def test_moved_wall_changes_the_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protocol, results = _suite(Path(tmp) / "s")
            for gen in results:
                moved = metamorph.moved_wall(gen.package, Path(tmp) / "m",
                                             protocol, rig_radius_mm=50)
                self.assertNotEqual(moved.package.fingerprint_sha256,
                                    gen.package.fingerprint_sha256)
                self.assertEqual(abs(moved.shift_mm), 500)


class TestPackageMutants(unittest.TestCase):
    def test_every_mutant_fails_for_its_own_cause(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protocol, results = _suite(Path(tmp) / "s")
            cases = mutants._package_cases(Path(tmp) / "m", protocol, results)
            for case in cases:
                with self.subTest(mutant=case["mutant"]):
                    self.assertTrue(case["ok"],
                                    f"{case['mutant']}: expected "
                                    f"{case.get('expected')}, got "
                                    f"{case.get('observed')}")
            self.assertGreaterEqual(len(cases), 14)


class TestSeal(unittest.TestCase):
    def test_commitment_and_seed_vectors(self) -> None:
        protocol = load_protocol(PROTOCOL_PATH)
        commit = seal.protocol_commitment(protocol.sha256, seal.REHEARSAL_SECRET)
        self.assertEqual(commit, sha256_bytes(
            b"SIM3/v1/commit\0" + bytes.fromhex(protocol.sha256)
            + seal.REHEARSAL_SECRET))
        seeds = [seal.derive_seed(seal.REHEARSAL_SECRET, "C", i) for i in range(4)]
        self.assertEqual(len(set(seeds)), 4)
        self.assertNotEqual(seeds[0],
                            seal.derive_seed(seal.REHEARSAL_SECRET, "B", 0))

    def test_latch_opens_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            latch = Path(tmp) / "c.json"
            seal.seal(latch, split="C", commitment="a" * 64,
                      inventory_sha256="b" * 64, custodian="test", n_packages=4)
            with seal.open_once(latch):
                pass
            self.assertEqual(seal.read_seal(latch).state, "consumed")
            with self.assertRaises(Sim3Error) as cm:
                with seal.open_once(latch):
                    pass
            self.assertEqual(cm.exception.code, "seal_already_consumed")

    def test_all_sealing_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            protocol, results = _suite(Path(tmp) / "s")
            cases, ok = mutants.sealing_cases(Path(tmp) / "seal", protocol,
                                              results)
            for case in cases:
                with self.subTest(check=case["check"]):
                    self.assertTrue(case["ok"], json.dumps(case)[:200])
            self.assertTrue(ok)


class TestRig(unittest.TestCase):
    def test_effective_sdf_is_a_separate_hash(self) -> None:
        raw = (EXAMPLE / "world.sdf").read_bytes()
        eff = build_effective(raw, sha256_bytes(raw), (0, 0, 1000), 50, 100)
        self.assertNotEqual(eff.sha256, eff.source_sha256)
        self.assertIn(RIG_MODEL.encode(), eff.data)
        for _, cls in WORLD_SYSTEMS:
            self.assertIn(cls.encode(), eff.data)

    def test_the_profile_refuses_the_effective_world(self) -> None:
        # The source is data; the effective copy carries code. They must
        # never be validated by the same gate.
        raw = (EXAMPLE / "world.sdf").read_bytes()
        eff = build_effective(raw, sha256_bytes(raw), (0, 0, 1000), 50, 100)
        with self.assertRaises(Sim3Error):
            parse_bytes(eff.data)


class TestTransport(unittest.TestCase):
    """The consumer's own parser, driven directly. No sandbox needed."""

    def _drive(self, lines: bytes) -> dict:
        proc = subprocess.run([sys.executable, str(PROBE)], input=lines,
                              capture_output=True, timeout=60)
        report = json.loads(proc.stderr.decode().strip().splitlines()[-1])
        return {"stdout": proc.stdout.decode(), "report": report}

    def test_well_formed_ticks_are_acked_in_order(self) -> None:
        lines = b"".join(
            json.dumps({"v": 1, "seq": i, "sim_time_ns": i * 1_000_000},
                       separators=(",", ":")).encode() + b"\n"
            for i in range(5))
        out = self._drive(lines)
        self.assertEqual(out["stdout"].split(),
                         ['{"v":1,"ack":0}', '{"v":1,"ack":1}', '{"v":1,"ack":2}',
                          '{"v":1,"ack":3}', '{"v":1,"ack":4}'])
        self.assertEqual(out["report"]["ticks"], 5)
        self.assertIsNone(out["report"]["protocol_error"])

    def test_a_tick_carrying_private_fields_is_refused(self) -> None:
        line = json.dumps({"v": 1, "seq": 0, "sim_time_ns": 0, "split": "C"}).encode()
        out = self._drive(line + b"\n")
        self.assertEqual(out["report"]["protocol_error"], "unexpected_fields")
        self.assertEqual(out["report"]["ticks"], 0)

    def test_out_of_order_and_oversized_ticks_are_refused(self) -> None:
        first = json.dumps({"v": 1, "seq": 0, "sim_time_ns": 0}).encode() + b"\n"
        skipped = json.dumps({"v": 1, "seq": 4, "sim_time_ns": 4}).encode() + b"\n"
        self.assertEqual(self._drive(first + skipped)["report"]["protocol_error"],
                         "out_of_order")
        huge = (b'{"v":1,"seq":0,"sim_time_ns":0,"pad":"'
                + b"A" * 300 + b'"}\n')
        self.assertEqual(self._drive(huge)["report"]["protocol_error"],
                         "line_too_long")

    def test_a_tick_line_fits_the_budget(self) -> None:
        line = json.dumps({"v": 1, "seq": 1000, "sim_time_ns": 10 ** 12},
                          separators=(",", ":")).encode() + b"\n"
        self.assertLessEqual(len(line), 256)


class TestSandboxConfig(unittest.TestCase):
    def test_argv_and_env_carry_no_world_identity(self) -> None:
        blob = json.dumps({"argv": SANDBOX_ARGV, "env": SANDBOX_ENV_EXPECTED})
        for leak in ("split", "seed", "package", "manifest", "sha256", "sim3-run"):
            self.assertNotIn(leak, blob)
        self.assertEqual(SANDBOX_ARGV, ["/usr/bin/python3", "/probe/probe.py"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
