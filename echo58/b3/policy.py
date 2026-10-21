"""B v3 prototype (development only): track A's agent with the hand-key bug fixed and switchable,
nameless policy pieces that ECHO may turn on from signals it measures in its own failed episodes.

Base fix (not a menu item): a failed attempt to pick while holding counts, for this episode,
against picking that id (the policy checks the empty-hand key; the outcome was booked under
the full hand, so the agent never learnt it had failed).

Pieces (each a generic rule over roles, no names):
    commit       do not drop what you hold to swap it for something already picked up in this episode while the held thing
                 may still open something reachable (walls, the commonest border id, excluded)
    no_retoggle  do not toggle again a cell you already changed in this episode
    clear        drop where the drop does not cut you off from cells you could reach before
    wander       when nothing is left to try, walk to the least visited reachable cell
    no_repick    do not pick up again what you dropped yourself on that cell when nothing has
                 changed since (no cell opened, nothing new picked)

Signals (per failed episode): `pickdrop` (one id picked >= 3 times), `retoggle` (one cell changed
by toggling >= 3 times), `blockdrop` (a drop shrank the reachable area), `idle` (>= 20 idle steps
in a row). Integers only.
"""
from __future__ import annotations

from collections import Counter, deque
from typing import Dict

from ..acumula.agent import XAgent
from ..memx.agent import DIRS, Agent

PIECES = ("commit", "no_retoggle", "clear", "wander", "no_repick")
SIGNAL_PIECE = {"pickdrop": "commit", "retoggle": "no_retoggle", "blockdrop": "clear", "idle": "wander"}


def reach(start, grid, passable, blocked=None):
    H, W = len(grid), len(grid[0])
    seen = {start: None}
    q = deque([start])
    while q:
        c = q.popleft()
        for dx, dy in DIRS:
            n = (c[0] + dx, c[1] + dy)
            if 0 <= n[0] < W and 0 <= n[1] < H and n not in seen and n != blocked and passable(*n):
                seen[n] = c
                q.append(n)
    return seen


