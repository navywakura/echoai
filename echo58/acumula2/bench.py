"""ACUMULA-2 bench: every round plays the same mix of families; the probe counts failed episodes.

    cd /home/roger/REALRXOS/RXos
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.acumula2.bench dev [--macros 1,2,3] [--no-llm]
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.acumula2.bench preflight
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.acumula2.bench exam
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List

from ..acumula import bench as B1
from ..acumula.agent import XAgent
from ..acumula.config import Config, ConfMemory
from ..acumula.diagnose import blame, candidates, menu
from ..memx.bench import MACROS, train_seeds

W = B1.W
ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab" / "echo58" / "acumula2"
HERE = Path(__file__).resolve().parent

W.MINIGRID.update({
    "BlockedUnlockPickup": "MiniGrid-BlockedUnlockPickup-v0",
    "LavaCrossingS9N1": "MiniGrid-LavaCrossingS9N1-v0",
    "ObstructedMaze2Dl": "MiniGrid-ObstructedMaze-2Dl-v0",
    "ObstructedMaze1Dlh": "MiniGrid-ObstructedMaze-1Dlh-v0",
})

MIX = ("DistShift1", "LavaCrossingS9N3", "KeyCorridorS3R2", "BlockedUnlockPickup")     # every round
PROBE = {"exam": ("DistShift2", "LavaCrossingS11N5", "ObstructedMaze2Dl", "DynObsRandom6"),
         "dev": ("LavaCrossingS9N1", "LavaCrossingS9N2", "ObstructedMaze1Dlh", "KeyCorridorS3R3")}
A_EXAM = B1.A_EXAM
ARMS = ("recursiva", "azar", "sin_acumular", "fija", "lote_final", "vacia_online", "llm")
N_ROUND, N_VAL, N_PROBE, N_Q3, K, ROUNDS = 10, 5, 30, 50, 6, 5        # per family
BASE = {"dev": 5_000_000, "exam": 6_000_000}


def seeds(phase: str, m: int) -> Dict:
    b = BASE[phase] + 100_000 * m
    return {"round": {r: [b + 1000 * r + i for i in range(N_ROUND)] for r in range(1, ROUNDS + 1)},
            "val": {r: [b + 10_000 + 1000 * r + i for i in range(N_VAL)] for r in range(1, ROUNDS + 1)},
            "probe": [b + 50_000 + i for i in range(N_PROBE)],
            "q3": [b + 60_000 + i for i in range(N_Q3)],
            "rand": b + 99_999}


def better(new: Dict[str, int], old: Dict[str, int]) -> bool:
    """Strict gate: never worse on harm or success, strictly better on harm, success or waste."""
    if new["harm"] > old["harm"] or new["success"] < old["success"]:
        return False
    return new["harm"] < old["harm"] or new["success"] > old["success"] or new["wasted"] < old["wasted"]


def accept(tries, cfg, mem, val_seeds):
    cur = B1.validate(mem, MIX, val_seeds)
    accepted = []
    for e in tries:
        if not cfg.valid(e):
            continue
        c2 = cfg.apply(e)
        m2 = mem.reconfigure(c2)
        v = B1.validate(m2, MIX, val_seeds)
        if better(v, cur):
            cfg, mem, cur = c2, m2, v
            accepted.append(e)
    return cfg, mem, accepted


def probe(mem: ConfMemory, fams, sd) -> Dict[str, Dict[str, int]]:
    out = B1.probe(mem, fams, sd)
    for v in out.values():
        v["failed"] = len(sd["probe"]) - v["success"]
    return out


def run_arm(arm: str, m: int, phase: str, use_llm: bool) -> Dict:
    sd = seeds(phase, m)
    fams_probe = PROBE[phase]
    if arm == "vacia_online":                  # empty memory learning online in the probe: same every round
        p = probe(ConfMemory(Config(), None), fams_probe, sd)
        return {"arm": arm, "macro": m, "rounds": [], "probe": {r: p for r in range(ROUNDS + 1)}, "edits": []}
    cfg = Config()
    mem = B1.start_memory(m)
    rng = random.Random(sd["rand"] * 7 + ARMS.index(arm))
    log = {"arm": arm, "macro": m, "rounds": [], "probe": {0: probe(mem, fams_probe, sd)}}
    all_failures: List = []
    edit_round: Dict[str, int] = {}
    for r in range(1, ROUNDS + 1):
        if arm == "sin_acumular":
            cfg = Config()
            mem = mem.reconfigure(cfg)
        ag = XAgent(source=mem, learn=mem)
        played, failures = [], []
        mem.surprises = []
        for s in sd["round"][r]:
            for f in MIX:
                res = B1.play(ag, f, s)
                failures += res.pop("failures")
                played.append(res)
        n_misled = len(failures)
        failures += mem.surprises
        mem.surprises = None
        all_failures += failures
        diag = [(layer, key, n, ",".join(sorted({o for la, k, o in failures if (la, k) == (layer, key)})))
                for (layer, key), n in blame(failures).most_common()]
        receipt, tries = None, []
        if arm in ("recursiva", "sin_acumular"):
            tries = candidates(failures, cfg, mem.raw)[:K]
        elif arm == "azar":
            full = menu(cfg, mem.l2)
            tries = rng.sample(full, min(K, len(full)))
        elif arm == "llm" and use_llm:
            from ..acumula.llm import choose
            tries, receipt = choose(diag, menu(cfg, mem.l2), K, f"v2-m{m}-r{r}-{phase}")
        elif arm == "lote_final" and r == ROUNDS:   # the whole budget, once, from everything seen
            tries = candidates(all_failures, cfg, mem.raw)[:K * ROUNDS]
        accepted = []
        if tries:
            cfg, mem, accepted = accept(tries, cfg, mem, sd["val"][r])
        for e in accepted:
            edit_round[repr(e)] = r
        log["rounds"].append({"round": r, "play": B1.totals(played), "misled": n_misled,
                              "surprises": len(failures) - n_misled, "blamed_keys": len(diag),
                              "tried": [repr(e) for e in tries], "accepted": [repr(e) for e in accepted],
                              "llm": receipt, "config": cfg.digest()})
        log["probe"][r] = probe(mem, fams_probe, sd)
    if arm == "recursiva":
        q3 = {}
        for name, c in (("base", Config()), ("final", cfg)):
            ag = XAgent(source=mem.reconfigure(c))
            q3[name] = {f: B1.totals([B1.play(ag, f, s) for s in sd["q3"]]) for f in A_EXAM}
        log["q3"] = q3
        # reported: the edits of rounds >= 2 without those of round 1, on the same final memory
        late = Config()
        for e in cfg.edits:
            if edit_round.get(repr(e), 1) >= 2 and late.valid(e):
                late = late.apply(e)
        log["ablation_no_r1"] = probe(mem.reconfigure(late), fams_probe, sd)
        coarse_seen, dependent = {}, 0
        for e in cfg.edits:
            k = e[1] if len(e) > 1 and isinstance(e[1], tuple) else None
            k = k[:3] if k is not None else None
            if k is not None and k in coarse_seen and coarse_seen[k] < edit_round[repr(e)]:
                dependent += 1
            if k is not None:
                coarse_seen.setdefault(k, edit_round[repr(e)])
        log["dependent_edits"] = dependent
    log["edits"] = [repr(e) for e in cfg.edits]
    log["edit_round"] = edit_round
    log["chain_head"] = mem.chain.head
    return log


def job(args) -> Dict:
    arm, m, phase, use_llm = args
    t = time.time()
    try:
        out = run_arm(arm, m, phase, use_llm)
    except Exception:
        import traceback
        out = {"arm": arm, "macro": m, "crash": traceback.format_exc()}
    out["secs"] = int(time.time() - t)
    return out


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frozen_state() -> Dict:
    st = B1.frozen_state()
    st["acumula2"] = {p.name: sha(p) for p in sorted(HERE.glob("*.py"))}
    st["families"] = {k: W.MINIGRID[k] for k in sorted(W.MINIGRID)}
    return st


def summary(res: List[Dict]) -> None:
    for arm in ARMS:
        for x in res:
            if "crash" in x and x["arm"] == arm:
                print(f"{arm} m{x['macro']} CRASHED:", x["crash"].splitlines()[-1])
        rows = [x for x in res if x["arm"] == arm and "crash" not in x]
        if not rows:
            continue
        line = []
        for r in range(ROUNDS + 1):
            f = sum(sum(v["failed"] for v in x["probe"][r].values()) for x in rows)
            h = sum(sum(v["harm"] for v in x["probe"][r].values()) for x in rows)
            line.append(f"{f}/{h}")
        print(f"{arm:13s} probe failed/harm r0..5: {' '.join(line)}")
        for x in rows:
            if x["edits"]:
                print(f"   m{x['macro']} {x['edit_round']}")
            if "q3" in x:
                print("   q3", {k: {f: (v['success'], v['harm']) for f, v in d.items()} for k, d in x["q3"].items()},
                      "ablation_no_r1 failed", sum(v["failed"] for v in x["ablation_no_r1"].values()),
                      "dependent", x["dependent_edits"])


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


def cmd_preflight(a) -> None:
    pf = LAB / "preflight.json"
    if pf.exists():
        raise SystemExit(f"{pf} exists: the freeze is written once")
    LAB.mkdir(parents=True, exist_ok=True)
    from ..acumula.llm import MODEL
    doc = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "frozen": frozen_state(),
           "mix": MIX, "probe": PROBE["exam"], "arms": ARMS, "K": K, "rounds": ROUNDS,
           "n": {"round": N_ROUND, "val": N_VAL, "probe": N_PROBE, "q3": N_Q3},
           "seeds": {m: seeds("exam", m) for m in MACROS}, "llm_model": MODEL,
           "start_heads": {m: B1.start_memory(m).chain.head for m in MACROS}}
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
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--macros", default="1,2,3")
    ap.add_argument("--no-llm", action="store_true")
    a = ap.parse_args(argv)
    {"dev": cmd_dev, "preflight": cmd_preflight, "exam": cmd_exam}[a.cmd](a)


if __name__ == "__main__":
    main()
