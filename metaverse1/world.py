"""META-WORLD-2: a block map that scales without touching the frozen physics.

COMPOSE-1's world is one fixed 7x7 slab of three-metre cells.  META-WORLD-2
replaces that slab with a **lattice of regions**, so extent, density and
variety can grow, while the cognitive packet keeps its 8-bit fields:

* a region holds at most ``REGION_CAPACITY`` cells, so a **local** index fits
  in one byte — that is what ``seq`` identifies, local state, never the raw
  world index;
* the region itself is one more byte, the ``region`` field ``fusion1.core``
  already carries;
* everything above that — lattice coordinates, templates, simulator object
  ids, orientation — lives **outside** the packet, in this module, and never
  reaches Q, CAM or T.

``MetaSpace`` is written against the region lattice, not derived from
``compose1_v3.Space``.  That is deliberate: the equivalence bench compares the
two implementations, and a subclass would make that comparison unable to fail.

Nothing here is imported by the agent.  Units are three-metre cells.
"""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable, Optional

from echoai.nexus0.compose1.space import DIRECTIONS, add
from echoai.nexus0.fusion1.core import packet

CELL_MM = 3000
ALTITUDE_MM = 2500

#: One byte of local index per region, so ``seq`` never needs a ninth bit.
REGION_CAPACITY = 256
#: One byte of region id, the field ``fusion1.core.packet`` already reserves.
MAX_REGIONS = 256

MOVE_COST, WAIT_COST = 4, 1
ENERGY_LOW, ENERGY_FULL = 30, 240


class WorldError(ValueError):
    """A world that would break an 8-bit field is refused, not truncated."""


@dataclass(frozen=True)
class Region:
    """One addressable block of cells.

    ``origin`` is the lattice cell of the region's lower corner, in cells.
    ``ident`` is the byte that travels in the packet; the lattice coordinate
    it came from stays here and never enters the policy.
    """

    ident: int
    origin: tuple[int, int]
    width: int
    height: int
    template: str = "room"

    def __post_init__(self) -> None:
        if not 0 <= self.ident < MAX_REGIONS:
            raise WorldError(f"region id {self.ident} does not fit one byte")
        if self.width < 1 or self.height < 1:
            raise WorldError("region must have positive extent")
        if self.width * self.height > REGION_CAPACITY:
            raise WorldError(
                f"region {self.ident} holds {self.width * self.height} cells; "
                f"a local index must fit one byte (max {REGION_CAPACITY})")

    def contains(self, cell) -> bool:
        x, y = cell[0] - self.origin[0], cell[1] - self.origin[1]
        return 0 <= x < self.width and 0 <= y < self.height

    def local_index(self, cell) -> int:
        """0..255 within this region.  This is what ``seq`` identifies."""
        x, y = cell[0] - self.origin[0], cell[1] - self.origin[1]
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise WorldError(f"cell {cell} is not in region {self.ident}")
        return y * self.width + x

    def cells(self) -> Iterable[tuple[int, int, int]]:
        for y in range(self.height):
            for x in range(self.width):
                yield (self.origin[0] + x, self.origin[1] + y, 0)


class BlockMap:
    """The lattice.  Holds regions and answers which region owns a cell."""

    def __init__(self, regions: Iterable[Region]):
        self.regions = list(regions)
        if not self.regions:
            raise WorldError("a map needs at least one region")
        if len(self.regions) > MAX_REGIONS:
            raise WorldError(f"{len(self.regions)} regions exceed one byte")
        idents = [region.ident for region in self.regions]
        if len(set(idents)) != len(idents):
            raise WorldError("region ids must be unique")
        self._owner: dict[tuple[int, int, int], Region] = {}
        for region in self.regions:
            for cell in region.cells():
                if cell in self._owner:
                    raise WorldError(f"regions overlap at {cell}")
                self._owner[cell] = region

    def __contains__(self, cell) -> bool:
        return tuple(cell) in self._owner

    def region_of(self, cell) -> Region:
        try:
            return self._owner[tuple(cell)]
        except KeyError:
            raise WorldError(f"cell {tuple(cell)} belongs to no region") from None

    def address(self, cell) -> tuple[int, int]:
        """(region byte, local index byte) — the whole cognitive address."""
        region = self.region_of(cell)
        return region.ident, region.local_index(cell)

    def cells(self) -> set[tuple[int, int, int]]:
        return set(self._owner)

    @property
    def size(self) -> tuple[int, int]:
        cells = self._owner
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        return (max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)


def minimal_regions() -> list[Region]:
    """The COMPOSE-1 slab, expressed as one region.

    Seven by seven is 49 cells, well inside one byte of local index, so the
    certified world is simply the smallest case of the lattice.
    """
    return [Region(ident=0, origin=(-1, -3), width=7, height=7, template="room")]


def wide_regions(regions_x: int, regions_y: int) -> list[Region]:
    """A lattice of COMPOSE-1-sized rooms, laid out left to right."""
    if regions_x < 1 or regions_y < 1:
        raise WorldError("a lattice needs at least one region per axis")
    if regions_x * regions_y > MAX_REGIONS:
        raise WorldError(f"{regions_x}x{regions_y} regions exceed one byte")
    out = []
    for ry in range(regions_y):
        for rx in range(regions_x):
            out.append(Region(ident=ry * regions_x + rx,
                              origin=(-1 + rx * 7, -3 + ry * 7),
                              width=7, height=7,
                              template="room" if (rx + ry) % 2 == 0 else "hall"))
    return out


