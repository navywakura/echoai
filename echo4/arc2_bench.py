"""E4-BENCH-ARC2 · ARC-AGI-2 with a model alone, with ECHO verifying its programs, and ECHO alone.

    python3 -m echoai.echo4.arc2_bench run OUT --split dev|exam --model qwen|deepseek --arms L LECHO C
    python3 -m echoai.echo4.arc2_bench solo OUT --split dev|exam        (ECHO alone: program search, $0)
    python3 -m echoai.echo4.arc2_bench audit OUT                        (re-executes stored programs, rescores)

Contract: docs/ECHO4-BENCH-ARC2-DESIGN.md (approved by Roger, 2026-09-25; thresholds fixed before dev).

  L      the model writes up to 2 output grids per test input (official 2 attempts)
  LECHO  the model writes transform(grid); ECHO executes it on the solved examples and reports
         which example and how many cells failed; up to 4 rounds; only a program that reproduces
         every example is submitted, otherwise ECHO abstains (score 0 for that task)
  C      control: 4 programs, each round sees its earlier programs but no verdict; the outputs of
         the first 2 that run without error are submitted
Model code runs in a separate process: AST-checked (no imports, dunders, open/eval/exec), 5 s CPU,
512 MB, restricted builtins, no files or network.
"""
import argparse
import ast
import copy
import hashlib
import json
import re
import resource
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import product
from pathlib import Path

from echoai.echo4.bench1 import api_key, ask, credits_remaining

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "lab/arc2/ARC-AGI-2/data"
SPLIT = ROOT / "lab/arc2/split.json"
SPLIT_SHA = "544f279c44ed526ef42d0ad0a6ee0579021ddab6e868d29b664be85a4c30ced5"
MODELS = {"qwen": "qwen/qwen3-30b-a3b-instruct-2507", "deepseek": "deepseek/deepseek-v4.1-flash"}
MAX_TOKENS = {"qwen": 6000, "deepseek": 12000}
ROUNDS = 4
LOCK = threading.Lock()

SYS_GRID = """You solve ARC puzzles. Each puzzle has solved examples (input grid -> output grid) that
share one hidden transformation. Grids are rows of digits 0-9 (colours). Infer the transformation
and apply it to each test input. You may give up to 2 attempts per test input.
Reply with only a JSON object: {"test_1": [GRID_ATTEMPT_1, GRID_ATTEMPT_2], "test_2": [...]} where
each GRID is a list of rows and each row a list of integers."""

SYS_CODE = """You solve ARC puzzles by writing a program. Each puzzle has solved examples (input grid ->
output grid) that share one hidden transformation. Grids are lists of rows of integers 0-9.
Write a Python function transform(grid) that returns the output grid for any input of this puzzle.
The examples are displayed as rows of digits, but transform receives a list of lists of ints
(grid[row][col]) and must return a list of lists of ints.
Rules: plain Python only; no import statements; no files; no printing. You may define helper
functions. Keep the program short (under 80 lines) with few comments; think briefly before it.
Reply with one ```python code block containing transform."""

FORBIDDEN_NAMES = {"open", "eval", "exec", "compile", "__import__", "globals", "locals", "vars", "input",
                   "getattr", "setattr", "delattr", "breakpoint", "help", "exit", "quit", "memoryview"}
RUNNER = r'''
import json, sys, copy
SAFE = {n: __builtins__[n] if isinstance(__builtins__, dict) else getattr(__builtins__, n) for n in (
    "len range enumerate zip min max sum sorted list dict set tuple abs any all reversed map filter int "
    "bool isinstance frozenset divmod round pow str float Exception ValueError IndexError KeyError "
    "TypeError StopIteration next iter hash slice").split()}
job = json.loads(sys.stdin.read())
env = {"__builtins__": SAFE}
out = []
try:
    exec(compile(job["code"], "<model>", "exec"), env)
    fn = env["transform"]
except Exception as exc:
    print(json.dumps([{"ok": False, "error": "define: %s: %s" % (type(exc).__name__, str(exc)[:120])}] * len(job["inputs"])))
    sys.exit(0)
for g in job["inputs"]:
    try:
        r = fn(copy.deepcopy(g))
        r = [list(map(int, row)) for row in r]
        ok = 0 < len(r) <= 30 and all(0 < len(row) <= 30 and all(0 <= v <= 9 for v in row) for row in r)
        out.append({"ok": ok, "grid": r if ok else None, "error": "" if ok else "not a 1..30 grid of 0-9"})
    except Exception as exc:
        out.append({"ok": False, "error": "%s: %s" % (type(exc).__name__, str(exc)[:120])})
print(json.dumps(out))
'''


