"""ECHO-SEED · clonable sandboxes where an un-trained ECHO learns concepts (towards ECHO-4.5).

    python3 -m echoai.seed.sandbox new NAME                 a seed: empty memory, primitives only
    python3 -m echoai.seed.sandbox clone PARENT NAME        a copy with its own future
    python3 -m echoai.seed.sandbox train NAME --rounds 3    wake (solve) -> sleep (concepts) -> holdout
    python3 -m echoai.seed.sandbox status NAME
    python3 -m echoai.seed.sandbox verify NAME              re-check the journal chain and every concept

Contract: docs/ECHO45-SEED-DESIGN.md. A sandbox lives in lab/seed/sandboxes/NAME/:
  manifest.json   name, parent, created, library sha
  library.json    learned concepts (only from verified programs of >= 2 different tasks)
  journal.jsonl   hash-chained facts: every verified program and every concept born
  rounds.jsonl    learning curve: solved in the train pool and in the untouched holdout
"""
import argparse
import hashlib
import json
import random
import shutil
import sys
import time
from multiprocessing import Pool
from pathlib import Path

from echoai.seed import dsl, gym
from echoai.seed.learn import Library, prior_from, sleep, solve

BASE = gym.ROOT / "lab/seed/sandboxes"


def _path(name):
    return BASE / name


