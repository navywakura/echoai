"""ECHO-4.5 S6 · self-improvement: ECHO asks, a language model proposes, ECHO verifies (docs/ECHO45-S6-AUTOMEJORA-DESIGN.md).

    python -m echoai.seed.selfimprove baseline                       what the base sandbox solves in A and B
    python -m echoai.seed.selfimprove run ARM --proposer P --calls N  ARM in {fijo, echo}; P = mock | openrouter:MODEL
    python -m echoai.seed.selfimprove probe ARM                      holdout with the arm's accepted operations
    python -m echoai.seed.selfimprove unfiltered                     the SIN FILTRO arm, from the echo arm's journal

The model only ever sees tasks of partition A. It proposes ONE new grid operation per call; the operation
enters the vocabulary only if it passes V1 (safe code), V2 (runs isolated, deterministic), V3 (solves >= 2
tasks that were not solved) and V4 (does not lower the solved count of a partition-B sample). ECHO never
lets the model touch the verifier, the sealed sets, the criteria or this file (hashes checked every round).
Everything (request, raw answer, verdict) goes to a hash-chained journal.
"""
import argparse
import ast
import hashlib
import heapq
import itertools
import json
import os
import random
import re
import resource
import signal
import sys
import time
from multiprocessing import get_context, TimeoutError as WorkerTimeout
from pathlib import Path

from echoai.seed import dsl, gym
from echoai.seed.learn import Library, distance, solve, task_grids
from echoai.seed import sandbox

BASE_SANDBOX = "echo45-s2v"
ROOT = Path(os.environ.get("S6_ROOT", gym.ROOT / "lab/seed/s6"))       # S6_ROOT: plumbing tests elsewhere
PART_SEED = "echo45-s6-AB"
N_B = 202
BUDGET = 400
SCREEN_BUDGET = 150
V3_SAMPLE, V4_SAMPLE = 40, 50
PROTECTED = ["seed/gym.py", "seed/learn.py", "seed/sandbox.py", "seed/selfimprove.py", "docs/ECHO45-S6-AUTOMEJORA-DESIGN.md"]
SAFE_BUILTINS = {n: __builtins__[n] if isinstance(__builtins__, dict) else getattr(__builtins__, n) for n in (
    "range", "len", "min", "max", "abs", "sum", "sorted", "enumerate", "zip", "list", "tuple", "set", "dict",
    "any", "all", "reversed", "int", "bool", "map", "filter", "ValueError", "IndexError", "Exception", "str", "round",
    "divmod", "isinstance", "frozenset", "next", "iter")}
FORBIDDEN = {"open", "exec", "eval", "compile", "input", "globals", "locals", "vars", "getattr", "setattr",
             "delattr", "__import__", "breakpoint", "help", "memoryview", "type", "object", "super"}
TYPES = ("P1", "P2", "P3", "P4")
Pool = get_context("spawn").Pool  # workers must not inherit the loaded GPU model/address space


# ------------------------------------------------------------------ partitions and protected files
def partition():
    ids = sorted(gym.split()["train"], key=lambda t: hashlib.sha256((t + PART_SEED).encode()).hexdigest())
    return {"B": sorted(ids[:N_B]), "A": sorted(ids[N_B:])}


def protected_hashes():
    return {p: hashlib.sha256((gym.ROOT / p).read_bytes()).hexdigest() for p in PROTECTED}