# ------------------------------------------------------------------ data

def load_split():
    s = SPLIT.read_text()
    if hashlib.sha256(s.encode()).hexdigest() != SPLIT_SHA:
        raise SystemExit("frozen split differs from the contract")
    return json.loads(s)


def task_names(split, which, model=None):
    if which == "dev":
        return split["dev"]
    if model == "deepseek":                    # seed order, so --limit N keeps the first N by seed
        return sorted(split["exam_deepseek"], key=lambda t: hashlib.sha256((t + "20260925-arc2-deepseek").encode()).hexdigest())
    return split["exam"]


def load_task(name, which):
    d = "training" if which == "dev" else "evaluation"
    raw = (DATA / d / (name + ".json")).read_bytes()
    return json.loads(raw)


def grid_str(g):
    return "\n".join("".join(str(v) for v in row) for row in g)


def task_prompt(task, with_tests=True):
    parts = []
    for i, p in enumerate(task["train"]):
        parts.append("Example %d input:\n%s\nExample %d output:\n%s" % (i + 1, grid_str(p["input"]), i + 1, grid_str(p["output"])))
    if with_tests:
        for i, p in enumerate(task["test"]):
            parts.append("Test %d input:\n%s" % (i + 1, grid_str(p["input"])))
    return "\n\n".join(parts)


# ------------------------------------------------------------------ isolated execution

def check_code(code):
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return "syntax error: %s" % exc.msg
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
            return "imports/global are not allowed"
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            return "dunder attributes are not allowed"
        if isinstance(node, ast.Name) and (node.id in FORBIDDEN_NAMES or node.id.startswith("__")):
            return "name %s is not allowed" % node.id
    if not any(isinstance(n, ast.FunctionDef) and n.name == "transform" for n in tree.body):
        return "no transform(grid) function"
    return ""


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))
    resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))


def execute(code, inputs):
    bad = check_code(code)
    if bad:
        return [{"ok": False, "error": bad}] * len(inputs)
    try:
        p = subprocess.run([sys.executable, "-I", "-S", "-c", RUNNER], input=json.dumps({"code": code, "inputs": inputs}),
                           capture_output=True, text=True, timeout=20, preexec_fn=_limits, cwd="/tmp", env={})
        return json.loads(p.stdout)
    except (subprocess.TimeoutExpired, ValueError):
        return [{"ok": False, "error": "timeout or crash"}] * len(inputs)


def extract_code(text):
    m = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    if m:
        return max(m, key=len)
    m = re.search(r"```(?:python)?\s*\n(.*)", text, re.S)          # reply cut before the closing fence
    return m[1] if m else ""


def parse_json_answer(text):
    start = text.index("{")
    for tail in ("", "}", "]}", "]]}"):
        for end in (text.rindex("}") + 1 if "}" in text[start:] else len(text), len(text)):
            try:
                return json.loads(text[start:end] + tail)
            except ValueError:
                continue
    raise ValueError("no JSON answer")


def diff_report(got, want):
    if not got["ok"]:
        return "error: " + got["error"]
    g = got["grid"]
    if len(g) != len(want) or len(g[0]) != len(want[0]):
        return "wrong size: got %dx%d, expected %dx%d" % (len(g), len(g[0]), len(want), len(want[0]))
    wrong = [(r, c) for r in range(len(want)) for c in range(len(want[0])) if g[r][c] != want[r][c]]
    if not wrong:
        return ""
    sample = ", ".join("(row %d, col %d): got %d expected %d" % (r, c, g[r][c], want[r][c]) for r, c in wrong[:5])
    return "%d of %d cells wrong; first: %s" % (len(wrong), len(want) * len(want[0]), sample)


