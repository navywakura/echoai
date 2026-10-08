"""Millimetre integers, and the exact-decimal gate that produces them.

SDF is written in metres as decimal text. The profile only admits values
that land exactly on a millimetre, so parsing is a decimal operation, not
a float one: ``0.1`` becomes ``100`` because ``Decimal("0.1") * 1000`` is
``100``, never ``100.00000000000000005``. Anything that does not land on
a millimetre is refused rather than rounded, because rounding here would
silently move a wall.

Everything downstream — AABBs, the free-space grid, the fingerprint, the
tolerances — is integer millimetres.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from echoai.nexus0.sim3.canon import Sim3Error

# Domain of the sim3-boxes-v1 profile, in millimetres.
DOMAIN_X_MM = (-8000, 8000)
DOMAIN_Y_MM = (-8000, 8000)
DOMAIN_Z_MM = (-200, 4000)

Vec3 = Tuple[int, int, int]


def mm(text: str, *, code: str = "number") -> int:
    """Exact metres-to-millimetres. No float ever touches the value."""
    s = str(text).strip()
    if s == "" or any(ch in s for ch in "eEnNiI"):
        # Refuse exponents and nan/inf spellings outright: the profile is
        # plain decimal, and Decimal would happily accept "1E3" or "NaN".
        raise Sim3Error(f"{code}_not_plain_decimal", repr(text))
    try:
        value = Decimal(s)
    except InvalidOperation:
        raise Sim3Error(f"{code}_not_decimal", repr(text)) from None
    scaled = value * 1000
    if scaled != scaled.to_integral_value():
        raise Sim3Error(f"{code}_not_millimetre", repr(text))
    return int(scaled)


def triple(text: str, *, code: str = "triple") -> Vec3:
    parts = str(text).split()
    if len(parts) != 3:
        raise Sim3Error(f"{code}_arity", repr(text))
    return (mm(parts[0], code=code), mm(parts[1], code=code), mm(parts[2], code=code))


def pose6(text: str, *, code: str = "pose") -> Vec3:
    """A pose with the rotation required to be exactly zero in v1."""
    parts = str(text).split()
    if len(parts) != 6:
        raise Sim3Error(f"{code}_arity", repr(text))
    for part in parts[3:]:
        if mm(part, code=code + "_rot") != 0:
            raise Sim3Error(f"{code}_rotation_not_zero", repr(text))
    return (mm(parts[0], code=code), mm(parts[1], code=code), mm(parts[2], code=code))


def rgba(text: str, *, code: str = "colour") -> Tuple[int, int, int, int]:
    """Grey RGBA in thousandths. Monochrome is a profile rule, not taste."""
    parts = str(text).split()
    if len(parts) != 4:
        raise Sim3Error(f"{code}_arity", repr(text))
    vals = [mm(p, code=code) for p in parts]
    for v in vals:
        if not 0 <= v <= 1000:
            raise Sim3Error(f"{code}_out_of_range", repr(text))
    if not (vals[0] == vals[1] == vals[2]):
        raise Sim3Error(f"{code}_not_grey", repr(text))
    if vals[3] != 1000:
        raise Sim3Error(f"{code}_alpha", repr(text))
    return (vals[0], vals[1], vals[2], vals[3])


@dataclass(frozen=True)
class Aabb:
    """Axis-aligned box in millimetres, half-open in neither direction."""

    lo: Vec3
    hi: Vec3

    @staticmethod
    def from_pose_size(pose: Vec3, size: Vec3) -> "Aabb":
        for axis, s in zip("xyz", size):
            if s <= 0:
                raise Sim3Error("box_size_not_positive", f"{axis}={s}")
            if s % 2 != 0:
                # Half-extents must also be whole millimetres, otherwise
                # the AABB of an odd-millimetre box is not representable
                # and every downstream comparison inherits a half-unit.
                raise Sim3Error("box_size_odd_mm", f"{axis}={s}")
        return Aabb(
            lo=tuple(p - s // 2 for p, s in zip(pose, size)),  # type: ignore[arg-type]
            hi=tuple(p + s // 2 for p, s in zip(pose, size)),  # type: ignore[arg-type]
        )

    def inflated(self, r: int) -> "Aabb":
        return Aabb(
            lo=tuple(v - r for v in self.lo),  # type: ignore[arg-type]
            hi=tuple(v + r for v in self.hi),  # type: ignore[arg-type]
        )

    def contains_point(self, p: Sequence[int]) -> bool:
        return all(self.lo[i] <= p[i] <= self.hi[i] for i in range(3))

    def intersects(self, other: "Aabb") -> bool:
        return all(
            self.lo[i] <= other.hi[i] and other.lo[i] <= self.hi[i] for i in range(3)
        )

    def intersects_xy_disc(self, cx: int, cy: int, r: int) -> bool:
        """Closest-point test between the box footprint and a disc."""
        dx = max(self.lo[0] - cx, 0, cx - self.hi[0])
        dy = max(self.lo[1] - cy, 0, cy - self.hi[1])
        return dx * dx + dy * dy <= r * r

    def covers_xy_disc(self, cx: int, cy: int, r: int) -> bool:
        return (
            self.lo[0] <= cx - r
            and self.hi[0] >= cx + r
            and self.lo[1] <= cy - r
            and self.hi[1] >= cy + r
        )

    def as_list(self) -> List[int]:
        return [*self.lo, *self.hi]

    def in_domain(self) -> bool:
        return (
            DOMAIN_X_MM[0] <= self.lo[0] and self.hi[0] <= DOMAIN_X_MM[1]
            and DOMAIN_Y_MM[0] <= self.lo[1] and self.hi[1] <= DOMAIN_Y_MM[1]
            and DOMAIN_Z_MM[0] <= self.lo[2] and self.hi[2] <= DOMAIN_Z_MM[1]
        )


def segment_free(a: Sequence[int], b: Sequence[int], solids: Sequence[Aabb],
                 *, samples: int = 64) -> bool:
    """Sampled segment test in exact integer arithmetic.

    Sampling, not an exact swept test: the design only asks for a
    discrete geometric check, and the report says so. The samples are
    rational points evaluated with integer cross-multiplication, so two
    machines agree bit for bit.
    """
    for k in range(samples + 1):
        p = [a[i] + (b[i] - a[i]) * k // samples for i in range(3)]
        for box in solids:
            if box.contains_point(p):
                return False
    return True


@dataclass
class FreeGrid:
    """Discrete free space for a sphere of a fixed radius, at ``step`` mm."""

    step: int
    lo: Vec3
    dims: Vec3
    blocked: bytearray

    @staticmethod
    def build(solids: Sequence[Aabb], radius: int, step: int) -> "FreeGrid":
        lo = (
            _ceil_to(DOMAIN_X_MM[0] + radius, step),
            _ceil_to(DOMAIN_Y_MM[0] + radius, step),
            _ceil_to(DOMAIN_Z_MM[0] + radius, step),
        )
        hi = (
            _floor_to(DOMAIN_X_MM[1] - radius, step),
            _floor_to(DOMAIN_Y_MM[1] - radius, step),
            _floor_to(DOMAIN_Z_MM[1] - radius, step),
        )
        dims = tuple(max(0, (hi[i] - lo[i]) // step + 1) for i in range(3))
        grid = FreeGrid(step=step, lo=lo, dims=dims,  # type: ignore[arg-type]
                        blocked=bytearray(dims[0] * dims[1] * dims[2]))
        for box in solids:
            grid._mark(box.inflated(radius))
        return grid

    def _mark(self, box: Aabb) -> None:
        rng = []
        for i in range(3):
            a = max(0, _ceil_div(box.lo[i] - self.lo[i], self.step))
            b = min(self.dims[i] - 1, (box.hi[i] - self.lo[i]) // self.step)
            if b < a:
                return
            rng.append((a, b))
        ny, nz = self.dims[1], self.dims[2]
        for ix in range(rng[0][0], rng[0][1] + 1):
            for iy in range(rng[1][0], rng[1][1] + 1):
                base = (ix * ny + iy) * nz
                self.blocked[base + rng[2][0]: base + rng[2][1] + 1] = b"\x01" * (
                    rng[2][1] - rng[2][0] + 1
                )

    def index_of(self, p: Sequence[int]) -> Optional[Vec3]:
        out = []
        for i in range(3):
            q, r = divmod(p[i] - self.lo[i], self.step)
            if r != 0 or not 0 <= q < self.dims[i]:
                return None
            out.append(q)
        return tuple(out)  # type: ignore[return-value]

    def centre_of(self, node: Sequence[int]) -> Vec3:
        return tuple(self.lo[i] + node[i] * self.step for i in range(3))  # type: ignore

    def is_free(self, node: Sequence[int]) -> bool:
        ny, nz = self.dims[1], self.dims[2]
        return not self.blocked[(node[0] * ny + node[1]) * nz + node[2]]

    def nearby_free(self, p: Sequence[int], inflated: Sequence[Aabb],
                    *, span: int = 2) -> List[Vec3]:
        """Cell centres a point may legally be attached to.

        ``inflated`` is the obstacle set already grown by radius +
        clearance — the same geometry the grid was built from. A centre
        only counts if the straight segment from the point to it is free
        in that geometry, so a spawn 40 mm from a wall cannot be rounded
        to a cell on the far side of it.
        """
        anchor = [
            self.lo[i] + max(0, min(self.dims[i] - 1,
                                    round((p[i] - self.lo[i]) / self.step))) * self.step
            for i in range(3)
        ]
        found: List[Vec3] = []
        for dx in range(-span, span + 1):
            for dy in range(-span, span + 1):
                for dz in range(-span, span + 1):
                    cand = (anchor[0] + dx * self.step,
                            anchor[1] + dy * self.step,
                            anchor[2] + dz * self.step)
                    node = self.index_of(cand)
                    if node is None or not self.is_free(node):
                        continue
                    if segment_free(p, cand, inflated):
                        found.append(node)
        return found

    def connected(self, starts: Iterable[Vec3], goals: Iterable[Vec3]) -> bool:
        goal_set = set(goals)
        if not goal_set:
            return False
        seen = bytearray(len(self.blocked))
        ny, nz = self.dims[1], self.dims[2]
        queue: deque = deque()
        for node in starts:
            idx = (node[0] * ny + node[1]) * nz + node[2]
            if not seen[idx]:
                seen[idx] = 1
                queue.append(node)
        if not queue:
            return False
        while queue:
            x, y, z = queue.popleft()
            if (x, y, z) in goal_set:
                return True
            for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0),
                               (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                nx_, ny_, nz_ = x + dx, y + dy, z + dz
                if not (0 <= nx_ < self.dims[0] and 0 <= ny_ < self.dims[1]
                        and 0 <= nz_ < self.dims[2]):
                    continue
                idx = (nx_ * ny + ny_) * nz + nz_
                if seen[idx] or self.blocked[idx]:
                    continue
                seen[idx] = 1
                queue.append((nx_, ny_, nz_))
        return False


def _ceil_div(a: int, b: int) -> int:
    return -((-a) // b)


def _ceil_to(v: int, step: int) -> int:
    return _ceil_div(v, step) * step


def _floor_to(v: int, step: int) -> int:
    return (v // step) * step


# --- distinction -----------------------------------------------------------

_PLANAR: Tuple[Tuple[int, int, int, int], ...] = (
    (1, 0, 0, 1), (0, -1, 1, 0), (-1, 0, 0, -1), (0, 1, -1, 0),   # rotations
    (-1, 0, 0, 1), (1, 0, 0, -1), (0, 1, 1, 0), (0, -1, -1, 0),   # reflections
)


def _apply_planar(box: Aabb, m: Tuple[int, int, int, int]) -> Aabb:
    a, b, c, d = m
    xs = [a * box.lo[0] + b * box.lo[1], a * box.hi[0] + b * box.hi[1]]
    ys = [c * box.lo[0] + d * box.lo[1], c * box.hi[0] + d * box.hi[1]]
    return Aabb(lo=(min(xs), min(ys), box.lo[2]), hi=(max(xs), max(ys), box.hi[2]))


def planar_classes(boxes: Sequence[Aabb]) -> List[Tuple]:
    """All canonical forms of a layout under the profile's symmetry group.

    Translation in the plane is quotiented out by shifting the whole
    layout so its bounding box starts at the origin; z is left alone
    because gravity is not symmetric.
    """
    out: List[Tuple] = []
    for m in _PLANAR:
        moved = [_apply_planar(b, m) for b in boxes]
        minx = min(b.lo[0] for b in moved)
        miny = min(b.lo[1] for b in moved)
        shifted = sorted(
            (b.lo[0] - minx, b.lo[1] - miny, b.lo[2],
             b.hi[0] - minx, b.hi[1] - miny, b.hi[2])
            for b in moved
        )
        out.append(tuple(shifted))
    return out


def planar_equivalent(a: Sequence[Aabb], b: Sequence[Aabb]) -> bool:
    if len(a) != len(b):
        return False
    ref = planar_classes(a)[0]
    return any(cls == ref for cls in planar_classes(b))


def fingerprint(entries: Sequence[Dict]) -> List[Dict]:
    """Order- and name-independent geometry footprint.

    Each entry is ``{aabb_mm, ambient, diffuse, role}``. Names and XML
    order are deliberately absent: a renamed, reordered copy of a world
    must produce exactly these bytes.
    """
    return sorted(
        (
            {
                "aabb_mm": list(e["aabb_mm"]),
                "ambient": list(e["ambient"]),
                "diffuse": list(e["diffuse"]),
                "role": e["role"],
            }
            for e in entries
        ),
        key=lambda e: (e["aabb_mm"], e["ambient"], e["diffuse"], e["role"]),
    )
