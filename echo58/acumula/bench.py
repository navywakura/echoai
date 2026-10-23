"""ACUMULA bench: five rounds, five arms, a probe of unseen families after each round.

    cd /home/user/REALRXOS/RXos
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.acumula.bench dev [--macros 1,2,3] [--no-llm]
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.acumula.bench preflight
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.acumula.bench exam

Development and exam use disjoint seed blocks and different probe families;
the exam probe families are never played before the exam.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..memx import world as W
from ..memx.bench import MACROS, train_seeds
from ..memx.memory import Memory
from .agent import XAgent
from .config import Config, ConfMemory
from .diagnose import blame, candidates, menu

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab" / "echo58" / "acumula"
HERE = Path(__file__).resolve().parent

W.MINIGRID.update({
    "DistShift1": "MiniGrid-DistShift1-v0", "LavaGapS5": "MiniGrid-LavaGapS5-v0",
    "LavaCrossingS9N2": "MiniGrid-LavaCrossingS9N2-v0", "DynObs5": "MiniGrid-Dynamic-Obstacles-5x5-v0",
    "SimpleCrossingS9N1": "MiniGrid-SimpleCrossingS9N1-v0", "LavaCrossingS9N3": "MiniGrid-LavaCrossingS9N3-v0",
    "KeyCorridorS3R2": "MiniGrid-KeyCorridorS3R2-v0", "DoorKey8": "MiniGrid-DoorKey-8x8-v0",
    # probe, exam only
    "LavaCrossingS11N5": "MiniGrid-LavaCrossingS11N5-v0", "DynObsRandom6": "MiniGrid-Dynamic-Obstacles-Random-6x6-v0",
    "BlockedUnlockPickup": "MiniGrid-BlockedUnlockPickup-v0", "ObstructedMaze1Dl": "MiniGrid-ObstructedMaze-1Dl-v0",
    # probe, development only
    "LavaGapS6": "MiniGrid-LavaGapS6-v0", "DynObsRandom5": "MiniGrid-Dynamic-Obstacles-Random-5x5-v0",
    "Unlock": "MiniGrid-Unlock-v0", "KeyCorridorS3R3": "MiniGrid-KeyCorridorS3R3-v0",
})

ROUNDS = (("DistShift1", "LavaGapS5"), ("LavaCrossingS9N2", "DynObs5"), ("DistShift2", "SimpleCrossingS9N1"),
          ("LavaCrossingS9N3", "KeyCorridorS3R2"), ("ShiftTest", "DoorKey8"))
PROBE = {"exam": ("LavaCrossingS11N5", "DynObsRandom6", "BlockedUnlockPickup", "ObstructedMaze1Dl"),
         "dev": ("LavaGapS6", "DynObsRandom5", "Unlock", "KeyCorridorS3R3")}
A_EXAM = ("DistShift2", "UnlockPickup", "DynObs16", "ShiftTest")
ARMS = ("recursiva", "azar", "sin_acumular", "fija", "llm")
N_ROUND, N_VAL, N_PROBE, N_Q3, K = 20, 10, 30, 50, 6      # per family
BASE = {"dev": 2_000_000, "exam": 3_000_000}


def seeds(phase: str, m: int) -> Dict:
    b = BASE[phase] + 100_000 * m
    return {"round": {r: [b + 1000 * r + i for i in range(N_ROUND)] for r in range(1, 6)},
            "val": {r: [b + 10_000 + 1000 * r + i for i in range(N_VAL)] for r in range(1, 6)},
            "probe": [b + 50_000 + i for i in range(N_PROBE)],
            "q3": [b + 60_000 + i for i in range(N_Q3)],
            "rand": b + 99_999}


def play(agent, fam: str, seed: int) -> Dict:
    w = W.make_world(fam, seed, "A2")
    r = agent.run(w)
    w.close()
    return r


def totals(rs: List[Dict]) -> Dict[str, int]:
    return {k: sum(r[k] for r in rs) for k in ("success", "harm", "wasted", "steps")}


def start_memory(m: int) -> ConfMemory:
    """Track A's training plan replayed by the rank-aware agent (base config reads it like A)."""
    mem = ConfMemory(Config(), Memory())
    agent = XAgent(source=mem, learn=mem)
    for fam, seed in train_seeds(m):
        w = W.make_world(fam, seed, "A1")
        agent.run(w)
        w.close()
    return mem


