"""ARC3-GYM · ECHO-4.5 S5 (docs/ECHO45-S5-DESIGN.md): generated turn-based games with the ARC-AGI-3 interface.

Run from echoai/ with the ARC venv (arcengine is needed for GameAction / GameState).

    python -m seed.arc3gym validate                    V1 and V2 (solver) on gym-train + gym-test
    python -m seed.arc3gym run AGENT --split test --rep N --out DIR

Every game: 64x64 frame, 16 colours, random palette, cell size 3-6 px, 5 levels of growing size, an
energy bar on the bottom row (GAME OVER when it runs out; the level is repeated). Each level is kept only
if an exact breadth-first solver finds a solution (and, for the cause families, none with the gate shut);
the reference action count of a level is that exact minimum.
"""
import argparse
import hashlib
import json
import random
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np

FAMILIES = ("K1", "K2", "K3", "K4", "C1", "C2", "M1")
# v3: hidden state (what the frame does not show): H1 order of two switches, H2 a gate that closes by itself
# after T steps, H3 a switch that must be entered 3 times, H4 a copy that replays your path (as in g50t).
HIDDEN = ("H1", "H2", "H3", "H4")
SPLITS = {"train": range(0, 40), "test": range(1000, 1060), "exam": range(5000, 5100)}   # exam: S5-D only
DIRS = {1: (0, -1), 2: (0, 1), 3: (-1, 0), 4: (1, 0)}      # ACTION1 up, 2 down, 3 left, 4 right
N_LEVELS = 5
# v1: the contracted gym (V2 red: random completed 27 % of test levels).
# v2 (declared after that red, same families): bigger levels, longer minimum solutions, a tighter energy bar
# and lights that also toggle their neighbours.
VERSIONS = {
    1: {"size0": 4, "grow": 1, "min_opt": 3, "limit": (3, 30), "c1_neighbours": False},
    2: {"size0": 6, "grow": 2, "min_opt": 8, "limit": (2, 10), "c1_neighbours": True},
    3: {"size0": 5, "grow": 1, "min_opt": 8, "limit": (2, 10), "c1_neighbours": True},
}
VERSION = 1