# ------------------------------------------------------------------ V1: safe code, V2: isolated and deterministic
def check_code(code):
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return "syntax error: %s" % exc.msg
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.With, ast.AsyncFunctionDef,
                             ast.Await, ast.Delete, ast.ClassDef)):
            return "construct not allowed: %s" % type(node).__name__
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            return "private attributes are not allowed"
        if isinstance(node, ast.Name) and (node.id in FORBIDDEN or node.id.startswith("__")):
            return "name %s is not allowed" % node.id
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            return "attribute assignment can mutate state between calls"
        if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and node.id in ("Exception", "ValueError", "IndexError")) or \
           (isinstance(node, ast.arg) and node.arg in ("Exception", "ValueError", "IndexError")) or \
           (isinstance(node, ast.FunctionDef) and node.name in ("Exception", "ValueError", "IndexError")):
            return "allowed exception types cannot be rebound"
        if isinstance(node, ast.ExceptHandler):
            if node.name in ("Exception", "ValueError", "IndexError"):
                return "allowed exception types cannot be rebound"
            types = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
            if not all(isinstance(t, ast.Name) and t.id in ("Exception", "ValueError", "IndexError") for t in types):
                return "exception handlers must name allowed Exception subclasses"
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            if node.decorator_list:
                return "function decorators are not allowed"
            if any(not isinstance(v, ast.Constant) for v in node.args.defaults +
                   [v for v in node.args.kw_defaults if v is not None]):
                return "function defaults must be constants"
            annotations = [a.annotation for a in node.args.args if a.annotation is not None]
            if node.returns is not None:
                annotations.append(node.returns)
            if any(not isinstance(a, (ast.Constant, ast.Name)) for a in annotations):
                return "annotations must be constants or simple names"
        elif not (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                  and isinstance(node.value.value, str)):
            return "only function definitions are allowed at module level"
    if not fns:
        return "no function"
    fns = [n for n in fns if n.name == "op"] or fns[-1:]      # the model may name it otherwise: the last one
    nargs = len(fns[0].args.args)
    if nargs not in (1, 2):
        return "op must take (grid) or (grid, c)"
    return ""


class ProposalTimeout(BaseException):
    """A proposal cannot swallow the deadline with `except Exception`."""


def _alarm(signum, frame):
    raise ProposalTimeout("operation too slow")


def compile_op(code):
    """-> (primitive callable on dsl grids, arity). Raises ValueError if the code is not allowed."""
    bad = check_code(code)
    if bad:
        raise ValueError(bad)
    env = {"__builtins__": SAFE_BUILTINS}
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, 0.05)
    try:
        exec(compile(code, "<proposal>", "exec"), env)
    except (Exception, ProposalTimeout) as exc:
        raise ValueError("proposal initialization failed: %s" % type(exc).__name__) from exc
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
    tops = [n.name for n in ast.parse(code).body if isinstance(n, ast.FunctionDef)]
    fn = env["op"] if "op" in tops else env[tops[-1]]
    arity = fn.__code__.co_argcount

    def prim(g, *c):
        old = signal.signal(signal.SIGALRM, _alarm)
        signal.setitimer(signal.ITIMER_REAL, 0.05)             # 50 ms per call: the search calls it thousands of times
        try:
            out = fn([list(r) for r in g], *c)
            if not isinstance(out, (list, tuple)) or not 1 <= len(out) <= 30:
                raise ValueError("not a bounded grid")
            if not all(isinstance(r, (list, tuple)) and 1 <= len(r) <= 30 for r in out):
                raise ValueError("not a bounded grid")
            if len({len(r) for r in out}) != 1:
                raise ValueError("ragged grid")
            if any(not isinstance(v, int) or not 0 <= v <= 9 for r in out for v in r):
                raise ValueError("bad colours")
            return dsl.G(out)
        except (Exception, ProposalTimeout) as exc:             # rejection, never a crash
            raise ValueError("proposal failed: %s" % type(exc).__name__)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)
    return prim, arity


def register(name, code):
    prim, arity = compile_op(code)
    (dsl.NO_ARG if arity == 1 else dsl.ONE_COLOR)[name] = prim
    return arity


def _worker_init(level, ops):
    resource.setrlimit(resource.RLIMIT_AS, (1 << 30, 1 << 30))
    sandbox._set_level(level)
    for name, code in ops:
        register(name, code)


def _solve(args):
    tid, concepts, prior, budget = args
    try:
        r = solve(gym.load(tid), Library(concepts, prior), max_expansions=budget)
    except (ValueError, KeyError, MemoryError):
        return tid, False
    return tid, r["program"] is not None