# ------------------------------------------------------------------ arms

def score_task(task, attempts):
    """attempts[i] = list of up to 2 grids for test i. Official: mean over test outputs."""
    hits = [int(any(a == t["output"] for a in (attempts[i] if i < len(attempts) else [])[:2])) for i, t in enumerate(task["test"])]
    return sum(hits), len(hits)


def arm_L(task, model, key):
    r = ask(MODELS[model], SYS_GRID, task_prompt(task), max_tokens=MAX_TOKENS[model], key=key)
    attempts = []
    try:
        text = r["content"]
        obj = parse_json_answer(text)
        for i in range(len(task["test"])):
            grids = obj.get("test_%d" % (i + 1), [])
            if grids and isinstance(grids[0], list) and grids[0] and isinstance(grids[0][0], int):
                grids = [grids]                                     # a single grid instead of a list
            attempts.append([g for g in grids if isinstance(g, list)][:2])
    except (ValueError, AttributeError, IndexError, TypeError):
        attempts = rows_fallback(r["content"], len(task["test"]))
    return {"calls": [r], "attempts": attempts}


def rows_fallback(text, n_tests):
    """Malformed JSON (a missing bracket): recover each test's rows as the innermost int lists."""
    cuts = [m.start() for m in re.finditer(r'"test_\d+"', text)] + [len(text)]
    attempts = []
    for i in range(n_tests):
        seg = text[cuts[i]:cuts[i + 1]] if i + 1 < len(cuts) else ""
        rows = [[int(v) for v in m.split(",")] for m in re.findall(r"\[\s*(\d\s*(?:,\s*\d\s*)*)\]", seg)]
        attempts.append([rows] if rows else [])
    return attempts


def arm_LECHO(task, model, key):
    calls, programs, feedback = [], [], ""
    train_in = [p["input"] for p in task["train"]]
    user0 = task_prompt(task)
    for rnd in range(ROUNDS):
        user = user0 if rnd == 0 else user0 + "\n\nYour previous program:\n```python\n%s\n```\nECHO ran it on the solved examples:\n%s\nFix it." % (programs[-1]["code"], feedback)
        r = ask(MODELS[model], SYS_CODE, user, max_tokens=MAX_TOKENS[model], key=key)
        calls.append(r)
        code = extract_code(r["content"])
        results = execute(code, train_in)
        reports = [diff_report(g, p["output"]) for g, p in zip(results, task["train"])]
        verified = bool(code) and all(rep == "" for rep in reports)
        programs.append({"code": code, "verified": verified, "train_reports": reports})
        if verified:
            outs = execute(code, [t["input"] for t in task["test"]])
            return {"calls": calls, "programs": programs, "verified_round": rnd,
                    "attempts": [[o["grid"]] if o["ok"] else [] for o in outs]}
        feedback = "\n".join("example %d: %s" % (i + 1, rep or "correct") for i, rep in enumerate(reports))
    return {"calls": calls, "programs": programs, "verified_round": None, "attempts": [[] for _ in task["test"]]}


def arm_C(task, model, key):
    calls, programs = [], []
    user0 = task_prompt(task)
    tests = [t["input"] for t in task["test"]]
    attempts = [[] for _ in task["test"]]
    for rnd in range(ROUNDS):
        user = user0 if rnd == 0 else user0 + "\n\nYour earlier programs (not checked):\n" + "\n".join(
            "```python\n%s\n```" % p["code"] for p in programs) + "\nWrite a different program for this puzzle."
        r = ask(MODELS[model], SYS_CODE, user, max_tokens=MAX_TOKENS[model], key=key)
        calls.append(r)
        code = extract_code(r["content"])
        outs = execute(code, tests)
        runs = bool(code) and all(o["ok"] for o in outs)
        programs.append({"code": code, "runs": runs})
        if runs and len(attempts[0]) < 2:
            for i, o in enumerate(outs):
                attempts[i].append(o["grid"])
    return {"calls": calls, "programs": programs, "attempts": attempts}


