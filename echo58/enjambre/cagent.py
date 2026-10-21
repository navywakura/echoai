"""The B v3 agent (all pieces on) plus what a teammate needs in a shared world (ENJAMBRE-1 redesign).

    remote   after entering an id p, the cells elsewhere whose id changed at that moment (ids that
             move by themselves excluded) are booked as "p changes g" in the private memory
    ask      if a cell of id g blocks the way, the reader knows that some id p on the board
             changes g, and a teammate shares the world (the agent is told how many do): post a request (p, g) on the world's board and
             wait next to g; give up after WAIT steps and flag the world as needing help
    hold     if a teammate's request is on the board: walk to the nearest cell of id p and stay on
             it until the request is withdrawn

The requester only asks with knowledge; the helper only needs the request (it carries p).
Integers only; no names.
"""
from __future__ import annotations

from typing import Dict

from ..b3.policy import PIECES, PAgent, reach
from ..memx.agent import DIRS

WAIT = 60


class CAgent(PAgent):
    def __init__(self, *a, me: int = 0, private=None, **k):
        super().__init__(*a, pieces=frozenset(PIECES), **k)
        self.me, self.private = me, private
        self.counters = {"asked": 0, "held": 0, "remote": 0}

    def run(self, world, max_steps: int = 100000, frames=None) -> Dict:
        self.view = world
        self.moved = set()
        self.waited = 0
        self.flip = 0
        r = super().run(world, max_steps, frames)
        r.update(self.counters)
        return r

    # -- learning: what my entering changed elsewhere --------------------------------
    def _watch(self, old, new, intent) -> None:
        movers = set(self.auto)                       # what was known to move before this step
        super()._watch(old, new, intent)
        # an id moves by itself only if it leaves one cell and shows up in another; a cell that
        # merely changes id in place (something opened elsewhere) is not a mover
        gone, came = {}, {}
        for y, (ro, rn) in enumerate(zip(old.grid, new.grid)):
            for x, (a, b) in enumerate(zip(ro, rn)):
                if a != b:
                    gone.setdefault(a, set()).add((x, y))
                    came.setdefault(b, set()).add((x, y))
        self.moved.update(i for i in gone if i in came and came[i] != gone[i])
        self.auto &= self.moved
        if self.private is None or intent is None or intent[0] != "ENTER" or new.pos == old.pos:
            return
        changed = set()
        for y, (ro, rn) in enumerate(zip(old.grid, new.grid)):
            for x, (a, b) in enumerate(zip(ro, rn)):
                if a != b and (x, y) not in (old.pos, new.pos) and a not in movers and b not in movers:
                    changed.add(a)
        self.private.remote_observe(intent[2], changed)
        self.counters["remote"] += bool(changed)

    # -- control ------------------------------------------------------------------------
    def _wait(self):
        self.flip ^= 1
        return ("L" if self.flip else "R"), None

    def _path_to(self, obs, world, targets, passable):
        """Next primitive towards entering the nearest cell in `targets` (None if none reachable)."""
        r = reach(obs.pos, obs.grid, passable)
        best = None
        for t in sorted(targets):
            for dx, dy in DIRS:
                n = (t[0] - dx, t[1] - dy)
                if n in r:
                    d, c = 0, n
                    while r[c] is not None:
                        c, d = r[c], d + 1
                    if best is None or (d, n, t) < best:
                        best = (d, n, t)
        if best is None:
            return None
        _, n, t = best
        if n == obs.pos:
            return n, t, self._toward(obs, world, t, "ENTER")
        step = n
        while r[step] != obs.pos:
            step = r[step]
        return n, t, self._toward(obs, world, step, "ENTER")

    def _decide(self, obs, world):
        board = getattr(getattr(world, "w", None), "board", None)
        if board is None:
            return super()._decide(obs, world)
        grid = obs.grid
        H, W = len(grid), len(grid[0])

        def passable(x, y):
            return self.belief(grid[y][x], "ENTER", 0) == "PASS"
        cells: Dict[int, list] = {}
        for y in range(H):
            for x in range(W):
                cells.setdefault(grid[y][x], []).append((x, y))

        # hold: a teammate asked for someone to stand on p (between two askers, the lower index is helped)
        for j, (p, g, cg) in sorted(board.items()):
            if j == self.me or (self.me in board and j > self.me):
                continue
            board.pop(self.me, None)
            here = grid[obs.pos[1]][obs.pos[0]]
            if here == p:
                self.counters["held"] += 1
                return self._wait()
            go = self._path_to(obs, world, cells.get(p, []), passable)
            if go is not None:
                return go[2]

        # ask: a closed g in the way, p changes g, a teammate in the world
        mine = board.get(self.me)
        if mine is not None:
            p, g, cg = mine
            if obs.pos == cg or self.waited >= WAIT:
                del board[self.me]                         # passed, or given up
            elif grid[cg[1]][cg[0]] != g:
                return super()._decide(obs, world)         # open: go through, keep the request until inside
            else:
                self.waited += 1
                go = self._path_to(obs, world, [cg], passable)
                if go is not None and go[0] != obs.pos:
                    return go[2]
                return self._wait()
        elif self.waited < WAIT:
            mates = world.w.n > 1                          # told how many share the world (declared)
            for g, cgs in sorted(cells.items()):
                if passable(*cgs[0]):
                    continue
                ps = [p for p in cells if p != g and self.source.knows(p, g)]
                if not ps:
                    continue
                go = self._path_to(obs, world, cgs, passable)
                if go is None:
                    continue
                if not mates:
                    world.w.needs_help = True
                    break
                board[self.me] = (ps[0], g, go[1])
                self.counters["asked"] += 1
                return go[2]
        return super()._decide(obs, world)
