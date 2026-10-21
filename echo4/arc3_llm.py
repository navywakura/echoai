"""E4-BENCH-ARC3-LLM · a language model plays ARC-AGI-3, alone and with ECHO.

    (ARC venv) python -m echoai.echo4.arc3_llm play OUT --split dev|exam --arm L|LP|LECHO --games G...
    (ARC venv) python -m echoai.echo4.arc3_agent audit OUT          (replays the recorded actions)

Contract: docs/ECHO4-BENCH-ARC3-LLM-DESIGN.md (approved, 2026-09-24).

  L      the model sees the 64x64 grid as text and what its last actions did
  LP     + ECHO's perception: objects (colour, size, centre) and which objects moved
  LECHO  + ECHO's memory, facts separated from hypotheses: what each action moves (BOUNDARY),
         inert actions, what ended the game, known states and untried ones, and the model's own
         predictions checked against what happened (firewall: a model rule is never a fact).
         Two extra orders: EXPLORE n (ECHO explores by itself) and GOTO sK (shortest known path).

Same budget for every arm: 60 model calls and at most 2000 actions per game.
The model is the player; the ECHO arm's engine is Arc3EchoV2 (frozen v2), used as memory and
executor. Receipts: every call (prompt, answer, cost) in OUT/<game>-<arm>.calls.jsonl.
"""
import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter, deque
from pathlib import Path

import numpy as np

from echoai.echo4.arc3_agent import (Arc3EchoV2, _act, arcade, frame_hash, games_for, objects,
                                     score)
from echoai.echo4.bench1 import api_key, ask, credits_remaining

MODEL = "qwen/qwen3-30b-a3b-instruct-2507"
CALLS, MAX_ACTIONS, MAX_SEQ, MAX_EXPLORE, MAX_TOKENS = 60, 2000, 16, 100, 400
HEX = "0123456789abcdef"

SYSTEM = """You are playing an unknown turn-based puzzle game on a 64x64 grid of colours 0-f.
Nobody tells you the rules or the goal: find them by acting. Completing a level gives progress;
the game may end (GAME OVER) and then it restarts at the current level. Fewer actions is better.
Actions: ACTION1..ACTION5 and ACTION7 are keys (often up/down/left/right/interact/undo; check what
they do). ACTION6 X Y clicks the cell at column X, row Y (0-63). Only the listed actions exist.
Reply with exactly three lines:
RULE: <one sentence: what you now think the goal or rule is>
EXPECT: <one of: change, no_change, level_up, game_over> (what your actions will cause)
ACTIONS: <up to 16 actions separated by commas, e.g. ACTION1, ACTION1, ACTION6 12 30>"""

SYSTEM_ECHO = SYSTEM + """
You also command ECHO, a memory and executor that watches every action. Its FACTS were observed
by ECHO itself; your earlier RULEs are shown as HYPOTHESES with what really happened.
Two extra orders may appear in ACTIONS (alone or with other actions):
EXPLORE N   ECHO tries untried actions by itself for N steps (N <= 100)
GOTO sK     ECHO walks the shortest known path back to known state sK"""


def grid_text(frame):
    return "\n".join("".join(HEX[int(v) & 15] for v in row) for row in np.asarray(frame))


def object_list(frame, limit=40):
    lines = []
    for i, (n, x, y, c) in enumerate(objects(frame)[:limit]):
        lines.append("o%d colour %s size %d centre (%d,%d)" % (i, HEX[c & 15], n, x, y))
    return "\n".join(lines) or "(none)"


def moved_objects(before, after, limit=8):
    """Objects (same colour and size) that disappeared at one centre and appeared at another."""
    a = Counter((c, n, x, y) for n, x, y, c in objects(before))
    b = Counter((c, n, x, y) for n, x, y, c in objects(after))
    gone, new = list((a - b).elements()), list((b - a).elements())
    out = []
    for c, n, x, y in gone:
        match = [o for o in new if o[0] == c and o[1] == n]
        if match:
            m = min(match, key=lambda o: abs(o[2] - x) + abs(o[3] - y))
            new.remove(m)
            out.append("colour %s size %d moved (%d,%d)->(%d,%d)" % (HEX[c & 15], n, x, y, m[2], m[3]))
        else:
            out.append("colour %s size %d at (%d,%d) disappeared or changed" % (HEX[c & 15], n, x, y))
    out += ["colour %s size %d appeared at (%d,%d)" % (HEX[c & 15], n, x, y) for c, n, x, y in new]
    return out[:limit]


