#!/usr/bin/env python3
"""META-WORLD-2 tests.

The point of most of these is not to show the bench is green — the bench says
that — but to show each of its measurements **can come out red**.  A control
that cannot fail proves nothing, which is the finding a reviewer made against
DRONE-3 and which this phase inherits as a rule.

So every measurement here is mutated on purpose and must be caught.
"""
from __future__ import annotations

import json
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ECHOAI = Path(__file__).resolve().parents[1]
if str(ECHOAI.parent) not in sys.path:
    sys.path.insert(0, str(ECHOAI.parent))

from echoai.metaverse1 import bench, sdf
from echoai.metaverse1.assets import custody
from echoai.metaverse1.world import (MAX_REGIONS, REGION_CAPACITY, BlockMap,
                                     MetaSpace, Region, WorldError,
                                     minimal_regions, wide_regions)
from echoai.nexus0.compose1_v3.space import Space


class Custody(unittest.TestCase):
    """METAVERSE-1 must not disturb the sealed phases."""

    def test_no_metaverse_code_under_nexus0(self):
        offenders = [p for p in (ECHOAI / "nexus0").rglob("*.py")
                     if "metaverse1" in p.parts]
        self.assertEqual(offenders, [])

    def test_lives_outside_nexus0(self):
        self.assertTrue((ECHOAI / "metaverse1" / "world.py").exists())
        self.assertFalse((ECHOAI / "nexus0" / "metaverse1").exists())


class ByteFields(unittest.TestCase):
    """The 8-bit fields are the invariant this phase could most easily break."""

    def test_region_over_capacity_is_refused(self):
        with self.assertRaises(WorldError):
            Region(ident=0, origin=(0, 0), width=17, height=17)

    def test_region_id_must_fit_one_byte(self):
        with self.assertRaises(WorldError):
            Region(ident=MAX_REGIONS, origin=(0, 0), width=2, height=2)

    def test_local_index_stays_within_one_byte(self):
        region = Region(ident=3, origin=(0, 0), width=16, height=16)
        indices = [region.local_index(cell) for cell in region.cells()]
        self.assertEqual(len(indices), REGION_CAPACITY)
        self.assertEqual(min(indices), 0)
        self.assertEqual(max(indices), REGION_CAPACITY - 1)

    def test_overlapping_regions_are_refused(self):
        with self.assertRaises(WorldError):
            BlockMap([Region(0, (0, 0), 4, 4), Region(1, (2, 2), 4, 4)])

    def test_every_cell_of_a_large_lattice_is_addressable(self):
        space = MetaSpace(7001, "static", regions=wide_regions(4, 4))
        for cell in space.domain:
            region, local = space.address(cell)
            self.assertTrue(0 <= region < MAX_REGIONS)
            self.assertTrue(0 <= local < REGION_CAPACITY)


class Equivalence(unittest.TestCase):
    """At minimal scale the lattice must be the certified world, exactly."""

    def test_minimal_lattice_matches_the_certified_space(self):
        result = bench.equivalence(seeds=range(7001, 7005))
        self.assertEqual(result["differences"], 0)
        self.assertTrue(result["green"])

    def test_metaspace_is_not_a_subclass_of_the_certified_space(self):
        """A subclass would make the comparison unable to fail."""
        self.assertFalse(issubclass(MetaSpace, Space))

    def test_equivalence_catches_a_changed_move_cost(self):
        """Mutant: the lattice charges a different cost per move."""
        original = bench.MetaSpace

        class Costlier(original):
            def step(self, action):
                row = super().step(action)
                row["cost"] += 1
                return row

        bench.MetaSpace = Costlier
        try:
            result = bench.equivalence(seeds=[7001], conditions=("static",))
        finally:
            bench.MetaSpace = original
        self.assertGreater(result["differences"], 0)
        self.assertFalse(result["green"])

    def test_equivalence_catches_a_shifted_wall(self):
        """Mutant: the lattice puts the dividing wall one cell over."""
        original = bench.MetaSpace

        class Shifted(original):
            def make_solids(self, gap):
                self.wall_x += 1
                try:
                    return super().make_solids(gap)
                finally:
                    self.wall_x -= 1

        bench.MetaSpace = Shifted
        try:
            result = bench.equivalence(seeds=[7001], conditions=("static",))
        finally:
            bench.MetaSpace = original
        self.assertGreater(result["differences"], 0)


