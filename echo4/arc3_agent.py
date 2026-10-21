"""E4-BENCH-ARC3 · ECHO-ARC3: ECHO's pieces playing ARC-AGI-3 without a language model.

    (ARC venv) python -m echoai.echo4.arc3_agent play OUT_DIR --split dev|exam --arm ECHO|NOBOUNDARY|RANDOM
    (ARC venv) python -m echoai.echo4.arc3_agent audit OUT_DIR       (replays every recorded game)

Contract: docs/ECHO4-BENCH-ARC3-DESIGN.md (approved, 2026-09-24).

  perceive   frame -> discrete state (fingerprint) + objects; each new state is a WSP fact in CAM
  BOUNDARY   separate what depends on me from what changes with time: the frame border holds
             step/energy bars that advance on their own (measured on dev games); the state
             fingerprint ignores it. The NOBOUNDARY ablation does not, and clicks at random.
  T          lived transitions (state, action) -> next state
  curiosity  go to the nearest known state with untried actions and try them; clicks aim at objects
  Q / delta  a GAME_OVER marks its (state, action) as deadly (negative delta); a completed level
             stores its winning path and replays it if that level start comes back
  gate       never an action the game does not allow

Built from ECHO's pieces (WSP, CAM, T, Q, gate); it is not the full MAINTAIN agent (declared).
"""
import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np

from echoai.core.cam import Cam
from echoai.core.dag import allocate
from echoai.core.spoke import encode_event
from echoai.core.wsp import pack

ROOT = Path(__file__).resolve().parents[1]
SPLIT = ROOT / "lab/arc3/split.json"
SPLIT_SHA = "91f23200c99619aa94ce4a9b897d015092f6d4d584e8b6df5f7f07652ac57e08"
EXCLUDED = {"ls20-9607627b"}          # opened during the feasibility probe (declared)
KEY_FILE = ROOT / ".arcprizekey"
MAX_CLICKS = 32
STATE_SOURCE = "arc3-observed-state"


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
        self.cam, self.n = Cam(), 0
        self.T = {}                  # (state, action) -> next state
        self.adj = {}                # state -> {action: next state} (same facts as T, for search)
        self.untried = {}            # state -> [actions]
        self.dead = set()            # (state, action) that ended the game: negative delta
        self.win_paths = {}          # level start state -> winning action list
        self.path = deque()
        self.level_start, self.level_actions = None, []

    # ---- memory: a new state is an observed fact in CAM
    def _remember(self, state):
        raw = pack(src=7, rel=35, dst=3, time=9, domain=9, generator=8, style=120 + (self.n >> 8) % 100,
                   slot=0, seq=self.n & 255)
        vertex, latency, _ = encode_event(raw)
        allocate(self.cam, raw, vertex, latency, (0,) * 6, has_fact=1, extract="state " + state,
                 source=STATE_SOURCE, key=raw)
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


# ---------------------------------------------------------------- playing (ARC venv only)

def _act(env, act):
    from arcengine import GameAction
    kind, value, xy = act
    if kind == "R":
        return env.reset()
    ga = GameAction.from_id(value) if hasattr(GameAction, "from_id") else GameAction(value)
    return env.step(ga, data={"x": int(xy[0]), "y": int(xy[1])}) if kind == "C" else env.step(ga)


def play(arcade, game, arm, budget, seed):
    from arcengine import GameState
    env = arcade.make(game)
    obs = env.reset()
    frame = np.array(obs.frame[-1])
    if arm == "RANDOM":
        agent = RandomAgent(obs.available_actions, seed)
    elif arm in ("ECHO2", "NOBOUNDARY2"):
        agent = Arc3EchoV2(obs.available_actions, seed, boundary=(arm == "ECHO2"))
    else:
        agent = Arc3Echo(obs.available_actions, seed, boundary=(arm == "ECHO"))
    win_levels = obs.win_levels
    record = {"game": game, "arm": arm, "seed": seed, "budget": budget, "win_levels": win_levels,
              "actions": [], "frames": [frame_hash(frame)], "levels": [0], "resets": 0}
    levels, level_actions, per_level = 0, 0, []
    state = agent.observe_state(frame)
    if isinstance(agent, Arc3Echo):
        agent.level_start = state
    for step in range(budget):
        act = agent.choose(state)
        obs = _act(env, act)
        if obs is None:
            break
        record["actions"].append([act[0], act[1], list(act[2]) if act[2] else None])
        level_actions += 1
        if isinstance(agent, Arc3Echo) and act[0] != "R":
            agent.level_actions.append(act)
        frame = np.array(obs.frame[-1])
        record["frames"].append(frame_hash(frame))
        record["levels"].append(int(obs.levels_completed))
        level_up = obs.levels_completed > levels
        game_over = obs.state is GameState.GAME_OVER
        nxt = agent.observe_state(frame)
        agent.learn(state, act, nxt, game_over, level_up)
        if level_up:
            per_level.append(level_actions)
            levels, level_actions = obs.levels_completed, 0
            if isinstance(agent, Arc3Echo):
                agent.level_start, agent.level_actions = nxt, []
        if obs.state is GameState.WIN:
            break
        if game_over:
            obs = env.reset()
            record["resets"] += 1
            record["actions"].append(["R", 0, None])
            frame = np.array(obs.frame[-1])
            record["frames"].append(frame_hash(frame))
            record["levels"].append(int(obs.levels_completed))
            nxt = agent.observe_state(frame)
            if isinstance(agent, Arc3Echo):
                agent.level_actions = []
        state = nxt
    record["levels_completed"] = levels
    record["actions_per_level"] = per_level
    if isinstance(agent, Arc3Echo):
        record["echo_stats"] = {"states": len(agent.untried), "transitions": len(agent.T),
                                "deadly": len(agent.dead), "states_with_untried": sum(1 for v in agent.untried.values() if v),
                                "win_paths": len(agent.win_paths)}
    return record