def kind_name(act):
    return "RESET" if act[0] == "R" else ("ACTION%d" % act[1] if act[0] == "K" else "ACTION6 %d %d" % act[2])


def parse(text, available, echo):
    """-> (rule, expect, [orders]); order = act tuple | ("EXPLORE", n) | ("GOTO", k) | ("GATE", word)."""
    rule = (re.search(r"RULE:\s*(.+)", text) or [None, ""])[1].strip()[:300]
    expect = (re.search(r"EXPECT:\s*(\w+)", text) or [None, ""])[1].lower()
    m = re.search(r"ACTIONS:\s*(.+)", text, re.S)
    orders = []
    for tok in re.split(r"[,\n;]+", m[1] if m else ""):
        tok = tok.strip().upper()
        if not tok:
            continue
        mm = re.match(r"ACTION6\s+(\d+)\s+(\d+)", tok)
        if mm:
            orders.append(("C", 6, (min(int(mm[1]), 63), min(int(mm[2]), 63))) if 6 in available else ("GATE", tok))
        elif re.match(r"ACTION[1-57]$", tok):
            a = int(tok[-1])
            orders.append(("K", a, None) if a in available else ("GATE", tok))
        elif tok == "RESET":
            orders.append(("R", 0, None))
        elif echo and re.match(r"EXPLORE\s+\d+", tok):
            orders.append(("EXPLORE", min(int(tok.split()[1]), MAX_EXPLORE)))
        elif echo and re.match(r"GOTO\s+S\d+", tok):
            orders.append(("GOTO", int(tok.split()[1][1:])))
        elif tok:
            orders.append(("GATE", tok[:20]))
        if len(orders) >= MAX_SEQ + 2:
            break
    return rule, expect, orders


