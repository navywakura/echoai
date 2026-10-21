"""Shared gridworlds for ENJAMBRE-1 (redesign): several agents in the same world, integer state.

The only module that knows what a cell *is*. Agents see opaque ids through one bijection for every
world (a common language, regime A1), except where a world declares a local exception. Mechanics
follow MiniGrid (turn L/R, forward F, pick P, drop D, toggle T; headings 0 +x, 1 +y, 2 -x, 3 -y).

Kinds of world (one seed draws one layout):
    door      a wall with a locked door; the key lies on the start side; goal behind
    lava      a column of lava with one gap; goal behind
    plate     a wall with a gate that is open only while someone stands on the plate; goal behind
    local     like lava with two gaps; one is guarded by a decorative tile, which burns here
              (it is harmless everywhere else)

Every world has decorative tiles on the floor. Teammates are drawn as one id; an agent never sees
itself. Turns rotate between the agents still in the world; when one reaches the goal the team
has solved the world and the others' episodes end (truncated, no outcome). Lava (and the local
tile) ends only that agent's episode. No floats.
"""
from __future__ import annotations

import random
import threading
from typing import Dict, List, Optional, Tuple

from ..memx.world import Obs

FLOOR, WALL, GOAL, LAVA, KEY = ("mg", 1, 0, 0), ("mg", 2, 5, 0), ("mg", 8, 1, 0), ("mg", 9, 0, 0), ("mg", 5, 4, 0)
LOCKED, CLOSED, OPEN = ("mg", 4, 4, 2), ("mg", 4, 4, 1), ("mg", 4, 4, 0)
TILE, PLATE, GATE, GATE_OPEN, MATE = ("mg", 3, 2, 0), ("co", 0), ("co", 1), ("co", 2), ("co", 3)
CLASSES = (FLOOR, WALL, GOAL, LAVA, KEY, LOCKED, CLOSED, OPEN, TILE, PLATE, GATE, GATE_OPEN, MATE)
KINDS = ("door", "lava", "plate", "local")
SECRET = 0xC0_E7A1
DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))
PASSABLE = {FLOOR, GOAL, LAVA, OPEN, TILE, PLATE, GATE_OPEN}


def language(seed: int = SECRET) -> Dict[Tuple, int]:
    ids = random.Random(seed).sample(range(1, 256), len(CLASSES))
    return dict(zip(CLASSES, ids))


def layout(kind: str, seed: int) -> Dict:
    """Draw until every agent has a start with a way out (deterministic: same seed, same world)."""
    rng = random.Random(seed)
    while True:
        L = _draw(kind, rng)
        if len(L["starts"]) >= 4:
            return L


def _draw(kind: str, rng: random.Random) -> Dict:
    W, H = rng.choice((9, 11)), rng.choice((7, 9))
    cells = [[FLOOR] * W for _ in range(H)]
    for x in range(W):
        cells[0][x] = cells[H - 1][x] = WALL
    for y in range(H):
        cells[y][0] = cells[y][W - 1] = WALL
    c = rng.randrange(3, W - 3)                                 # dividing column
    gap = rng.randrange(1, H - 1)
    for y in range(1, H - 1):
        cells[y][c] = LAVA if kind in ("lava", "local") else WALL
    cells[gap][c] = {"door": LOCKED, "plate": GATE}.get(kind, FLOOR)
    gap2 = rng.choice([y for y in range(1, H - 1) if abs(y - gap) >= 2]) if kind == "local" else None
    keep = {(c - 1, gap), (c + 1, gap)}                         # the way through stays clear (review 21/10)
    if gap2 is not None:
        keep |= {(c - 1, gap2), (c + 1, gap2)}
    left = [(x, y) for x in range(1, c) for y in range(1, H - 1) if (x, y) not in keep]
    right = [(x, y) for x in range(c + 1, W - 1) for y in range(1, H - 1) if (x, y) not in keep]
    rng.shuffle(left)
    rng.shuffle(right)
    gx, gy = right.pop()
    cells[gy][gx] = GOAL
    plate = None
    if kind == "door":
        kx, ky = left.pop()
        cells[ky][kx] = KEY
    if kind == "plate":
        plate = left.pop()
        cells[plate[1]][plate[0]] = PLATE
    for x, y in left[:2] + right[:2]:                           # decorative tiles, both sides
        cells[y][x] = TILE
    if kind == "local":                                         # a second gap, guarded by a tile
        cells[gap2][c] = FLOOR
        cells[gap2][c - 1] = TILE
    hot = {TILE} if kind == "local" else set()
    safe = {FLOOR, GOAL, TILE, PLATE, KEY, LOCKED, GATE} - hot  # what a way out may cross
    out, q = {(gx, gy)}, [(gx, gy)]
    while q:
        x, y = q.pop()
        for dx, dy in DIRS:
            n = (x + dx, y + dy)
            if n not in out and cells[n[1]][n[0]] in safe:
                out.add(n)
                q.append(n)
    starts = [s for s in left[2:] if cells[s[1]][s[0]] == FLOOR and s in out]
    return {"W": W, "H": H, "cells": cells, "starts": starts, "plate": plate, "gate": (c, gap),
            "hot": hot}