class MetaSpace:
    """A mission world over a block map.

    The public surface matches what the COMPOSE-1 consumer already uses —
    ``scan``, ``step``, ``path_distance``, ``oracle_distance``,
    ``home_distance`` — because META-WORLD-2 may enlarge the world but may not
    change the contract the certified benches were measured against.
    """

    def __init__(self, seed, condition="static", *, regions=None, detail=0):
        rng = random.Random(seed)
        self.seed = seed
        self.condition = condition
        self.detail = int(detail)
        self.rotation = rng.randrange(4)
        self.wall_x = rng.choice((1, 2, 3))
        self.gap_y = rng.choice((-2, -1, 1, 2))
        self.blocks = BlockMap(minimal_regions() if regions is None else regions)
        self.start = (0, 0, 0)
        self.goal = self.rotate((4, 0, 0))
        self.pos = self.start
        self.steps = self.collisions = 0
        self.energy = ENERGY_LOW if condition == "low_energy" else ENERGY_FULL
        self.domain = {self.rotate(cell) for cell in self.blocks.cells()}
        self.solids = self.make_solids(None if condition == "closed" else self.gap_y)
        self.camera_solids = set(self.solids)
        self.moved = False

    # ------------------------------------------------------------- geometry

    def rotate(self, p):
        x, y, z = p
        for _ in range(self.rotation):
            x, y = -y, x
        return x, y, z

    def make_solids(self, gap):
        """Perimeter of the whole map, plus the dividing wall of each region.

        With one region this is exactly the COMPOSE-1 geometry; with more, the
        same rule tiles, which is the point: no branch by world name.
        """
        cells = self.blocks.cells()
        xs = [c[0] for c in cells]
        ys = [c[1] for c in cells]
        low_x, high_x, low_y, high_y = min(xs), max(xs), min(ys), max(ys)
        out = set()
        for cell in cells:
            x, y, _ = cell
            wall = x in (low_x, high_x) or y in (low_y, high_y)
            if not wall:
                region = self.blocks.region_of(cell)
                local_wall_x = region.origin[0] + 1 + self.wall_x
                wall = x == local_wall_x and y != region.origin[1] + 3 + gap \
                    if gap is not None else x == local_wall_x
            if wall:
                out.add(self.rotate(cell))
        return out

    def visible(self, target):
        # Discrete ray through cell centres; occupied endpoints remain visible.
        dx, dy = target[0] - self.pos[0], target[1] - self.pos[1]
        n = max(abs(dx), abs(dy)) * 12
        if not n:
            return True
        for step in range(n):
            p = (self.pos[0] + round(dx * step / n),
                 self.pos[1] + round(dy * step / n), 0)
            if p != target and p in self.solids:
                return False
        return True

    # ---------------------------------------------------------- observation

    def address(self, cell) -> tuple[int, int]:
        """Cognitive address of a world cell, after undoing the rotation."""
        return self.blocks.address(self.unrotate(cell))

    def unrotate(self, p):
        x, y, z = p
        for _ in range((4 - self.rotation) % 4):
            x, y = -y, x
        return x, y, z

    def scan(self):
        cells = []
        for p in sorted(self.domain):
            if not self.visible(p):
                continue
            region, _local = self.address(p)
            cells.append(dict(
                position=list(p),
                depth=packet(int(p in self.camera_solids), 40, region=region).hex(),
                lidar=packet(int(p in self.solids), 40, region=region).hex()))
        self.camera_solids = set(self.solids)
        return dict(now_ns=self.steps * 25_000_000, odometry=list(self.pos),
                    energy=self.energy, station_observed=self.pos == self.goal,
                    cells=cells)

    # --------------------------------------------------------------- action

    def step(self, action):
        if type(action) is not int or not 0 <= action < 7:
            raise ValueError("action")
        before = self.pos
        target = add(before, DIRECTIONS[action])
        blocked = target not in self.domain or target in self.solids
        self.collisions += blocked
        if not blocked:
            self.pos = target
        cost = WAIT_COST if action == 6 else MOVE_COST
        self.steps += 1
        self.energy -= cost
        if self.condition == "dynamic" and self.steps >= 2 and not self.moved:
            old_gap = self.rotate((self.wall_x, self.gap_y, 0))
            if self.pos != old_gap:
                self.solids = self.make_solids(-self.gap_y)
                self.moved = True
        return dict(before=list(before), after=list(self.pos),
                    delta=[b - a for a, b in zip(before, self.pos)],
                    blocked=blocked, cost=cost, energy=self.energy)

    # ------------------------------------------------------------ distances

    def home_distance(self, p):
        return self.path_distance(p, self.start)

    def path_distance(self, start, goal):
        if start not in self.domain or start in self.solids:
            return None
        queue = deque([(start, 0)])
        seen = {start}
        while queue:
            p, n = queue.popleft()
            if p == goal:
                return n
            for v in DIRECTIONS[:4]:
                q = add(p, v)
                if q in self.domain and q not in self.solids and q not in seen:
                    seen.add(q)
                    queue.append((q, n + 1))
        return None

    def oracle_distance(self):
        return self.path_distance(self.start, self.goal)

    # --------------------------------------------------------------- report

    def describe(self) -> dict:
        """What this world is, for the record.  Never handed to the agent."""
        width, height = self.blocks.size
        return dict(seed=self.seed, condition=self.condition, detail=self.detail,
                    regions=len(self.blocks.regions),
                    cells=len(self.domain), solids=len(self.solids),
                    size_cells=[width, height],
                    size_m=[width * CELL_MM / 1000, height * CELL_MM / 1000],
                    rotation=self.rotation, wall_x=self.wall_x, gap_y=self.gap_y,
                    templates=sorted({r.template for r in self.blocks.regions}))
