"""One fixed base policy for every arm; arms differ only in the memory they start with.

Each step the agent:
  1. goes for anything it believes is a GOAL (BFS over cells it believes PASS),
  2. otherwise probes the nearest (id, act) whose outcome it does not know,
  3. otherwise drops what it carries, otherwise idles.
Beliefs come first from what happened in this episode (counts, majority),
then from the starting memory (lower-bound rules), else unknown. Cells it
believes HURT or NOOP are never entered. Integers only; no names anywhere.
"""
from __future__ import annotations

import hashlib
import random
from collections import deque
from typing import Dict, List, Optional, Tuple

from .memory import OUTCOMES, Memory

DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))     # MiniGrid headings: 0 +x, 1 +y, 2 -x, 3 -y
ACT_ORDER = ("ENTER", "PICK", "TOGGLE")


def signature(ident: int, counts: Dict[int, int], border: Dict[int, int], auto: set) -> int:
    c = counts.get(ident, 0)
    cb = 0 if c <= 1 else 1 if c <= 4 else 2 if c <= 15 else 3
    b = border.get(ident, 0)
    bb = 0 if b == 0 else 1 if b * 2 < c else 2
    return (16 if ident in auto else 0) + cb * 4 + bb


class Marginal:
    """Vetoes as often as a real memory does, but on a coin that ignores what the key is.

    Only veto answers (HURT, NOOP) at the learned memory's per-mille rates; the
    coin is keyed by episode as well, so no id is vetoed in every world.
    """

    def __init__(self, rates: Dict[str, int], seed: int):
        self.rates = {k: rates.get(k, 0) for k in ("HURT", "NOOP")}
        self.seed = seed
        self.queries = 0
        self.hits = 0

    def recall(self, ident: int, sig: int, act: str, hand: int) -> Optional[str]:
        self.queries += 1
        h = hashlib.sha256(f"{self.seed}|{ident}|{act}|{hand}".encode()).digest()
        u = int.from_bytes(h[:4], "big") % 1000
        if u < self.rates["HURT"]:
            self.hits += 1
            return "HURT"
        if u < self.rates["HURT"] + self.rates["NOOP"]:
            self.hits += 1
            return "NOOP"
        return None