class Game:
    """One game played by the model; ECHO v2 watches every action (it only speaks in the LECHO arm)."""

    def __init__(self, arc, game, arm):
        from arcengine import GameState
        self.GameState = GameState
        self.env = arc.make(game)
        obs = self.env.reset()
        self.available = sorted(int(a) for a in obs.available_actions)
        self.frame = np.array(obs.frame[-1])
        self.win_levels = obs.win_levels
        self.echo = Arc3EchoV2(obs.available_actions, int(hashlib.sha256(game.encode()).hexdigest()[:8], 16))
        self.state = self.echo.observe_state(self.frame)
        self.echo.level_start = self.state
        self.ids = {self.state: 0}
        self.levels, self.level_actions, self.per_level = 0, 0, []
        self.record = {"game": game, "arm": arm, "model": MODEL, "budget_calls": CALLS, "win_levels": self.win_levels,
                       "actions": [], "frames": [frame_hash(self.frame)], "levels": [0], "resets": 0,
                       "origin": [], "calls": 0}
        self.effects = {}           # kind -> Counter of observed consequences (ECHO facts)
        self.overs = []             # kinds of the last action before each GAME OVER
        self.border_only = 0        # steps where only the masked border changed (time, not me)
        self.hypotheses = []        # (call, rule, expect, observed)
        self.done = False

    def sid(self, s):
        return self.ids.setdefault(s, len(self.ids))

    def step(self, act, origin):
        before = self.frame
        obs = _act(self.env, act)
        if obs is None:
            self.done = True
            return "no-observation"
        self.record["actions"].append([act[0], act[1], list(act[2]) if act[2] else None])
        self.record["origin"].append(origin)
        self.frame = np.array(obs.frame[-1])
        self.record["frames"].append(frame_hash(self.frame))
        self.record["levels"].append(int(obs.levels_completed))
        self.level_actions += 1
        if act[0] != "R":
            self.echo.level_actions.append(act)
        level_up = obs.levels_completed > self.levels
        over = obs.state is self.GameState.GAME_OVER
        nxt = self.echo.observe_state(self.frame)
        self.echo.learn(self.state, act, nxt, over, level_up)
        changed = nxt != self.state
        if not changed and frame_hash(self.frame) != frame_hash(before):
            self.border_only += 1
        kind = kind_name(act) if act[0] != "C" else "ACTION6 on colour %s" % HEX[int(before[act[2][1], act[2][0]]) & 15]
        eff = self.effects.setdefault(kind, Counter())
        eff["tries"] += 1
        eff["changed"] += int(changed)
        if changed and not over:
            for mv in moved_objects(before, self.frame, limit=2):
                eff[mv.split(" moved ")[0] + " moved " + _direction(mv)] += 1
        outcome = "level_up" if level_up else "game_over" if over else "change" if changed else "no_change"
        if level_up:
            self.per_level.append(self.level_actions)
            self.levels, self.level_actions = int(obs.levels_completed), 0
            self.echo.level_start, self.echo.level_actions = nxt, []
        if obs.state is self.GameState.WIN:
            self.done = True
        if over:
            self.overs.append(kind)
            obs = self.env.reset()
            self.record["resets"] += 1
            self.record["actions"].append(["R", 0, None])
            self.record["origin"].append("auto-reset")
            self.frame = np.array(obs.frame[-1])
            self.record["frames"].append(frame_hash(self.frame))
            self.record["levels"].append(int(obs.levels_completed))
            nxt = self.echo.observe_state(self.frame)
            self.echo.level_actions = []
        self.state = nxt
        self.sid(nxt)
        if len(self.record["actions"]) >= MAX_ACTIONS:
            self.done = True
        return outcome

    # ---- what the model sees
    def prompt(self, arm, call, last_report, prev_frame):
        head = ["Call %d of %d. Levels completed: %d of %d. Actions used: %d." %
                (call + 1, CALLS, self.levels, self.win_levels, len(self.record["actions"])),
                "Available actions: %s" % ", ".join("ACTION6 X Y" if a == 6 else "ACTION%d" % a for a in self.available),
                "What your last actions did:\n" + (last_report or "(first call)")]
        if arm in ("LP", "LECHO"):
            mv = moved_objects(prev_frame, self.frame) if prev_frame is not None else []
            head.append("Objects now (ECHO perception, rare colours first):\n" + object_list(self.frame))
            head.append("Objects that moved since your last call:\n" + ("\n".join(mv) or "(none)"))
        if arm == "LECHO":
            head.append(self.memory())
        head.append("Grid (row 0 first, column 0 left):\n" + grid_text(self.frame))
        return "\n\n".join(head)

    def memory(self):
        lines = ["ECHO MEMORY. FACTS (observed by ECHO):"]
        for kind, e in sorted(self.effects.items(), key=lambda kv: -kv[1]["tries"])[:14]:
            moves = [k for k, _ in e.most_common() if " moved " in k][:2]
            lines.append("- %s: tried %d, changed the world %d%s" % (kind, e["tries"], e["changed"],
                                                                      ("; " + "; ".join(moves)) if moves else ""))
        if self.border_only:
            lines.append("- %d times only the grid border changed after an action (a step or energy bar "
                         "moving with time): not caused by you." % self.border_only)
        if self.overs:
            lines.append("- GAME OVER %d times; last action each time: %s" %
                         (len(self.overs), ", ".join(k for k, _ in Counter(self.overs).most_common(4))))
        frontier = [s for s, todo in self.echo.untried.items() if todo]
        lines.append("- known states %d; you are in s%d; states with untried actions: %d%s" %
                     (len(self.echo.untried), self.sid(self.state), len(frontier),
                      (" (e.g. %s)" % ", ".join("s%d" % self.sid(s) for s in frontier[:6])) if frontier else ""))
        if self.echo.win_paths:
            lines.append("- a winning path is known for %d level(s)" % len(self.echo.win_paths))
        if self.hypotheses:
            lines.append("HYPOTHESES (your earlier rules; never facts) and what really happened:")
            for call, rule, expect, observed in self.hypotheses[-6:]:
                verdict = "NO PREDICTION" if not expect else "CONFIRMED" if expect in observed else "REFUTED"
                lines.append("- call %d: \"%s\" expected %s, observed %s -> prediction %s" %
                             (call + 1, rule[:140], expect or "?", "/".join(sorted(observed)) or "nothing", verdict))
        return "\n".join(lines)

    def run_orders(self, orders, arm):
        report, observed = [], set()
        for order in orders:
            if self.done:
                break
            if order[0] == "GATE":
                report.append("%s: not allowed here, skipped" % order[1])
            elif order[0] == "EXPLORE":
                outs = Counter()
                for _ in range(order[1]):
                    if self.done:
                        break
                    o = self.step(self.echo.choose(self.state), "echo-explore")
                    outs[o] += 1
                    observed.add(o)
                    if o == "level_up":
                        break
                report.append("EXPLORE %d: %s" % (order[1], ", ".join("%s %d" % kv for kv in outs.items())))
            elif order[0] == "GOTO":
                target = next((s for s, k in self.ids.items() if k == order[1]), None)
                path = _path(self.echo, self.state, target) if target else None
                if path is None:
                    report.append("GOTO s%d: no known path" % order[1])
                else:
                    for act in path[:50]:
                        if self.done:
                            break
                        o = self.step(act, "echo-goto")
                        observed.add(o)
                    report.append("GOTO s%d: now in s%d" % (order[1], self.sid(self.state)))
            else:
                o = self.step(order, "model")
                observed.add(o)
                report.append("%s -> %s" % (kind_name(order), o))
        return report[:24], observed


