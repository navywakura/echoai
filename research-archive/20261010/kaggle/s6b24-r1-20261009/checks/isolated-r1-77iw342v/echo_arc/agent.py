"""echo-arc · ECHO's ARC-AGI-3 agent, self-contained (ARC Prize 2026 submission package).

Copyright 2026 RxLabs (Roger Navarro). If this submission wins a prize it is released under
CC-BY 4.0 as the competition rules require. It does NOT import the echoAI-4 core.

Ported from echoai/echo4/arc3_agent.py (v2 = Arc3EchoV2, exam 2026-09-24/25). The only change:
observed states go to a hash-chained fact journal instead of the core's CAM.
  BOUNDARY  the frame border (step/energy bars) is time, not me: masked from the state
  T         lived transitions; curiosity goes to the nearest state with untried actions
  delta     a GAME OVER marks its (state, action) as deadly unless it had been survived before
  effects   what an action kind does is generalised across states; inert clicks are deprioritised
"""
import hashlib
import random
from collections import Counter, deque

import numpy as np

MAX_CLICKS = 32


def fingerprint(frame, boundary):
    f = np.array(frame, dtype=np.int8)
    if boundary:
        f = f.copy()
        f[0, :] = f[-1, :] = f[:, 0] = f[:, -1] = -1      # the border: time, not me
    return hashlib.sha1(f.tobytes()).hexdigest()[:16]


def frame_hash(frame):
    return hashlib.sha1(np.array(frame, dtype=np.int8).tobytes()).hexdigest()[:16]