def solve_many(tids, ops, budget, workers, lib):
    if not tids:
        return set()
    with Pool(workers, initializer=_worker_init, initargs=(sandbox.level_of(BASE_SANDBOX), ops)) as pool:
        res = pool.map(_solve, [(t, lib.concepts, lib.prior, budget) for t in tids])
    return {t for t, ok in res if ok}


def deterministic(code, grids):
    prim, arity = compile_op(code)
    args = [()] if arity == 1 else [(c,) for c in range(1, 4)]
    successes = 0
    for g in grids:
        for a in args:
            try:
                x, y = prim(g, *a), prim(g, *a)
            except ValueError:
                continue
            if x != y:
                return False
            successes += 1
    if not successes:
        raise ValueError("operation could not execute on any screening grid")
    return True


def _deterministic_worker(args):
    resource.setrlimit(resource.RLIMIT_CPU, (5, 6))
    resource.setrlimit(resource.RLIMIT_NOFILE, (16, 16))
    code, grids = args
    try:
        ok = deterministic(code, grids)
        return ok, "" if ok else "not deterministic"
    except (Exception, ProposalTimeout) as exc:
        return False, type(exc).__name__


def deterministic_check(code, grids):
    """Test proposals outside the model process, with memory and CPU limits."""
    with Pool(1, initializer=_worker_init, initargs=(sandbox.level_of(BASE_SANDBOX), [])) as pool:
        result = pool.apply_async(_deterministic_worker, ((code, grids),))
        try:
            return result.get(timeout=15)
        except WorkerTimeout:
            return False, "isolated process exceeded its resource limit"


# ------------------------------------------------------------------ what ECHO knows about its failures
def near_miss(task, lib, budget=SCREEN_BUDGET):
    """Best partial program (lowest distance to the outputs) found by the same search as learn.solve."""
    train, _ = task_grids(task)
    inputs, targets = tuple(g for g, _ in train), tuple(t for _, t in train)
    moves = lib.moves(set().union(*(dsl.palette(g) for g in inputs)), set().union(*(dsl.palette(t) for t in targets)))
    tie = itertools.count()
    best = (distance(inputs, targets), [])
    frontier, seen, n = [(best[0], next(tie), inputs, [], 0)], {inputs}, 0
    while frontier and n < budget:
        d, _, state, prog, cost = heapq.heappop(frontier)
        n += 1
        if len(prog) >= 3:
            continue
        for mv in moves:
            try:
                nxt = tuple(lib.apply(g, mv) for g in state)
            except (ValueError, IndexError, ZeroDivisionError):
                continue
            if nxt in seen:
                continue
            seen.add(nxt)
            dd = distance(nxt, targets)
            if dd < best[0]:
                best = (dd, prog + [mv])
            heapq.heappush(frontier, (cost + 1 + 3 * dd, next(tie), nxt, prog + [mv], cost + 1))
    return best


def grid_text(g):
    return "\n".join("".join(str(v) for v in r) for r in g)


def task_text(tid, k=3):
    t = gym.load(tid)
    parts = []
    for i, p in enumerate(t["train"][:k]):
        parts.append("example %d input:\n%s\noutput:\n%s" % (i + 1, grid_text(p["input"]), grid_text(p["output"])))
    return "task %s\n%s" % (tid, "\n".join(parts))


HEADER = """You help a small program-search system that solves grid puzzles by chaining operations.
Its vocabulary already has these operations: {vocab}.
Write ONE new Python function that would help it:

    def op(grid):            # or def op(grid, c):  with c a colour 0-9
        ...
        return new_grid      # list of lists of ints 0-9, at most 30x30

Rules: no imports, no underscores in names, pure (no printing, no files), fast. A grid is a list of rows.
The operation must be GENERAL (useful for many puzzles), not a lookup of these examples.
Answer with the function in one ```python block and nothing else.

"""


def vocab_names():
    return ", ".join(sorted(list(dsl.NO_ARG) + list(dsl.ONE_COLOR) + list(dsl.TWO_COLOR)))