def _chain(path, event):
    lines = path.read_text().splitlines() if path.exists() else []
    prev = json.loads(lines[-1])["hash"] if lines else "0" * 64
    body = dict(event, prev=prev)
    body["hash"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    with path.open("a") as f:
        f.write(json.dumps(body, sort_keys=True) + "\n")


def load_library(name):
    prior_path = _path(name) / "prior.json"
    prior = json.loads(prior_path.read_text()) if prior_path.exists() else None
    return Library(json.loads((_path(name) / "library.json").read_text()), prior)


def save_library(name, lib):
    (_path(name) / "library.json").write_text(json.dumps(lib.concepts, sort_keys=True, indent=1))
    if lib.prior:
        (_path(name) / "prior.json").write_text(json.dumps(lib.prior, sort_keys=True, indent=1))
    m = json.loads((_path(name) / "manifest.json").read_text())
    m["library_sha256"] = lib.sha()
    m["concepts"] = len(lib.concepts)
    (_path(name) / "manifest.json").write_text(json.dumps(m, sort_keys=True, indent=1))


def level_of(name):
    return json.loads((_path(name) / "manifest.json").read_text()).get("level", "S0")


def _set_level(level):
    if level == "S1" and dsl.LEVEL == "S0":
        dsl.enable_s1()
    elif level == "S1b" and dsl.LEVEL not in ("S1b", "S2v"):
        dsl.enable_s1b()
    elif level == "S2v" and dsl.LEVEL != "S2v":
        dsl.enable_s2v()


def new(name, level="S0"):
    p = _path(name)
    if p.exists():
        raise SystemExit("sandbox exists: %s" % name)
    _set_level(level)
    p.mkdir(parents=True)
    (p / "manifest.json").write_text(json.dumps({"name": name, "parent": None, "created": int(time.time()),
                                                 "level": level, "primitives": dsl.primitive_count()}, indent=1))
    save_library(name, Library())
    _chain(p / "journal.jsonl", {"kind": "born", "name": name, "parent": None})
    print(json.dumps({"new": name, "level": level, "primitives": dsl.primitive_count()}))


def clone(parent, name):
    src, dst = _path(parent), _path(name)
    if dst.exists():
        raise SystemExit("sandbox exists: %s" % name)
    shutil.copytree(src, dst)
    m = json.loads((dst / "manifest.json").read_text())
    m.update({"name": name, "parent": parent, "created": int(time.time())})
    (dst / "manifest.json").write_text(json.dumps(m, sort_keys=True, indent=1))
    _chain(dst / "journal.jsonl", {"kind": "cloned", "name": name, "parent": parent,
                                   "parent_library_sha256": m.get("library_sha256")})
    print(json.dumps({"clone": name, "parent": parent}))


_INTUITION = {}


def _solve_one(args):
    tid, concepts, budget, level = args[:4]
    prior = args[4] if len(args) > 4 else None
    guide_path = args[5] if len(args) > 5 else None
    _set_level(level)
    try:
        task = gym.load(tid)
        lib = Library(concepts, prior)
        if guide_path:
            if guide_path not in _INTUITION:
                from echoai.seed.intuition import Intuition
                _INTUITION[guide_path] = Intuition(guide_path)
            lib.guide = _INTUITION[guide_path].probs(task)
        r = solve(task, lib, max_expansions=budget)
    except (ValueError, KeyError) as exc:
        r = {"program": None, "expansions": 0, "test_ok": None, "error": type(exc).__name__}
    return tid, r


def verified_programs(name):
    out = {}
    for line in (_path(name) / "journal.jsonl").read_text().splitlines():
        e = json.loads(line)
        if e["kind"] == "verified":
            out[e["task"]] = e["program"]
    return out


def train(name, rounds, budget, workers, sample):
    p = _path(name)
    sp = gym.split()
    rng = random.Random(name)
    level = level_of(name)
    _set_level(level)
    for _ in range(rounds):
        lib = load_library(name)
        known = verified_programs(name)
        rnd = sum(1 for _ in (p / "rounds.jsonl").open()) + 1 if (p / "rounds.jsonl").exists() else 1
        todo = [t for t in sp["train"] if t not in known]
        rng.shuffle(todo)
        todo = todo[:sample] if sample else todo
        t0 = time.time()
        with Pool(workers) as pool:
            wake = pool.map(_solve_one, [(t, lib.concepts, budget, level, lib.prior) for t in todo])
        new_facts = 0
        for tid, r in wake:
            if r["program"] is not None:
                _chain(p / "journal.jsonl", {"kind": "verified", "task": tid, "program": r["program"],
                                             "test_ok": r["test_ok"], "round": rnd})
                new_facts += 1
        known = verified_programs(name)
        added = sleep(lib, known, rnd)
        if lib.prior:                                        # S2: intuition follows what keeps working
            lib.prior = prior_from(known)
        for cid in added:
            _chain(p / "journal.jsonl", {"kind": "concept", "id": cid, "steps": lib.concepts[cid]["steps"],
                                         "tasks": lib.concepts[cid]["tasks"], "round": rnd})
        save_library(name, lib)
        with Pool(workers) as pool:
            hold = pool.map(_solve_one, [(t, lib.concepts, budget, level, lib.prior) for t in sp["holdout"]])
        row = {"round": rnd, "wake_tasks": len(todo), "wake_new_verified": new_facts,
               "train_verified_total": len(known), "train_pool": len(sp["train"]),
               "concepts_added": len(added), "concepts_total": len(lib.concepts),
               "holdout_verified": sum(r["program"] is not None for _, r in hold),
               "holdout_test_correct": sum(bool(r["test_ok"]) for _, r in hold), "holdout": len(sp["holdout"]),
               "library_sha256": lib.sha(), "seconds": int(time.time() - t0)}
        with (p / "rounds.jsonl").open("a") as f:
            f.write(json.dumps(row, sort_keys=True) + "\n")
        print(json.dumps(row))
        sys.stdout.flush()


def verify(name):
    """The journal chain is intact and every concept still reproduces the tasks it came from."""
    p = _path(name)
    _set_level(level_of(name))
    prev, bad = "0" * 64, []
    for i, line in enumerate((p / "journal.jsonl").read_text().splitlines()):
        e = json.loads(line)
        h = e.pop("hash")
        if e["prev"] != prev or hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest() != h:
            bad.append("journal line %d" % (i + 1))
        prev = h
    lib = load_library(name)
    progs = verified_programs(name)
    for tid, prog in progs.items():
        task = gym.load(tid)
        try:
            ok = all(_run(lib, prog, pr["input"]) == dsl.G(pr["output"]) for pr in task["train"])
        except (ValueError, IndexError, KeyError):
            ok = False
        if not ok:
            bad.append("program " + tid)
    print(json.dumps({"sandbox": name, "valid": not bad, "problems": bad[:20], "verified_programs": len(progs),
                      "concepts": len(lib.concepts)}, indent=1))
    return 0 if not bad else 1


def _run(lib, prog, grid):
    g = dsl.G(grid)
    for item in prog:
        g = lib.apply(g, item)
    return g


def probe(name, budget, workers, intuition=None):
    """Measure the holdout with the sandbox's current library and level, learning nothing."""
    level = level_of(name)
    _set_level(level)
    lib = load_library(name)
    sp = gym.split()
    t0 = time.time()
    with Pool(workers) as pool:
        hold = pool.map(_solve_one, [(t, lib.concepts, budget, level, lib.prior, intuition) for t in sp["holdout"]])
    solved = sorted(t for t, r in hold if r["program"] is not None)
    row = {"sandbox": name, "level": level, "concepts": len(lib.concepts), "budget": budget, "prior": bool(lib.prior), "intuition": intuition,
           "holdout_verified": len(solved), "holdout_test_correct": sum(bool(r["test_ok"]) for _, r in hold),
           "holdout": len(sp["holdout"]), "seconds": int(time.time() - t0), "solved": solved}
    with (_path(name) / "probes.jsonl").open("a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in row.items() if k != "solved"}))


def set_prior(name, source):
    """S2 intuition from the verified programs of `source` (train-pool facts only; never the holdout)."""
    lib = load_library(name)
    lib.prior = prior_from(verified_programs(source))
    save_library(name, lib)
    _chain(_path(name) / "journal.jsonl", {"kind": "prior", "source": source, "items": len(lib.prior),
                                           "sha256": hashlib.sha256(json.dumps(lib.prior, sort_keys=True).encode()).hexdigest()})
    top = sorted(lib.prior.items(), key=lambda kv: -kv[1])[:8]
    print(json.dumps({"sandbox": name, "prior_from": source, "items": len(lib.prior), "top": top}))


def status(name):
    p = _path(name)
    print((p / "manifest.json").read_text())
    if (p / "rounds.jsonl").exists():
        print((p / "rounds.jsonl").read_text())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("new", "clone", "train", "status", "verify", "probe", "prior"))
    ap.add_argument("--level", choices=("S0", "S1", "S1b", "S2v"), default="S0")
    ap.add_argument("names", nargs="+")
    ap.add_argument("--rounds", type=int, default=1)
    ap.add_argument("--budget", type=int, default=400, help="search expansions per task")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--sample", type=int, default=0, help="wake on at most N train tasks per round (0 = all)")
    ap.add_argument("--intuition", help="weights of the S2 intuition network (probe only)")
    args = ap.parse_args(argv)
    if args.command == "new":
        new(args.names[0], args.level)
    elif args.command == "prior":
        set_prior(args.names[0], args.names[1] if len(args.names) > 1 else args.names[0])
    elif args.command == "probe":
        probe(args.names[0], args.budget, args.workers, args.intuition)
    elif args.command == "clone":
        clone(args.names[0], args.names[1])
    elif args.command == "train":
        train(args.names[0], args.rounds, args.budget, args.workers, args.sample)
    elif args.command == "status":
        status(args.names[0])
    else:
        return verify(args.names[0])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