class Level:
    """Static data of one level; the dynamic state is (pos, opened, box, lit)."""

    def __init__(self, fam, w, h):
        self.fam, self.w, self.h = fam, w, h
        self.walls, self.gate = set(), set()
        self.start = self.goal = self.switch = self.box = self.target = None
        self.lights, self.dummies, self.arrows = [], [], {}
        self.optimal = None
        self.lit0 = frozenset()
        self.switch2 = None
        self.timer = 0

    def init(self):
        if self.fam == "H4":
            return (self.start, False, None, frozenset(), ((), (), 0, None))
        if self.fam in HIDDEN:
            return (self.start, False, None, frozenset(), 0)
        return (self.start, False, self.box, self.lit0)

    def free(self, c, opened):
        x, y = c
        return 0 <= x < self.w and 0 <= y < self.h and c not in self.walls and (opened or c not in self.gate)

    def step(self, s, act, target=None):
        """Pure game logic, shared by the environment and the solver. target: clicked object id."""
        if self.fam in HIDDEN:
            return self._hstep(s, act)
        pos, opened, box, lit = s
        fam = self.fam
        if act in DIRS and fam in ("K1", "K2", "K3", "K4", "M1"):
            return self._move(s, DIRS[act])
        if act == 5 and fam == "K3" and pos == self.switch:
            return (pos, True, box, lit)
        if act == 6 and target is not None:
            kind, val = target
            if fam == "C1" and kind == "light":
                flip = {val}
                if VERSIONS[VERSION]["c1_neighbours"]:
                    x, y = val
                    flip |= {c for c in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if c in self.lights}
                return (pos, opened, box, lit ^ flip)
            if fam == "C2" and kind == "arrow":
                return self._move(s, DIRS[val])
            if fam == "M1" and kind == "switch":
                return (pos, True, box, lit)
        return s

    def _move(self, s, d):
        pos, opened, box, lit = s
        n = (pos[0] + d[0], pos[1] + d[1])
        if not self.free(n, opened):
            return s
        if box is not None and n == box:
            b2 = (box[0] + d[0], box[1] + d[1])
            if not self.free(b2, opened):
                return s
            return (n, opened, b2, lit)
        if self.fam == "K2" and n == self.switch:
            opened = True
        return (n, opened, box, lit)

    def _hstep(self, s, act):
        """Hidden-state families: the state has a fifth element the frame does not show."""
        pos, opened, box, lit, h = s
        if self.fam == "H4":
            rec, gpath, gi, gpos = h
            if act == 5:                                        # back to the start; a copy replays what you did
                gpos = self.start
                return (self.start, self.start == self.switch, None, lit, ((), rec, 0, gpos))
            if act not in DIRS:
                return s
            d = DIRS[act]
            n = (pos[0] + d[0], pos[1] + d[1])
            if self.free(n, opened):
                pos = n
            rec = rec + (act,) if len(rec) < 16 else rec
            if gpos is not None and gi < len(gpath):
                gd = DIRS[gpath[gi]]
                gn = (gpos[0] + gd[0], gpos[1] + gd[1])
                if self.free(gn, opened):
                    gpos = gn
                gi += 1
            return (pos, pos == self.switch or gpos == self.switch, None, lit, (rec, gpath, gi, gpos))
        if act not in DIRS:
            return s
        d = DIRS[act]
        n = (pos[0] + d[0], pos[1] + d[1])
        if not self.free(n, opened):
            n = pos
        entered = n != pos
        if self.fam == "H1":                                    # switch, then switch2: the order is hidden
            if entered and n == self.switch:
                h = 1
            elif entered and n == self.switch2:
                opened, h = opened or h == 1, 0
        elif self.fam == "H2":                                  # the gate closes by itself after T steps
            if opened:
                h -= 1
                if h <= 0:
                    opened, h = False, 0
            if entered and n == self.switch:
                opened, h = True, self.timer
        elif self.fam == "H3":                                  # the third entry opens it
            if entered and n == self.switch and not opened:
                h += 1
                opened = h >= 3
        return (n, opened, None, lit, h)

    def won(self, s):
        if self.fam == "K4":
            return s[2] == self.target
        if self.fam == "C1":
            return s[3] == frozenset(self.lights)
        return s[0] == self.goal

    def actions(self):
        """Solver actions: (action id, click target or None)."""
        acts = []
        if self.fam in ("K1", "K2", "K3", "K4", "M1") or self.fam in HIDDEN:
            acts += [(a, None) for a in DIRS]
        if self.fam in ("K3", "H4"):
            acts.append((5, None))
        if self.fam == "C1":
            acts += [(6, ("light", c)) for c in self.lights] + [(6, ("dummy", c)) for c in self.dummies]
        if self.fam == "C2":
            acts += [(6, ("arrow", k)) for k in self.arrows]
        if self.fam == "M1":
            acts.append((6, ("switch", self.switch)))
        return acts

    def _walk(self, a, b, opened):
        prev, q = {a: None}, deque([a])
        while q:
            c = q.popleft()
            if c == b:
                path = []
                while prev[c] is not None:
                    c, k = prev[c]
                    path.append(k)
                return list(reversed(path))
            for k, d in DIRS.items():
                n = (c[0] + d[0], c[1] + d[1])
                if n not in prev and self.free(n, opened):
                    prev[n] = (c, k)
                    q.append(n)
        return None

    def _solve_h4(self):
        """H4 reference (an upper bound, not the exact minimum): walk to the switch, press 5, then reach the goal
        while the copy replays that walk and stays on the switch (exact search over (me, copy step))."""
        p = self._walk(self.start, self.switch, False)
        if not p:
            return None
        s = self.init()
        for k in p:
            s = self.step(s, k)
        s = self.step(s, 5)
        prev, q = {s: None}, deque([s])
        while q and len(prev) < 200000:
            c = q.popleft()
            if self.won(c):
                path = []
                while prev[c] is not None:
                    c, k = prev[c]
                    path.append((k, None))
                return [(k, None) for k in p] + [(5, None)] + list(reversed(path))
            for k in DIRS:
                n = self.step(c, k)
                key = n
                if key not in prev:
                    prev[key] = (c, k)
                    q.append(n)
        return None

    def solve(self, opened_only=None):
        """Exact shortest solution (list of (action, target)) or None. opened_only=False: gate never opens."""
        if self.fam == "H4":
            return None if opened_only is False else self._solve_h4()
        s0 = self.init()
        prev, q = {s0: None}, deque([s0])
        acts = self.actions()
        while q:
            s = q.popleft()
            if self.won(s):
                path = []
                while prev[s] is not None:
                    s, a = prev[s]
                    path.append(a)
                return list(reversed(path))
            if len(prev) > 400000:
                return None
            for a in acts:
                n = self.step(s, *a)
                if opened_only is False and n[1]:
                    continue
                if n not in prev:
                    prev[n] = (s, a)
                    q.append(n)
        return None