ARMS = {"L": arm_L, "LECHO": arm_LECHO, "C": arm_C}


# ------------------------------------------------------------------ ECHO alone: program search

def _bg(g):
    flat = [v for row in g for v in row]
    return max(set(flat), key=flat.count)


def _rot(g):
    return [list(r) for r in zip(*g[::-1])]


def _crop(g):
    bg = _bg(g)
    rows = [i for i, r in enumerate(g) if any(v != bg for v in r)]
    cols = [j for j in range(len(g[0])) if any(r[j] != bg for r in g)]
    return [r[cols[0]:cols[-1] + 1] for r in g[rows[0]:rows[-1] + 1]] if rows and cols else g


def _scale(g, k):
    return [[v for v in row for _ in range(k)] for row in g for _ in range(k)]


def _down(g, k):
    if len(g) % k or len(g[0]) % k:
        raise ValueError
    return [row[::k] for row in g[::k]]


def _tile(g, a, b):
    return [row * b for row in g] * a


def _mirror_tile(g):
    top = [row + row[::-1] for row in g]
    return top + top[::-1]


PRIMS = {
    "id": lambda g: g, "rot90": _rot, "rot180": lambda g: _rot(_rot(g)), "rot270": lambda g: _rot(_rot(_rot(g))),
    "flipud": lambda g: g[::-1], "fliplr": lambda g: [r[::-1] for r in g], "transpose": lambda g: [list(r) for r in zip(*g)],
    "crop": _crop, "up2": lambda g: _scale(g, 2), "up3": lambda g: _scale(g, 3), "down2": lambda g: _down(g, 2),
    "down3": lambda g: _down(g, 3), "tile2x2": lambda g: _tile(g, 2, 2), "tile3x3": lambda g: _tile(g, 3, 3),
    "tile1x2": lambda g: _tile(g, 1, 2), "tile2x1": lambda g: _tile(g, 2, 1), "mirror2x2": _mirror_tile,
}


def _colormap(pairs):
    m = {}
    for a, b in pairs:
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return None
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if m.setdefault(x, y) != y:
                    return None
    return m


def solo_solve(task):
    """Depth-2 composition of primitives, optionally followed by a learned consistent colour map."""
    for n1, n2 in product(PRIMS, PRIMS):
        if n1 != "id" and n2 == "id":
            continue
        try:
            f = lambda g: PRIMS[n2](PRIMS[n1](g))
            mids = [f(p["input"]) for p in task["train"]]
        except (ValueError, IndexError):
            continue
        if all(m == p["output"] for m, p in zip(mids, task["train"])):
            prog, cmap = (n1, n2), None
        else:
            cmap = _colormap([(m, p["output"]) for m, p in zip(mids, task["train"])])
            if not cmap or any([[cmap[v] for v in r] for r in m] != p["output"] for m, p in zip(mids, task["train"])):
                continue
            prog = (n1, n2)
        try:
            outs = [f(t["input"]) for t in task["test"]]
            if cmap:
                outs = [[[cmap.get(v, v) for v in r] for r in o] for o in outs]
        except (ValueError, IndexError):
            continue
        return {"program": list(prog), "colormap": {str(k): v for k, v in (cmap or {}).items()},
                "attempts": [[o] for o in outs]}
    return {"program": None, "colormap": {}, "attempts": [[] for _ in task["test"]]}


# ------------------------------------------------------------------ runs, reports, audit

def usage_cost(calls):
    return sum(int(c.get("usage", {}).get("cost_micro_usd", 0)) for c in calls)


def run(out, which, model, arms, workers, budget_usd, floor_usd, limit=0):
    split = load_split()
    names = task_names(split, which, model)
    if limit:
        names = names[:limit]
    key = api_key()
    spent = [0]
    stop = threading.Event()
    budget = int(budget_usd * 1_000_000)

    def one(name, arm):
        path = out / model / arm / (name + ".json")
        if path.exists() or stop.is_set():
            return
        if spent[0] >= budget or credits_remaining(key) < int(floor_usd * 1_000_000):
            stop.set()
            return
        task = load_task(name, which)
        rec = ARMS[arm](task, model, key)
        hit, n = score_task(task, rec["attempts"])
        rec.update({"task": name, "arm": arm, "model": MODELS[model], "hits": hit, "tests": n,
                    "cost_micro_usd": usage_cost(rec["calls"])})
        for c in rec["calls"]:
            c.pop("request", None)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rec))
        with LOCK:
            spent[0] += rec["cost_micro_usd"]

    jobs = [(n, a) for a in arms for n in names]
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(lambda j: one(*j), jobs))
    print(json.dumps({"model": model, "split": which, "spent_usd": spent[0] / 1e6, "stopped": stop.is_set()}))


