"""B v3 investigation (lab tool, not the agent): watch ECHO play, find where it gets stuck, and why.

    cd /home/roger/REALRXOS/RXos
    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.b3.trace FAMILY [--n 10] [--seed0 7000000]

The agent never sees names; this tool translates ids back to MiniGrid names only
to explain the traces to people. Agent: track A's memory read with the
corrections B found (order, refine by rank 0 of the 5-15 and >15 classes).
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from ..acumula import bench as B1
from ..acumula.agent import XAgent
from ..acumula.config import Config
from ..acumula2 import bench as B2  # noqa: F401  (registers the v2 families)

OUT = Path(__file__).resolve().parents[2] / "lab" / "echo58" / "b3"
CORRECTED = (("order",), ("refine", (8, "ENTER", 0), 32), ("refine", (12, "ENTER", 0), 32))


def namer(world):
    from minigrid.core.constants import IDX_TO_COLOR, IDX_TO_OBJECT
    inv = {v: k for k, v in world.ids.items()}
    states = {0: "open", 1: "closed", 2: "locked"}

    def name(i):
        if not i:
            return "-"
        k = inv[i]
        t, c, s = k[1:]
        obj = IDX_TO_OBJECT[t]
        if obj in ("empty", "wall", "floor", "lava", "goal", "unseen"):
            return obj
        return f"{IDX_TO_COLOR[c]}-{obj}" + (f"({states[s]})" if obj == "door" else "")
    return name


class Tracer(XAgent):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.steps = []

    def _decide(self, obs, world):
        prim, intent = super()._decide(obs, world)
        self.steps.append((obs, prim, intent))
        return prim, intent


def stuck_point(steps, repeats=3):
    seen = Counter()
    for t, (obs, prim, intent) in enumerate(steps):
        key = (obs.pos, obs.dir, obs.hand, obs.grid)
        seen[key] += 1
        if seen[key] >= repeats:
            return t
    return None


def explain(agent, obs, world, name):
    """Every distinct id on the board: what the agent believes each action does to it."""
    rows = []
    for i in sorted(set(v for row in obs.grid for v in row)):
        b = {a: agent.belief(i, a, obs.hand if a == "TOGGLE" else 0) for a in world.acts}
        tried = {a: agent.E.get((i, a, obs.hand if a == "TOGGLE" else 0)) is not None for a in world.acts}
        rows.append({"thing": name(i), "count": agent.counts.get(i, 0), "sig": agent.sig(i),
                     "belief": b, "tested_here": tried})
    return rows


def run(family: str, n: int, seed0: int) -> dict:
    mem = B1.start_memory(1)
    cfg = Config()
    for e in CORRECTED:
        cfg = cfg.apply(e)
    mem = mem.reconfigure(cfg)
    report = {"family": family, "episodes": []}
    for i in range(n):
        w = B1.W.make_world(family, seed0 + i, "A2")
        ag = Tracer(source=mem)
        res = ag.run(w)
        name = namer(w)
        t = stuck_point(ag.steps)
        ep = {"seed": seed0 + i, "result": {k: res[k] for k in ("success", "harm", "steps", "wasted")},
              "stuck_at": t}
        acts = [(prim, None if it is None else (it[0], name(it[2]))) for _, prim, it in ag.steps]
        ep["intents"] = Counter(f"{a[1][0]}:{a[1][1]}" for a in acts if a[1]).most_common(12)
        if t is not None:
            obs = ag.steps[t][0]
            ep["hand"] = name(obs.hand)
            ep["last_actions"] = acts[max(0, t - 25):t + 1]
            ep["beliefs"] = explain(ag, obs, w, name)
        w.close()
        report["episodes"].append(ep)
    return report


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("family")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--seed0", type=int, default=7_000_000)
    a = ap.parse_args(argv)
    rep = run(a.family, a.n, a.seed0)
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"trace-{a.family}.json"
    p.write_text(json.dumps(rep, indent=1, default=str))
    ok = sum(e["result"]["success"] for e in rep["episodes"])
    stuck = sum(e["stuck_at"] is not None for e in rep["episodes"])
    print(f"{a.family}: success {ok}/{a.n}, stuck in a loop {stuck}/{a.n} -> {p}")


if __name__ == "__main__":
    main()
