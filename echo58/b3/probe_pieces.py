"""Dev check: play a family with some B v3 pieces on, learning online like the bench probe.

    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.b3.probe_pieces FAMILY [PIECE ...]
"""
from __future__ import annotations

import sys
from collections import Counter

from ..acumula import bench as B1
from ..acumula.config import Config
from ..acumula2 import bench as B2  # noqa: F401  (registers the v2 families)
from .policy import PAgent
from .trace import CORRECTED, namer

B1.W.MINIGRID["ObstructedMaze1Dlhb"] = "MiniGrid-ObstructedMaze-1Dlhb-v0"


class TPAgent(PAgent):
    def _decide(self, obs, world):
        prim, intent = super()._decide(obs, world)
        self.trace.append(intent)
        return prim, intent


def main(argv=None) -> None:
    argv = argv or sys.argv[1:]
    fam, pieces = argv[0], frozenset(argv[1:])
    cfg = Config()
    for e in CORRECTED:
        cfg = cfg.apply(e)
    mem = B1.start_memory(1).reconfigure(cfg).probe_copy()
    ag = TPAgent(source=mem, learn=mem, pieces=pieces)
    ok, sig, tops = 0, Counter(), Counter()
    for i in range(20):
        ag.trace = []
        w = B1.W.make_world(fam, 7_000_000 + i, "A2")
        r = ag.run(w)
        ok += r["success"]
        sig.update(r["signals"])
        if not r["success"]:
            name = namer(w)
            c = Counter(f"{it[0]}:{name(it[2])}" for it in ag.trace if it)
            tops[" + ".join(k for k, _ in c.most_common(2))] += 1
        w.close()
    print(f"{fam} {sorted(pieces) or '-'}: success {ok}/20 signals {dict(sig)} fails {dict(tops.most_common(4))}")


if __name__ == "__main__":
    main()