def build_request(kind, state, rng):
    """ECHO writes the request from its own data. Returns (prompt, task ids used)."""
    failed = sorted(state["failed_A"])
    if kind == "FIJO":
        tids = rng.sample(failed, 3)
        return HEADER.format(vocab=vocab_names()) + "Here are 3 puzzles it cannot solve yet:\n\n" + \
            "\n\n".join(task_text(t) for t in tids), tids
    if kind == "P1":                                            # a near miss
        cands = sorted(state["near"].items(), key=lambda kv: (kv[1][0], kv[0]))
        cands = [c for c in cands if c[0] not in state["asked"]] or cands
        tid, (d, prog) = cands[0] if cands else (rng.choice(failed), (1.0, []))
        return HEADER.format(vocab=vocab_names()) + (
            "With the chain {prog} it gets {pct}% of the cells of this puzzle right, but not all. "
            "Propose an operation that closes the gap (for this puzzle and similar ones):\n\n{t}").format(
            prog=" -> ".join(str(p) for p in prog) or "(nothing)", pct=int(100 * (1 - d)), t=task_text(tid)), [tid]
    if kind == "P2":                                            # a cluster of failures that look alike
        groups = {}
        for t in failed:
            groups.setdefault(state["shape"].get(t, "?"), []).append(t)
        key = max(sorted(groups), key=lambda k: len(groups[k]))
        tids = rng.sample(groups[key], min(3, len(groups[key])))
        return HEADER.format(vocab=vocab_names()) + ("These {n} puzzles fail and look alike ({why}). "
                                                     "Propose one operation they have in common:\n\n{t}").format(
            n=len(tids), why=key, t="\n\n".join(task_text(t, 2) for t in tids)), tids
    if kind == "P3":                                            # generalise something that already works
        acc = state["accepted"]
        if acc:
            name, code, tids = acc[rng.randrange(len(acc))]
            target = rng.choice(failed)
            return HEADER.format(vocab=vocab_names()) + ("This operation of mine works:\n```python\n{c}\n```\n"
                                                         "It solved {n} puzzles. Propose a MORE GENERAL version (different "
                                                         "name ok) or a close relative that would solve puzzles like this "
                                                         "one:\n\n{t}").format(c=code, n=len(tids), t=task_text(target)), [target]
        kind = "P4"
    # P4: ECHO composes the request freely from its journal
    unused = sorted(set(dsl.NO_ARG) - state["used_ops"])[:12]
    tids = rng.sample(failed, 2)
    return HEADER.format(vocab=vocab_names()) + ("Notes from my journal: {a} puzzles solved, {b} not. Operations I never "
                                                 "use: {u}. Two puzzles I fail:\n\n{t}").format(
        a=state["n_solved"], b=len(failed), u=", ".join(unused) or "none", t="\n\n".join(task_text(t, 2) for t in tids)), tids


def shape_key(tid):
    t = gym.load(tid)
    rel = set()
    for p in t["train"]:
        hi, wi, ho, wo = len(p["input"]), len(p["input"][0]), len(p["output"]), len(p["output"][0])
        rel.add("same size" if (hi, wi) == (ho, wo) else "output smaller" if ho * wo < hi * wi else "output larger")
    return " / ".join(sorted(rel))


# ------------------------------------------------------------------ proposers
def mock_proposer(prompt, rng=random.Random(0)):
    """Plumbing test only: returns hand-written operations (some useful, some broken, one unsafe)."""
    pool = [
        "def op(grid):\n    return [row[:] for row in grid[::-1]]\n",                       # duplicate of flipud
        "def op(grid, c):\n    h=len(grid); w=len(grid[0])\n    return [[c if grid[y][x]==0 and ((y>0 and grid[y-1][x]) or (y<h-1 and grid[y+1][x])) else grid[y][x] for x in range(w)] for y in range(h)]\n",
        "def op(grid):\n    import os\n    return grid\n",                                      # unsafe: V1
        "def op(grid):\n    while True:\n        pass\n",                                       # hangs: V2
        "def op(grid):\n    return [[max(r) for r in grid]]\n",
        "def op(grid):\n    w=len(grid[0])\n    return [[r[x] or r[w-1-x] for x in range(w)] for r in grid]\n",
    ]
    return "```python\n%s```" % pool[rng.randrange(len(pool))]


