"""B v3 prototype bench (development only, no contract): ACUMULA-2's rounds with a menu that holds
memory edits *and* policy pieces (policy.py), proposed from signals in ECHO's own failed episodes.

    cd /home/user/REALRXOS/RXos
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.b3.bench --macros 1 2 3

Same mix, gate, seeds and controls as ACUMULA-2 dev; dev probe swaps ObstructedMaze1Dlh (already
solved from round 1) for ObstructedMaze1Dlhb (box + ball). The hand-key fix is in the base agent
of every arm.
"""
from __future__ import annotations

import argparse
import json
import random
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, List

from ..acumula import bench as B1
from ..acumula.config import Config, ConfMemory
from ..acumula.diagnose import candidates, menu
from ..acumula2 import bench as B2
from .policy import PIECES, SIGNAL_PIECE, PAgent
from .trace import OUT

B1.W.MINIGRID["ObstructedMaze1Dlhb"] = "MiniGrid-ObstructedMaze-1Dlhb-v0"
PROBE = ("LavaCrossingS9N1", "LavaCrossingS9N2", "ObstructedMaze1Dlhb", "KeyCorridorS3R3")
ARMS = ("recursiva", "azar", "sin_acumular", "fija", "lote_final", "vacia_online", "piezas_dadas")
PAIRS = (("commit", "no_repick"),)          # pieces raised by the same signal, offered together too


class PConfig(Config):
    def __init__(self):
        super().__init__()
        self.pieces = frozenset()

    def copy(self):
        c = PConfig()
        b = Config.copy(self)
        c.__dict__.update(b.__dict__)
        c.pieces = self.pieces
        return c

    def apply(self, edit):
        if edit[0] != "piece":
            c = Config.apply(self, edit)
            p = PConfig()
            p.__dict__.update(c.__dict__)
            p.pieces = self.pieces
            return p
        c = self.copy()
        c.pieces = c.pieces | set(edit[1])
        c.edits.append(edit)
        return c

    def valid(self, edit):
        if edit[0] == "piece":
            return not set(edit[1]) <= self.pieces
        return Config.valid(self, edit)


def agent(mem, learn=None):
    return PAgent(source=mem, learn=learn, pieces=getattr(mem.cfg, "pieces", frozenset()))


def play(ag, fam, seed):
    w = B1.W.make_world(fam, seed, "A2")
    r = ag.run(w)
    w.close()
    return r


def validate(mem, fams, seeds_):
    ag = agent(mem)
    return B1.totals([play(ag, f, s) for s in seeds_ for f in fams])


def probe(mem, sd):
    out = {}
    for f in PROBE:
        cp = mem.probe_copy()
        v = B1.totals([play(agent(cp, cp), f, s) for s in sd["probe"]])
        v["failed"] = len(sd["probe"]) - v["success"]
        out[f] = v
    return out


def piece_candidates(signals: Counter, cfg) -> List:
    out = []
    for sig, _ in signals.most_common():
        p = SIGNAL_PIECE[sig]
        for e in [("piece", (p,))] + [("piece", pr) for pr in PAIRS if p in pr]:
            if cfg.valid(e) and e not in out:
                out.append(e)
    return out


def piece_menu(cfg) -> List:
    return [e for e in [("piece", (p,)) for p in PIECES] + [("piece", pr) for pr in PAIRS] if cfg.valid(e)]


def accept(tries, cfg, mem, val):
    cur = validate(mem, B2.MIX, val)
    acc = []
    for e in tries:
        if not cfg.valid(e):
            continue
        c2 = cfg.apply(e)
        m2 = mem.reconfigure(c2)
        v = validate(m2, B2.MIX, val)
        if B2.better(v, cur):
            cfg, mem, cur = c2, m2, v
            acc.append(e)
    return cfg, mem, acc


def run_arm(arm: str, m: int) -> Dict:
    t0 = time.time()
    sd = B2.seeds("dev", m)
    if arm == "vacia_online":                  # empty memory, base pieces, learning online in the probe
        p = probe(ConfMemory(PConfig(), None), sd)
        return {"arm": arm, "macro": m, "rounds": [], "probe": {r: p for r in range(B2.ROUNDS + 1)}, "edits": []}
    cfg = PConfig()
    if arm == "piezas_dadas":                  # every piece on from the start (my design); ECHO edits memory only
        cfg = cfg.apply(("piece", PIECES))
    mem = B1.start_memory(m).reconfigure(cfg)
    rng = random.Random(sd["rand"] * 7 + ARMS.index(arm))
    log = {"arm": arm, "macro": m, "rounds": [], "probe": {0: probe(mem, sd)}}
    all_f, all_s = [], Counter()
    for r in range(1, B2.ROUNDS + 1):
        if arm == "sin_acumular":
            cfg = PConfig()
            mem = mem.reconfigure(cfg)
        ag = agent(mem, mem)
        failures, signals, played = [], Counter(), []
        mem.surprises = []
        for s in sd["round"][r]:
            for f in B2.MIX:
                res = play(ag, f, s)
                failures += res.pop("failures")
                signals.update(res.pop("signals"))
                played.append(res)
        failures += mem.surprises
        mem.surprises = None
        all_f += failures
        all_s += signals
        tries = []
        if arm == "piezas_dadas":
            tries = candidates(failures, cfg, mem.raw)[:B2.K]
        elif arm in ("recursiva", "sin_acumular"):
            tries = candidates(failures, cfg, mem.raw)[:B2.K] + piece_candidates(signals, cfg)
        elif arm == "azar":
            n = len(candidates(failures, cfg, mem.raw)[:B2.K] + piece_candidates(signals, cfg))
            full = menu(cfg, mem.l2) + piece_menu(cfg)
            tries = rng.sample(full, min(n, len(full)))
        elif arm == "lote_final" and r == B2.ROUNDS:
            tries = candidates(all_f, cfg, mem.raw)[:B2.K * B2.ROUNDS] + piece_candidates(all_s, cfg)
        acc = []
        if tries:
            cfg, mem, acc = accept(tries, cfg, mem, sd["val"][r])
        log["rounds"].append({"round": r, "play": B1.totals(played), "signals": dict(signals),
                              "tried": [repr(e) for e in tries], "accepted": [repr(e) for e in acc]})
        log["probe"][r] = probe(mem, sd)
    log["edits"] = [repr(e) for e in cfg.edits]
    log["secs"] = int(time.time() - t0)
    return log


def job(a):
    return run_arm(*a)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--macros", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--arms", nargs="+", default=list(ARMS))
    a = ap.parse_args(argv)
    jobs = [(arm, m) for m in a.macros for arm in a.arms]
    with ProcessPoolExecutor(max_workers=min(len(jobs), 12)) as ex:
        res = list(ex.map(job, jobs))
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"bench-dev-{time.strftime('%Y%m%dT%H%M%S')}.json"
    p.write_text(json.dumps({"runs": res}, indent=1, default=str))
    for arm in a.arms:
        rows = [x for x in res if x["arm"] == arm]
        line = []
        for r in range(B2.ROUNDS + 1):
            f = sum(sum(v["failed"] for v in x["probe"][r].values()) for x in rows)
            h = sum(sum(v["harm"] for v in x["probe"][r].values()) for x in rows)
            line.append(f"{f}/{h}")
        print(f"{arm:13s} probe failed/harm r0..5: {' '.join(line)}")
        for x in rows:
            print("   ", x["macro"], [rd["accepted"] for rd in x["rounds"]])
    print("->", p)


if __name__ == "__main__":
    main()