class Detail(unittest.TestCase):
    """Visual fidelity must not move a collision box."""

    def test_collision_is_stable_across_detail_levels(self):
        space = MetaSpace(7001, "static")
        digests = {sdf.collision_digest(sdf.source_sdf(space, detail=level))
                   for level in (0, 1, 2)}
        self.assertEqual(len(digests), 1)

    def test_visuals_actually_grow_with_detail(self):
        """Otherwise 'detail is stable' would be true of a no-op."""
        space = MetaSpace(7001, "static")
        counts = [sdf.visual_count(sdf.source_sdf(space, detail=level))
                  for level in (0, 1, 2)]
        self.assertLess(counts[0], counts[2])

    def test_detail_catches_a_decoration_that_collides(self):
        """Mutant: a level-2 fixture is emitted solid."""
        original = sdf._fixtures

        def solid_fixtures(space):
            return [line.replace('<link name="link">',
                                 '<link name="link"><collision name="collision">'
                                 '<geometry><box><size>1 1 1</size></box>'
                                 '</geometry></collision>')
                    for line in original(space)]

        sdf._fixtures = solid_fixtures
        try:
            result = bench.detail(seeds=[7001])
        finally:
            sdf._fixtures = original
        self.assertGreater(result["breaks"], 0)
        self.assertFalse(result["green"])

    def test_detail_level_is_validated(self):
        with self.assertRaises(ValueError):
            sdf.source_sdf(MetaSpace(7001, "static"), detail=3)


class Scaling(unittest.TestCase):
    """Bigger worlds must stay well formed."""

    def test_enlarged_world_is_bigger_and_still_solvable(self):
        small = MetaSpace(7001, "static").describe()
        large = MetaSpace(7001, "static", regions=wide_regions(3, 2)).describe()
        self.assertGreater(large["cells"], small["cells"])
        self.assertGreater(large["size_m"][0], small["size_m"][0])
        self.assertIsNotNone(
            MetaSpace(7001, "static", regions=wide_regions(3, 2)).oracle_distance())

    def test_lattice_beyond_one_byte_of_regions_is_refused(self):
        with self.assertRaises(WorldError):
            wide_regions(17, 17)

    def test_scaling_measurement_is_green_for_declared_lattices(self):
        self.assertTrue(bench.scaling()["green"])


class WorldBranches(unittest.TestCase):
    """No branch on a seed or on a world name."""

    def test_engine_has_no_world_branches(self):
        self.assertTrue(bench.no_world_branches()["green"])

    def test_the_check_catches_a_seed_branch(self):
        """Mutant: source that special-cases one bench seed."""
        source = "def f(seed):\n    return 1 if seed == 7001 else 0\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mutant.py"
            path.write_text(source, encoding="utf-8")
            result = bench.no_world_branches(path)
        self.assertFalse(result["green"])
        self.assertTrue(result["offences"])

    def test_the_check_catches_a_named_world_branch(self):
        source = "def f(name):\n    return name == 'sala-secreta'\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mutant.py"
            path.write_text(source, encoding="utf-8")
            self.assertFalse(bench.no_world_branches(path)["green"])