def objects(grid):
    """Connected components (4-neighbour, same colour): (size, x, y, colour), rare colours first."""
    grid = np.asarray(grid)
    h, w = grid.shape
    seen = np.zeros((h, w), bool)
    comps = []
    for y in range(h):
        for x in range(w):
            if seen[y, x]:
                continue
            c = int(grid[y, x])
            stack, n, sx, sy = [(y, x)], 0, 0, 0
            seen[y, x] = True
            while stack:
                cy, cx = stack.pop()
                n += 1
                sx += cx
                sy += cy
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and grid[ny, nx] == c:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            comps.append((n, sx // n, sy // n, c))
    counts = {}
    for n, _, _, c in comps:
        counts[c] = counts.get(c, 0) + n
    comps = [o for o in comps if o[0] < 0.25 * h * w]                 # drop backgrounds
    comps.sort(key=lambda o: (counts[o[3]], o[0], o[2], o[1]))        # rare colours, small first
    return comps


class Arc3Echo:
    def __init__(self, available, seed, boundary=True):
        self.available = sorted(int(a) for a in available)
        self.rng = random.Random(seed)
        self.boundary = boundary
        self.facts, self.n = [], 0
        self.T = {}                  # (state, action) -> next state
        self.adj = {}                # state -> {action: next state} (same facts as T, for search)
        self.untried = {}            # state -> [actions]
        self.dead = set()            # (state, action) that ended the game: negative delta
        self.win_paths = {}          # level start state -> winning action list
        self.path = deque()
        self.level_start, self.level_actions = None, []

    # ---- memory: a new state is an observed fact in CAM
    def _remember(self, state):
        """An observed state is a FACT: appended to a hash-chained journal (no core import)."""
        prev = self.facts[-1][1] if self.facts else "0" * 16
        self.facts.append((state, hashlib.sha1((prev + state).encode()).hexdigest()[:16]))
        self.n += 1

    def actions_for(self, frame):
        acts = [("K", a, None) for a in self.available if a in (1, 2, 3, 4, 5, 7)]
        if 6 in self.available:
            if self.boundary:
                seen = set()
                for _, x, y, c in objects(frame):
                    if (x, y) not in seen:
                        seen.add((x, y))
                        acts.append(("C", 6, (x, y)))
                    if len(seen) >= MAX_CLICKS:
                        break
            else:
                acts += [("C", 6, (self.rng.randint(0, 63), self.rng.randint(0, 63))) for _ in range(MAX_CLICKS)]
        return acts

    def observe_state(self, frame):
        s = fingerprint(frame, self.boundary)
        if s not in self.untried:
            self._remember(s)
            acts = self.actions_for(frame)
            self.rng.shuffle(acts)
            self.untried[s] = acts
        return s

    def _bfs(self, start):
        """Shortest known path to a state that still has untried actions."""
        prev, q = {start: None}, deque([start])
        while q:
            s = q.popleft()
            if s != start and self.untried.get(s):
                path, cur = [], s
                while prev[cur] is not None:
                    ps, act = prev[cur]
                    path.append(act)
                    cur = ps
                return list(reversed(path))
            for act, ns in self.adj.get(s, {}).items():
                if ns not in prev and (s, act) not in self.dead:
                    prev[ns] = (s, act)
                    q.append(ns)
        return None

    def choose(self, state):
        if state == self.level_start and state in self.win_paths and not self.path:
            self.path = deque(self.win_paths[state])                      # replay what worked (Q)
        if self.path:
            return self.path.popleft()
        while self.untried.get(state):
            act = self.untried[state].pop()
            if (state, act) not in self.dead:
                return act
        path = self._bfs(state)
        if path:
            self.path = deque(path[1:])
            return path[0]
        known = [a for a in self.actions_for_state_fallback() if (state, a) not in self.dead]
        return self.rng.choice(known) if known else ("R", 0, None)

    def actions_for_state_fallback(self):
        return [("K", a, None) for a in self.available if a in (1, 2, 3, 4, 5, 7)] or \
               [("C", 6, (self.rng.randint(0, 63), self.rng.randint(0, 63)))]

    def learn(self, state, act, next_state, game_over, level_up):
        if game_over:
            self.dead.add((state, act))
            self.path.clear()
        elif next_state != state:
            if self.T.get((state, act)) not in (None, next_state):
                self.path.clear()                                         # T conflict: replan
            self.T[(state, act)] = next_state
            self.adj.setdefault(state, {})[act] = next_state
        if level_up and self.level_start is not None:
            self.win_paths[self.level_start] = list(self.level_actions)


class Arc3EchoV2(Arc3Echo):
    """v2 (declared in docs/ECHO4-BENCH-ARC3-D-DESIGN.md; developed on the 8 dev games only).

    Two fixes over v1, both from measured dev failures:
      - blame: a GAME_OVER after an action that had already been survived from the same state is
        the step/energy budget running out, not that action (v1 marked it deadly anyway);
      - effect memory: what an action *kind* does is generalised across states (keys by id,
        clicks by the colour and size class of the clicked object). Untried actions are ordered
        by the estimated chance that they change the world, so no-op clicks stop eating the budget.
    """
    MAX_TARGETS = 64

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.kind = {}               # act -> kind key (keys: id; clicks: colour + size class)
        self.effect = {}             # kind -> [tries, changes]
        self.survived = set()        # (state, act) that did not end the game at least once

    def actions_for(self, frame):
        grid = np.asarray(frame)
        acts = []
        for a in self.available:
            if a in (1, 2, 3, 4, 5, 7):
                act = ("K", a, None)
                self.kind[act] = ("K", a)
                acts.append(act)
        if 6 in self.available:
            if self.boundary:
                seen = set()
                for n, x, y, c in objects(grid):
                    if (x, y) in seen:
                        continue
                    seen.add((x, y))
                    act = ("C", 6, (x, y))
                    self.kind.setdefault(act, ("C", c, min(n.bit_length(), 8)))
                    acts.append(act)
                    if len(seen) >= self.MAX_TARGETS:
                        break
            else:
                for _ in range(MAX_CLICKS):
                    x, y = self.rng.randint(0, 63), self.rng.randint(0, 63)
                    act = ("C", 6, (x, y))
                    self.kind.setdefault(act, ("C", int(grid[y, x]), 0))
                    acts.append(act)
        return acts

    def _promise(self, act):
        tries, changes = self.effect.get(self.kind.get(act), (0, 0))
        return (changes + 1) * 1000 // (tries + 2)

    def observe_state(self, frame):
        s = fingerprint(frame, self.boundary)
        if s not in self.untried:
            self._remember(s)
            acts = self.actions_for(frame)
            self.rng.shuffle(acts)
            self.untried[s] = acts
        return s

    def choose(self, state):
        todo = self.untried.get(state)
        if todo and not self.path:
            todo.sort(key=self._promise)                  # stable: ties keep the shuffled order
            if self._promise(todo[-1]) < 150:               # every kind here looks inert: go elsewhere
                path = self._bfs_promising(state)
                if path:
                    self.path = deque(path[1:])
                    return path[0]
        return super().choose(state)

    def _bfs_promising(self, start):
        prev, q = {start: None}, deque([start])
        while q:
            s = q.popleft()
            if s != start and self.untried.get(s) and max(map(self._promise, self.untried[s])) >= 150:
                path, cur = [], s
                while prev[cur] is not None:
                    ps, act = prev[cur]
                    path.append(act)
                    cur = ps
                return list(reversed(path))
            for act, ns in self.adj.get(s, {}).items():
                if ns not in prev and (s, act) not in self.dead:
                    prev[ns] = (s, act)
                    q.append(ns)
        return None

    def learn(self, state, act, next_state, game_over, level_up):
        k = self.kind.get(act)
        if k is not None and act[0] != "R":
            e = self.effect.setdefault(k, [0, 0])
            e[0] += 1
            e[1] += int(next_state != state or game_over or level_up)
        if game_over and (state, act) in self.survived:
            self.path.clear()                                 # budget ran out: not this action's fault
            return
        if not game_over:
            self.survived.add((state, act))
        super().learn(state, act, next_state, game_over, level_up)


class Arc3EchoV3(Arc3EchoV2):
    """v3 · ECHO-4.5 S3 (docs/ECHO45-S3-DESIGN.md; developed on the 8 dev games only).

      - game clock: cells near the edge that change on most steps by themselves (energy / step bars,
        not only the outer ring) are learned in the first WARMUP observations, then masked from the
        state and never clicked;
      - clicks land on a cell that BELONGS to the object (the member nearest its centre), never on
        the mean position (which can fall outside a ring or an L), and never on border/clock cells.
    """
    WARMUP, EDGE = 30, 4

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.changes = np.zeros((64, 64), dtype=np.int32)
        self.n_obs = 0
        self.prev = None
        self.clock = None                                   # frozen boolean mask after WARMUP

    def _edge(self, shape):
        h, w = shape
        e = np.zeros((h, w), dtype=bool)
        e[: self.EDGE, :] = e[-self.EDGE:, :] = e[:, : self.EDGE] = e[:, -self.EDGE:] = True
        return e

    def _update_clock(self, frame):
        f = np.asarray(frame)
        if self.clock is not None:
            return
        if self.prev is not None and self.prev.shape == f.shape:
            self.changes[: f.shape[0], : f.shape[1]] += (self.prev != f)
            self.n_obs += 1
        self.prev = f.copy()
        if self.n_obs >= self.WARMUP:
            ch = self.changes[: f.shape[0], : f.shape[1]]
            self.clock = (ch * 2 >= self.n_obs) & self._edge(f.shape)
            ring = np.zeros(f.shape, dtype=bool)
            ring[0, :] = ring[-1, :] = ring[:, 0] = ring[:, -1] = True
            self.clock |= ring

    def _key(self, frame):
        f = np.array(frame, dtype=np.int8)
        if self.clock is None:
            return fingerprint(frame, self.boundary)
        f = f.copy()
        f[self.clock] = -1
        return hashlib.sha1(f.tobytes()).hexdigest()[:16]

    def actions_for(self, frame):
        grid = np.asarray(frame)
        acts = []
        for a in self.available:
            if a in (1, 2, 3, 4, 5, 7):
                act = ("K", a, None)
                self.kind[act] = ("K", a)
                acts.append(act)
        if 6 in self.available:
            h, w = grid.shape
            banned = np.zeros((h, w), dtype=bool)
            banned[0, :] = banned[-1, :] = banned[:, 0] = banned[:, -1] = True
            if self.clock is not None:
                banned |= self.clock
            for n, cells, c in _components(grid):
                free = [(y, x) for y, x in cells if not banned[y, x]]
                if not free:
                    continue
                cy = sum(y for y, _ in free) / len(free)
                cx = sum(x for _, x in free) / len(free)
                y, x = min(free, key=lambda p: (p[0] - cy) ** 2 + (p[1] - cx) ** 2)
                act = ("C", 6, (int(x), int(y)))
                self.kind.setdefault(act, ("C", c, min(n.bit_length(), 8)))
                acts.append(act)
                if len(acts) >= self.MAX_TARGETS + 7:
                    break
        return acts

    def observe_state(self, frame):
        self._update_clock(frame)
        s = self._key(frame)
        if s not in self.untried:
            self._remember(s)
            acts = self.actions_for(frame)
            self.rng.shuffle(acts)
            self.untried[s] = acts
        return s


class Arc3EchoV3b(Arc3EchoV3):
    """v3b · S3 with the self (BOUNDARY by objects), on top of v3.

      - self discovery: after each key action, same-signature objects (colour, size) are matched
        between frames; the signature whose displacement is consistent per key, with >= 2 distinct
        directions, is "me" (a fact from contingency, not a hint from the game);
      - action rules: key -> displacement of "me"; (position, key) with no displacement = blocked
        (the walls are learned);
      - exploration in the space of my positions: while no plan is being followed, prefer a key that
        takes "me" to a position not yet visited and not known to be blocked.
    """
    MIN_EVIDENCE = 8

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.keys = [a for a in self.available if a in (1, 2, 3, 4)]
        self.moves = {}                                     # (sig, key) -> Counter of (dx, dy)
        self.me = None                                      # signature of my body once discovered
        self.rule = {}                                      # key -> (dx, dy) for my body
        self.pos = None
        self.visited = set()
        self.blocked = set()
        self.last_key = None
        self.last_frame = None

    @staticmethod
    def _sigs(grid):
        out = {}
        for n, cells, c in _components(np.asarray(grid)):
            key = (c, n)
            if key in out:
                out[key] = None                             # ambiguous: several objects share it
            else:
                cy = sum(y for y, _ in cells) * 2 // n       # doubled centre, integers only
                cx = sum(x for _, x in cells) * 2 // n
                out[key] = (cx, cy)
        return {k: v for k, v in out.items() if v is not None}

    def _learn_self(self, frame):
        if self.last_key is None or self.last_frame is None:
            return
        a, b = self._sigs(self.last_frame), self._sigs(frame)
        for sig, (x0, y0) in a.items():
            if sig in b:
                d = (b[sig][0] - x0, b[sig][1] - y0)
                self.moves.setdefault((sig, self.last_key), Counter())[d] += 1
        if self.me is None:
            best = None
            for sig in {s for s, _ in self.moves}:
                dirs, evidence = set(), 0
                for k in self.keys:
                    c = self.moves.get((sig, k))
                    if c:
                        d, n = c.most_common(1)[0]
                        if d != (0, 0) and n * 10 >= sum(c.values()) * 7:
                            dirs.add(d)
                            evidence += n
                if len(dirs) >= 2 and evidence >= self.MIN_EVIDENCE and (best is None or evidence > best[0]):
                    best = (evidence, sig)
            if best:
                self.me = best[1]
                for k in self.keys:
                    c = self.moves.get((self.me, k))
                    if c:
                        self.rule[k] = c.most_common(1)[0][0]

    def observe_state(self, frame):
        self._learn_self(frame)
        if self.me is not None:
            here = self._sigs(frame).get(self.me)
            if here is not None:
                if self.pos is not None and self.last_key is not None and here == self.pos:
                    self.blocked.add((self.pos, self.last_key))
                self.pos = here
                self.visited.add(here)
        self.last_frame = np.asarray(frame).copy()
        return super().observe_state(frame)

    def choose(self, state):
        act = None
        if self.me is not None and not self.path and self.pos is not None and self.rule and \
                not (state == self.level_start and state in self.win_paths):
            fresh = []
            for k in self.keys:
                d = self.rule.get(k)
                if d is None or (self.pos, k) in self.blocked or ((state, ("K", k, None)) in self.dead):
                    continue
                if (self.pos[0] + d[0], self.pos[1] + d[1]) not in self.visited:
                    fresh.append(k)
            if fresh:
                k = fresh[self.rng.randrange(len(fresh))]
                act = ("K", k, None)
                todo = self.untried.get(state)
                if todo and act in todo:
                    todo.remove(act)
        if act is None:
            act = super().choose(state)
        self.last_key = act[1] if act[0] == "K" and act[1] in self.keys else None
        return act


class Arc3EchoV4(Arc3EchoV3b):
    """v4 · ECHO-4.5 S4 (docs/ECHO45-S4-DESIGN.md; developed on the 8 dev games only).

      - "me" may be several identical bodies moving together (instances matched by nearest centre);
      - object curiosity: in key games, once "me" and the key rules are known, ECHO PLANS the shortest
        path (learned rules + learned walls, unknown moves assumed free) to touch objects: first those
        that look like it (same colour or size), then rare colours;
      - goal hypothesis: at a level up, the kind (colour) of the object nearest to "me", or the kinds
        clicked just before, becomes a HYPOTHESIS tried first in the next level; a new win confirms it,
        otherwise it is refuted. Hypotheses are logged, never stored as facts.
    """
    MAX_PER_TARGET = 60
    _rules_when_done = 0

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.goal_colours = Counter()                       # hypotheses: colour -> wins near it
        self.win_kinds = Counter()                          # click kinds seen right before a win
        self.hypotheses = []                                # log: (level, kind, verdict)
        self.targets_done = set()
        self.target = None
        self.target_steps = 0
        self.recent_clicks = deque(maxlen=3)
        self.level = 0
        self.key_tries = Counter()
        self.babble = 1                                      # try every key once first (S4 iteration 2)

    # ---- several identical bodies
    @staticmethod
    def _sigs_multi(grid):
        out = {}
        for n, cells, c in _components(np.asarray(grid)):
            cy = sum(y for y, _ in cells) * 2 // n
            cx = sum(x for _, x in cells) * 2 // n
            out.setdefault((c, n), []).append((cx, cy))
        return out

    def _learn_self(self, frame):
        if self.last_key is None or self.last_frame is None:
            return
        a, b = self._sigs_multi(self.last_frame), self._sigs_multi(frame)
        for sig, ps in a.items():
            qs = b.get(sig)
            if not qs or len(qs) != len(ps) or len(ps) > 4:
                continue
            ds = set()
            for (x0, y0) in ps:
                x1, y1 = min(qs, key=lambda q: abs(q[0] - x0) + abs(q[1] - y0))
                ds.add((x1 - x0, y1 - y0))
            if len(ds) == 1:
                self.moves.setdefault((sig, self.last_key), Counter())[ds.pop()] += 1
        if self.me is None:
            best = None
            for sig in {s for s, _ in self.moves}:
                dirs, evidence = set(), 0
                for k in self.keys:
                    c = self.moves.get((sig, k))
                    if c:
                        d, n = c.most_common(1)[0]
                        if d != (0, 0) and n * 10 >= sum(c.values()) * 7:
                            dirs.add(d)
                            evidence += n
                if len(dirs) >= 2 and evidence >= self.MIN_EVIDENCE and (best is None or evidence > best[0]):
                    best = (evidence, sig)
            if best:
                self.me = best[1]
        if self.me is not None:
            for k in self.keys:
                c = self.moves.get((self.me, k))
                if c:
                    d = c.most_common(1)[0][0]
                    if d != (0, 0):
                        self.rule[k] = d

    def observe_state(self, frame):
        self._learn_self(frame)
        if self.me is not None:
            here = self._sigs_multi(frame).get(self.me)
            if here:
                here = min(here)
                if self.pos is not None and self.last_key is not None and here == self.pos:
                    self.blocked.add((self.pos, self.last_key))
                self.pos = here
                self.visited.add(here)
        self.last_frame = np.asarray(frame).copy()
        return Arc3EchoV3.observe_state(self, frame)

    # ---- targets and planning
    def _targets(self):
        f = self.last_frame
        if f is None or self.me is None:
            return []
        banned = self.clock if self.clock is not None else np.zeros(f.shape, bool)
        colour_count = Counter(int(v) for v in f.ravel())
        out = []
        for n, cells, c in _components(f):
            if (c, n) == self.me or all(banned[y, x] for y, x in cells):
                continue
            cy = sum(y for y, _ in cells) * 2 // n
            cx = sum(x for _, x in cells) * 2 // n
            key = (c, n, cx, cy)
            if key in self.targets_done:
                continue
            like_me = int(c == self.me[0]) + int(n == self.me[1])
            out.append((-self.goal_colours[c], -like_me, colour_count[c], n, key))
        out.sort()
        return [t[-1] for t in out]

    def _plan(self, goal):
        if self.pos is None or not self.rule:
            return None
        step = max(max(abs(dx), abs(dy)) for dx, dy in self.rule.values())
        gx, gy = goal
        start = self.pos
        prev, q = {start: None}, deque([start])
        while q:
            p = q.popleft()
            if abs(p[0] - gx) + abs(p[1] - gy) <= step:
                path = []
                while prev[p] is not None:
                    p, k = prev[p]
                    path.append(k)
                return list(reversed(path))
            if len(prev) > 4000:
                return None
            for k, (dx, dy) in self.rule.items():
                nxt = (p[0] + dx, p[1] + dy)
                if (p, k) in self.blocked or nxt in prev or not (-8 <= nxt[0] <= 136 and -8 <= nxt[1] <= 136):
                    continue
                prev[nxt] = (p, k)
                q.append(nxt)
        return None

    def choose(self, state):
        act = None
        # motor babbling: like a person with a new game, press every key a few times first
        fresh_keys = [k for k in self.keys if self.key_tries[k] < self.babble and (state, ("K", k, None)) not in self.dead]
        if fresh_keys and not self.path:
            act = ("K", fresh_keys[0], None)
        if act is None and self.me is not None and self.rule and not self.path and \
                not (state == self.level_start and state in self.win_paths):
            for _ in range(6):
                if self.target is None:
                    ts = self._targets()
                    if not ts and self.targets_done and len(self.rule) > self._rules_when_done:
                        self.targets_done = set()           # new rules: unreachable targets may be reachable now
                        ts = self._targets()
                    if not ts:
                        self._rules_when_done = len(self.rule)
                        break
                    self.target, self.target_steps = ts[0], 0
                plan = self._plan(self.target[2:])
                if plan and self.target_steps < self.MAX_PER_TARGET:
                    self.target_steps += 1
                    act = ("K", plan[0], None)
                    break
                self.targets_done.add(self.target)          # reached, unreachable or too costly
                self.target = None
        if act is None:
            act = Arc3EchoV3.choose(self, state)
        self.last_key = act[1] if act[0] == "K" and act[1] in self.keys else None
        if act[0] == "K":
            self.key_tries[act[1]] += 1
        if act[0] == "C":
            self.recent_clicks.append(self.kind.get(act))
        return act

    def _promise(self, act):
        base = super()._promise(act)
        k = self.kind.get(act)
        return base + 1000 * self.win_kinds.get(k, 0) if k is not None else base

    def learn(self, state, act, next_state, game_over, level_up):
        if level_up:
            self.level += 1
            tried = self.target[0] if self.target else None
            if tried is not None and self.goal_colours.get(tried):
                self.hypotheses.append((self.level, ("near", tried), "confirmed"))
            if self.pos is not None and self.last_frame is not None:
                near = self._nearest_colour()
                if near is not None:
                    self.goal_colours[near] += 1
                    self.hypotheses.append((self.level, ("near", near), "proposed"))
            for k in self.recent_clicks:
                if k is not None:
                    self.win_kinds[k] += 1
            self.targets_done, self.target, self.visited, self.blocked = set(), None, set(), set()
        super().learn(state, act, next_state, game_over, level_up)

    def _nearest_colour(self):
        f = self.last_frame
        best = None
        for n, cells, c in _components(f):
            if (c, n) == self.me or (self.clock is not None and all(self.clock[y, x] for y, x in cells)):
                continue
            cy = sum(y for y, _ in cells) * 2 // n
            cx = sum(x for _, x in cells) * 2 // n
            d = abs(cx - self.pos[0]) + abs(cy - self.pos[1])
            if best is None or d < best[0]:
                best = (d, c)
        return best[1] if best else None


class Arc3EchoV41(Arc3EchoV4):
    """v4.1 · S4 iteration 1 (after watching g50t: ACTION5 switches which body obeys the arrows).

      - "me" is recomputed from the LAST key presses, so it can change body after a mode key;
      - goal by likeness: the object with exactly my signature (e.g. the dot inside the U frame) is the
        first goal hypothesis; if no known path reaches it, the non-move keys (5, 7) are tried once each
        (they may switch body or open the way) and v3 exploration continues;
      - without a goal hypothesis the agent behaves exactly as v3 (no blind object touching).
    """
    WINDOW = 16

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.recent = deque(maxlen=self.WINDOW)             # (sig, key, displacement) of recent presses
        self.mode_keys = [a for a in self.available if a in (5, 7)]
        self.mode_tried = Counter()
        self.stuck = 0
        self.still = Counter()                               # instance centre of my signature -> times it stayed while I moved
        self.prev_instances = None

    def _learn_self(self, frame):
        if self.last_key is None or self.last_frame is None:
            return
        a, b = self._sigs_multi(self.last_frame), self._sigs_multi(frame)
        for sig, ps in a.items():
            qs = b.get(sig)
            if not qs or len(qs) != len(ps) or len(ps) > 4:
                continue
            ds = {(min(qs, key=lambda q: abs(q[0] - x0) + abs(q[1] - y0))[0] - x0,
                   min(qs, key=lambda q: abs(q[0] - x0) + abs(q[1] - y0))[1] - y0) for x0, y0 in ps}
            if len(ds) == 1:
                d = ds.pop()
                self.recent.append((sig, self.last_key, d))
                self.moves.setdefault((sig, self.last_key), Counter())[d] += 1
        per = {}
        for sig, k, d in self.recent:
            if d != (0, 0):
                per.setdefault(sig, {}).setdefault(k, Counter())[d] += 1
        best = None
        for sig, bykey in per.items():
            dirs = {c.most_common(1)[0][0] for c in bykey.values()}
            ev = sum(c.most_common(1)[0][1] for c in bykey.values())
            if len(dirs) >= 2 and ev >= 4 and (best is None or ev > best[0]):
                best = (ev, sig, bykey)
        if best and best[1] != self.me:
            self.me, self.pos = best[1], None
            self.rule = {k: c.most_common(1)[0][0] for k, c in best[2].items()}
            self.blocked, self.visited = set(), set()
        elif best:
            for k, c in best[2].items():
                self.rule[k] = c.most_common(1)[0][0]

    def _goal(self):
        """Goal hypothesis: an object identical to me (same colour and size), else a colour that won before."""
        f = self.last_frame
        if f is None or self.me is None or self.pos is None:
            return None
        cands = []
        for n, cells, c in _components(f):
            if self.clock is not None and all(self.clock[y, x] for y, x in cells):
                continue
            cy = sum(y for y, _ in cells) * 2 // n
            cx = sum(x for _, x in cells) * 2 // n
            key = (c, n, cx, cy)
            if key in self.targets_done or (cx, cy) == self.pos:
                continue
            if (c, n) == self.me:
                if self.still[(cx, cy)] >= 3:                 # identical to me but it does NOT move with me
                    cands.append((0, abs(cx - self.pos[0]) + abs(cy - self.pos[1]), key))
            elif self.goal_colours.get(c):
                cands.append((1, abs(cx - self.pos[0]) + abs(cy - self.pos[1]), key))
        return min(cands)[2] if cands else None

    def observe_state(self, frame):
        st = super().observe_state(frame)
        if self.me is not None:
            inst = set(self._sigs_multi(frame).get(self.me, []))
            if self.prev_instances is not None and inst != self.prev_instances:
                for c in inst & self.prev_instances:            # some of my kind moved, these stayed
                    self.still[c] += 1
            self.prev_instances = inst
        return st

    def choose(self, state):
        act = None
        fresh_keys = [k for k in self.keys if self.key_tries[k] < self.babble and (state, ("K", k, None)) not in self.dead]
        if fresh_keys and not self.path:
            act = ("K", fresh_keys[0], None)
        if act is None and not self.path and not (state == self.level_start and state in self.win_paths):
            goal = self._goal()
            if goal is not None:
                if self.target != goal:
                    self.target, self.target_steps = goal, 0
                plan = self._plan(goal[2:])
                if plan and self.target_steps < self.MAX_PER_TARGET:
                    self.target_steps += 1
                    act = ("K", plan[0], None)
                else:
                    untried_modes = [k for k in self.mode_keys if self.mode_tried[(goal, k)] == 0]
                    if untried_modes:
                        k = untried_modes[0]
                        self.mode_tried[(goal, k)] += 1
                        act = ("K", k, None)
                    else:
                        self.targets_done.add(goal)
                        self.target = None
        if act is None:
            act = Arc3EchoV3.choose(self, state)
        self.last_key = act[1] if act[0] == "K" and act[1] in self.keys else None
        if act[0] == "K":
            self.key_tries[act[1]] += 1
        if act[0] == "C":
            self.recent_clicks.append(self.kind.get(act))
        return act


class Arc3EchoV5(Arc3EchoV41):
    """v5 · S4 iteration 3 (docs/ECHO45-S4-DESIGN.md): a verified world model, planning inside it.

      - prediction: before each key press the model predicts whether "me" moves; the outcome is
        checked against the real frame (every transition is a replay test, done incrementally);
      - simplification: walls are learned as COLOURS (a colour that blocked me and never let me through),
        one rule instead of one case per (position, key); the rule travels to the next level;
      - planning in the model: paths are searched on the current frame with the wall colours, so the
        agent does not bump its way through a maze;
      - world events: a change in the arena that "me" did not make is a surprise. Where my instances
        (me or my copies) were at that moment becomes a CAUSAL HYPOTHESIS (never a fact); stale walls
        and targets are forgotten;
      - two steps: when the goal is unreachable in the model, go to the cause first (test it: the event
        must repeat), try the mode keys there (leave a copy), then plan to the goal again.
    """
    MARGIN = 2
    EXPLORE = True
    STRICT_MOVES = False
    WALL_MIN = 3
    BABBLE = 1
    TEST_WINDOW = 4

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.passed = Counter()                             # colour -> times I moved onto it
        self.stopped = Counter()                            # colour -> times it was in my way when I did not move
        self.pred = [0, 0]                                  # [right, wrong] model predictions
        self.arena = None                                   # (y0, x0, y1, x1) where my body has been
        self.causes = {}                                    # instance centre -> {"region", "seen", "tests", "ok"}
        self.pending = None                                 # (cause key, steps left) while a cause is being tested
        self.events = 0
        self.my_cells = []
        self._testing = None
        self.babble = self.BABBLE

    # ---- the self, from all the evidence (a corridor lets me move in one direction for a long time)
    def _learn_self(self, frame):
        super()._learn_self(frame)
        best = None
        for sig in {s for s, _ in self.moves}:
            dirs, ev = {}, 0
            for k in self.keys:
                c = self.moves.get((sig, k))
                if not c:
                    continue
                nz = [(n, d) for d, n in c.items() if d != (0, 0)]
                if nz:
                    n, d = max(nz)
                    if n * 10 >= sum(c.values()) * 5:
                        dirs[k] = d
                        ev += n
            if dirs and ev >= self.MIN_EVIDENCE and (len(set(dirs.values())) >= 2 or ev >= 2 * self.MIN_EVIDENCE):
                if best is None or (len(dirs), ev) > (len(best[2]), best[0]):
                    best = (ev, sig, dirs)
        if best is None:
            return
        if self.me is None:
            self.me, self.pos = best[1], None
        if best[1] == self.me:
            for k, d in best[2].items():
                self.rule.setdefault(k, d)

    # ---- the model
    def _walls(self):
        # one rule per colour; robust to the odd noisy step (a reset, a copy moving me)
        return {c for c, n in self.stopped.items() if n >= self.WALL_MIN and self.passed[c] * 10 < n}

    def _instances(self, frame):
        if self.me is None or frame is None:
            return []
        return [cells for n, cells, c in _components(np.asarray(frame)) if (c, n) == self.me]

    def _fits(self, frame, cells, own, dy, dx, walls):
        h, w = frame.shape
        for y, x in cells:
            ny, nx = y + dy, x + dx
            if not (0 <= ny < h and 0 <= nx < w):
                return False
            if (ny, nx) in own:
                continue
            if (self.clock is not None and self.clock[ny, nx]) or int(frame[ny, nx]) in walls:
                return False
        return True

    def _fitmap(self, frame, cells, own, walls):
        """Same test as _fits for every shift at once (numpy): allowed[dy+64, dx+64]. Cached per frame."""
        key = (tuple(sorted(walls)), tuple(cells))
        if getattr(self, "_fm_frame", None) is frame and self._fm_key == key:
            return self._fm
        h, w = frame.shape
        bad = np.isin(frame, list(walls)) if walls else np.zeros((h, w), bool)
        if self.clock is not None:
            bad = bad | self.clock
        for y, x in own:
            bad[y, x] = False
        pad = np.ones((h + 128, w + 128), bool)
        pad[64:64 + h, 64:64 + w] = bad
        ok = np.ones((129, 129), bool)
        for y, x in cells:
            ok &= ~pad[y:y + 129, x:x + 129]
        self._fm_frame, self._fm_key, self._fm = frame, key, ok
        return ok

    def _plan(self, goal):
        f = self.last_frame
        if self.pos is None or not self.rule or f is None or not self.my_cells:
            return super()._plan(goal)
        cells = [p for inst in self.my_cells for p in inst]
        own, walls = set(cells), self._walls()
        fm = self._fitmap(f, cells, own, walls)
        step = max(max(abs(dx), abs(dy)) for dx, dy in self.rule.values())
        gx, gy = goal
        start = (0, 0)
        prev, q = {start: None}, deque([start])
        while q:
            off = q.popleft()
            px, py = self.pos[0] + 2 * off[1], self.pos[1] + 2 * off[0]
            if abs(px - gx) + abs(py - gy) <= step:
                path = []
                while prev[off] is not None:
                    off, k = prev[off]
                    path.append(k)
                return list(reversed(path))
            if len(prev) > 4000:
                return None
            for k, (dx, dy) in self.rule.items():
                nxt = (off[0] + dy // 2, off[1] + dx // 2)
                if nxt in prev or ((px, py), k) in self.blocked:
                    continue
                if not (-64 <= nxt[0] <= 64 and -64 <= nxt[1] <= 64 and fm[nxt[0] + 64, nxt[1] + 64]):
                    continue
                prev[nxt] = (off, k)
                q.append(nxt)
        return None

    def observe_state(self, frame):
        before, key, pos0, me0 = self.last_frame, self.last_key, self.pos, self.me
        cells0 = self.my_cells
        st = super().observe_state(frame)
        f = np.asarray(frame)
        self.my_cells = self._instances(f)
        if self.me is None or self.me != me0 or before is None or before.shape != f.shape:
            return st
        flat = [p for inst in self.my_cells for p in inst]
        if flat:
            ys, xs = [y for y, _ in flat], [x for _, x in flat]
            box = (min(ys), min(xs), max(ys), max(xs))
            a = self.arena or box
            self.arena = (min(a[0], box[0]), min(a[1], box[1]), max(a[2], box[2]), max(a[3], box[3]))
        if key is not None and key in self.rule and cells0:
            dx, dy = self.rule[key]
            old = [p for inst in cells0 for p in inst]
            own = set(old)
            predicted = self._fits(before, old, own, dy // 2, dx // 2, self._walls())
            moved = self.pos != pos0
            self.pred[int(predicted != moved)] += 1
            if self.STRICT_MOVES and moved and (pos0 is None or self.pos is None or
                                                (self.pos[0] - pos0[0], self.pos[1] - pos0[1]) != (dx, dy)):
                self._world_event(before, f, cells0)            # a jump (reset, teleport), not this key's move
                return st
            under = {int(before[y + dy // 2, x + dx // 2]) for y, x in old
                     if (y + dy // 2, x + dx // 2) not in own
                     and 0 <= y + dy // 2 < f.shape[0] and 0 <= x + dx // 2 < f.shape[1]}
            for c in under:
                if moved:
                    self.passed[c] += 1
                elif not self.passed[c]:
                    self.stopped[c] += 1
        self._world_event(before, f, cells0)
        return st

    def _world_event(self, before, f, cells0):
        """A change in the arena that is not my body moving: a surprise, and a causal hypothesis."""
        if self.arena is None:
            return
        changed = before != f
        if self.clock is not None:
            changed &= ~self.clock
        for inst in list(cells0) + list(self.my_cells):
            for y, x in inst:
                changed[y, x] = False
        m = self.MARGIN
        y0, x0 = max(self.arena[0] - m, 0), max(self.arena[1] - m, 0)
        y1, x1 = self.arena[2] + m, self.arena[3] + m
        win = np.zeros_like(changed)
        win[y0:y1 + 1, x0:x1 + 1] = True
        pts = np.argwhere(changed & win)
        if self.pending is not None:
            k, left = self.pending
            self.pending = (k, left - 1) if left > 1 else None
        if len(pts) == 0:
            if self.pending is None and getattr(self, "_testing", None) is not None:
                k = self._testing
                self._testing = None
                if k in self.causes and not self.causes[k]["ok"]:
                    self.hypotheses.append((self.level, ("cause", k), "refuted"))
            return
        region = (int(pts[:, 0].min()), int(pts[:, 1].min()), int(pts[:, 0].max()), int(pts[:, 1].max()))
        flat = [p for inst in self.my_cells for p in inst]
        if flat and self.rule:
            reach = max(max(abs(dx), abs(dy)) for dx, dy in self.rule.values()) // 2 + 1
            ys, xs = [y for y, _ in flat], [x for _, x in flat]
            gap_y = max(region[0] - max(ys), min(ys) - region[2], 0)
            gap_x = max(region[1] - max(xs), min(xs) - region[3], 0)
            if max(gap_y, gap_x) <= reach:
                return                                          # I pushed or touched it: not action at a distance
        self.events += 1
        self.blocked, self.targets_done, self.target = set(), set(), None       # the world changed: forget stale cases
        if self.pending is not None and self.pending[0] in self.causes:
            k = self.pending[0]
            self.causes[k]["ok"] += 1
            self.hypotheses.append((self.level, ("cause", k), "confirmed"))
            self.pending, self._testing = None, None
        for inst in self.my_cells:
            n = len(inst)
            c = (sum(x for _, x in inst) * 2 // n, sum(y for y, _ in inst) * 2 // n)
            if c not in self.causes:
                self.causes[c] = {"region": region, "seen": 0, "tests": 0, "ok": 0}
                self.hypotheses.append((self.level, ("cause", c), "proposed"))
            self.causes[c]["seen"] += 1

    # ---- two steps: the cause first, then the goal
    def _cause_step(self):
        if not self.causes or self.pos is None:
            return None
        order = sorted(self.causes.items(),
                       key=lambda kv: (-kv[1]["ok"], kv[1]["tests"], abs(kv[0][0] - self.pos[0]) + abs(kv[0][1] - self.pos[1])))
        for c, h in order:
            if h["tests"] >= 1 + len(self.mode_keys) + h["ok"] * 2:
                continue
            plan = self._plan(c)
            if plan is None:
                continue
            if plan:
                return ("K", plan[0], None)
            h["tests"] += 1                                    # standing on the cause: test it, then leave a copy
            self.pending, self._testing = (c, self.TEST_WINDOW), c
            modes = [k for k in self.mode_keys if self.mode_tried[(c, k)] == 0]
            if modes:
                self.mode_tried[(c, modes[0])] += 1
                return ("K", modes[0], None)
        return None

    def _frontier_step(self):
        """Explore in the model: the nearest position my body can reach (walls as colours) and has not visited."""
        f = self.last_frame
        if f is None or not self.my_cells or self.pos is None:
            return None
        cells = [p for inst in self.my_cells for p in inst]
        own, walls = set(cells), self._walls()
        fm = self._fitmap(f, cells, own, walls)
        prev, q = {(0, 0): None}, deque([(0, 0)])
        while q and len(prev) < 4000:
            off = q.popleft()
            p = (self.pos[0] + 2 * off[1], self.pos[1] + 2 * off[0])
            if off != (0, 0) and p not in self.visited:
                while prev[off][0] != (0, 0):
                    off = prev[off][0]
                return prev[off][1]
            for k, (dx, dy) in self.rule.items():
                nxt = (off[0] + dy // 2, off[1] + dx // 2)
                if nxt in prev or (p, k) in self.blocked or \
                        not (-64 <= nxt[0] <= 64 and -64 <= nxt[1] <= 64 and fm[nxt[0] + 64, nxt[1] + 64]):
                    continue
                prev[nxt] = (off, k)
                q.append(nxt)
        return None

    BODY_WITH_CLICKS = False

    def _click_mode(self):
        """v3 behaviour in click games; with BODY_WITH_CLICKS, only while no body has been found."""
        if 6 not in self.available:
            return False
        return not (self.BODY_WITH_CLICKS and self.me is not None and self.rule and self.keys)

    def _promise(self, act):
        if self._click_mode():
            return Arc3EchoV2._promise(self, act)
        return super()._promise(act)

    def choose(self, state):
        if self._click_mode():                                    # with clicks, the body is not the whole game: v3
            act = Arc3EchoV3.choose(self, state)
            self.last_key = act[1] if act[0] == "K" and act[1] in self.keys else None
            return act
        if self.me is not None and self.rule and not self.path and self.key_tries and \
                all(self.key_tries[k] >= self.babble for k in self.keys) and \
                not (state == self.level_start and state in self.win_paths):
            goal = self._goal()
            k = None
            if goal is not None and self._plan(goal[2:]) is None:
                act = self._cause_step()
                k = act[1] if act is not None else None
            elif goal is None and self.EXPLORE:
                k = self._frontier_step()
            if k is not None:
                self.last_key = k if k in self.keys else None
                self.key_tries[k] += 1
                return ("K", k, None)
        return super().choose(state)

    def learn(self, state, act, next_state, game_over, level_up):
        super().learn(state, act, next_state, game_over, level_up)
        if level_up:
            self.causes, self.pending, self.arena = {}, None, None  # positions are per level; wall colours travel

    def report(self):
        return {"predictions_right": self.pred[0], "predictions_wrong": self.pred[1],
                "wall_colours": sorted(self._walls()), "world_events": self.events,
                "hypotheses": [[lvl, list(k), v] for lvl, k, v in self.hypotheses]}


_COMP_CACHE = {}


def _components(grid):
    """Same-colour 4-connected components with their cells: (size, cells, colour), rare colours first.

    Pure function of the frame, memoised (several modules ask for the same frame on every step)."""
    key = (grid.shape, grid.dtype.str, grid.tobytes())
    hit = _COMP_CACHE.get(key)
    if hit is not None:
        return hit
    out = _components_raw(grid)
    if len(_COMP_CACHE) >= 8:
        _COMP_CACHE.pop(next(iter(_COMP_CACHE)))
    _COMP_CACHE[key] = out
    return out


def _components_raw(grid):
    h, w = grid.shape
    g = np.asarray(grid).tolist()                         # plain lists: same walk, far faster than numpy indexing
    seen = [[False] * w for _ in range(h)]
    comps = []
    for y in range(h):
        row = g[y]
        for x in range(w):
            if seen[y][x]:
                continue
            c = int(row[x])
            stack, cells = [(y, x)], []
            seen[y][x] = True
            while stack:
                cy, cx = stack.pop()
                cells.append((cy, cx))
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < h and 0 <= nx < w and not seen[ny][nx] and g[ny][nx] == c:
                        seen[ny][nx] = True
                        stack.append((ny, nx))
            comps.append((len(cells), cells, c))
    counts = {}
    for n, _, c in comps:
        counts[c] = counts.get(c, 0) + n
    comps = [o for o in comps if o[0] < 0.25 * h * w]
    comps.sort(key=lambda o: (counts[o[2]], o[0], min(o[1])))
    return comps


class Arc3EchoV51(Arc3EchoV5):
    """v5.1 · S5 (docs/ECHO45-S5-DESIGN.md): two faults that ARC3-GYM showed and the 8 dev games did not.
    Found and fixed on gym-train only.

      - the floor taken for the body: when the body moves, the hole it leaves shifts the floor's centre by a
        pixel with every key. v5.1 only accepts as "me" an object that moves RIGIDLY (same cells, translated);
      - the goal hypothesis at a level up was read from the NEW level's frame (inherited from v4) and could be
        the floor. v5.1 reads it from the frame just before the win, never the arena's commonest colour nor
        a wall colour.
    """

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.rigid = {}                                      # (sig, key) -> Counter of pixel shifts (dx, dy)
        self._pre = (None, None)                             # (frame, pos) before the latest observation

    def observe_state(self, frame):
        self._pre = (self.last_frame, self.pos)
        return super().observe_state(frame)

    def _nearest_colour(self):
        f, pos = self._pre
        if f is None or pos is None or self.me is None:
            return None
        common = Counter(int(v) for v in f.ravel()).most_common(1)[0][0]
        if self.arena is not None:
            y0, x0, y1, x1 = self.arena
            common = Counter(int(v) for v in f[y0:y1 + 1, x0:x1 + 1].ravel()).most_common(1)[0][0]
        skip = self._walls() | {common, self.me[0]}
        best = None
        for n, cells, c in _components(f):
            if c in skip or (self.clock is not None and all(self.clock[y, x] for y, x in cells)):
                continue
            cy = sum(y for y, _ in cells) * 2 // n
            cx = sum(x for _, x in cells) * 2 // n
            d = abs(cx - pos[0]) + abs(cy - pos[1])
            if best is None or d < best[0]:
                best = (d, c)
        return best[1] if best else None

    def _learn_self(self, frame):
        before, key = self.last_frame, self.last_key
        super()._learn_self(frame)
        if key is None or before is None or before.shape != np.asarray(frame).shape:
            return
        a, b = {}, {}
        for n, cells, c in _components(np.asarray(before)):
            a.setdefault((c, n), []).append(cells)
        for n, cells, c in _components(np.asarray(frame)):
            b.setdefault((c, n), []).append(cells)
        for sig, insts in a.items():
            if len(insts) != 1 or len(b.get(sig, ())) != 1:
                continue
            ca, cb = insts[0], b[sig][0]
            (y0, x0), (y1, x1) = min(ca), min(cb)
            dy, dx = y1 - y0, x1 - x0
            if {(y + dy, x + dx) for y, x in ca} == set(cb):
                self.rigid.setdefault((sig, key), Counter())[(dx, dy)] += 1
        best = None
        for sig in {s for s, _ in self.rigid}:
            dirs, ev = {}, 0
            for k in self.keys:
                cnt = self.rigid.get((sig, k))
                if not cnt:
                    continue
                nz = [(n, d) for d, n in cnt.items() if d != (0, 0)]
                if nz:
                    n, d = max(nz)
                    if n * 10 >= sum(cnt.values()) * 5:
                        dirs[k] = d
                        ev += n
            if dirs and ev >= self.MIN_EVIDENCE and (len(set(dirs.values())) >= 2 or ev >= 2 * self.MIN_EVIDENCE):
                if best is None or (len(dirs), ev) > (len(best[2]), best[0]):
                    best = (ev, sig, dirs)
        if best is None:
            return
        rule = {k: (2 * dx, 2 * dy) for k, (dx, dy) in best[2].items()}     # doubled units, like the centres
        if best[1] != self.me:
            self.me, self.pos = best[1], None
            self.blocked, self.visited = set(), set()
        self.rule.update(rule)


class Arc3EchoV52(Arc3EchoV51):
    """v5.2 · S5 causes (developed on ARC3-GYM train only).

      - nothing left to explore: go back to a known cause (where the world changed at a distance), stand on it,
        and explore what it opens; before, causes were only used once a goal was known;
      - touch and try: when my body steps onto an object of a colour I have not tested yet (not floor, not
        wall), the mode keys (5, 7) are pressed there once, as a person pressing "use" on a new thing.
    """
    BABBLE = 2
    STRICT_MOVES = True                                      # only a move equal to the key's rule teaches walls

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.tested_colours = set()
        self.to_try = deque()
        self.attempt = 0                                     # +1 at every GAME OVER or level up
        self.used = {}                                       # cause -> attempt in which it was last re-enacted

    def _world_event(self, before, f, cells0):
        n0 = self.events
        super()._world_event(before, f, cells0)
        if self.events > n0 and self.pos is not None and self.pos in self.causes:
            h = self.causes[self.pos]
            if h["seen"] >= 2:                               # the same effect again when I came back here
                h["ok"] += 1
                self.hypotheses.append((self.level, ("cause", self.pos), "confirmed"))
            self.used[self.pos] = self.attempt

    def learn(self, state, act, next_state, game_over, level_up):
        super().learn(state, act, next_state, game_over, level_up)
        if game_over or level_up:
            self.attempt += 1

    def _reenact(self):
        """Go back to a cause confirmed before (or seen once) that has not been re-enacted in this attempt."""
        if not self.causes or self.pos is None:
            return None
        order = sorted(self.causes.items(), key=lambda kv: (-kv[1]["ok"], -kv[1]["seen"],
                                                           abs(kv[0][0] - self.pos[0]) + abs(kv[0][1] - self.pos[1])))
        for c, h in order:
            if self.used.get(c) == self.attempt:
                continue
            plan = self._plan(c)
            if plan:
                return plan[0]
            if plan == []:
                self.used[c] = self.attempt
        return None

    def _under(self, before, cells0):
        """Colours my body covered after the last move (read from the frame before it)."""
        if before is None or not self.my_cells or not cells0:
            return set()
        old = {p for inst in cells0 for p in inst}
        new = {p for inst in self.my_cells for p in inst}
        return {int(before[y, x]) for y, x in new - old if 0 <= y < before.shape[0] and 0 <= x < before.shape[1]}

    def observe_state(self, frame):
        before, cells0, moved_from = self.last_frame, self.my_cells, self.pos
        st = super().observe_state(frame)
        if self.mode_keys and self.me is not None and self.pos != moved_from and self.arena is not None:
            y0, x0, y1, x1 = self.arena
            common = Counter(int(v) for v in before[y0:y1 + 1, x0:x1 + 1].ravel()).most_common(1)[0][0] if before is not None else None
            for c in self._under(before, cells0) - self._walls() - {common, self.me[0]} - self.tested_colours:
                self.tested_colours.add(c)
                self.to_try.extend(self.mode_keys)
        return st

    def choose(self, state):
        if not self._click_mode() and self.me is not None and self.rule and not self.path and \
                not (state == self.level_start and state in self.win_paths):
            if self.to_try:
                k = self.to_try.popleft()
                self.last_key = None
                self.key_tries[k] += 1
                return ("K", k, None)
            confirmed = any(h["ok"] and self.used.get(c) != self.attempt for c, h in self.causes.items())
            if all(self.key_tries[k] >= self.babble for k in self.keys) and self._goal() is None \
                    and (confirmed or self._frontier_step() is None):
                k = self._reenact()
                if k is not None:
                    self.last_key = k if k in self.keys else None
                    self.key_tries[k] += 1
                    return ("K", k, None)
        return super().choose(state)


class Arc3EchoV53(Arc3EchoV52):
    """v5.3 · S5+ (developed on ARC3-GYM train only): the body model also in games that have clicks, once a
    body moved by keys has been found (before that, and in click-only games, it stays v3)."""
    BODY_WITH_CLICKS = True


class Arc3EchoV54(Arc3EchoV53):
    """v5.4 · pushing (developed on ARC3-GYM train only).

      - pushable: an object that moved rigidly with my own move, right when I walked into it;
      - push experiment: with a pushable known and no goal, ECHO plans IN THE MODEL (my body + the object, walls
        as colours) to put the object onto each candidate: a still object of a rare colour (not floor, wall,
        me, the pushable). The first candidate colour that wins a level becomes the goal hypothesis for the
        next levels. Plans are followed while the world does what the model predicted; else re-planned.
    """
    PUSH_STATES = 30000
    BODY_WITH_CLICKS = False                                 # v5.3 hurt bp35/m0r0 in the real dev games

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.pushable = Counter()                            # sig -> times it moved with me when I walked into it
        self.push_goal = Counter()                           # candidate colour -> levels won by pushing onto it
        self.push_done = set()                               # (level, candidate key) already tried
        self.push_plan = deque()                             # [(key, expected my centre after it)]
        self.push_target = None
        self.push_fail = set()                               # (attempt, candidate) with no plan from that state

    def _learn_self(self, frame):
        before, key = self.last_frame, self.last_key
        super()._learn_self(frame)
        if key is None or before is None or self.me is None or key not in self.rule:
            return
        dx, dy = self.rule[key]
        a, b = {}, {}
        for n, cells, c in _components(np.asarray(before)):
            a.setdefault((c, n), []).append(cells)
        for n, cells, c in _components(np.asarray(frame)):
            b.setdefault((c, n), []).append(cells)
        mine = a.get(self.me)
        if not mine or len(mine) != 1:
            return
        me_new = {(y + dy // 2, x + dx // 2) for y, x in mine[0]}
        for sig, insts in a.items():
            if sig == self.me or len(insts) != 1 or len(b.get(sig, ())) != 1:
                continue
            ca, cb = insts[0], b[sig][0]
            if me_new & set(ca) and {(y + dy // 2, x + dx // 2) for y, x in ca} == set(cb):
                self.pushable[sig] += 1

    def _push_plan(self):
        f = self.last_frame
        if f is None or not self.pushable or not self.my_cells or self.pos is None or len(self.rule) < len(self.keys):
            return None                                        # plan only with every key's rule known
        sig = self.pushable.most_common(1)[0][0]
        comps = _components(f)
        boxes = [cells for n, cells, c in comps if (c, n) == sig]
        if len(boxes) != 1:
            return None
        box = boxes[0]
        me_cells = [p for inst in self.my_cells for p in inst]
        y0, x0, y1, x1 = self.arena if self.arena is not None else (0, 0, f.shape[0] - 1, f.shape[1] - 1)
        common = Counter(int(v) for v in f[y0:y1 + 1, x0:x1 + 1].ravel()).most_common(1)[0][0]
        walls = self._walls() - {sig[0]}
        skip = walls | {common, self.me[0], sig[0]}
        cands = []
        for n, cells, c in comps:
            if c in skip or (self.clock is not None and all(self.clock[y, x] for y, x in cells)):
                continue
            cy, cx = sum(y for y, _ in cells) * 2 // n, sum(x for _, x in cells) * 2 // n
            key = (c, n, cx, cy)
            if (self.level, key) in self.push_done or (self.attempt, key) in self.push_fail:
                continue
            cands.append((-self.push_goal[c], n, key))
        if not cands:
            return None
        cands.sort()
        target = cands[0][2]
        own = set(me_cells) | set(box)
        fm_me = self._fitmap_raw(f, me_cells, own, walls)
        fm_box = self._fitmap_raw(f, box, own, walls)
        D = {(my - by, mx - bx) for by, bx in box for my, mx in me_cells}     # box_off - me_off when they overlap
        bcy, bcx = sum(y for y, _ in box) * 2 // len(box), sum(x for _, x in box) * 2 // len(box)
        tx, ty = target[2], target[3]
        moves = [(k, (dy // 2, dx // 2)) for k, (dx, dy) in self.rule.items()]
        start = ((0, 0), (0, 0))
        prev, q = {start: None}, deque([start])
        ok = lambda fm, o: -64 <= o[0] <= 64 and -64 <= o[1] <= 64 and fm[o[0] + 64, o[1] + 64]
        while q and len(prev) < self.PUSH_STATES:
            st = q.popleft()
            m, bo = st
            if abs(bcx + 2 * bo[1] - tx) <= 1 and abs(bcy + 2 * bo[0] - ty) <= 1:
                path = []
                while prev[st] is not None:
                    st0, k = prev[st]
                    path.append((k, (self.pos[0] + 2 * st[0][1], self.pos[1] + 2 * st[0][0])))
                    st = st0
                return target, list(reversed(path))
            for k, d in moves:
                nm = (m[0] + d[0], m[1] + d[1])
                if not ok(fm_me, nm):
                    continue
                nb = bo
                if (bo[0] - nm[0], bo[1] - nm[1]) in D:
                    nb = (bo[0] + d[0], bo[1] + d[1])
                    if not ok(fm_box, nb):
                        continue
                nxt = (nm, nb)
                if nxt not in prev:
                    prev[nxt] = (st, k)
                    q.append(nxt)
        self.push_fail.add((self.attempt, target))              # unreachable from here: retry after a reset
        return None

    def _fitmap_raw(self, frame, cells, own, walls):
        h, w = frame.shape
        bad = np.isin(frame, list(walls)) if walls else np.zeros((h, w), bool)
        if self.clock is not None:
            bad = bad | self.clock
        for y, x in own:
            bad[y, x] = False
        pad = np.ones((h + 128, w + 128), bool)
        pad[64:64 + h, 64:64 + w] = bad
        okm = np.ones((129, 129), bool)
        for y, x in cells:
            okm &= ~pad[y:y + 129, x:x + 129]
        return okm

    def choose(self, state):
        if self.pushable and not self._click_mode() and self.me is not None and self.rule and not self.path \
                and self._goal() is None and not (state == self.level_start and state in self.win_paths):
            if self.push_plan and self.push_plan[0][1] is not None and self._expect not in (None, self.pos):
                self.push_plan.clear()                           # the world did not follow the model: re-plan
            if not self.push_plan:
                for _ in range(4):
                    res = self._push_plan()
                    if res is None:
                        continue
                    self.push_target, plan = res
                    self.push_plan = deque(plan)
                    break
            if self.push_plan:
                k, self._expect = self.push_plan.popleft()
                if not self.push_plan:
                    self.push_done.add((self.level, self.push_target))
                self.last_key = k
                self.key_tries[k] += 1
                return ("K", k, None)
        self._expect = None
        return super().choose(state)

    _expect = None

    def learn(self, state, act, next_state, game_over, level_up):
        if level_up and self.push_target is not None and not self.push_plan:
            self.push_goal[self.push_target[0]] += 1
            self.hypotheses.append((self.level + 1, ("push onto", self.push_target[0]), "proposed"))
        if game_over or level_up:
            self.push_plan.clear()
            self.push_target = None
        super().learn(state, act, next_state, game_over, level_up)


class Arc3EchoV55(Arc3EchoV54):
    """v5.5 · clicks that work as keys (developed on ARC3-GYM train only).

    In a click-only game, if clicking a still object moves another object rigidly and always by the same
    displacement, that click is a "key" and the moved object is "me" (contingency, as with keys). With two such
    clicks in different directions the whole body model (walls as colours, planning, causes, pushing) is used,
    with those clicks as its keys. Until then, and if it never happens, the agent is v3.
    """
    PSEUDO = 100
    MIN_CLICK_EVIDENCE = 2

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.click_moves = {}                                # click xy -> Counter of (sig, (dx, dy)) rigid moves
        self.pkey_xy = {}                                    # pseudo key id -> click xy
        self._last_click = None

    def _click_mode(self):
        if self.pkey_xy:
            return False
        return super()._click_mode()

    def _rigid_moves(self, before, frame):
        a, b = {}, {}
        for n, cells, c in _components(np.asarray(before)):
            a.setdefault((c, n), []).append(cells)
        for n, cells, c in _components(np.asarray(frame)):
            b.setdefault((c, n), []).append(cells)
        out = []
        for sig, insts in a.items():
            if len(insts) != 1 or len(b.get(sig, ())) != 1:
                continue
            ca, cb = insts[0], b[sig][0]
            (y0, x0), (y1, x1) = min(ca), min(cb)
            d = (x1 - x0, y1 - y0)
            if d != (0, 0) and {(y + d[1], x + d[0]) for y, x in ca} == set(cb):
                out.append((sig, d))
        return out

    def observe_state(self, frame):
        before, xy = self.last_frame, self._last_click
        st = super().observe_state(frame)
        if xy is not None and before is not None and not self.keys_real() and before.shape == np.asarray(frame).shape:
            for sig, d in self._rigid_moves(before, frame):
                self.click_moves.setdefault(xy, Counter())[(sig, d)] += 1
            self._adopt_click_keys()
        return st

    def keys_real(self):
        return [a for a in self.available if a in (1, 2, 3, 4)]

    def _adopt_click_keys(self):
        per_sig = {}
        for xy, cnt in self.click_moves.items():
            (sig, d), n = cnt.most_common(1)[0]
            if n >= self.MIN_CLICK_EVIDENCE and n * 10 >= sum(cnt.values()) * 7:
                per_sig.setdefault(sig, {})[xy] = d
        if self.pkey_xy:                                      # adopted: keep adding clicks that move the same body
            moves = per_sig.get(self.me, {})
            known = set(self.pkey_xy.values())
            for xy, d in sorted(moves.items()):
                if xy not in known:
                    k = self.PSEUDO + len(self.pkey_xy)
                    self.pkey_xy[k], self.rule[k] = xy, (2 * d[0], 2 * d[1])
                    self.keys.append(k)
                    self.key_tries[k] = self.babble
            return
        best = max(per_sig.items(), key=lambda kv: len(set(kv[1].values())), default=None)
        if best is None or len(set(best[1].values())) < 2:
            return
        sig, moves = best
        self.me, self.pos = sig, None
        self.keys, self.rule = [], {}
        for i, (xy, d) in enumerate(sorted(moves.items())):
            k = self.PSEUDO + i
            self.pkey_xy[k] = xy
            self.keys.append(k)
            self.rule[k] = (2 * d[0], 2 * d[1])
            self.key_tries[k] = self.babble                      # already pressed while discovering them
        self.blocked, self.visited = set(), set()
        self.hypotheses.append((self.level, ("click keys", sig, len(moves)), "proposed"))

    def choose(self, state):
        act = super().choose(state)
        if act[0] == "K" and act[1] in self.pkey_xy:
            xy = self.pkey_xy[act[1]]
            act = ("C", 6, xy)
        self._last_click = act[2] if act[0] == "C" else None
        return act


class Arc3EchoV56(Arc3EchoV55):
    """v5.6 · a model of what each click changes (developed on ARC3-GYM train only).

    In click-only games without a body, every click's effect is recorded pixel by pixel (old -> new, assumed to
    toggle back). Pixels that always change together are one "unit" (a light, whatever its shape). At a level up,
    if every unit that changed ended in ONE colour, the goal hypothesis is "every pixel of the toggling colours
    shows that colour". In the next level ECHO clicks each toggling object once to learn its effect, plans the
    shortest click sequence in the model (breadth-first over the units' colours) and follows it. The border is
    excluded (BOUNDARY: bars are time, not the world).
    """
    MAX_UNITS = 16

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.effects = {}                                    # click xy -> {pixel: (old, new)}
        self.clicked_cells = set()
        self.toggle_colours = set()
        self.goal_colour = None
        self.click_plan = deque()

    def _pure_click(self):
        return 6 in self.available and not self.keys_real() and not self.pkey_xy

    def _inner(self, y, x, h, w):
        e = self.EDGE
        return e <= y < h - e and e <= x < w - e

    def observe_state(self, frame):
        before, xy = self.last_frame, self._last_click
        st = super().observe_state(frame)
        if not self._pure_click() or xy is None or before is None:
            return st
        f = np.asarray(frame)
        if before.shape != f.shape:
            return st
        h, w = f.shape
        for n, cells, c in _components(before):
            if (xy[1], xy[0]) in cells:
                self.clicked_cells |= set(cells)
                break
        eff = {}
        for y, x in np.argwhere(before != f):
            if self._inner(y, x, h, w):
                eff[(int(y), int(x))] = (int(before[y, x]), int(f[y, x]))
        self._undo = (xy, self.effects.get(xy), set(self.toggle_colours))
        self.effects[xy] = eff
        for a, b in eff.values():
            self.toggle_colours |= {a, b}
        return st

    _undo = None

    def _units(self):
        sig = {}
        for xy, eff in self.effects.items():
            for p in eff:
                sig.setdefault(p, set()).add(xy)
        groups = {}
        for p, clicks in sig.items():
            groups.setdefault(frozenset(clicks), []).append(p)
        return [min(ps) for ps in groups.values()]

    def _plan_clicks(self):
        f = self.last_frame
        h, w = f.shape
        for n, cells, c in _components(f):                     # learn every toggling object's effect first
            if c in self.toggle_colours and all(self._inner(y, x, h, w) for y, x in cells) \
                    and not set(cells) <= self.clicked_cells:
                free = [p for p in cells if p not in self.clicked_cells]
                y, x = free[len(free) // 2]
                return [(int(x), int(y))]
        reps = self._units()
        if not reps or len(reps) > self.MAX_UNITS:
            return None
        pos = {p: i for i, p in enumerate(reps)}
        acts = []
        for xy, eff in self.effects.items():
            e = {pos[p]: ab for p, ab in eff.items() if p in pos}
            if e:
                acts.append((xy, e))
        start = tuple(int(f[p]) for p in reps)
        prev, q = {start: None}, deque([start])
        while q and len(prev) < 40000:
            s = q.popleft()
            if all(v == self.goal_colour for v in s):
                path = []
                while prev[s] is not None:
                    s, b = prev[s]
                    path.append(b)
                return list(reversed(path))
            for xy, e in acts:
                n = list(s)
                for i, (old, new) in e.items():
                    n[i] = new if s[i] == old else old if s[i] == new else s[i]
                n = tuple(n)
                if n not in prev:
                    prev[n] = (s, xy)
                    q.append(n)
        return None

    def choose(self, state):
        if self._pure_click() and self.goal_colour is not None and self.last_frame is not None \
                and not (state == self.level_start and state in self.win_paths):
            if not self.click_plan:
                plan = self._plan_clicks()
                if plan:
                    self.click_plan = deque(plan)
            if self.click_plan:
                xy = self.click_plan.popleft()
                self._last_click = xy
                self.last_key = None
                return ("C", 6, xy)
        return super().choose(state)

    def learn(self, state, act, next_state, game_over, level_up):
        if (level_up or game_over) and self._undo is not None:    # that frame is a new level / a reset, not an effect
            xy, prev_eff, prev_cols = self._undo
            if prev_eff is None:
                self.effects.pop(xy, None)
            else:
                self.effects[xy] = prev_eff
            self.toggle_colours = prev_cols
        self._undo = None
        if level_up and self._pure_click() and self._pre[0] is not None and self.effects \
                and act[0] == "C" and act[2] in self.effects:
            pre = self._pre[0].copy()                          # the winning click is not seen: apply its known effect
            for (y, x), (old, new) in self.effects[act[2]].items():
                pre[y, x] = new if pre[y, x] == old else old if pre[y, x] == new else pre[y, x]
            final = {int(pre[p]) for p in self._units()}
            if len(final) == 1:
                self.goal_colour = final.pop()
                self.hypotheses.append((self.level + 1, ("all toggles show", self.goal_colour), "proposed"))
        if level_up or game_over:
            self.click_plan.clear()
        if level_up:
            self.effects, self.clicked_cells = {}, set()
        super().learn(state, act, next_state, game_over, level_up)


class Arc3EchoV57(Arc3EchoV56):
    """v5.7 · hidden state (developed on ARC3-GYM v3 train only).

      - reset keys: a mode key that sends my body back to where the level started is expensive. Once seen, it is
        removed from blind exploration and only pressed on purpose (touch and try); after pressing it on purpose,
        ECHO does not press it again for a while, so whatever it set off (a copy replaying my path) can happen;
      - what worked travels: a colour whose touch-and-try was followed by a change at a distance is tried again in
        every level (tested colours are per level; useful colours first).
    """
    HOLD = 40

    def __init__(self, available, seed, boundary=True):
        super().__init__(available, seed, boundary)
        self.reset_keys = set()
        self.start_pos = None
        self.hold = 0
        self.useful_colours = Counter()
        self._tried_at = None                                # (colour, events before) of the last deliberate try
        self.jumps = {}                                      # mode key -> Counter of where it sent me

    def observe_state(self, frame):
        pos0, key0, move0 = self.pos, getattr(self, "_last_mode", None), self.last_key
        tested0 = set(self.tested_colours)
        st = super().observe_state(frame)
        new_cols = self.tested_colours - tested0
        if new_cols:
            self._last_colour = min(new_cols)                 # the colour that triggered this touch and try
        self._track(frame, pos0, move0)
        if key0 is not None and self.pos is not None and pos0 is not None and self.pos != pos0:
            self.jumps.setdefault(key0, Counter())[self.pos] += 1
            if self.jumps[key0].most_common(1)[0][1] >= 2 and key0 not in self.reset_keys:
                self.reset_keys.add(key0)                     # it always sends me to the same place: a reset
                self.start_pos = self.jumps[key0].most_common(1)[0][0]
                pass                                          # blind presses are filtered in choose()
        if self._tried_at is not None and self.events > self._tried_at[1]:
            self.useful_colours[self._tried_at[0]] += 1
            self._tried_at = None
        return st

    def choose(self, state):
        if self._click_mode():                                # games with clicks: unchanged (v5.6)
            return super().choose(state)
        if self.hold:
            self.hold -= 1
        if self.to_try:                                       # a deliberate try (touch and try)
            k = self.to_try[0]
            if k in self.reset_keys and self.hold:
                self.to_try.popleft()
            else:
                self.to_try.popleft()
                if k in self.reset_keys:
                    self.hold = self.HOLD
                self._last_mode = k
                self.last_key = None
                self.key_tries[k] += 1
                self._tried_at = (self._last_colour, self.events) if self._last_colour is not None else None
                return ("K", k, None)
        act = super().choose(state)
        if act[0] == "K" and act[1] in self.reset_keys:       # blind press of an expensive key: explore first
            alt = self._frontier_step() if (self.me is not None and self.rule) else None
            if alt is None and self.hold:
                alt = next((k for k in self.keys if (self.pos, k) not in self.blocked), None)
            if alt is not None:                               # nothing new to explore and no test running: allowed
                act = ("K", alt, None)
                self.last_key = alt
        self._last_mode = act[1] if act[0] == "K" and act[1] in self.mode_keys else None
        return act

    _last_mode = None
    _last_colour = None
    _prev_cells = None

    def _goal(self):
        """A still twin of me is a goal only if I have no key that leaves copies of me."""
        g = super()._goal()
        if g is not None and self.reset_keys and self.me is not None and (g[0], g[1]) == tuple(self.me):
            return None
        return g

    def _track(self, frame, pos0, key):
        """Identity: with several bodies identical to me (a copy), I am the one where my own move predicts."""
        insts = self._instances(frame)
        if not insts and pos0 is not None and self.me is not None and self._prev_cells:
            f = np.asarray(frame)                              # touching a twin: one blob of my colour
            dx, dy = self.rule.get(key, (0, 0)) if key is not None else (0, 0)
            for sx, sy in ((dx // 2, dy // 2), (0, 0)):         # where my move predicts, else where I was
                cells = [(y + sy, x + sx) for y, x in self._prev_cells]
                if all(0 <= y < f.shape[0] and 0 <= x < f.shape[1] and int(f[y, x]) == self.me[0] for y, x in cells):
                    self.pos = (pos0[0] + 2 * sx, pos0[1] + 2 * sy)
                    self.my_cells = [cells]
                    self.visited.add(self.pos)
                    break
            self._prev_cells = self.my_cells[0] if self.my_cells else self._prev_cells
            return
        if len(insts) < 2 or pos0 is None:
            self._prev_cells = insts[0] if insts else self._prev_cells
            return
        exp = pos0
        if key is not None and key in self.rule:
            exp = (pos0[0] + self.rule[key][0], pos0[1] + self.rule[key][1])
        best = None
        for inst in insts:
            n = len(inst)
            c = (sum(x for _, x in inst) * 2 // n, sum(y for y, _ in inst) * 2 // n)
            d = abs(c[0] - exp[0]) + abs(c[1] - exp[1])       # where MY move predicts, not where I was
            if best is None or d < best[0]:
                best = (d, c, inst)
        self.pos, self.my_cells = best[1], [best[2]]
        self._prev_cells = best[2]
        self.visited.add(self.pos)

    def _under(self, before, cells0):
        return super()._under(before, cells0)

    def learn(self, state, act, next_state, game_over, level_up):
        super().learn(state, act, next_state, game_over, level_up)
        if level_up:
            self.tested_colours = set()                       # per level; useful ones are tried first again
            self.start_pos, self.hold = None, 0
        if game_over:
            self.hold = 0
            self.tested_colours -= set(self.useful_colours)   # retry what worked after a reset


class Arc3EchoV5NoExplore(Arc3EchoV5):
    """v5 without exploring in the model (ablation)."""
    EXPLORE = False


class RandomAgent:
    """The official random policy (any allowed action, clicks anywhere), seeded for the audit."""
    def __init__(self, available, seed):
        self.available = sorted(int(a) for a in available)
        self.rng = random.Random(seed)

    def observe_state(self, frame):
        return None

    def choose(self, state):
        a = self.rng.choice([a for a in self.available])
        return ("C", 6, (self.rng.randint(0, 63), self.rng.randint(0, 63))) if a == 6 else ("K", a, None)

    def learn(self, *args):
        pass