def probe(mem: ConfMemory, fams, sd) -> Dict[str, Dict[str, int]]:
    """Learning speed in unseen worlds: each family on its own throw-away copy, learning online."""
    out = {}
    for f in fams:
        cp = mem.probe_copy()
        ag = XAgent(source=cp, learn=cp)
        out[f] = totals([play(ag, f, s) for s in sd["probe"]])
    return out


def validate(mem: ConfMemory, fams, seeds_) -> Dict[str, int]:
    ag = XAgent(source=mem)                     # frozen: validation does not learn
    return totals([play(ag, f, s) for s in seeds_ for f in fams])


def better(new: Dict[str, int], old: Dict[str, int]) -> bool:
    """Non-inferior on validation (amendment 1): no more harm and no less success; when both tie,
    waste may not grow by 10 % or more."""
    if new["harm"] > old["harm"] or new["success"] < old["success"]:
        return False
    return (new["harm"] < old["harm"] or new["success"] > old["success"]
            or new["wasted"] * 10 < old["wasted"] * 11 or new["wasted"] == old["wasted"] == 0)


def run_arm(arm: str, m: int, phase: str, use_llm: bool) -> Dict:
    sd = seeds(phase, m)
    fams_probe = PROBE[phase]
    cfg = Config()
    mem = start_memory(m)
    rng = random.Random(sd["rand"] * 7 + ARMS.index(arm))
    log = {"arm": arm, "macro": m, "rounds": [], "probe": {0: probe(mem, fams_probe, sd)}}
    for r in range(1, 6):
        fams = ROUNDS[r - 1]
        if arm == "sin_acumular":
            cfg = Config()
            mem = mem.reconfigure(cfg)
        ag = XAgent(source=mem, learn=mem)
        played, failures = [], []
        mem.surprises = []
        for s in sd["round"][r]:
            for f in fams:
                res = play(ag, f, s)
                failures += res.pop("failures")
                played.append(res)
        n_misled = len(failures)
        failures += mem.surprises
        mem.surprises = None
        diag = [(layer, key, n, ",".join(sorted({o for la, k, o in failures if (la, k) == (layer, key)})))
                for (layer, key), n in blame(failures).most_common()]
        receipt = None
        if arm in ("recursiva", "sin_acumular"):
            tries = candidates(failures, cfg, mem.raw)[:K]
        elif arm == "azar":
            full = menu(cfg, mem.l2)
            tries = rng.sample(full, min(K, len(full)))
        elif arm == "llm" and use_llm:
            tries, receipt = choose_llm(diag, menu(cfg, mem.l2), f"m{m}-r{r}-{phase}")
        else:
            tries = []
        accepted = []
        if tries:
            cur = validate(mem, fams, sd["val"][r])
            for e in tries:
                if not cfg.valid(e):
                    continue
                c2 = cfg.apply(e)
                m2 = mem.reconfigure(c2)
                v = validate(m2, fams, sd["val"][r])
                if better(v, cur):
                    cfg, mem, cur = c2, m2, v
                    accepted.append(e)
        log["rounds"].append({"round": r, "families": fams, "play": totals(played), "misled": n_misled, "surprises": len(failures) - n_misled,
                              "blamed_keys": len(diag), "tried": [repr(e) for e in tries],
                              "accepted": [repr(e) for e in accepted], "llm": receipt, "config": cfg.digest()})
        log["probe"][r] = probe(mem, fams_probe, sd)
    if arm == "recursiva":                     # Q3: final config vs base on the same final memory, A's exam families
        q3 = {}
        for name, c in (("base", Config()), ("final", cfg)):
            ag = XAgent(source=mem.reconfigure(c))
            q3[name] = {f: totals([play(ag, f, s) for s in sd["q3"]]) for f in A_EXAM}
        log["q3"] = q3
    log["edits"] = [repr(e) for e in cfg.edits]
    log["chain_head"] = mem.chain.head
    return log


def choose_llm(diag, full, tag):
    from .llm import choose
    picks, receipt = choose(diag, full, K, tag)
    return picks, receipt