def _direction(mv):
    m = re.search(r"\((\d+),(\d+)\)->\((\d+),(\d+)\)", mv)
    if not m:
        return "?"
    dx, dy = int(m[3]) - int(m[1]), int(m[4]) - int(m[2])
    return "by (%+d,%+d)" % (dx, dy)


def _path(echo, start, target):
    prev, q = {start: None}, deque([start])
    while q:
        s = q.popleft()
        if s == target:
            path, cur = [], s
            while prev[cur] is not None:
                ps, act = prev[cur]
                path.append(act)
                cur = ps
            return list(reversed(path))
        for act, ns in echo.adj.get(s, {}).items():
            if ns not in prev and (s, act) not in echo.dead:
                prev[ns] = (s, act)
                q.append(ns)
    return None


def play(arc, game, arm, out, key, floor_micro):
    g = Game(arc, game, arm)
    calls_path = out / ("%s-%s.calls.jsonl" % (game, arm))
    calls_path.write_text("")
    system = SYSTEM_ECHO if arm == "LECHO" else SYSTEM
    last_report, prev_frame, spent, stopped = "", None, 0, ""
    for call in range(CALLS):
        if g.done:
            break
        if call % 10 == 0 and credits_remaining(key) < floor_micro:
            stopped = "budget floor reached"
            break
        user = g.prompt(arm, call, last_report, prev_frame)
        r = ask(MODEL, system, user, max_tokens=MAX_TOKENS, key=key)
        spent += int(r["usage"].get("cost_micro_usd", 0))
        rule, expect, orders = parse(r["content"], g.available, arm == "LECHO")
        prev_frame = g.frame
        report, observed = g.run_orders(orders or [("GATE", "no actions in reply")], arm)
        g.hypotheses.append((call, rule, expect, observed))
        last_report = "\n".join(report)
        with calls_path.open("a") as f:
            f.write(json.dumps({"call": call, "user_sha": hashlib.sha256(user.encode()).hexdigest(),
                                "user": user, "content": r["content"], "usage": r["usage"], "error": r["error"],
                                "ms": r["ms"], "rule": rule, "expect": expect, "observed": sorted(observed)}) + "\n")
        g.record["calls"] = call + 1
    rec = g.record
    rec["levels_completed"], rec["actions_per_level"] = g.levels, g.per_level
    rec["cost_micro_usd"], rec["stopped"] = spent, stopped
    rec["origin_counts"] = dict(Counter(rec["origin"]))
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("play",))
    ap.add_argument("out")
    ap.add_argument("--split", choices=("dev", "exam"), default="dev")
    ap.add_argument("--arm", choices=("L", "LP", "LECHO"), required=True)
    ap.add_argument("--games", nargs="*")
    ap.add_argument("--floor-usd", type=float, required=True, help="stop when OpenRouter credit drops below this")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    key = api_key()
    arc = arcade()
    baselines = {e.game_id: list(e.baseline_actions or []) for e in arc.get_environments()}
    allowed = games_for(args.split)
    for game in args.games or allowed:
        if game not in allowed:
            raise SystemExit("%s is not in the %s split" % (game, args.split))
        t = time.time()
        rec = play(arc, game, args.arm, out, key, int(args.floor_usd * 1_000_000))
        rec["score"] = score(rec, baselines.get(game, []))
        rec["seconds"] = int(time.time() - t)
        (out / ("%s-%s.json" % (game, args.arm))).write_text(json.dumps(rec))
        print(json.dumps({"game": game, "arm": args.arm, "levels": rec["levels_completed"], "of": rec["win_levels"],
                          "score": rec["score"], "actions": len(rec["actions"]), "calls": rec["calls"],
                          "origin": rec["origin_counts"], "usd": rec["cost_micro_usd"] / 1e6,
                          "stopped": rec["stopped"], "seconds": rec["seconds"]}))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