def openrouter_proposer(model, paid_ok=False):
    """OpenRouter. Only ':free' models unless Nav has approved paid ones (paid_ok): S6 step 0 costs $0."""
    import urllib.request, urllib.error
    if not model.endswith(":free") and not paid_ok:
        raise SystemExit("paid model %s needs Nav's go (use a :free model for step 0)" % model)
    key = (gym.ROOT / ".openrouterkey").read_text().strip()

    def call(prompt):
        body = {"model": model, "temperature": 0.7, "max_tokens": 1200, "usage": {"include": True},
                "messages": [{"role": "user", "content": prompt}]}
        last = ""
        for attempt in range(6):
            try:
                req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                             headers={"Content-Type": "application/json", "Authorization": "Bearer " + key,
                                                      "HTTP-Referer": "https://rxlabs.org", "X-Title": "echoAI S6"})
                with urllib.request.urlopen(req, timeout=240) as r:
                    data = json.loads(r.read())
                cost = (data.get("usage") or {}).get("cost") or 0
                if cost and not paid_ok:
                    raise SystemExit("a free model reported a cost: stopping")
                return (data["choices"][0]["message"].get("content") or "").strip()
            except urllib.error.HTTPError as exc:
                last = "HTTP %d" % exc.code
                exc.close()
                if exc.code not in (429, 500, 502, 503, 504):
                    break
            except (OSError, ValueError, KeyError, IndexError) as exc:
                last = type(exc).__name__
            time.sleep(15 * (attempt + 1))                      # free tiers are rate limited
        raise RuntimeError("proposer failed: %s" % last)
    return call