class AssetCustody(unittest.TestCase):
    """declaration -> mesh -> receipt: three files, three paths, one chain.

    These are regression tests for a defect that actually destroyed evidence:
    the receipt used to be written to ``out/<name>.json`` and overwrote the
    input declaration of ``wide-3x2``.  Each rule below is checked by breaking
    it on purpose.
    """

    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.directory, ignore_errors=True)
        self.source = self.directory / f"mundo{custody.DECLARATION_SUFFIX}"
        self.source.write_text(json.dumps(
            {"schema": "echoai-metaverse1-world-v1", "solids": []}),
            encoding="utf-8")

    @staticmethod
    def fake_glb(nodes=1):
        """A minimal well-formed GLB container, built by hand."""
        document = json.dumps({"asset": {"version": "2.0",
                                         "generator": "test"},
                               "nodes": [{} for _ in range(nodes)],
                               "meshes": []}).encode("utf-8")
        document += b" " * (-len(document) % 4)
        body = struct.pack("<II", len(document), 0x4E4F534A) + document
        return struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body

    def export_ok(self, nodes=1):
        def export(mesh):
            mesh.parent.mkdir(parents=True, exist_ok=True)
            mesh.write_bytes(self.fake_glb(nodes))
        return export

    # 1 — the source survives the build, byte for byte
    def test_declaration_is_untouched_by_the_build(self):
        before = self.source.read_bytes()
        paths = custody.plan(self.source, self.directory, "mundo")
        custody.build(paths, self.export_ok(), tool="test", parameters={})
        self.assertEqual(self.source.read_bytes(), before)

    # 2 — three different paths
    def test_the_three_artefacts_have_three_paths(self):
        paths = custody.plan(self.source, self.directory, "mundo")
        self.assertEqual(
            len({paths.declaration, paths.mesh, paths.receipt}), 3)

    def test_a_receipt_that_would_land_on_the_declaration_is_refused(self):
        """The original defect: receipt path == declaration path."""
        collision = self.directory / f"choque{custody.RECEIPT_SUFFIX}"
        collision.write_text("{}", encoding="utf-8")
        with self.assertRaises(custody.CustodyError):
            custody.plan(collision, self.directory, "choque")

    # 3 — the receipt points at the declaration, never at itself
    def test_receipt_points_at_the_declaration_not_at_itself(self):
        paths = custody.plan(self.source, self.directory, "mundo")
        payload = custody.build(paths, self.export_ok(), tool="test",
                                parameters={})
        self.assertEqual(payload["declaration"]["path"], str(self.source))
        self.assertNotEqual(payload["declaration"]["path"],
                            payload["receipt_path"])
        self.assertTrue(custody.verify(paths.receipt)["ok"])

    def test_verify_catches_a_self_referencing_receipt(self):
        """Mutant: exactly the shape wide-3x2.json was left in."""
        paths = custody.plan(self.source, self.directory, "mundo")
        custody.build(paths, self.export_ok(), tool="test", parameters={})
        payload = json.loads(paths.receipt.read_text(encoding="utf-8"))
        payload["declaration"]["path"] = str(paths.receipt)
        paths.receipt.write_text(json.dumps(payload), encoding="utf-8")
        result = custody.verify(paths.receipt)
        self.assertFalse(result["ok"])
        self.assertTrue(any("its own declaration" in problem
                            for problem in result["problems"]))

    # 4 — the recorded hashes are the hashes on disk
    def test_recorded_hashes_match_the_files(self):
        paths = custody.plan(self.source, self.directory, "mundo")
        payload = custody.build(paths, self.export_ok(), tool="test",
                                parameters={})
        self.assertEqual(payload["declaration"]["sha256"],
                         custody.sha256_file(self.source))
        self.assertEqual(payload["mesh"]["sha256"],
                         custody.sha256_file(paths.mesh))

    def test_verify_catches_a_mesh_changed_after_the_build(self):
        paths = custody.plan(self.source, self.directory, "mundo")
        custody.build(paths, self.export_ok(), tool="test", parameters={})
        paths.mesh.write_bytes(self.fake_glb(nodes=9))
        result = custody.verify(paths.receipt)
        self.assertFalse(result["ok"])
        self.assertTrue(any("mesh hash" in problem
                            for problem in result["problems"]))

    # 5 — the artefact is a readable glTF container, not a truncated write
    def test_a_truncated_mesh_is_not_accepted(self):
        def export(mesh):
            mesh.write_bytes(self.fake_glb()[:40])
        paths = custody.plan(self.source, self.directory, "mundo")
        with self.assertRaises(custody.CustodyError):
            custody.build(paths, export, tool="test", parameters={})

    # 6 — a failed export leaves no misleading green receipt
    def test_a_raising_export_writes_no_receipt(self):
        def export(mesh):
            raise RuntimeError("Blender died")
        paths = custody.plan(self.source, self.directory, "mundo")
        with self.assertRaises(RuntimeError):
            custody.build(paths, export, tool="test", parameters={})
        self.assertFalse(paths.receipt.exists())

    def test_an_export_that_writes_nothing_leaves_no_receipt(self):
        paths = custody.plan(self.source, self.directory, "mundo")
        with self.assertRaises(custody.CustodyError):
            custody.build(paths, lambda mesh: None, tool="test", parameters={})
        self.assertFalse(paths.receipt.exists())

    def test_a_failed_reimport_leaves_no_receipt(self):
        """The container can be well formed and still not re-import."""
        paths = custody.plan(self.source, self.directory, "mundo")
        with self.assertRaises(custody.CustodyError):
            custody.build(paths, self.export_ok(), tool="test", parameters={},
                          extra_validation=lambda mesh: {
                              "ok": False, "reason": "re-import failed"})
        self.assertFalse(paths.receipt.exists())

    def test_a_passing_reimport_is_recorded(self):
        paths = custody.plan(self.source, self.directory, "mundo")
        payload = custody.build(
            paths, self.export_ok(), tool="test", parameters={},
            extra_validation=lambda mesh: {"ok": True, "reimported_objects": 7})
        self.assertEqual(payload["validation"]["reimported_objects"], 7)
        self.assertTrue(payload["validation"]["ok"])

    # overwriting is allowed, but never silently
    def test_existing_artefacts_are_not_overwritten_by_default(self):
        paths = custody.plan(self.source, self.directory, "mundo")
        custody.build(paths, self.export_ok(), tool="test", parameters={})
        with self.assertRaises(custody.CustodyError):
            custody.plan(self.source, self.directory, "mundo")

    def test_overwriting_records_what_was_replaced(self):
        first = custody.plan(self.source, self.directory, "mundo")
        before = custody.build(first, self.export_ok(nodes=1), tool="test",
                               parameters={})
        again = custody.plan(self.source, self.directory, "mundo",
                             overwrite=True)
        after = custody.build(again, self.export_ok(nodes=4), tool="test",
                              parameters={})
        self.assertEqual(after["replaced"]["mesh"]["sha256"],
                         before["mesh"]["sha256"])
        self.assertNotEqual(after["mesh"]["sha256"], before["mesh"]["sha256"])