def solo(out, which):
    split = load_split()
    for name in task_names(split, which):
        task = load_task(name, which)
        rec = solo_solve(task)
        hit, n = score_task(task, rec["attempts"])
        rec.update({"task": name, "arm": "SOLO", "hits": hit, "tests": n})
        path = out / "echo" / "SOLO" / (name + ".json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rec))
    print(json.dumps(summary(out)))


def summary(out):
    rows = {}
    for f in sorted(out.glob("*/*/*.json")):
        rec = json.loads(f.read_text())
        k = "%s/%s" % (f.parent.parent.name, f.parent.name)
        s = rows.setdefault(k, {"tasks": 0, "score_pm_sum": 0, "tasks_solved": 0, "cost_micro_usd": 0, "calls": 0})
        s["tasks"] += 1
        s["score_pm_sum"] += rec["hits"] * 1000 // rec["tests"]
        s["tasks_solved"] += int(rec["hits"] == rec["tests"])
        s["cost_micro_usd"] += rec.get("cost_micro_usd", 0)
        s["calls"] += len(rec.get("calls", []))
    for s in rows.values():
        s["score_pm"] = s["score_pm_sum"] // max(s["tasks"], 1)
    return rows


def audit(out):
    """Re-execute every stored program and the ECHO-alone search; rescore from the public test outputs."""
    split = load_split()
    bad = []
    for f in sorted(out.glob("*/*/*.json")):
        rec = json.loads(f.read_text())
        which = "dev" if rec["task"] in split["dev"] else "exam"
        task = load_task(rec["task"], which)
        tests = [t["input"] for t in task["test"]]
        if rec["arm"] == "LECHO" and rec["verified_round"] is not None:
            code = rec["programs"][rec["verified_round"]]["code"]
            ok = all(r["ok"] and r["grid"] == p["output"] for r, p in zip(execute(code, [p["input"] for p in task["train"]]), task["train"]))
            if not ok or [[o["grid"]] if o["ok"] else [] for o in execute(code, tests)] != rec["attempts"]:
                bad.append(f.name)
        elif rec["arm"] == "SOLO" and solo_solve(task)["attempts"] != rec["attempts"]:
            bad.append(f.name)
        if score_task(task, rec["attempts"]) != (rec["hits"], rec["tests"]):
            bad.append(f.name)
    rows = summary(out)
    sha = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
    receipt = {"valid": not bad, "mismatches": bad, "summary_sha256": sha, "records": len(list(out.glob("*/*/*.json")))}
    (out / "audit-receipt.json").write_text(json.dumps(receipt, indent=1, sort_keys=True))
    print(json.dumps(receipt, indent=1))
    return 0 if not bad else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("run", "solo", "audit", "summary"))
    ap.add_argument("out")
    ap.add_argument("--split", choices=("dev", "exam"), default="dev")
    ap.add_argument("--model", choices=tuple(MODELS))
    ap.add_argument("--arms", nargs="*", default=["L", "LECHO", "C"])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--budget-usd", type=float, default=1.0)
    ap.add_argument("--floor-usd", type=float, default=0.60)
    ap.add_argument("--limit", type=int, default=0, help="first N tasks of the split only (cost probes)")
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.command == "run":
        run(out, args.split, args.model, args.arms, args.workers, args.budget_usd, args.floor_usd, args.limit)
        print(json.dumps(summary(out), indent=1))
    elif args.command == "solo":
        solo(out, args.split)
    elif args.command == "audit":
        return audit(out)
    else:
        print(json.dumps(summary(out), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