def job(args) -> Dict:
    arm, m, phase, use_llm = args
    t = time.time()
    try:
        out = run_arm(arm, m, phase, use_llm)
    except Exception:                           # one crashed job must not abort the one-shot exam
        import traceback
        out = {"arm": arm, "macro": m, "crash": traceback.format_exc()}
    out["secs"] = int(time.time() - t)
    return out


# -- freeze ----------------------------------------------------------------------
def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frozen_state() -> Dict:
    from ..memx.bench import frozen_state as memx_state
    st = memx_state()
    st.pop("marginal_freq", None)
    st["acumula"] = {p.name: sha(p) for p in sorted(HERE.glob("*.py"))}
    st["families"] = {k: W.MINIGRID[k] for k in sorted(W.MINIGRID)}
    return st


def cmd_dev(a) -> None:
    LAB.mkdir(parents=True, exist_ok=True)
    macros = [int(x) for x in a.macros.split(",")]
    jobs = [(arm, m, "dev", not a.no_llm) for m in macros for arm in ARMS]
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        res = list(ex.map(job, jobs))
    out = LAB / f"dev-{time.strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runs": res}, indent=1))
    print(out)
    summary(res)


def summary(res: List[Dict]) -> None:
    for arm in ARMS:
        for x in res:
            if "crash" in x and x["arm"] == arm:
                print(f"{arm} m{x['macro']} CRASHED:", x["crash"].splitlines()[-1])
        rows = [x for x in res if x["arm"] == arm and "crash" not in x]
        if not rows:
            continue
        line = []
        for r in range(6):
            h = sum(sum(v["harm"] for v in x["probe"][r].values()) for x in rows)
            s = sum(sum(v["success"] for v in x["probe"][r].values()) for x in rows)
            line.append(f"{s}/{h}")
        acc = sum(len(rr["accepted"]) for x in rows for rr in x["rounds"])
        print(f"{arm:13s} probe succ/harm by round 0..5: {' '.join(line)}  accepted={acc}")
        for x in rows:
            print("   m%d edits %s" % (x["macro"], x["edits"]))
            if "q3" in x:
                print("   m%d q3 %s" % (x["macro"], {k: {f: (v['success'], v['harm']) for f, v in d.items()} for k, d in x["q3"].items()}))


def cmd_preflight(a) -> None:
    pf = LAB / "preflight.json"
    if pf.exists():
        raise SystemExit(f"{pf} exists: the freeze is written once")
    LAB.mkdir(parents=True, exist_ok=True)
    doc = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "frozen": frozen_state(),
           "rounds": ROUNDS, "probe": PROBE["exam"], "arms": ARMS, "K": K,
           "n": {"round": N_ROUND, "val": N_VAL, "probe": N_PROBE, "q3": N_Q3},
           "seeds": {m: seeds("exam", m) for m in MACROS}, "llm_model": __import__(
               "echoai.echo58.acumula.llm", fromlist=["MODEL"]).MODEL}
    doc["seeds_sha256"] = hashlib.sha256(json.dumps(doc["seeds"], sort_keys=True).encode()).hexdigest()
    pf.write_text(json.dumps(doc, indent=1, sort_keys=True))
    print(pf, doc["seeds_sha256"])


def cmd_exam(a) -> None:
    pf = json.loads((LAB / "preflight.json").read_text())
    if pf["frozen"] != json.loads(json.dumps(frozen_state())):
        raise SystemExit("something frozen changed since preflight: refusing to examine")
    out = LAB / "exam"
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"{out} is not empty: the exam runs once")
    out.mkdir(exist_ok=True)
    jobs = [(arm, m, "exam", True) for m in MACROS for arm in ARMS]
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for r in ex.map(job, jobs):
            (out / f"{r['arm']}-m{r['macro']:02d}.json").write_text(json.dumps(r, indent=1))
            print("done", r["arm"], r["macro"], r["secs"], flush=True)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("dev", "preflight", "exam"))
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--macros", default="1,2,3")
    ap.add_argument("--no-llm", action="store_true")
    a = ap.parse_args(argv)
    {"dev": cmd_dev, "preflight": cmd_preflight, "exam": cmd_exam}[a.cmd](a)


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    main()