class PAgent(XAgent):
    def __init__(self, *a, pieces=frozenset(), **k):
        super().__init__(*a, **k)
        self.pieces = frozenset(pieces)

    def run(self, world, max_steps: int = 100000, frames=None) -> Dict:
        self.ban: Dict = {}                  # (id, act) -> hand it applies to (None: any)
        self.cur_hand = 0
        self.opened = Counter()              # cells changed by my own toggles
        self.picked = Counter()
        self.visits = Counter()
        self.idle = self.max_idle = self.blockdrops = 0
        self.steps_n = 0
        self.clear_walk = Counter()
        self.progress = 0                    # cells opened + ids picked for the first time
        self.dropped: Dict = {}              # cell -> (id, progress when dropped)
        self.repick_ban: Dict = {}           # id -> progress at which the ban was set
        r = super().run(world, max_steps, frames)
        sig = set()
        if not r["success"]:
            if self.picked and max(self.picked.values()) >= 3:
                sig.add("pickdrop")
            if self.opened and max(self.opened.values()) >= 3:
                sig.add("retoggle")
            if self.blockdrops:
                sig.add("blockdrop")
            if self.max_idle >= 20:
                sig.add("idle")
        r["signals"] = sorted(sig)
        return r

    def belief(self, ident, act, hand):
        if act == "PICK" and self.repick_ban.get(ident, -1) == getattr(self, "progress", None):
            return "NOOP"
        b = self.ban.get((ident, act), 0)
        if b is None or (b and b == self.cur_hand):
            return "NOOP"
        return super().belief(ident, act, hand)

    def _outcome(self, old, new, intent) -> str:
        out = super()._outcome(old, new, intent)
        act, cell, ident, hand, _ = intent
        if act == "PICK" and hand and out == "NOOP":                 # base fix (hand key)
            self.E.setdefault((ident, "PICK", 0), [0] * 6)[1] += 1
        if act == "PICK" and out == "PICK":
            if not self.picked[ident]:
                self.progress += 1
            self.picked[ident] += 1
            d = self.dropped.pop(cell, None)
            if d is not None and d == (ident, self.progress) and "no_repick" in self.pieces:
                self.repick_ban[ident] = self.progress
        if act == "TOGGLE" and out == "OPEN":
            self.opened[cell] += 1
            self.progress += 1
        return out

    def _useful(self, h, obs) -> bool:
        """Something reachable, other than the walls (commonest border id), the held id might still open."""
        wall = max(self.border, key=lambda i: (self.border[i], -i), default=None)
        grid = obs.grid

        def passable(x, y):
            return self.belief(grid[y][x], "ENTER", 0) == "PASS"
        H, W = len(grid), len(grid[0])
        near = set()
        for c in reach(obs.pos, grid, passable):
            for dx, dy in DIRS:
                x, y = c[0] + dx, c[1] + dy
                if 0 <= x < W and 0 <= y < H:
                    near.add(grid[y][x])
        return any(t not in (h, wall) and self.belief(t, "ENTER", 0) != "PASS"
                   and self.belief(t, "TOGGLE", h) in (None, "OPEN") for t in near)

    def _drop(self, obs, world, grid, ok, passable, avoid=None):
        self._drop_for = avoid
        if "clear" not in self.pieces or world.absolute:
            return super()._drop(obs, world, grid, ok, passable, avoid)
        before = reach(obs.pos, grid, passable)
        floor = max((i for i in self.counts if self.belief(i, "ENTER", 0) == "PASS"),
                    key=lambda i: (self.counts[i], -i), default=None)
        for dx, dy in DIRS:
            n = (obs.pos[0] + dx, obs.pos[1] + dy)
            if n != avoid and ok(*n) and grid[n[1]][n[0]] == floor:
                if len(reach(obs.pos, grid, passable, blocked=n)) == len(before) - 1:
                    return self._face(obs, n, ("D", ("DROP", n, floor, obs.hand, 0)))
        # no harmless neighbour: walk (at most 8 steps per held id) to the nearest reachable cell that has one
        self.clear_walk[obs.hand] += 1
        for c in [] if self.clear_walk[obs.hand] > 8 else sorted(before, key=lambda c: (abs(c[0] - obs.pos[0]) + abs(c[1] - obs.pos[1]), c)):
            if c == obs.pos:
                continue
            for dx, dy in DIRS:
                n = (c[0] + dx, c[1] + dy)
                if n != avoid and ok(*n) and grid[n[1]][n[0]] == floor and n != obs.pos:
                    if len(reach(c, grid, passable, blocked=n)) == len(reach(c, grid, passable)) - 1:
                        step = c
                        while before[step] != obs.pos:
                            step = before[step]
                        return self._toward(obs, world, step, "ENTER")
        return super()._drop(obs, world, grid, ok, passable, avoid)

    def _face(self, obs, cell, action):
        out = Agent._face(obs, cell, action)
        if out is not action:
            self._turned = True
        return out

    def _decide(self, obs, world):
        self.cur_hand = obs.hand
        self.visits[obs.pos] += 1
        for _ in range(8):
            self._drop_for = None
            self._turned = False
            prim, intent = super()._decide(obs, world)
            tgt = obs.grid[self._drop_for[1]][self._drop_for[0]] if self._drop_for is not None else None
            if (intent and intent[0] == "DROP" and tgt is not None and "commit" in self.pieces
                    and self.picked[tgt] and self._useful(obs.hand, obs)):
                self.ban[(tgt, "PICK")] = obs.hand
            elif intent and intent[0] == "TOGGLE" and "no_retoggle" in self.pieces and self.opened[intent[1]]:
                self.ban[(intent[2], "TOGGLE")] = None
            else:
                break
            self.belief_cache = {}
        else:                                # last pass set a ban: decide once more under it
            self._drop_for = None
            self._turned = False
            prim, intent = super()._decide(obs, world)
        if intent and intent[0] == "DROP" and not world.absolute:
            self.dropped[intent[1]] = (obs.hand, self.progress)
            def passable(x, y):
                return self.belief(obs.grid[y][x], "ENTER", 0) == "PASS"
            if len(reach(obs.pos, obs.grid, passable, blocked=intent[1])) < len(reach(obs.pos, obs.grid, passable)) - 1:
                self.blockdrops += 1
        idle = prim == "L" and intent is None and not self._turned and self.steps_n > 0   # nothing to do, not a turn to face
        self.steps_n += 1
        self.idle = self.idle + 1 if idle else 0
        self.max_idle = max(self.max_idle, self.idle)
        if idle and "wander" in self.pieces and self.idle >= 3 and not world.absolute:
            def passable(x, y):
                return self.belief(obs.grid[y][x], "ENTER", 0) == "PASS"
            r = reach(obs.pos, obs.grid, passable)
            cells = [c for c in r if c != obs.pos]
            if cells:
                t = min(cells, key=lambda c: (self.visits[c], abs(c[0] - obs.pos[0]) + abs(c[1] - obs.pos[1]), c))
                step = t
                while r[step] != obs.pos:
                    step = r[step]
                return self._toward(obs, world, step, "ENTER")
        return prim, intent
