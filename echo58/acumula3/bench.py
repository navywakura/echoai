"""ACUMULA-3 (B v3) bench: ACUMULA-2's stationary rounds with a menu of memory edits *and* policy
pieces (b3/policy.py) proposed from ECHO's own failed episodes (contract ACUMULA3-DESIGN.md).

    cd /home/user/REALRXOS/RXos
    PYTHONPATH=. echoai/simulation/.venv-sandbox/bin/python -m echoai.echo58.acumula3.bench dev --macros 1,2,3
    PYTHONPATH=. echoai/simulation/.venv-sandbox/bin/python -m echoai.echo58.acumula3.bench preflight
    PYTHONPATH=. echoai/simulation/.venv-sandbox/bin/python -m echoai.echo58.acumula3.bench exam
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Dict, List

from ..acumula import bench as B1
from ..acumula.config import Config, ConfMemory
from ..acumula.diagnose import candidates, menu
from ..acumula2 import bench as B2
from ..b3.policy import PIECES, SIGNAL_PIECE, PAgent
from ..memx.bench import MACROS

W = B1.W
ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "lab" / "echo58" / "acumula3"
HERE = Path(__file__).resolve().parent
POLICY = ROOT / "echo58" / "b3" / "policy.py"

W.MINIGRID.update({
    "ObstructedMaze1Dlhb": "MiniGrid-ObstructedMaze-1Dlhb-v0",
    "ObstructedMaze2Dlh": "MiniGrid-ObstructedMaze-2Dlh-v0",
    "DynObsRandom5": "MiniGrid-Dynamic-Obstacles-Random-5x5-v0",
    "LavaCrossingS11N5": "MiniGrid-LavaCrossingS11N5-v0",
})

MIX = B2.MIX
PROBE = {"exam": ("LavaCrossingS11N5", "DistShift2", "ObstructedMaze2Dlh", "DynObsRandom5"),
         "dev": ("LavaCrossingS9N1", "LavaCrossingS9N2", "ObstructedMaze1Dlhb", "KeyCorridorS3R3")}
A_EXAM = B1.A_EXAM
ARMS = ("recursiva", "azar", "sin_acumular", "fija", "lote_final", "vacia_online", "piezas_dadas")
PAIRS = (("commit", "no_repick"),)          # pieces raised by the same signal, offered together too
N_ROUND, N_VAL, N_PROBE, N_Q3, K, ROUNDS = B2.N_ROUND, B2.N_VAL, B2.N_PROBE, B2.N_Q3, B2.K, B2.ROUNDS
BASE = {"dev": 5_000_000, "exam": 8_000_000}


def seeds(phase: str, m: int) -> Dict:
    b = BASE[phase] + 100_000 * m
    return {"round": {r: [b + 1000 * r + i for i in range(N_ROUND)] for r in range(1, ROUNDS + 1)},
            "val": {r: [b + 10_000 + 1000 * r + i for i in range(N_VAL)] for r in range(1, ROUNDS + 1)},
            "probe": [b + 50_000 + i for i in range(N_PROBE)],
            "q3": [b + 60_000 + i for i in range(N_Q3)],
            "rand": b + 99_999}


class PConfig(Config):
    """A memory configuration plus the set of policy pieces switched on."""

    def __init__(self):
        super().__init__()
        self.pieces = frozenset()

    def copy(self) -> "PConfig":
        c = PConfig()
        c.__dict__.update(Config.copy(self).__dict__)
        c.pieces = self.pieces
        return c

    def apply(self, edit) -> "PConfig":
        if edit[0] != "piece":
            return Config.apply(self, edit)          # Config.apply works on self.copy(): stays a PConfig
        c = self.copy()
        c.pieces = c.pieces | frozenset(edit[1])
        c.edits.append(edit)
        return c

    def valid(self, edit) -> bool:
        if edit[0] == "piece":
            return not frozenset(edit[1]) <= self.pieces
        return Config.valid(self, edit)


def agent(mem: ConfMemory, learn=None) -> PAgent:
    return PAgent(source=mem, learn=learn, pieces=getattr(mem.cfg, "pieces", frozenset()))


def play(ag, fam: str, seed: int) -> Dict:
    w = W.make_world(fam, seed, "A2")
    r = ag.run(w)
    w.close()
    return r


def validate(mem: ConfMemory, fams, seeds_) -> Dict[str, int]:
    ag = agent(mem)                                  # frozen: validation does not learn
    return B1.totals([play(ag, f, s) for s in seeds_ for f in fams])


def probe(mem: ConfMemory, fams, sd) -> Dict[str, Dict[str, int]]:
    out = {}
    for f in fams:
        cp = mem.probe_copy()
        v = B1.totals([play(agent(cp, cp), f, s) for s in sd["probe"]])
        v["failed"] = len(sd["probe"]) - v["success"]
        out[f] = v
    return out


def piece_candidates(signals: Counter, cfg: PConfig) -> List:
    out = []
    for sig, _ in sorted(signals.items(), key=lambda kv: (-kv[1], kv[0])):
        p = SIGNAL_PIECE[sig]
        for e in [("piece", (p,))] + [("piece", pr) for pr in PAIRS if p in pr]:
            if cfg.valid(e) and e not in out:
                out.append(e)
    return out


def piece_menu(cfg: PConfig) -> List:
    return [e for e in [("piece", (p,)) for p in PIECES] + [("piece", pr) for pr in PAIRS] if cfg.valid(e)]


def accept(tries, cfg, mem, val_seeds):
    cur = validate(mem, MIX, val_seeds)
    accepted, validated = [], []
    for e in tries:
        if not cfg.valid(e):
            continue
        validated.append(e)
        c2 = cfg.apply(e)
        m2 = mem.reconfigure(c2)
        v = validate(m2, MIX, val_seeds)
        if B2.better(v, cur):
            cfg, mem, cur = c2, m2, v
            accepted.append(e)
    return cfg, mem, accepted, validated


def run_arm(arm: str, m: int, phase: str) -> Dict:
    sd = seeds(phase, m)
    fams_probe = PROBE[phase]
    if arm == "vacia_online":                  # empty memory learning online in the probe: same every round
        p = probe(ConfMemory(PConfig(), None), fams_probe, sd)
        return {"arm": arm, "macro": m, "rounds": [], "probe": {r: p for r in range(ROUNDS + 1)}, "edits": []}
    cfg = PConfig()
    if arm == "piezas_dadas":                  # every piece on from the start; ECHO edits memory only
        cfg = cfg.apply(("piece", PIECES))
    mem = B1.start_memory(m).reconfigure(cfg)
    rng = random.Random(sd["rand"] * 7 + ARMS.index(arm))
    log = {"arm": arm, "macro": m, "rounds": [], "probe": {0: probe(mem, fams_probe, sd)}}
    all_f: List = []
    all_s: Counter = Counter()
    edit_round: Dict[str, int] = {}
    tried_round: Dict[str, int] = {}
    for r in range(1, ROUNDS + 1):
        if arm == "sin_acumular":
            cfg = PConfig()
            mem = mem.reconfigure(cfg)
        ag = agent(mem, mem)
        played, failures, signals = [], [], Counter()
        mem.surprises = []
        for s in sd["round"][r]:
            for f in MIX:
                res = play(ag, f, s)
                failures += res.pop("failures")
                signals.update(res.pop("signals"))
                played.append(res)
        failures += mem.surprises
        mem.surprises = None
        all_f += failures
        all_s += signals
        own_mem, own_pieces = candidates(failures, cfg, mem.raw)[:K], piece_candidates(signals, cfg)
        own = own_mem + own_pieces
        tries: List = []
        if arm in ("recursiva", "sin_acumular"):
            tries = own
        elif arm == "piezas_dadas":
            tries = candidates(failures, cfg, mem.raw)[:K]
        elif arm == "azar":                       # stratified: as many memory edits and pieces as ECHO proposes
            mm, pm = menu(cfg, mem.l2), piece_menu(cfg)
            tries = rng.sample(mm, min(len(own_mem), len(mm))) + rng.sample(pm, min(len(own_pieces), len(pm)))
        elif arm == "lote_final" and r == ROUNDS:   # the whole budget, once, from everything seen
            tries = candidates(all_f, cfg, mem.raw)[:K * ROUNDS] + piece_candidates(all_s, cfg)
        accepted, validated = [], []
        if tries:
            cfg, mem, accepted, validated = accept(tries, cfg, mem, sd["val"][r])
        for e in validated:
            tried_round.setdefault(repr(e), r)
        for e in accepted:
            edit_round[repr(e)] = r
        log["rounds"].append({"round": r, "play": B1.totals(played), "signals": dict(signals),
                              "tried": [repr(e) for e in tries], "accepted": [repr(e) for e in accepted],
                              "config": cfg.digest(), "pieces": sorted(cfg.pieces)})
        log["probe"][r] = probe(mem, fams_probe, sd)
    if arm == "recursiva":
        q3 = {}
        for name, c in (("base", PConfig()), ("final", cfg)):
            ag = agent(mem.reconfigure(c))
            q3[name] = {f: B1.totals([play(ag, f, s) for s in sd["q3"]]) for f in A_EXAM}
        log["q3"] = q3
    # Q4: accepted in round r >= 2 after having been tried (and rejected) in an earlier round
    log["late_after_reject"] = sorted(e for e, r in edit_round.items() if r >= 2 and tried_round.get(e, r) < r)
    log["edits"] = [repr(e) for e in cfg.edits]
    log["edit_round"] = edit_round
    log["destroyed"] = mem.destroyed
    log["chain_head"] = mem.chain.head
    return log


def job(args) -> Dict:
    arm, m, phase = args
    t = time.time()
    try:
        out = run_arm(arm, m, phase)
    except Exception:
        import traceback
        out = {"arm": arm, "macro": m, "crash": traceback.format_exc()}
    out["secs"] = int(time.time() - t)
    return out


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def frozen_state() -> Dict:
    st = B2.frozen_state()
    st["acumula3"] = {p.name: sha(p) for p in sorted(HERE.glob("*.py"))}
    import numpy
    st["b3_policy"] = sha(POLICY)
    st["b3_init"] = sha(POLICY.with_name("__init__.py"))
    st["numpy"] = numpy.__version__
    st["contract"] = sha(ROOT / "ECHO-5.8" / "docs" / "ACUMULA3-DESIGN.md")
    st["tests"] = sha(ROOT / "tests" / "test_echo58_acumula3.py")
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


def cmd_dev(a) -> None:
    LAB.mkdir(parents=True, exist_ok=True)
    macros = [int(x) for x in a.macros.split(",")]
    jobs = [(arm, m, "dev") for m in macros for arm in ARMS]
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
    doc = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "frozen": frozen_state(),
           "mix": MIX, "probe": PROBE["exam"], "arms": ARMS, "K": K, "rounds": ROUNDS, "pairs": PAIRS,
           "n": {"round": N_ROUND, "val": N_VAL, "probe": N_PROBE, "q3": N_Q3},
           "seeds": {m: seeds("exam", m) for m in MACROS},
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
    jobs = [(arm, m, "exam") for m in MACROS for arm in ARMS]
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for r in ex.map(job, jobs):
            (out / f"{r['arm']}-m{r['macro']:02d}.json").write_text(json.dumps(r, indent=1))
            print("done", r["arm"], r["macro"], r["secs"], "CRASH" if "crash" in r else "", flush=True)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("dev", "preflight", "exam"))
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--macros", default="1,2,3")
    a = ap.parse_args(argv)
    {"dev": cmd_dev, "preflight": cmd_preflight, "exam": cmd_exam}[a.cmd](a)


if __name__ == "__main__":
    main()