def score(record, baseline):
    """Official formula: per level min(100, baseline/actions*100) if completed, else 0; mean over levels."""
    scores = []
    for i, base in enumerate(baseline):
        if i < len(record["actions_per_level"]):
            taken = record["actions_per_level"][i]
            scores.append(min(100.0, 100.0 * base / taken) if taken else 0.0)
        else:
            scores.append(0.0)
    return round(sum(scores) / len(scores), 3) if scores else 0.0


def games_for(split_name):
    split = json.loads(SPLIT.read_text())
    if hashlib.sha256(json.dumps(split, sort_keys=True, indent=1).encode()).hexdigest() != SPLIT_SHA:
        raise ValueError("frozen split differs from the contract")
    return [g for g in split[split_name] if g not in EXCLUDED]


def arcade():
    """Local play with Nav's key. Importing arc_agi may load a .env.example from the working
    directory (placeholder key, online mode), so the key and the mode are passed explicitly."""
    key = KEY_FILE.read_text().strip() if KEY_FILE.is_file() else os.environ.get("ARC_API_KEY", "")
    os.environ["ENVIRONMENTS_DIR"] = str(ROOT / "lab/arc3/environment_files")
    import arc_agi
    os.environ["ARC_API_KEY"] = key
    os.environ["OPERATION_MODE"] = "normal"
    return arc_agi.Arcade(arc_api_key=key, operation_mode=arc_agi.OperationMode.NORMAL)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("play", "audit"))
    ap.add_argument("out")
    ap.add_argument("--split", choices=("dev", "exam"), default="dev")
    ap.add_argument("--arm", choices=("ECHO", "NOBOUNDARY", "RANDOM", "ECHO2", "NOBOUNDARY2"), default="ECHO")
    ap.add_argument("--budget", type=int, default=2000)
    ap.add_argument("--games", nargs="*")
    ap.add_argument("--rep", type=int, default=0, help="repeat index (RANDOM seeds); 0 = the dev seed")
    args = ap.parse_args(argv)
    out = Path(args.out)
    arc = arcade()
    baselines = {e.game_id: list(e.baseline_actions or []) for e in arc.get_environments()}
    if args.command == "play":
        out.mkdir(parents=True, exist_ok=True)
        games = args.games or games_for(args.split)
        summary = []
        for g in games:
            t = time.time()
            tag = args.arm if not args.rep else "%s-r%d" % (args.arm, args.rep)
            seed = int(hashlib.sha256((g + tag).encode()).hexdigest()[:8], 16)
            rec = play(arc, g, args.arm, args.budget, seed)
            rec["score"] = score(rec, baselines.get(g, []))
            rec["seconds"] = int(time.time() - t)
            (out / ("%s-%s.json" % (g, tag))).write_text(json.dumps(rec))
            line = {"game": g, "arm": args.arm, "levels": rec["levels_completed"], "of": rec["win_levels"],
                    "score": rec["score"], "actions": len(rec["actions"]), "resets": rec["resets"],
                    "seconds": rec["seconds"]}
            summary.append(line)
            print(json.dumps(line))
            sys.stdout.flush()
        return 0
    # audit: replay every recorded action sequence and compare frames and levels
    bad = []
    for f in sorted(out.glob("*.json")):
        rec = json.loads(f.read_text())
        if "actions" not in rec:
            continue
        env = arc.make(rec["game"])
        obs = env.reset()
        frames, levels = [frame_hash(np.array(obs.frame[-1]))], [0]
        for kind, value, xy in rec["actions"]:
            obs = _act(env, (kind, value, tuple(xy) if xy else None))
            frames.append(frame_hash(np.array(obs.frame[-1])))
            levels.append(int(obs.levels_completed))
        if frames != rec["frames"] or levels != rec["levels"]:
            bad.append(f.name)
    print(json.dumps({"replayed": len(list(out.glob("*.json"))), "mismatches": bad, "valid": not bad}))
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
