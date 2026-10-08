"""A declarative world generator with a PRNG you can reimplement.

Two rules shape this module.

*The generator may build connectivity; it may not hand over its
solution.* The flood fill decides whether a candidate is admissible and
then the path is discarded. Nothing about it reaches the manifest, the
report or the consumer.

*Reproducible means reproducible in another language.* Python's
``random`` is a Mersenne Twister whose stream is an implementation
detail; SplitMix64 is nine lines of integer arithmetic, so an auditor
can regenerate seed 7 without running our code. Bounded draws use
rejection, not modulo, so the distribution is exactly uniform.

Rejected candidates consume an index and are written to a ledger. A
world the generator could not close is a number in the report, never a
quietly reduced difficulty.
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from echoai.nexus0.sim3.canon import Sim3Error, canonical_bytes, loads_strict, read_bounded, sha256_bytes
from echoai.nexus0.sim3.pkg import Package, Protocol, _validate_schema, load_package
from echoai.nexus0.sim3.seal import SPLITS

MASK64 = (1 << 64) - 1
GOLDEN = 0x9E3779B97F4A7C15

# Fixed across every split. The floor is common ground, literally.
FLOOR_POSE = (0, 0, -100)
FLOOR_SIZE = (12000, 12000, 200)
STATION_SIZE = (600, 600, 200)
FAMILY_SCHEMA = Path(__file__).resolve().parents[2] / "docs" / "schemas" / "sim3-world-family.schema.json"
DEFAULT_FAMILY_PATH = Path(__file__).resolve().parents[2] / "docs" / "examples" / "sim3-families" / "rehearsal-v1.json"


class SplitMix64:
    """The reference SplitMix64, with uniform bounded draws by rejection."""

    def __init__(self, seed: int) -> None:
        self.state = int(seed) & MASK64
        self.draws = 0

    def next_u64(self) -> int:
        self.draws += 1
        self.state = (self.state + GOLDEN) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return z ^ (z >> 31)

    def below(self, n: int) -> int:
        if n <= 0:
            raise Sim3Error("prng_bound", str(n))
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            v = self.next_u64()
            if v < limit:
                return v % n

    def lattice(self, lo: int, hi: int, step: int) -> int:
        """Uniform on ``lo, lo+step, ..., hi`` — bounds must be on the lattice."""
        if (hi - lo) % step != 0 or hi < lo:
            raise Sim3Error("prng_lattice", f"{lo}..{hi} step {step}")
        return lo + step * self.below((hi - lo) // step + 1)

    def choice(self, options: Sequence[int]) -> int:
        return options[self.below(len(options))]


def metres(v_mm: int) -> str:
    """Exact millimetres back to the decimal metres SDF wants."""
    return str(Decimal(int(v_mm)) / 1000)


@dataclass
class Box:
    name: str
    pose: Tuple[int, int, int]
    size: Tuple[int, int, int]
    grey: int
    role: str


@dataclass
class Layout:
    boxes: List[Box]
    spawn_xy: Tuple[int, int]
    archetype: str


def _floor(grey: int = 300) -> Box:
    return Box("m0", FLOOR_POSE, FLOOR_SIZE, grey, "floor")


def _station(x: int, y: int) -> Box:
    return Box("", (x, y, STATION_SIZE[2] // 2), STATION_SIZE, 900, "charging_station")


def load_family(path: Path = DEFAULT_FAMILY_PATH) -> Dict:
    """Load range data for the three fixed v1 templates.

    Geometry topology is intentionally limited by the SIM-3 profile, but all
    stochastic ranges live in a checked file. A new family therefore changes
    no Python source and is still auditable by its SHA-256.
    """
    raw = read_bounded(Path(path), code="family")
    family = loads_strict(raw, code="family")
    schema = loads_strict(read_bounded(FAMILY_SCHEMA, code="family_schema"),
                          code="family_schema")
    _validate_schema(family, schema, "family_schema")
    for label, spec in family["archetypes"].items():
        for key, value in spec.items():
            if key.endswith("_mm") and isinstance(value, dict):
                if value["lo"] > value["hi"]:
                    raise Sim3Error("family_range_order", f"{label}.{key}")
    return family


def _draw(rng: SplitMix64, spec: Dict, name: str) -> int:
    value = spec[name]
    if isinstance(value, list):
        return rng.choice(tuple(int(v) for v in value))
    return rng.lattice(int(value["lo"]), int(value["hi"]), int(value["step"]))


def archetype_a(rng: SplitMix64, family: Dict) -> Layout:
    """One wall across the middle, shorter than the room."""
    spec = family["archetypes"]["A"]
    thickness = _draw(rng, spec, "thickness_choices_mm")
    wall_x = _draw(rng, spec, "wall_x_mm")
    half_len = _draw(rng, spec, "half_length_mm")
    height = _draw(rng, spec, "height_mm")
    st_x = _draw(rng, spec, "station_x_mm")
    st_y = _draw(rng, spec, "station_y_mm")
    boxes = [
        _floor(),
        Box("", (wall_x, 0, height // 2), (thickness, 2 * half_len, height), 600,
            "barrier"),
        _station(st_x, st_y),
    ]
    spawn = (_draw(rng, spec, "spawn_x_mm"), _draw(rng, spec, "spawn_y_mm"))
    return Layout(boxes, spawn, "A")


def archetype_b(rng: SplitMix64, family: Dict) -> Layout:
    """Two staggered walls: the gap is never on the straight line."""
    spec = family["archetypes"]["B"]
    thickness = _draw(rng, spec, "thickness_choices_mm")
    x1 = _draw(rng, spec, "wall1_x_mm")
    x2 = _draw(rng, spec, "wall2_x_mm")
    span1 = _draw(rng, spec, "span1_mm")
    span2 = _draw(rng, spec, "span2_mm")
    h1 = _draw(rng, spec, "height1_mm")
    h2 = _draw(rng, spec, "height2_mm")
    st_x = _draw(rng, spec, "station_x_mm")
    st_y = _draw(rng, spec, "station_y_mm")
    boxes = [
        _floor(),
        Box("", (x1, -span1 // 2, h1 // 2), (thickness, span1, h1), 600, "barrier"),
        Box("", (x2, span2 // 2, h2 // 2), (thickness, span2, h2), 600, "barrier"),
        _station(st_x, st_y),
    ]
    spawn = (_draw(rng, spec, "spawn_x_mm"), _draw(rng, spec, "spawn_y_mm"))
    return Layout(boxes, spawn, "B")


def archetype_c(rng: SplitMix64, family: Dict) -> Layout:
    """A three-sided pocket. The station sits inside; the mouth faces -x."""
    spec = family["archetypes"]["C"]
    st_x = _draw(rng, spec, "station_x_mm")
    st_y = _draw(rng, spec, "station_y_mm")
    depth = _draw(rng, spec, "depth_mm")
    half_w = _draw(rng, spec, "half_width_mm")
    height = _draw(rng, spec, "height_mm")
    thickness = _draw(rng, spec, "thickness_choices_mm")
    back_x = st_x + depth
    boxes = [
        _floor(),
        Box("", (back_x, st_y, height // 2), (thickness, 2 * half_w, height), 600,
            "barrier"),
        Box("", (st_x, st_y + half_w, height // 2),
            (2 * depth, thickness, height), 600, "barrier"),
        Box("", (st_x, st_y - half_w, height // 2),
            (2 * depth, thickness, height), 600, "barrier"),
        _station(st_x, st_y),
    ]
    spawn = (_draw(rng, spec, "spawn_x_mm"), _draw(rng, spec, "spawn_y_mm"))
    return Layout(boxes, spawn, "C")


ARCHETYPES = {"A": archetype_a, "B": archetype_b, "C": archetype_c}


def build_layout(rng: SplitMix64, archetype: str, family: Dict) -> Layout:
    try:
        return ARCHETYPES[archetype](rng, family)
    except KeyError:
        raise Sim3Error("family_archetype", str(archetype)) from None


def render_sdf(layout: Layout) -> bytes:
    """Emit the profile's exact tree. Names are assigned here, m0..mN."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<sdf version="1.8">',
        '  <world name="sim3">',
        "    <gravity>0 0 -9.81</gravity>",
        '    <physics name="1ms" type="ignored">',
        "      <max_step_size>0.001</max_step_size>",
        "      <real_time_factor>1</real_time_factor>",
        "    </physics>",
    ]
    for i, box in enumerate(layout.boxes):
        box.name = f"m{i}"
        pose = " ".join(metres(v) for v in box.pose) + " 0 0 0"
        size = " ".join(metres(v) for v in box.size)
        grey = metres(box.grey)
        colour = f"{grey} {grey} {grey} 1"
        lines += [
            f'    <model name="{box.name}">',
            "      <static>true</static>",
            f"      <pose>{pose}</pose>",
            '      <link name="body">',
            '        <collision name="solid">',
            f"          <geometry><box><size>{size}</size></box></geometry>",
            "        </collision>",
            '        <visual name="shape">',
            f"          <geometry><box><size>{size}</size></box></geometry>",
            f"          <material><ambient>{colour}</ambient>"
            f"<diffuse>{colour}</diffuse></material>",
            "        </visual>",
            "      </link>",
            "    </model>",
        ]
    lines += ["  </world>", "</sdf>", ""]
    return "\n".join(lines).encode("utf-8")