def _open_cells(lv, rng, k, avoid):
    cells = [(x, y) for x in range(lv.w) for y in range(lv.h) if (x, y) not in lv.walls and (x, y) not in avoid]
    rng.shuffle(cells)
    return cells[:k]


def _dist(lv, a, b):
    """Shortest walk from a to b with the gate open (for the H2 timer)."""
    prev, q = {a: 0}, deque([a])
    while q:
        c = q.popleft()
        if c == b:
            return prev[c]
        for d in DIRS.values():
            n = (c[0] + d[0], c[1] + d[1])
            if n not in prev and lv.free(n, True):
                prev[n] = prev[c] + 1
                q.append(n)
    return 0


def make_level(fam, idx, rng, max_w, max_h):
    for _ in range(400):
        v = VERSIONS[VERSION]
        w = min(max_w, v["size0"] + v["grow"] * idx + rng.randint(0, 2))
        h = min(max_h, v["size0"] + v["grow"] * idx + rng.randint(0, 2))
        if fam in ("K4", "H4"):
            w, h = min(w, 7), min(h, 7)
        lv = Level(fam, w, h)
        dens = 0.15 if fam == "K4" else 0.25
        if fam != "C1":
            lv.walls = {(x, y) for x in range(w) for y in range(h) if rng.random() < dens}
        cells = _open_cells(lv, rng, 8, set())
        if len(cells) < 4:
            continue
        if fam == "C1":
            n = 3 + idx // 2 if VERSION == 1 else 4 + idx
            cells = [(x, y) for x in range(w) for y in range(h)]
            rng.shuffle(cells)
            if VERSIONS[VERSION]["c1_neighbours"]:                  # a connected blob, so neighbours matter
                blob = [cells[0]]
                while len(blob) < n:
                    x, y = blob[rng.randrange(len(blob))]
                    c = rng.choice(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
                    if 0 <= c[0] < w and 0 <= c[1] < h and c not in blob:
                        blob.append(c)
                rest = [c for c in cells if c not in blob]
                lv.lights, lv.dummies = blob, rest[:2]
                s = (lv.start, False, None, frozenset(blob))             # scramble from the solved board:
                for _ in range(n + idx):                                 # always solvable
                    s = lv.step(s, 6, ("light", blob[rng.randrange(n)]))
                lv.lit0 = s[3]
            else:
                lv.lights, lv.dummies = cells[:n], cells[n:n + 2]
            lv.start = (-1, -1)
        else:
            lv.start, lv.goal = cells[0], cells[1]
        if fam in ("K2", "K3", "M1") or fam in HIDDEN:
            gx, gy = lv.goal
            nbrs = [c for c in ((gx + 1, gy), (gx - 1, gy), (gx, gy + 1), (gx, gy - 1)) if 0 <= c[0] < w and 0 <= c[1] < h]
            rng.shuffle(nbrs)
            lv.gate = {nbrs[0]}
            lv.walls |= set(nbrs[1:])
            lv.walls -= {lv.start, lv.goal} | lv.gate
            sw = [c for c in cells[2:] if c not in lv.walls and c not in lv.gate and c != lv.goal]
            if not sw:
                continue
            lv.switch = sw[0]
            if fam == "H1":
                if len(sw) < 2:
                    continue
                lv.switch2 = sw[1]
            if fam == "H2":
                lv.timer = _dist(lv, lv.switch, lv.goal) + 1       # just enough to run to the goal
                if lv.timer <= 1:
                    continue
        if fam == "K4":
            lv.box, lv.target, lv.goal = cells[2], cells[3], None
        if fam == "C2":
            lv.arrows = {1: None, 2: None, 3: None, 4: None}
        sol = lv.solve()
        if sol is None or ((fam in ("K2", "K3", "M1") or fam in HIDDEN) and lv.solve(opened_only=False) is not None):
            continue
        if len(sol) < (3 if fam == "C1" else VERSIONS[VERSION]["min_opt"]):
            continue
        lv.optimal = len(sol)
        return lv
    raise RuntimeError("could not generate a level")


class Game:
    def __init__(self, seed):
        tag = "ARC3GYM-%d" % seed if VERSION == 1 else "ARC3GYM-v%d-%d" % (VERSION, seed)
        rng = random.Random(hashlib.sha256(tag.encode()).digest())
        self.seed = seed
        fams = HIDDEN if VERSION == 3 else FAMILIES
        self.fam = fams[rng.randrange(len(fams))]
        cols = list(range(16))
        rng.shuffle(cols)
        self.pal = dict(zip(("out", "floor", "wall", "me", "goal", "switch", "gate", "box", "on", "off", "dummy", "bar"), cols))
        self.cs = rng.randint(3, 6)
        self.ox, self.oy = 2, 2
        max_w = (64 - 4 - (self.cs + 1) * 2) // self.cs
        max_h = (64 - 6) // self.cs
        self.levels = [make_level(self.fam, i, rng, max_w, max_h) for i in range(N_LEVELS)]
        self.baseline = [lv.optimal for lv in self.levels]
        self.game_id = "gym%d-%04d-%s" % (VERSION, seed, self.fam) if VERSION > 1 else "gym%04d-%s" % (seed, self.fam)
        self.available = sorted({a for lv in self.levels for a, _ in lv.actions()})

    # ---- pixels
    def _rect(self, c):
        x, y = c
        return self.ox + x * self.cs, self.oy + y * self.cs

    def arrow_rect(self, k):
        """The four arrow buttons of C2, in a column at the right edge."""
        return 64 - 3 - self.cs, 3 + (k - 1) * (self.cs + 2)

    def render(self, lv, s, left, limit):
        p, cs = self.pal, self.cs
        f = np.full((64, 64), p["out"], dtype=np.int8)

        def block(c, colour, hollow=False):
            x0, y0 = self._rect(c)
            f[y0:y0 + cs, x0:x0 + cs] = colour
            if hollow and cs >= 3:
                f[y0 + 1:y0 + cs - 1, x0 + 1:x0 + cs - 1] = p["floor"]

        pos, opened, box, lit = s[:4]
        if lv.fam != "C1":
            f[self.oy:self.oy + lv.h * cs, self.ox:self.ox + lv.w * cs] = p["floor"]
            for c in lv.walls:
                block(c, p["wall"])
            if not opened:
                for c in lv.gate:
                    block(c, p["gate"])
            if lv.switch is not None:
                block(lv.switch, p["switch"], hollow=True)
            if lv.switch2 is not None:
                block(lv.switch2, p["dummy"], hollow=True)
            if lv.goal is not None:
                block(lv.goal, p["goal"], hollow=True)
            if lv.target is not None:
                block(lv.target, p["goal"], hollow=True)
            if box is not None:
                block(box, p["box"])
            if lv.fam == "H4" and s[4][3] is not None:
                block(s[4][3], p["me"])                          # the copy looks exactly like me
            block(pos, p["me"])
        else:
            for c in lv.lights:
                block(c, p["on"] if c in lit else p["off"])
            for c in lv.dummies:
                block(c, p["dummy"])
        if lv.fam == "C2":
            for k in DIRS:
                x0, y0 = self.arrow_rect(k)
                f[y0:y0 + cs, x0:x0 + cs] = p["dummy"]
        f[63, :] = p["out"]
        f[63, : max(0, 64 * left // limit)] = p["bar"]
        return f

    def target_at(self, lv, x, y):
        """Which object a click at pixel (x, y) hits, if any."""
        if lv.fam == "C2":
            for k in DIRS:
                x0, y0 = self.arrow_rect(k)
                if x0 <= x < x0 + self.cs and y0 <= y < y0 + self.cs:
                    return ("arrow", k)
            return None
        c = ((x - self.ox) // self.cs, (y - self.oy) // self.cs)
        if x < self.ox or y < self.oy:
            return None
        if lv.fam == "C1":
            if c in lv.lights:
                return ("light", c)
            if c in lv.dummies:
                return ("dummy", c)
        if lv.fam == "M1" and c == lv.switch:
            return ("switch", c)
        return None


class Obs:
    def __init__(self, frame, available, levels, state, win_levels):
        self.frame, self.available_actions, self.levels_completed = [frame], available, levels
        self.state, self.win_levels = state, win_levels


class GymEnv:
    """Same surface as an arc_agi environment: reset() and step(GameAction, data={x, y})."""

    def __init__(self, seed):
        self.game = Game(seed)
        self.game_id = self.game.game_id
        self.baseline_actions = self.game.baseline
        self.level = 0
        self.s = None

    def _limit(self):
        a, b = VERSIONS[VERSION]["limit"]
        return a * self.game.levels[self.level].optimal + b

    def _obs(self, state):
        lv = self.game.levels[min(self.level, N_LEVELS - 1)]
        return Obs(self.game.render(lv, self.s, self._limit() - self.steps, self._limit()),
                   self.game.available, self.level, state, N_LEVELS)

    def reset(self):
        from arcengine import GameState
        if self.level >= N_LEVELS:
            self.level = 0
        self.s, self.steps = self.game.levels[self.level].init(), 0
        return self._obs(GameState.NOT_FINISHED)

    def step(self, ga, data=None):
        from arcengine import GameState
        act = int(ga.value)
        lv = self.game.levels[self.level]
        target = None
        if act == 6 and data:
            target = self.game.target_at(lv, int(data["x"]), int(data["y"]))
        if act in self.game.available:
            self.s = lv.step(self.s, act, target)
        self.steps += 1
        if lv.won(self.s):
            self.level += 1
            if self.level >= N_LEVELS:
                return Obs(self.game.render(lv, self.s, 0, 1), self.game.available, self.level, GameState.WIN, N_LEVELS)
            self.s, self.steps = self.game.levels[self.level].init(), 0
            return self._obs(GameState.NOT_FINISHED)
        if self.steps >= self._limit():
            return self._obs(GameState.GAME_OVER)
        return self._obs(GameState.NOT_FINISHED)


# ---- validation (V1, V2 solver part) and runs
def _solution_actions(game, lv, sol):
    out = []
    for a, t in sol:
        if a != 6:
            out.append((a, None))
            continue
        kind, val = t
        if kind == "arrow":
            x0, y0 = game.arrow_rect(val)
        else:
            x0, y0 = game._rect(val)
        out.append((6, (x0 + game.cs // 2, y0 + game.cs // 2)))
    return out


def validate(seeds):
    from arcengine import GameAction, GameState
    fams, levels, solved = {}, 0, 0
    for sd in seeds:
        a, b = Game(sd), Game(sd)
        assert a.baseline == b.baseline and a.fam == b.fam, "not deterministic"
        env = GymEnv(sd)
        obs = env.reset()
        h0 = hashlib.sha1(obs.frame[0].tobytes()).hexdigest()
        assert h0 == hashlib.sha1(GymEnv(sd).reset().frame[0].tobytes()).hexdigest(), "frames differ"
        for i, lv in enumerate(env.game.levels):
            for act, xy in _solution_actions(env.game, lv, lv.solve()):
                obs = env.step(GameAction.from_id(act), data={"x": xy[0], "y": xy[1]} if xy else None)
            levels += 1
            solved += int(obs.levels_completed == i + 1)
        fams[env.game.fam] = fams.get(env.game.fam, 0) + 1
        assert obs.state is GameState.WIN
    return {"games": len(seeds), "levels": levels, "solver_levels": solved, "families": fams}


class _Random:
    def __init__(self, available, seed, boundary=True):
        from echo_arc.agent import RandomAgent
        self.a = RandomAgent(available, seed)
        self.level_start, self.level_actions = None, []

    def observe_state(self, frame):
        return None

    def choose(self, state):
        return self.a.choose(state)

    def learn(self, *args):
        pass


def run(agent, split, rep, budget, out):
    from echo_arc import runner
    runner.AGENTS.setdefault("random", _Random)
    rows = []
    for sd in SPLITS[split]:
        env = GymEnv(sd)
        rec = runner.play(env, budget, runner.seed_for(env.game_id, rep), agent_name=agent)
        rec.update(game=env.game_id, agent=agent, rep=rep,
                   official_score=runner.official_game_score(rec["actions_per_level"], env.baseline_actions))
        rows.append({"game": env.game_id, "levels": rec["levels_completed"], "score": round(rec["official_score"], 4),
                     "actions": len(rec["actions"])})
        if out:
            Path(out).mkdir(parents=True, exist_ok=True)
            rec.pop("frames", None)
            (Path(out) / (env.game_id + ".json")).write_text(json.dumps(rec))
    summary = {"agent": agent, "split": split, "rep": rep, "games": len(rows),
               "levels": sum(r["levels"] for r in rows), "of": len(rows) * N_LEVELS,
               "mean_official_score": round(sum(r["score"] for r in rows) / len(rows), 4)}
    if out:
        (Path(out) / "summary.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1))
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("validate", "run"))
    ap.add_argument("agent", nargs="?")
    ap.add_argument("--split", default="test", choices=tuple(SPLITS))
    ap.add_argument("--rep", type=int, default=0)
    ap.add_argument("--budget", type=int, default=2000)
    ap.add_argument("--out")
    ap.add_argument("--version", type=int, default=1, choices=tuple(VERSIONS))
    a = ap.parse_args(argv)
    global VERSION
    VERSION = a.version
    t = time.time()
    if a.cmd == "validate":
        res = validate(list(SPLITS["train"]) + list(SPLITS["test"]))
    else:
        res = run(a.agent, a.split, a.rep, a.budget, a.out)
    res["seconds"] = round(time.time() - t, 1)
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