def hf_proposer(model_id):
    """A local open model (Kaggle GPUs). Generates a whole round of requests in one batch."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_id)
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.float16, device_map="auto")
    model.eval()

    def gen(texts):
        enc = tok(texts, return_tensors="pt", padding=True, truncation=True, max_length=6000).to(model.device)
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=700, do_sample=True, temperature=0.7, top_p=0.95,
                                 pad_token_id=tok.pad_token_id or tok.eos_token_id)
        return tok.batch_decode(out[:, enc["input_ids"].shape[1]:], skip_special_tokens=True)

    def batch(prompts, seed):
        torch.manual_seed(seed)
        texts = [tok.apply_chat_template([{"role": "user", "content": p}], tokenize=False, add_generation_prompt=True)
                 for p in prompts]
        outs = []
        for i in range(0, len(texts), 2):                      # small batches: long grids fill the T4 memory
            try:
                outs += gen(texts[i:i + 2])
            except torch.cuda.OutOfMemoryError:
                torch.cuda.empty_cache()
                for t in texts[i:i + 2]:                       # one by one; a prompt that still does not fit gets no answer
                    try:
                        outs += gen([t])
                    except torch.cuda.OutOfMemoryError:
                        torch.cuda.empty_cache()
                        outs.append(None)
        batch.usage = [{"prompt_tokens": len(tok.encode(t)),
                        "completion_tokens": len(tok.encode(a, add_special_tokens=False)) if a else 0,
                        "cost_usd": 0} for t, a in zip(texts, outs)]
        return outs
    batch.batch = True
    return batch


def extract_code(text):
    m = re.findall(r"```(?:python)?\s*\n(.*?)```", text or "", re.S)
    return max(m, key=len) if m else ""


# ------------------------------------------------------------------ the loop
def _journal(arm, event):
    p = ROOT / arm / "journal.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    sandbox._chain(p, dict(event, t=int(time.time())))


def load_ops(arm):
    d = ROOT / arm / "ops"
    events = [e for e in _events(arm) if e.get("verdict") == "accepted"]
    if events:
        return [(e["name"], (d / (e["name"] + ".py")).read_text()) for e in events]
    return [(f.stem, f.read_text()) for f in sorted(d.glob("*.py"))] if d.exists() else []


def _save_checkpoint(arm, state, bandit, rng, b_sample, b_base, pending):
    body = {"state": {k: sorted(v) if isinstance(v, set) else v for k, v in state.items()},
            "bandit": bandit, "rng": rng.getstate(), "b_sample": b_sample, "b_base": b_base,
            "pending": pending, "events": len(_events(arm))}
    path = ROOT / arm / "checkpoint.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(body, sort_keys=True))
    tmp.replace(path)


def _tuples(value):
    return tuple(_tuples(v) for v in value) if isinstance(value, list) else value


def baseline(workers):
    part = partition()
    lib = sandbox.load_library(BASE_SANDBOX)
    known_A = solve_many(part['A'], [], BUDGET, workers, lib)
    known_B = solve_many(part['B'], [], BUDGET, workers, lib)
    out = {"A_solved": sorted(known_A), "B_solved": sorted(known_B),
           "A": len(part["A"]), "B": len(part["B"]), "library_sha256": lib.sha()}
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "baseline.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in out.items()}))


def run(arm, proposer_spec, calls, rounds, workers, seed):
    assert arm in ("fijo", "echo")
    base = json.loads((ROOT / "baseline.json").read_text())
    part = partition()
    lib = sandbox.load_library(BASE_SANDBOX)
    sandbox._set_level(sandbox.level_of(BASE_SANDBOX))
    rng = random.Random("%s-%s" % (seed, arm))
    if proposer_spec == "mock":
        propose = mock_proposer
    elif proposer_spec.startswith("hf:"):
        propose = hf_proposer(proposer_spec[3:])
    else:
        propose = openrouter_proposer(proposer_spec.split(":", 1)[1])
    hashes = protected_hashes()
    manifest_path = ROOT / arm / "protected.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists() and json.loads(manifest_path.read_text()) != hashes:
        raise SystemExit("protected files differ from this campaign's initial manifest")
    manifest_path.write_text(json.dumps(hashes, sort_keys=True, indent=1))
    ops = load_ops(arm)
    for name, code in ops:
        register(name, code)
    solved_A = set(base["A_solved"]) | {t for e in _events(arm) if e.get("verdict") == "accepted" for t in e["new_A"]}
    b_sample = sorted(rng.sample(part["B"], V4_SAMPLE))
    b_base = len(solve_many(b_sample, ops, BUDGET, workers, lib))
    state = {"failed_A": set(part["A"]) - solved_A, "near": {}, "asked": set(), "accepted": [],
             "shape": {}, "used_ops": set(), "n_solved": len(solved_A)}
    for e in _events(arm):
        if e.get("verdict") == "accepted":
            state["accepted"].append((e["name"], e["code"], e["new_A"]))
    for t in sorted(state["failed_A"]):
        state["shape"][t] = shape_key(t)
    for prog in sandbox.verified_programs(BASE_SANDBOX).values():
        state["used_ops"] |= {p if isinstance(p, str) else p[0] for p in prog}
    bandit = {k: [0, 0] for k in TYPES}                        # tries, accepted (integers)
    for e in _events(arm):
        if e.get("type") in bandit:
            bandit[e["type"]][0] += 1
            bandit[e["type"]][1] += e.get("verdict") == "accepted"
    per_round = max(1, calls // rounds)
    done = sum(1 for e in _events(arm) if "verdict" in e)
    checkpoint_path = ROOT / arm / "checkpoint.json"
    pending_batch = []
    if checkpoint_path.exists():
        cp = json.loads(checkpoint_path.read_text())
        if cp["events"] != len(_events(arm)):
            raise SystemExit("checkpoint/journal mismatch; manual recovery required")
        state, bandit = cp["state"], cp["bandit"]
        for k in ("failed_A", "asked", "used_ops"):
            state[k] = set(state[k])
        rng.setstate(_tuples(cp["rng"]))
        b_sample, b_base, pending_batch = cp["b_sample"], cp["b_base"], cp["pending"]
    while done < calls:
        if protected_hashes() != hashes:
            _journal(arm, {"kind": "abort", "why": "a protected file changed"})
            raise SystemExit("protected file changed: campaign void")
        n = 0 if pending_batch else min(per_round - done % per_round, calls - done)
        requests, pending = [], {k: 0 for k in TYPES}
        for _ in range(n):                                    # ECHO writes this round's requests
            if arm == "fijo":
                kind = "FIJO"
            else:                                             # integer bandit; requests already queued count as tries
                kind = max(TYPES, key=lambda k: ((bandit[k][1] * 1000) // (bandit[k][0] + pending[k] + 1)
                                                 + 300 // (bandit[k][0] + pending[k] + 1), -TYPES.index(k)))
                pending[kind] += 1
                if kind == "P1":
                    for t in sorted(state["failed_A"] - set(state["near"]))[:4]:
                        state["near"][t] = near_miss(gym.load(t), lib)
            prompt, tids = build_request(kind, state, rng)
            state["asked"] |= set(tids)
            requests.append((kind, prompt, tids))
        if not pending_batch:
            t0 = time.time()
            why = "model returned no answer (including a GPU memory failure)"
            try:
                if getattr(propose, "batch", False):
                    answers = propose([p for _, p, _ in requests], seed=done)
                else:
                    answers = [propose(p) for _, p, _ in requests]
            except RuntimeError as exc:
                answers = [None] * len(requests)
                why = str(exc)[:200]
            if len(answers) != len(requests):
                raise RuntimeError("proposer returned a different number of answers than requests")
            secs = round((time.time() - t0) / max(len(requests), 1), 1)
            usage = getattr(propose, "usage", [{} for _ in requests])
            pending_batch = [[kind, prompt, tids, answer, secs, why, tokens]
                             for (kind, prompt, tids), answer, tokens in zip(requests, answers, usage)]
            _save_checkpoint(arm, state, bandit, rng, b_sample, b_base, pending_batch)
        while pending_batch:
            kind, prompt, tids, answer, secs, why, tokens = pending_batch[0]
            if answer is None:
                _journal(arm, {"kind": "proposal", "type": kind, "tasks": tids, "prompt": prompt, "answer": None,
                               "verdict": "no answer", "why": why, "new_A": [], "call": done + 1,
                               "round": done // per_round + 1, **tokens})
                done += 1
                if kind in bandit:
                    bandit[kind][0] += 1
                pending_batch.pop(0)
                _save_checkpoint(arm, state, bandit, rng, b_sample, b_base, pending_batch)
                print(json.dumps({"arm": arm, "call": done, "type": kind, "verdict": "no answer",
                                  "accepted_total": len(ops)}), flush=True)
                continue
            code = extract_code(answer)
            name = "s6_%s_%s" % (arm, hashlib.sha256(code.encode()).hexdigest()[:8])
            ev = {"kind": "proposal", "type": kind, "tasks": tids, "prompt": prompt, "answer": answer, "code": code,
                  "name": name, "seconds_model": secs, "call": done + 1, "round": done // per_round + 1,
                  **tokens}
            print(json.dumps({"arm": arm, "checking": done + 1, "type": kind}), flush=True)
            if any(name == o[0] for o in ops):
                verdict, why_v, new_A = "rejected", "duplicate of an accepted operation", set()
            else:
                verdict, why_v, new_A = verify(code, name, tids, state, ops, lib, workers, rng, b_sample, b_base)
            ev.update(verdict=verdict, why=why_v, new_A=sorted(new_A))
            if kind in bandit:
                bandit[kind][0] += 1
                bandit[kind][1] += verdict == "accepted"
            if verdict == "accepted":
                (ROOT / arm / "ops").mkdir(parents=True, exist_ok=True)
                (ROOT / arm / "ops" / (name + ".py")).write_text(code)
                ops.append((name, code))
                register(name, code)
                state["failed_A"] -= new_A
                state["n_solved"] += len(new_A)
                state["accepted"].append((name, code, sorted(new_A)))
                b_base = len(solve_many(b_sample, ops, BUDGET, workers, lib))
            _journal(arm, ev)
            done += 1
            pending_batch.pop(0)
            _save_checkpoint(arm, state, bandit, rng, b_sample, b_base, pending_batch)
            print(json.dumps({"arm": arm, "call": done, "type": kind, "verdict": verdict, "why": why_v[:80],
                              "new_A": len(new_A), "accepted_total": len(ops)}))
            sys.stdout.flush()
    final_hashes = protected_hashes()
    if final_hashes != hashes:
        raise SystemExit("protected file changed: campaign void")
    (ROOT / arm / "completed.json").write_text(json.dumps({"calls": done, "ops": len(ops),
        "initial_hashes": hashes, "final_hashes": final_hashes}, indent=1))


def verify(code, name, tids, state, ops, lib, workers, rng, b_sample, b_base):
    if not code.strip():
        return "rejected", "V1: no code in the answer", set()
    try:
        compile_op(code)
    except (ValueError, SyntaxError) as exc:
        return "rejected", "V1: %s" % exc, set()
    grids = [dsl.G(p["input"]) for t in tids for p in gym.load(t)["train"][:2]]
    ok, reason = deterministic_check(code, grids)
    if not ok:
        return "rejected", "V2: %s" % reason, set()
    trial = ops + [(name, code)]
    screen = [t for t in tids if t in state["failed_A"]]
    if not solve_many(screen, trial, SCREEN_BUDGET, workers, lib):
        return "rejected", "V3: solves none of the tasks it was asked about", set()
    pool = sorted(set(rng.sample(sorted(state["failed_A"]), min(V3_SAMPLE, len(state["failed_A"])))) | set(screen))
    new_A = solve_many(pool, trial, BUDGET, workers, lib)
    # A task is new only if the current library cannot solve it at the SAME budget.
    # The sandbox journal alone may predate the expanded S2v vocabulary.
    before_A = solve_many(sorted(new_A), ops, BUDGET, workers, lib)
    new_A -= before_A
    if len(new_A) < 2:
        return "rejected", "V3: only %d new task(s)" % len(new_A), new_A
    b_now = len(solve_many(b_sample, trial, BUDGET, workers, lib))
    if b_now < b_base:
        return "rejected", "V4: partition B sample went from %d to %d" % (b_base, b_now), new_A
    return "accepted", "V3 +%d, V4 %d>=%d" % (len(new_A), b_now, b_base), new_A


def _events(arm):
    p = ROOT / arm / "journal.jsonl"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


def probe(arm, workers):
    sp = gym.split()
    lib = sandbox.load_library(BASE_SANDBOX)
    ops = [] if arm == "semilla" else load_ops(arm)
    if arm == "sinfiltro":
        # Identical source has the same operation name: the registry contains it only once.
        unique = {}
        for event in _events("echo"):
            if event.get("code") and not event["why"].startswith(("V1", "V2")):
                unique.setdefault(event["name"], event["code"])
        ops = list(unique.items())
    with Pool(workers, initializer=_worker_init, initargs=(sandbox.level_of(BASE_SANDBOX), ops)) as pool:
        res = pool.map(_probe_one, [(t, lib.concepts, lib.prior) for t in sp["holdout"]])
    row = {"arm": arm, "ops": len(ops), "holdout_test_correct": sum(r for _, r in res), "holdout": len(res),
           "solved": sorted(t for t, r in res if r)}
    (ROOT / ("probe-%s.json" % arm)).write_text(json.dumps(row, indent=1))
    print(json.dumps({k: v for k, v in row.items() if k != "solved"}))


def _probe_one(args):
    tid, concepts, prior = args
    try:
        r = solve(gym.load(tid), Library(concepts, prior), max_expansions=BUDGET)
    except (ValueError, KeyError, MemoryError):
        return tid, False
    return tid, bool(r["test_ok"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("baseline", "run", "probe"))
    ap.add_argument("arm", nargs="?")
    ap.add_argument("--proposer", default="mock")
    ap.add_argument("--calls", type=int, default=300)
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--seed", default="s6")
    a = ap.parse_args(argv)
    if a.cmd == "baseline":
        baseline(a.workers)
    elif a.cmd == "run":
        run(a.arm, a.proposer, a.calls, a.rounds, a.workers, a.seed)
    else:
        probe(a.arm, a.workers)
    return 0


if __name__ == "__main__":
    sys.exit(main())
