"""E4-BENCH-ARC3-LLM2 · the model solves ARC-AGI-3 using ECHO as its laboratory.

    (ARC venv) python -m echoai.echo4.arc3_llm2 play OUT --backend opus|gpt --arm L|LECHO --split dev|exam
                    [--games G...] [--manual FILE] [--lessons] [--floor-usd X]
    (ARC venv) python -m echoai.echo4.arc3_llm2 manual OUT --backend B --arm A      (dev lessons -> manual)
    (ARC venv) python -m echoai.echo4.arc3_agent audit OUT                          (replay)

Contract: docs/ECHO4-BENCH-ARC3-LLM2-DESIGN.md (approved, 2026-09-25).

Both arms: grid, last results, the model's own NOTES (unverified, returned next call) and its own
MANUAL (lessons it wrote on dev games). LECHO adds ECHO as a laboratory: object perception,
observed FACTS, rule tests (CONFIRMED/REFUTED, carried across levels, never facts), a capability
ledger with this game's numbers, and the EXPLORE/GOTO orders. The only difference is ECHO.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

from echoai.echo4.arc3_agent import arcade, games_for, score
from echoai.echo4.arc3_llm import Game, HEX, moved_objects, object_list
from echoai.echo4.bench1 import api_key, ask, credits_remaining

MODELS = {"opus": "claude-opus-5-5 (claude -p, clean mode, effort low)", "gpt": "openai/gpt-5.4-mini"}
GPT_DEV = ("bp35-0a0ad940", "g50t-5849a774", "sk48-d8078629", "su15-1944f8ab")
GPT_EXAM = ("cn04-2fe56bfb", "dc22-fdcac232", "r11l-495a7899", "re86-8af5384d", "tn36-ef4dde99",
            "tr87-cd924810", "tu93-0768757b", "vc33-5430563c")
CALLS, MAX_TOKENS, NOTES_MAX, MANUAL_MAX = 30, 700, 600, 2000
EMPTY_MCP = Path(__file__).resolve().parents[1] / "lab/arc3/empty-mcp.json"

BASE = """You are solving an unknown turn-based puzzle game on a 64x64 grid of colours 0-f.
Nobody tells you the rules or the goal: discover them by acting, then solve each level with as
few actions as possible. GAME OVER restarts the current level. Only the listed actions exist:
ACTION1..ACTION5 and ACTION7 are keys; ACTION6 X Y clicks column X, row Y (0-63).
You have no memory between calls except your NOTES, which you rewrite every call.
Reply with exactly four lines:
NOTES: <what you want to remember next call, max 600 characters>
RULE: <one sentence: the rule or goal you are working on now>
EXPECT: <change | no_change | level_up | game_over | moves C DX DY> (what your ACTIONS will cause;
        "moves C DX DY" = some object of colour C shifts by DX columns and DY rows)