class CoopWorld:
    """One shared world for the agents of one round; each agent drives it through its View."""

    def __init__(self, kind: str, seed: int, n: int, ids: Dict[Tuple, int], max_steps: int = 300):
        self.kind, self.seed, self.n, self.ids, self.max_steps = kind, seed, n, ids, max_steps
        L = layout(kind, seed)
        self.W, self.H, self.cells = L["W"], L["H"], [list(r) for r in L["cells"]]
        self.plate, self.gate, self.hot = L["plate"], L["gate"], L["hot"]
        rng = random.Random(seed * 7 + n)
        self.pos = [L["starts"][i] for i in range(n)]
        self.dir = [rng.randrange(4) for _ in range(n)]
        self.hand: List[Optional[Tuple]] = [None] * n
        self.alive = [True] * n
        self.steps = [0] * n
        self.solved_by: Optional[int] = None
        self.turn = 0
        self.cv = threading.Condition()
        self.board: Dict = {}                                    # help requests posted in this world
        self.needs_help = False                                  # someone knew how, but was alone
        self._gate()

    # -- shared state ------------------------------------------------------------
    def _gate(self) -> None:
        if self.plate is None:
            return
        x, y = self.gate
        held = any(self.alive[i] and self.pos[i] == self.plate for i in range(self.n))
        inside = any(self.alive[i] and self.pos[i] == (x, y) for i in range(self.n))
        self.cells[y][x] = GATE_OPEN if held or inside else GATE

    def obs(self, i: int) -> Obs:
        grid = [[self.ids[c] for c in row] for row in self.cells]
        for j in range(self.n):
            if j != i and self.alive[j]:
                x, y = self.pos[j]
                grid[y][x] = self.ids[MATE]
        done = self.solved_by is not None or not self.alive[i] or self.steps[i] >= self.max_steps
        term = not self.alive[i] or self.solved_by == i
        reward = 1000 - self.steps[i] if self.solved_by == i else 0
        return Obs(tuple(tuple(r) for r in grid), self.pos[i], self.dir[i],
                   self.ids[self.hand[i]] if self.hand[i] else 0, reward, term, done and not term)

    def _active(self, i: int) -> bool:
        return self.alive[i] and self.solved_by is None and self.steps[i] < self.max_steps

    def _advance(self) -> None:
        for k in range(1, self.n + 1):
            j = (self.turn + k) % self.n
            if self._active(j):
                self.turn = j
                return

    def act(self, i: int, prim: str) -> None:
        x, y = self.pos[i]
        dx, dy = DIRS[self.dir[i]]
        fx, fy = x + dx, y + dy
        front = self.cells[fy][fx]
        mate = any(j != i and self.alive[j] and self.pos[j] == (fx, fy) for j in range(self.n))
        if prim == "L":
            self.dir[i] = (self.dir[i] - 1) % 4
        elif prim == "R":
            self.dir[i] = (self.dir[i] + 1) % 4
        elif prim == "F" and front in PASSABLE and not mate:
            self.pos[i] = (fx, fy)
            if front == GOAL:
                self.solved_by = i
            elif front == LAVA or front in self.hot:
                self.alive[i] = False
        elif prim == "P" and front == KEY and self.hand[i] is None and not mate:
            self.hand[i], self.cells[fy][fx] = KEY, FLOOR
        elif prim == "D" and front == FLOOR and self.hand[i] is not None and not mate:
            self.cells[fy][fx], self.hand[i] = self.hand[i], None
        elif prim == "T":
            if front == LOCKED and self.hand[i] == KEY:
                self.cells[fy][fx] = OPEN
            elif front == CLOSED:
                self.cells[fy][fx] = OPEN
            elif front == OPEN and not mate:
                self.cells[fy][fx] = CLOSED
        self.steps[i] += 1
        if not self.alive[i] or self.steps[i] >= self.max_steps:
            self.board.pop(i, None)                              # withdrawn in its own turn (review 21/10)
        self._gate()


class View:
    """What one agent holds: reset/step like a single-agent world, turns enforced underneath."""

    absolute = False
    acts = ("ENTER", "PICK", "TOGGLE")
    prims = ("L", "R", "F", "P", "D", "T")

    def __init__(self, world: CoopWorld, i: int):
        self.w, self.i = world, i

    def reset(self) -> Obs:
        with self.w.cv:
            self.w.cv.wait_for(lambda: self.w.turn == self.i or not self.w._active(self.i))
            return self.w.obs(self.i)

    def step(self, prim: str) -> Obs:
        w = self.w
        with w.cv:
            w.cv.wait_for(lambda: w.turn == self.i or not w._active(self.i))
            if w._active(self.i):
                w.act(self.i, prim)
                w._advance()
                w.cv.notify_all()
            w.cv.wait_for(lambda: w.turn == self.i or not w._active(self.i))
            return w.obs(self.i)

    def leave(self) -> None:
        w = self.w
        with w.cv:
            w.steps[self.i] = w.max_steps                       # out of the rotation
            w.board.pop(self.i, None)
            if w.turn == self.i:
                w._advance()
            w.cv.notify_all()

    def frame(self):
        return None

    def close(self) -> None:
        pass


def play_together(world: CoopWorld, agents: List) -> List[Dict]:
    """Run one episode of every agent in the shared world, one thread each, strict turns."""
    out: List[Optional[Dict]] = [None] * len(agents)

    def go(i: int) -> None:
        v = View(world, i)
        try:
            out[i] = agents[i].run(v)
        finally:
            v.leave()

    ts = [threading.Thread(target=go, args=(i,)) for i in range(len(agents))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return out