class ReconstructedWorld(unittest.TestCase):
    """wide-3x2 lost its declaration.  What replaces it must be auditable."""

    WORLDS = ECHOAI / "lab" / "metaverse1" / "worlds"

    def test_the_declaration_is_derivable_from_its_parameters(self):
        """Two runs of the same parameters give the same declaration."""
        from echoai.metaverse1 import declare
        space = MetaSpace(7001, "static", regions=wide_regions(3, 2))
        again = MetaSpace(7001, "static", regions=wide_regions(3, 2))
        self.assertEqual(declare.declaration(space),
                         declare.declaration(again))

    def test_reconstruction_matches_the_surviving_receipt_fields(self):
        """The lost original left three numbers behind.  They must agree.

        ``wide-3x2.json`` was overwritten by a receipt, but that receipt kept
        ``solids``, ``regions`` and ``size_m``.  A reconstruction that does not
        reproduce those three is not the same world.
        """
        damaged = self.WORLDS / "wide-3x2.json"
        if not damaged.is_file():
            self.skipTest("the damaged artefact is not present")
        survived = json.loads(damaged.read_text(encoding="utf-8"))
        space = MetaSpace(7001, "static", regions=wide_regions(3, 2))
        described = space.describe()
        self.assertEqual(described["solids"], survived["solids"])
        self.assertEqual(described["regions"], survived["regions"])
        self.assertEqual(list(described["size_m"]), list(survived["size_m"]))

    def test_the_rebuilt_world_keeps_its_chain_of_custody(self):
        receipt = self.WORLDS / f"wide-3x2{custody.RECEIPT_SUFFIX}"
        if not receipt.is_file():
            self.skipTest("wide-3x2 has not been rebuilt yet")
        result = custody.verify(receipt)
        self.assertTrue(result["ok"], result["problems"])
        self.assertTrue(result["receipt"]["reconstruction"]["is_reconstruction"])


class Report(unittest.TestCase):
    """The report says what it is and what it is not."""

    def test_report_is_green_and_states_its_limits(self):
        report = bench.run(save=False)
        self.assertTrue(report["green"])
        self.assertEqual(len(report["certificate_sha256"]), 64)
        joined = " ".join(report["limits"]).lower()
        self.assertIn("hardware", joined)
        self.assertIn("14/15", joined)

    def test_certificate_changes_when_a_measurement_changes(self):
        report = bench.run(save=False)
        mutated = json.loads(json.dumps(report))
        mutated["measurements"]["equivalence"]["differences"] = 1
        payload = bench._canonical({k: v for k, v in mutated.items()
                                    if k not in ("created", "elapsed_s",
                                                 "certificate_sha256")})
        import hashlib
        self.assertNotEqual(hashlib.sha256(payload.encode()).hexdigest(),
                            report["certificate_sha256"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