ACTIONS: <up to 16 actions separated by commas, e.g. ACTION1, ACTION6 12 30>"""

ECHO_PART = """
You work with ECHO, a laboratory that watches every action. ECHO gives you FACTS it observed itself,
tests each RULE you state against what really happens (CONFIRMED or REFUTED; rules are never
facts), and keeps score of what worked in this game. Use it: state testable rules, read the
verdicts, and let ECHO do tedious work. Extra orders allowed in ACTIONS:
EXPLORE N   ECHO tries untried actions by itself for N steps (N <= 100), stops at a level up
GOTO sK     ECHO walks the shortest known path back to known state sK"""

LESSONS_ASK = """The game is over for you. Write exactly 5 short lessons (one line each, max 300
characters total per lesson) that would help you play a NEW, different game of this kind better%s.
Start each line with "- "."""


# ---------------------------------------------------------------- model backends (receipts)

def ask_opus(system, user):
    """Claude Code headless in clean mode: no tools, settings, MCP servers or slash commands."""
    cmd = ["claude", "-p", "--model", "opus", "--effort", "low", "--tools", "", "--setting-sources", "",
           "--strict-mcp-config", "--mcp-config", str(EMPTY_MCP), "--disable-slash-commands",
           "--no-session-persistence", "--output-format", "json", "--system-prompt", system]
    started = time.monotonic_ns()
    content, usage, error = "", {}, ""
    for attempt in range(4):
        try:
            p = subprocess.run(cmd, input=user, capture_output=True, text=True, timeout=600,
                               cwd=str(EMPTY_MCP.parent))
            d = json.loads(p.stdout)
            if d.get("is_error"):
                error = "is_error:" + str(d.get("result", ""))[:120]
                if "limit" in error.lower():
                    break
            else:
                content = (d.get("result") or "").strip()
                u = d.get("usage") or {}
                usage = {k: int(v) for k, v in u.items() if isinstance(v, int) and not isinstance(v, bool)}
                usage["list_cost_micro_usd"] = int(round(float(d.get("total_cost_usd", 0)) * 1_000_000))
                error = ""
                break
        except (subprocess.TimeoutExpired, ValueError, OSError) as exc:
            error = type(exc).__name__
        time.sleep(10 * (attempt + 1))
    return {"model": MODELS["opus"], "content": content, "usage": usage, "error": error,
            "ms": (time.monotonic_ns() - started) // 1_000_000}


def ask_backend(backend, system, user, key):
    if backend == "opus":
        return ask_opus(system, user)
    r = ask(MODELS["gpt"], system, user, max_tokens=MAX_TOKENS, key=key)
    r.pop("request", None)
    return r


# ---------------------------------------------------------------- the game with ECHO as laboratory

def parse_expect(text):
    m = re.search(r"EXPECT:\s*moves\s+([0-9a-fA-F])\s+(-?\d+)\s+(-?\d+)", text)
    if m:
        return ("moves", int(m[1], 16), int(m[2]), int(m[3]))
    m = re.search(r"EXPECT:\s*(\w+)", text)
    word = m[1].lower() if m else ""
    return (word,) if word in ("change", "no_change", "level_up", "game_over") else ("",)


def expect_text(e):
    return "moves %s %+d %+d" % (HEX[e[1]], e[2], e[3]) if e[0] == "moves" else (e[0] or "nothing")


class Game2(Game):
    def __init__(self, arc, game, arm):
        super().__init__(arc, game, arm)
        self.moves = []                      # (colour, dx, dy) observed after the current orders
        self.rules = {}                      # rule text -> [confirmed, refuted, last call]
        self.ledger = {o: Counter() for o in ("model", "echo-explore", "echo-goto")}

    def step(self, act, origin):
        before = self.frame
        outcome = super().step(act, origin)
        led = self.ledger.get(origin)
        if led is not None:
            led["actions"] += 1
            led["changes"] += int(outcome in ("change", "level_up"))
            led["levels"] += int(outcome == "level_up")
            led["game_overs"] += int(outcome == "game_over")
        if outcome in ("change", "level_up"):
            for mv in moved_objects(before, self.frame, limit=8):
                m = re.match(r"colour (\w) size \d+ moved \((\d+),(\d+)\)->\((\d+),(\d+)\)", mv)
                if m:
                    self.moves.append((int(m[1], 16), int(m[4]) - int(m[2]), int(m[5]) - int(m[3])))
        return outcome

    def verdict(self, expect, observed):
        if not expect[0]:
            return "NO PREDICTION"
        if expect[0] == "moves":
            ok = any(c == expect[1] and dx == expect[2] and dy == expect[3] for c, dx, dy in self.moves)
        else:
            ok = expect[0] in observed
        return "CONFIRMED" if ok else "REFUTED"

    def lab(self):
        facts = re.sub(r"; [^;\n]*moved \?", "", self.memory().split("HYPOTHESES")[0].rstrip())
        lines = [facts]
        lines.append("ECHO SCORE IN THIS GAME (facts):")
        for origin, led in self.ledger.items():
            if led["actions"]:
                lines.append("- %s: %d actions, %d changed the world, %d level(s), %d game over(s)" %
                             (origin.replace("echo-", "ECHO ").replace("model", "your own actions"),
                              led["actions"], led["changes"], led["levels"], led["game_overs"]))
        if self.rules:
            lines.append("YOUR RULES (hypotheses, tested by ECHO; never facts):")
            for rule, (ok, bad, last) in sorted(self.rules.items(), key=lambda kv: -kv[1][2])[:8]:
                lines.append("- \"%s\": confirmed %d, refuted %d" % (rule[:160], ok, bad))
        return "\n".join(lines)


def prompt(g, arm, call, last_report, prev_frame, notes, manual):
    parts = ["Call %d of %d. Levels completed: %d of %d. Actions used: %d." %
             (call + 1, CALLS, g.levels, g.win_levels, len(g.record["actions"])),
             "Available actions: %s" % ", ".join("ACTION6 X Y" if a == 6 else "ACTION%d" % a for a in g.available)]
    if manual:
        parts.append("YOUR MANUAL (lessons you wrote after earlier games):\n" + manual)
    parts.append("YOUR NOTES from last call (unverified):\n" + (notes or "(none)"))
    parts.append("What your last actions did:\n" + (last_report or "(first call)"))
    if arm == "LECHO":
        mv = moved_objects(prev_frame, g.frame) if prev_frame is not None else []
        parts.append("Objects now (ECHO perception, rare colours first):\n" + object_list(g.frame))
        parts.append("Objects that moved since your last call:\n" + ("\n".join(mv) or "(none)"))
        parts.append(g.lab())
    parts.append("Grid (row 0 first, column 0 left):\n" + "\n".join(
        "".join(HEX[int(v) & 15] for v in row) for row in np.asarray(g.frame)))
    return "\n\n".join(parts)


def play(arc, game, arm, backend, out, key, floor_micro, manual, lessons):
    from echoai.echo4.arc3_llm import parse
    g = Game2(arc, game, arm)
    tag = "%s-%s" % (backend, arm)
    calls_path = out / ("%s-%s.calls.jsonl" % (game, tag))
    calls_path.write_text("")
    system = BASE + (ECHO_PART if arm == "LECHO" else "")
    notes, last_report, prev_frame, spent, stopped = "", "", None, 0, ""
    for call in range(CALLS):
        if g.done:
            break
        if backend == "gpt" and call % 10 == 0 and credits_remaining(key) < floor_micro:
            stopped = "budget floor reached"
            break
        user = prompt(g, arm, call, last_report, prev_frame, notes, manual)
        r = ask_backend(backend, system, user, key)
        if r["error"] and not r["content"]:
            stopped = "model error: " + r["error"]
            _log(calls_path, call, user, r, "", ("",), [], "")
            break
        spent += int(r["usage"].get("cost_micro_usd", 0))
        text = r["content"]
        m = re.search(r"NOTES:\s*(.+?)(?:\n\s*RULE:|\Z)", text, re.S)
        notes = m[1].strip()[:NOTES_MAX] if m else notes
        rule, _, orders = parse(text, g.available, arm == "LECHO")
        expect = parse_expect(text)
        prev_frame, g.moves = g.frame, []
        report, observed = g.run_orders(orders or [("GATE", "no actions in reply")], arm)
        verdict = g.verdict(expect, observed)
        if arm == "LECHO" and rule and expect[0]:
            st = g.rules.setdefault(rule, [0, 0, call])
            st[0 if verdict == "CONFIRMED" else 1] += 1
            st[2] = call
        report.append("Your prediction (%s): %s" % (expect_text(expect), verdict) if arm == "LECHO"
                      else "You predicted: %s" % expect_text(expect))
        last_report = "\n".join(report)
        _log(calls_path, call, user, r, rule, expect, sorted(observed), verdict)
        g.record["calls"] = call + 1
    rec = g.record
    rec.update({"model": MODELS[backend], "backend": backend, "arm": tag, "levels_completed": g.levels,
                "actions_per_level": g.per_level, "cost_micro_usd": spent, "stopped": stopped,
                "origin_counts": dict(Counter(rec["origin"])),
                "manual_sha": hashlib.sha256(manual.encode()).hexdigest() if manual else "",
                "level_origins": [rec["origin"][i - 1] for i in range(1, len(rec["levels"]))
                                  if rec["levels"][i] > rec["levels"][i - 1]]})
    if lessons and not stopped.startswith("model error"):
        extra = " and to use ECHO better" if arm == "LECHO" else ""
        r = ask_backend(backend, system, "What happened in this game:\n%s\n\nLevels completed: %d of %d.\n\n%s" %
                        (g.lab() if arm == "LECHO" else "(your notes) " + notes, g.levels, g.win_levels,
                         LESSONS_ASK % extra), key)
        spent += int(r["usage"].get("cost_micro_usd", 0))
        rec["cost_micro_usd"] = spent
        (out / ("%s-%s.lessons.txt" % (game, tag))).write_text(r["content"])
    return rec


def _log(path, call, user, r, rule, expect, observed, verdict):
    with path.open("a") as f:
        f.write(json.dumps({"call": call, "user_sha": hashlib.sha256(user.encode()).hexdigest(), "user": user,
                            "content": r["content"], "usage": r["usage"], "error": r["error"], "ms": r["ms"],
                            "rule": rule, "expect": list(expect), "observed": observed, "verdict": verdict}) + "\n")


def build_manual(out, backend, arm):
    lines = []
    for f in sorted(out.glob("*-%s-%s.lessons.txt" % (backend, arm))):
        lines += [l.strip() for l in f.read_text().splitlines() if l.strip().startswith("-")]
    manual, seen = "", set()
    for i in range(5):                                   # round-robin by lesson rank across games
        for f in sorted(out.glob("*-%s-%s.lessons.txt" % (backend, arm))):
            ls = [l.strip() for l in f.read_text().splitlines() if l.strip().startswith("-")]
            if i < len(ls) and ls[i] not in seen and len(manual) + len(ls[i]) + 1 <= MANUAL_MAX:
                seen.add(ls[i])
                manual += ls[i] + "\n"
    return manual.strip()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("play", "manual"))
    ap.add_argument("out")
    ap.add_argument("--backend", choices=("opus", "gpt"), required=True)
    ap.add_argument("--arm", choices=("L", "LECHO"), required=True)
    ap.add_argument("--split", choices=("dev", "exam"), default="dev")
    ap.add_argument("--games", nargs="*")
    ap.add_argument("--manual", default="")
    ap.add_argument("--lessons", action="store_true")
    ap.add_argument("--floor-usd", type=float, default=2.40)
    args = ap.parse_args(argv)
    out = Path(args.out)
    if args.command == "manual":
        text = build_manual(out, args.backend, args.arm)
        path = out / ("manual-%s-%s.txt" % (args.backend, args.arm))
        path.write_text(text)
        print(json.dumps({"manual": str(path), "chars": len(text),
                          "sha256": hashlib.sha256(text.encode()).hexdigest()}))
        return 0
    out.mkdir(parents=True, exist_ok=True)
    EMPTY_MCP.write_text('{"mcpServers": {}}')
    key = api_key() if args.backend == "gpt" else ""
    manual = Path(args.manual).read_text().strip() if args.manual else ""
    arc = arcade()
    baselines = {e.game_id: list(e.baseline_actions or []) for e in arc.get_environments()}
    allowed = games_for(args.split)
    if args.backend == "gpt":
        allowed = [g for g in allowed if g in (GPT_DEV if args.split == "dev" else GPT_EXAM)]
    for game in args.games or allowed:
        if game not in allowed:
            raise SystemExit("%s is not allowed for %s/%s" % (game, args.backend, args.split))
        dest = out / ("%s-%s-%s.json" % (game, args.backend, args.arm))
        if dest.exists():
            continue                                   # resumable: finished games are kept
        t = time.time()
        rec = play(arc, game, args.arm, args.backend, out, key, int(args.floor_usd * 1_000_000), manual,
                   args.lessons)
        rec["score"] = score(rec, baselines.get(game, []))
        rec["seconds"] = int(time.time() - t)
        if rec["stopped"].startswith("model error"):
            (out / ("%s-%s-%s.partial" % (game, args.backend, args.arm))).write_text(json.dumps(rec))
        else:
            dest.write_text(json.dumps(rec))
        print(json.dumps({"game": game, "arm": rec["arm"], "levels": rec["levels_completed"], "of": rec["win_levels"],
                          "score": rec["score"], "actions": len(rec["actions"]), "calls": rec["calls"],
                          "origin": rec["origin_counts"], "level_origins": rec["level_origins"],
                          "usd": rec["cost_micro_usd"] / 1e6, "stopped": rec["stopped"], "seconds": rec["seconds"]}))
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