class Agent:
    def __init__(self, source=None, learn: Optional[Memory] = None):
        self.source = source                   # Memory, Marginal or None (frozen during exams)
        self.learn = learn                     # memory being trained, or None
        self.answers: Dict[str, int] = {}      # what the source answered (for the marginal arm)

    # -- one episode -------------------------------------------------------------
    def run(self, world, max_steps: int = 100000, frames: Optional[list] = None) -> Dict:
        self.E: Dict[Tuple, List[int]] = {}
        self.auto: set = set()
        obs = world.reset()
        steps = wasted = ret = 0
        result = {"success": 0, "harm": 0}
        if frames is not None:
            frames.append(world.frame())
        result.update(harm_probe=0, harm_auto=0, harm_other=0)
        while not obs.done and steps < max_steps:
            cause = "harm_other"
            self._scan(obs.grid)
            if steps == 0 and not world.absolute:
                prim, intent = "L", None                # look one tick first: what moves by itself?
            else:
                prim, intent = self._decide(obs, world)
            prior = self.belief(intent[2], intent[0], intent[3]) if intent and intent[0] != "DROP" else None
            new = world.step(prim)
            steps += 1
            ret += new.reward
            if frames is not None:
                frames.append(world.frame())
            self._watch(obs, new, intent)
            if intent is not None and intent[0] != "DROP":
                out = self._outcome(obs, new, intent)
                act, (x, y), ident, hand, sig = intent
                self.E.setdefault((ident, act, hand), [0] * len(OUTCOMES))[OUTCOMES.index(out)] += 1
                if self.learn is not None:
                    self.learn.observe(ident, sig, act, hand, out)
                wasted += out == "NOOP"
                if out == "HURT":
                    cause = "harm_auto" if ident in self.auto else "harm_probe" if prior is None else "harm_other"
            if new.terminated:
                result["success" if new.reward > 0 else "harm"] = 1
                if new.reward <= 0:
                    result[cause] = 1                     # exclusive and exhaustive split of harm
            obs = new
        result.update(steps=steps, wasted=wasted, ret=ret)
        return result

    # -- perception --------------------------------------------------------------
    def _scan(self, grid) -> None:
        H, W = len(grid), len(grid[0])
        counts: Dict[int, int] = {}
        border: Dict[int, int] = {}
        for y in range(H):
            for x in range(W):
                i = grid[y][x]
                counts[i] = counts.get(i, 0) + 1
                if x in (0, W - 1) or y in (0, H - 1):
                    border[i] = border.get(i, 0) + 1
        self.counts, self.border = counts, border
        self.sig_cache: Dict[int, int] = {}
        self.belief_cache: Dict[Tuple, Optional[str]] = {}
        self.recalled: Dict[Tuple, Optional[str]] = {}

    def sig(self, ident: int) -> int:
        s = self.sig_cache.get(ident)
        if s is None:
            s = self.sig_cache[ident] = signature(ident, self.counts, self.border, self.auto)
        return s

    def belief(self, ident: int, act: str, hand: int) -> Optional[str]:
        key = (ident, act, hand)
        if key in self.belief_cache:
            return self.belief_cache[key]
        c = self.E.get(key)
        if c:
            b = OUTCOMES[max(range(len(OUTCOMES)), key=lambda k: (c[k], -k))]
        elif self.source is not None:
            b = self.source.recall(ident, self.sig(ident), act, hand)
            self.answers[b or "NONE"] = self.answers.get(b or "NONE", 0) + 1
            self.recalled[key] = b
        else:
            b = None
        self.belief_cache[key] = b
        return b

    def _believed(self, ident: int, act: str, hand: int, verify: bool) -> Optional[str]:
        """In verify mode a remembered answer is testimony: unless it warns of harm, test it here."""
        b = self.belief(ident, act, hand)
        key = (ident, act, hand)
        if verify and b not in (None, "HURT") and key not in self.E and key in self.recalled:
            return None
        return b

    def _watch(self, old, new, intent) -> None:
        """Ids that change place without the agent acting on them move by themselves."""
        skip = {intent[1]} if intent is not None else set()
        involved = set()
        for y, (ro, rn) in enumerate(zip(old.grid, new.grid)):
            for x, (a, b) in enumerate(zip(ro, rn)):
                if a != b and (x, y) not in skip:
                    involved.update((a, b))
        if len(involved) >= 2:
            top = max(self.counts.get(i, 0) for i in involved)
            self.auto.update(i for i in involved if self.counts.get(i, 0) < top)

    @staticmethod
    def _outcome(old, new, intent) -> str:
        act, (x, y), ident, hand, sig = intent
        if new.terminated:
            return "GOAL" if new.reward > 0 else "HURT"
        if new.reward > 0:
            return "GOAL"
        if act == "ENTER":
            return "PASS" if new.pos != old.pos else "NOOP"
        if act == "PICK":
            return "PICK" if new.hand and new.hand != old.hand else "NOOP"
        return "OPEN" if new.grid[y][x] != ident else "NOOP"

    # -- control -----------------------------------------------------------------
    def _decide(self, obs, world):
        grid, pos = obs.grid, obs.pos
        H, W = len(grid), len(grid[0])

        def ok(x, y):
            return 0 <= x < W and 0 <= y < H

        def passable(x, y):
            return self.belief(grid[y][x], "ENTER", 0) == "PASS"

        dist = {pos: 0}
        parent = {pos: None}
        q = deque([pos])
        while q:
            c = q.popleft()
            for dx, dy in DIRS:
                n = (c[0] + dx, c[1] + dy)
                if ok(*n) and n not in dist and passable(*n):
                    dist[n] = dist[c] + 1
                    parent[n] = c
                    q.append(n)

        def candidates(verify: bool):
            def believe(i, a, h):
                return self._believed(i, a, h, verify)
            # Things to hold: ids that were picked up, worth fetching while some
            # other id has not been tried with them in hand.
            ids = set(self.counts)
            hold = set()
            if not world.absolute and "TOGGLE" in world.acts:
                for i in ids:
                    if believe(i, "PICK", 0) == "PICK":
                        for t in ids:
                            if t != i and believe(t, "ENTER", 0) != "PASS" and believe(t, "TOGGLE", i) in (None, "OPEN"):
                                hold.add(i)
                                break

            goals, probes = [], []
            for y in range(H):
                for x in range(W):
                    if (x, y) == pos:
                        continue
                    ident = grid[y][x]
                    fromc = [(dist[(x - dx, y - dy)], (x - dx, y - dy)) for dx, dy in DIRS if (x - dx, y - dy) in dist]
                    if not fromc:
                        continue
                    d, r = min(fromc)
                    floorlike = believe(ident, "ENTER", 0) == "PASS"
                    for k, act in enumerate(world.acts):
                        if act != "ENTER" and floorlike:
                            continue
                        h = obs.hand if act == "TOGGLE" else 0     # picking always starts empty-handed
                        b = believe(ident, act, h)
                        if b == "GOAL":
                            goals.append((d, k, y, x, act, r))
                        elif b is None:
                            probes.append((d, k, y, x, act, r))
                        elif act == "PICK" and b == "PICK" and (ident, "PICK", 0) not in self.E:
                            probes.append((d, 7, y, x, act, r))           # claimed pickable: verify (reversible)
                        elif act == "TOGGLE" and b == "OPEN":
                            pickable = "PICK" in world.acts and self.belief(ident, "PICK", 0) not in ("NOOP", "HURT")
                            if not pickable or (ident, "PICK", 0) in self.E:
                                probes.append((d, 8, y, x, act, r))       # known progress, after the reversible act
                        elif act == "PICK" and b == "PICK" and ident in hold and ident != obs.hand:
                            probes.append((d, 9, y, x, act, r))           # fetch what opens something
            return goals, probes

        goals, probes = candidates(False)
        if not goals and not probes and self.source is not None:
            goals, probes = candidates(True)          # stuck: re-test what memory only claimed
        pick = min(goals) if goals else min(probes) if probes else None
        if pick is not None:
            _, _, y, x, act, r = pick
            if r != pos:
                step = r
                while parent[step] != pos:
                    step = parent[step]
                return self._toward(obs, world, step, "ENTER")
            if act == "PICK" and obs.hand:
                drop = self._drop(obs, world, grid, ok, passable, avoid=(x, y))
                if drop is not None:
                    return drop
            return self._toward(obs, world, (x, y), act)
        if obs.hand:
            drop = self._drop(obs, world, grid, ok, passable)
            if drop is not None:
                return drop
        if world.absolute:
            for d, (dx, dy) in enumerate(DIRS):
                n = (pos[0] + dx, pos[1] + dy)
                if ok(*n) and passable(*n):
                    return self._toward(obs, world, n, "ENTER")
            return "M0", None
        return "L", None

    def _drop(self, obs, world, grid, ok, passable, avoid=None):
        """Drop what is held on a neighbouring cell of the commonest passable id (bare floor)."""
        if world.absolute:
            return None
        floor = max((i for i in self.counts if self.belief(i, "ENTER", 0) == "PASS"),
                    key=lambda i: (self.counts[i], -i), default=None)
        for dx, dy in DIRS:
            n = (obs.pos[0] + dx, obs.pos[1] + dy)
            if n != avoid and ok(*n) and grid[n[1]][n[0]] == floor:
                return self._face(obs, n, ("D", ("DROP", n, floor, obs.hand, 0)))
        return None

    def _toward(self, obs, world, cell, act):
        x, y = cell
        ident = obs.grid[y][x]
        h = 0 if act == "ENTER" else obs.hand          # what was really in hand
        intent = (act, cell, ident, h, self.sig(ident))
        if world.absolute:
            d = DIRS.index((x - obs.pos[0], y - obs.pos[1]))
            return "M%d" % d, intent
        return self._face(obs, cell, ({"ENTER": "F", "PICK": "P", "TOGGLE": "T"}[act], intent))

    @staticmethod
    def _face(obs, cell, action):
        d = DIRS.index((cell[0] - obs.pos[0], cell[1] - obs.pos[1]))
        if obs.dir == d:
            return action
        return ("R" if (d - obs.dir) % 4 == 1 else "L"), None


class RandomAgent:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def run(self, world, max_steps: int = 100000, frames: Optional[list] = None) -> Dict:
        obs = world.reset()
        steps = ret = 0
        res = {"success": 0, "harm": 0, "harm_probe": 0, "harm_auto": 0, "harm_other": 0}
        while not obs.done and steps < max_steps:
            obs = world.step(self.rng.choice(world.prims))
            steps += 1
            ret += obs.reward
            if obs.terminated:
                res["success" if obs.reward > 0 else "harm"] = 1
                res["harm_other"] = int(obs.reward <= 0)
        res.update(steps=steps, wasted=-1, ret=ret)
        return res
