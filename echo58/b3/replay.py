"""B v3 investigation: rebuild the `recursiva` arm of ACUMULA-2 dev round by round and trace its probe
exactly as the bench plays it (each family on a throw-away copy, learning online over the 30 seeds).

    PYTHONPATH=. echoai/simulation/.venv-sandbox/bin/python -m echoai.echo58.b3.replay [--macro 1]

Checks itself against the dev JSON (failed per family per round must match) before explaining anything.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

from ..acumula import bench as B1
from ..acumula.config import Config
from ..acumula.diagnose import candidates
from ..acumula2 import bench as B2
from .probe_fixes import Fixed
from .trace import OUT, Tracer, namer, stuck_point

DEV = B2.LAB / "dev-20261020T183421.json"


def traced_probe(mem, fam, sd, fixes=()):
    cp = mem.probe_copy()
    ag = Fixed(source=cp, learn=cp) if fixes else Tracer(source=cp, learn=cp)
    ag.fixes = fixes
    eps = []
    for s in sd["probe"]:
        ag.steps = []
        w = B1.W.make_world(fam, s, "A2")
        r = ag.run(w)
        name = namer(w)
        ep = {"seed": s, "success": r["success"], "harm": r["harm"], "steps": r["steps"]}
        if not r["success"]:
            c = Counter(f"{it[0]}:{name(it[2])}" for _, _, it in ag.steps if it)
            ep["top"] = c.most_common(4)
            ep["stuck_at"] = stuck_point(ag.steps, repeats=6)
            ep["last"] = [(p, None if it is None else (it[0], name(it[2]), it[3] and name(it[3])))
                          for _, p, it in ag.steps[-20:]]
        w.close()
        eps.append(ep)
    return eps


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--macro", type=int, default=1)
    ap.add_argument("--fix", nargs="*", default=[], help="probe-only fixes (lab): loop, handkey")
    a = ap.parse_args(argv)
    m = a.macro
    ref = next(x for x in json.load(open(DEV))["runs"] if x["arm"] == "recursiva" and x["macro"] == m)
    sd = B2.seeds("dev", m)
    cfg, mem = Config(), B1.start_memory(m)
    out = {"macro": m, "rounds": {}}
    for r in range(0, B2.ROUNDS + 1):
        if r:
            ag = B2.XAgent(source=mem, learn=mem)
            failures = []
            mem.surprises = []
            for s in sd["round"][r]:
                for f in B2.MIX:
                    failures += B1.play(ag, f, s).pop("failures")
            failures += mem.surprises
            mem.surprises = None
            cfg, mem, acc = B2.accept(candidates(failures, cfg, mem.raw)[:B2.K], cfg, mem, sd["val"][r])
        rows = {}
        for f in B2.PROBE["dev"]:
            eps = traced_probe(mem, f, sd, tuple(a.fix))
            failed = sum(not e["success"] for e in eps)
            want = ref["probe"][str(r)][f]["failed"]
            rows[f] = {"failed": failed, "matches_dev": failed == want,
                       "failures": [e for e in eps if not e["success"]]}
            print(f"r{r} {f}: failed {failed} (dev {want})", flush=True)
        out["rounds"][r] = {"edits": [repr(e) for e in cfg.edits], "probe": rows}
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / (f"replay-m{m}" + "".join("-" + x for x in a.fix) + ".json")
    p.write_text(json.dumps(out, indent=1, default=str))
    print("->", p)


if __name__ == "__main__":
    main()