def render_manifest(layout: Layout, sdf_sha: str, protocol_sha: str,
                    spawn_z: int) -> bytes:
    manifest = {
        "schema_version": 1,
        "profile": "sim3-boxes-v1",
        "sdf": {"path": "world.sdf", "sha256": sdf_sha},
        "protocol_sha256": protocol_sha,
        "spawn_mm": [layout.spawn_xy[0], layout.spawn_xy[1], spawn_z],
        "roles": [{"model": b.name, "role": b.role} for b in layout.boxes],
    }
    return canonical_bytes(manifest) + b"\n"


def package_id(secret: bytes, split: str, index: int) -> str:
    """An opaque directory name. Not the split, not the seed, not the hash."""
    raw = hashlib.sha256(
        b"SIM3/v1/pkgid\0" + secret + split.encode("ascii") + b"\0"
        + int(index).to_bytes(4, "big")
    ).digest()
    return raw[:8].hex()


@dataclass
class GenResult:
    package_id: str
    split: str
    index: int
    seed: int
    attempts: int
    path: Path
    package: Package
    rejections: List[Dict] = field(default_factory=list)


def generate_one(out_root: Path, protocol: Protocol, secret: bytes, split: str,
                 index: int, seed: int, *, archetype: Optional[str] = None,
                 family: Optional[Dict] = None) -> GenResult:
    """Build one package, retrying inside the protocol's attempt budget."""
    max_attempts = int(protocol.geometry["max_generation_attempts"])
    spawn_z = FLOOR_POSE[2] + FLOOR_SIZE[2] // 2 + int(
        protocol.rig["start_center_above_floor_mm"])
    pid = package_id(secret, split, index)
    pkg_dir = Path(out_root) / "packages" / pid
    rng = SplitMix64(seed)
    family = family or load_family()
    rejections: List[Dict] = []

    for attempt in range(1, max_attempts + 1):
        layout = build_layout(rng, archetype or split, family)
        sdf_raw = render_sdf(layout)
        sdf_sha = sha256_bytes(sdf_raw)
        manifest_raw = render_manifest(layout, sdf_sha, protocol.sha256, spawn_z)
        if pkg_dir.exists():
            shutil.rmtree(pkg_dir)
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "world.sdf").write_bytes(sdf_raw)
        (pkg_dir / "manifest.json").write_bytes(manifest_raw)
        try:
            package = load_package(pkg_dir, protocol)
        except Sim3Error as exc:
            rejections.append({"attempt": attempt, "code": exc.code,
                               "detail": exc.detail})
            continue
        return GenResult(pid, split, index, seed, attempt, pkg_dir, package,
                         rejections)

    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    raise Sim3Error(
        "generation_exhausted",
        f"{split}/{index}: {max_attempts} attempts, "
        f"last={rejections[-1]['code'] if rejections else 'none'}",
    )


def generate_suite(out_root: Path, protocol: Protocol, secret: bytes,
                   assignment: Sequence[Tuple[str, int, int]], *,
                   family_path: Path = DEFAULT_FAMILY_PATH) -> List[GenResult]:
    """``assignment`` is an ordered list of ``(split, index, seed)``."""
    family = load_family(family_path)
    results: List[GenResult] = []
    for split, index, seed in assignment:
        results.append(generate_one(out_root, protocol, secret, split, index, seed,
                                    family=family))
    ids = [r.package_id for r in results]
    if len(set(ids)) != len(ids):
        raise Sim3Error("package_id_collision", ",".join(sorted(ids)))
    return results


def rehearsal_assignment() -> List[Tuple[str, int, int]]:
    """The v1 infrastructure bench: public seeds 0-11, 4 per split.

    These integers are direct fixtures, exactly as SIM3-DESIGN.md §6
    says. The sealed HMAC derivation is exercised separately so that a
    green here never doubles as a claim about custody.
    """
    out: List[Tuple[str, int, int]] = []
    for s, split in enumerate(SPLITS):
        for k in range(4):
            seed = s * 4 + k
            out.append((split, k, seed))
    return out
