"""Packages: hash first, structure second, geometry last.

A SIM-3 package is two files and nothing else. Validation is deliberately
ordered:

1. the bytes are hashed and compared with the manifest **before** any
   parser sees them, so a manifest can never describe a file other than
   the one that runs;
2. JSON Schema checks shape;
3. this module checks everything JSON Schema cannot say — that roles
   form a bijection with the models, that the spawn is not inside a
   wall, that the floor actually holds the rig up, and that the station's
   approach point is reachable through the inflated geometry.

The flood fill is a private evaluator artefact. It exists so the bench
can refuse an impossible world; it is never exported, and the consumer
never learns that it ran.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0.sim3.canon import (
    Sim3Error,
    canonical_sha256,
    loads_strict,
    read_bounded,
    safe_child,
    sha256_bytes,
)
from echoai.nexus0.sim3.geom import (
    Aabb,
    DOMAIN_X_MM,
    DOMAIN_Y_MM,
    DOMAIN_Z_MM,
    FreeGrid,
    Vec3,
    fingerprint,
)
from echoai.nexus0.sim3.sdfprof import SdfWorld, parse_bytes

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "docs" / "schemas"
MANIFEST_NAME = "manifest.json"
SDF_NAME = "world.sdf"
PROTOCOL_NAME = "protocol.json"
ALLOWED_PACKAGE_FILES = frozenset({MANIFEST_NAME, SDF_NAME, PROTOCOL_NAME})

ROLE_FLOOR = "floor"
ROLE_BARRIER = "barrier"
ROLE_STATION = "charging_station"


def _schema(name: str) -> Dict:
    return loads_strict(read_bounded(SCHEMA_DIR / name, code="schema"), code="schema")


def _validate_schema(instance: Dict, schema: Dict, code: str) -> None:
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - dependency is declared in the lock
        raise Sim3Error("jsonschema_missing", "python3 -m pip install jsonschema") from None
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        raise Sim3Error(code, f"{'/'.join(str(p) for p in first.path)}: {first.message}")


@dataclass(frozen=True)
class Protocol:
    sha256: str
    data: Dict

    @property
    def step_ns(self) -> int:
        return int(self.data["step_ns"])

    @property
    def steps(self) -> int:
        return int(self.data["steps"])

    @property
    def geometry(self) -> Dict:
        return self.data["geometry"]

    @property
    def rig(self) -> Dict:
        return self.data["rig"]

    @property
    def criteria(self) -> Dict:
        return self.data["criteria"]

    @property
    def timeouts(self) -> Dict:
        return self.data["timeouts"]


def load_protocol(path: Path) -> Protocol:
    raw = read_bounded(Path(path), code="protocol")
    data = loads_strict(raw, code="protocol")
    _validate_schema(data, _schema("sim3-protocol.schema.json"), "protocol_schema")
    return Protocol(sha256=sha256_bytes(raw), data=data)


@dataclass
class Package:
    path: Path
    sdf: SdfWorld
    manifest: Dict
    manifest_sha256: str
    roles: Dict[str, str]
    spawn_mm: Vec3
    rig_start_mm: Vec3
    approach_mm: Vec3
    floor: str
    station: str
    barriers: List[str]
    fingerprint: List[Dict]
    fingerprint_sha256: str
    package_sha256: str
    connectivity_nodes: Tuple[int, int] = (0, 0)
    warnings: List[str] = field(default_factory=list)

    def aabb_of(self, name: str) -> Aabb:
        model = self.sdf.by_name(name)
        assert model is not None
        return model.aabb

    def public_view(self) -> Dict:
        """What may appear in a report. Never what may reach a consumer."""
        return {
            "sdf_sha256": self.sdf.sha256,
            "manifest_sha256": self.manifest_sha256,
            "package_sha256": self.package_sha256,
            "fingerprint_sha256": self.fingerprint_sha256,
            "n_models": len(self.sdf.models),
            "n_barriers": len(self.barriers),
        }


def load_package(path: Path, protocol: Protocol) -> Package:
    pkg_dir = Path(path)
    _check_package_dir(pkg_dir)

    manifest_path = safe_child(pkg_dir, MANIFEST_NAME, code="manifest")
    manifest_raw = read_bounded(manifest_path, code="manifest")
    manifest = loads_strict(manifest_raw, code="manifest")
    _validate_schema(manifest, _schema("sim3-manifest.schema.json"), "manifest_schema")

    if manifest["protocol_sha256"] != protocol.sha256:
        raise Sim3Error(
            "protocol_mismatch",
            f"manifest says {manifest['protocol_sha256']}, protocol is {protocol.sha256}",
        )

    sdf_path = safe_child(pkg_dir, manifest["sdf"]["path"], code="sdf")
    sdf_raw = read_bounded(sdf_path, code="sdf")
    sdf_sha = sha256_bytes(sdf_raw)
    if sdf_sha != manifest["sdf"]["sha256"]:
        # Before the parser. A world whose bytes do not match its
        # manifest is not a world with a small problem.
        raise Sim3Error("sdf_hash_mismatch",
                        f"file {sdf_sha}, manifest {manifest['sdf']['sha256']}")
    sdf = parse_bytes(sdf_raw)

    roles = _roles(manifest, sdf)
    floor = _single(roles, ROLE_FLOOR)
    station = _single(roles, ROLE_STATION)
    barriers = sorted(n for n, r in roles.items() if r == ROLE_BARRIER)
    if not barriers:
        raise Sim3Error("roles_no_barrier", "at least one barrier is required")

    _no_repeated_poses(sdf)

    geom = protocol.geometry
    rig = protocol.rig
    floor_top = sdf.by_name(floor).aabb.hi[2]  # type: ignore[union-attr]
    spawn = tuple(int(v) for v in manifest["spawn_mm"])
    rig_start = (spawn[0], spawn[1],
                 floor_top + int(rig["start_center_above_floor_mm"]))
    if spawn[2] != rig_start[2]:
        raise Sim3Error(
            "spawn_height_mismatch",
            f"spawn z {spawn[2]} != floor top {floor_top} + "
            f"{rig['start_center_above_floor_mm']}",
        )

    station_box = sdf.by_name(station).aabb  # type: ignore[union-attr]
    station_model = sdf.by_name(station)
    approach = (
        station_model.pose_mm[0],  # type: ignore[union-attr]
        station_model.pose_mm[1],  # type: ignore[union-attr]
        station_box.hi[2] + int(geom["probe_radius_mm"]) + int(geom["target_offset_mm"]),
    )
    _in_domain_point(spawn, "spawn")
    _in_domain_point(approach, "approach")

    # Order matters for diagnosis: "the spawn is inside a wall" is a
    # different defect from "a barrier stands in the drop column", and the
    # mutant table names them separately.
    _spawn_not_solid(sdf, spawn, int(geom["probe_radius_mm"]))
    _column_checks(sdf, roles, floor, spawn, rig_start, approach, geom, rig)

    nodes = _connectivity(sdf, spawn, approach, geom)

    entries = [
        {
            "aabb_mm": m.aabb.as_list(),
            "ambient": list(m.ambient),
            "diffuse": list(m.diffuse),
            "role": roles[m.name],
        }
        for m in sdf.models
    ]
    fp = fingerprint(entries)
    manifest_sha = sha256_bytes(manifest_raw)
    return Package(
        path=pkg_dir,
        sdf=sdf,
        manifest=manifest,
        manifest_sha256=manifest_sha,
        roles=roles,
        spawn_mm=spawn,  # type: ignore[arg-type]
        rig_start_mm=rig_start,
        approach_mm=approach,
        floor=floor,
        station=station,
        barriers=barriers,
        fingerprint=fp,
        fingerprint_sha256=canonical_sha256(fp),
        package_sha256=canonical_sha256(
            {"manifest_sha256": manifest_sha, "sdf_sha256": sdf_sha}
        ),
        connectivity_nodes=nodes,
    )


def _check_package_dir(pkg_dir: Path) -> None:
    if pkg_dir.is_symlink():
        raise Sim3Error("package_symlink", str(pkg_dir))
    if not pkg_dir.is_dir():
        raise Sim3Error("package_missing", str(pkg_dir))
    for entry in sorted(os.listdir(pkg_dir)):
        if entry not in ALLOWED_PACKAGE_FILES:
            raise Sim3Error("package_extra_file", entry)
        st = os.lstat(pkg_dir / entry)
        if os.path.stat.S_ISLNK(st.st_mode):
            raise Sim3Error("package_symlink_entry", entry)


def _roles(manifest: Dict, sdf: SdfWorld) -> Dict[str, str]:
    roles: Dict[str, str] = {}
    for item in manifest["roles"]:
        name = item["model"]
        if name in roles:
            raise Sim3Error("roles_duplicate_model", name)
        roles[name] = item["role"]
    model_names = {m.name for m in sdf.models}
    missing = sorted(model_names - set(roles))
    extra = sorted(set(roles) - model_names)
    if missing:
        raise Sim3Error("roles_model_unassigned", ",".join(missing))
    if extra:
        raise Sim3Error("roles_model_absent", ",".join(extra))
    return roles


def _single(roles: Dict[str, str], role: str) -> str:
    named = sorted(n for n, r in roles.items() if r == role)
    if len(named) != 1:
        raise Sim3Error(f"roles_{role}_count", str(len(named)))
    return named[0]


def _no_repeated_poses(sdf: SdfWorld) -> None:
    seen: Dict[Vec3, str] = {}
    for m in sdf.models:
        if m.pose_mm in seen:
            raise Sim3Error("model_pose_repeated", f"{seen[m.pose_mm]},{m.name}")
        seen[m.pose_mm] = m.name


def _in_domain_point(p: Sequence[int], what: str) -> None:
    if not (DOMAIN_X_MM[0] <= p[0] <= DOMAIN_X_MM[1]
            and DOMAIN_Y_MM[0] <= p[1] <= DOMAIN_Y_MM[1]
            and DOMAIN_Z_MM[0] <= p[2] <= DOMAIN_Z_MM[1]):
        raise Sim3Error(f"{what}_out_of_domain", str(list(p)))


def _column_checks(sdf: SdfWorld, roles: Dict[str, str], floor: str,
                   spawn: Sequence[int], rig_start: Sequence[int],
                   approach: Sequence[int], geom: Dict, rig: Dict) -> None:
    """The floor holds the rig up; barriers stay out of both columns."""
    rig_r = int(rig["radius_mm"])
    probe_r = int(geom["probe_radius_mm"])
    floor_box = sdf.by_name(floor).aabb  # type: ignore[union-attr]
    if not floor_box.covers_xy_disc(rig_start[0], rig_start[1], rig_r):
        raise Sim3Error("floor_missing_under_rig", str(list(rig_start)))
    if not floor_box.covers_xy_disc(approach[0], approach[1], probe_r):
        raise Sim3Error("floor_missing_under_approach", str(list(approach)))

    floor_top = floor_box.hi[2]
    drop_lo = floor_top
    drop_hi = rig_start[2] + rig_r
    for m in sdf.models:
        if roles[m.name] != ROLE_BARRIER:
            continue
        if m.aabb.intersects_xy_disc(rig_start[0], rig_start[1], rig_r) \
                and m.aabb.hi[2] > drop_lo and m.aabb.lo[2] < drop_hi:
            raise Sim3Error("barrier_in_rig_column", m.name)
        if m.aabb.intersects_xy_disc(approach[0], approach[1], probe_r):
            raise Sim3Error("barrier_in_approach_column", m.name)


def _spawn_not_solid(sdf: SdfWorld, spawn: Sequence[int], radius: int) -> None:
    ball = Aabb(lo=(spawn[0] - radius, spawn[1] - radius, spawn[2] - radius),
                hi=(spawn[0] + radius, spawn[1] + radius, spawn[2] + radius))
    for m in sdf.models:
        if m.aabb.intersects(ball):
            raise Sim3Error("spawn_inside_solid", m.name)


def _connectivity(sdf: SdfWorld, spawn: Sequence[int], approach: Sequence[int],
                  geom: Dict) -> Tuple[int, int]:
    radius = int(geom["probe_radius_mm"]) + int(geom["clearance_mm"])
    step = int(geom["grid_mm"])
    solids = sdf.aabbs()
    inflated = [b.inflated(radius) for b in solids]
    grid = FreeGrid.build(solids, radius, step)
    starts = grid.nearby_free(spawn, inflated)
    goals = grid.nearby_free(approach, inflated)
    if not starts:
        raise Sim3Error("spawn_not_attachable", str(list(spawn)))
    if not goals:
        raise Sim3Error("approach_not_attachable", str(list(approach)))
    if not grid.connected(starts, goals):
        raise Sim3Error("goal_unreachable",
                        f"spawn {list(spawn)} -> approach {list(approach)}")
    return (len(starts), len(goals))
