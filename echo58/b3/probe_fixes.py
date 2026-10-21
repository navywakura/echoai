"""B v3 investigation: switch on generic policy fixes one at a time and see what the next obstacle is.

    PYTHONPATH=. echoai/ECHO-5/.venv-sandbox/bin/python -m echoai.echo58.b3.probe_fixes FAMILY [FIX ...]

Fixes (generic, nameless; candidates for a B v3 policy-edit menu):
    loop     a state seen 3 times means the intent pursued there does nothing: believe NOOP for this episode
    handkey  an attempt to pick while holding is booked under the key the policy checks (hand 0)
"""
from __future__ import annotations

import sys
from collections import Counter

from ..acumula import bench as B1
from ..acumula.config import Config
from ..memx.agent import Agent
from .trace import CORRECTED, Tracer, namer, stuck_point


class Fixed(Tracer):
    fixes: tuple = ()

    def run(self, world, max_steps: int = 100000, frames=None):
        self.seen = Counter()
        self.banned = set()
        return super().run(world, max_steps, frames)

    def belief(self, ident, act, hand):
        if (ident, act, hand) in getattr(self, "banned", ()):
            return "NOOP"
        return super().belief(ident, act, hand)

    def _decide(self, obs, world):
        if "loop" in self.fixes:
            key = (obs.pos, obs.dir, obs.hand, obs.grid)
            self.seen[key] += 1
            if self.seen[key] >= 3 and self.steps:
                last = [it for _, _, it in self.steps[-12:] if it is not None and it[0] != "DROP"]
                for it in last:
                    self.banned.add((it[2], it[0], it[3]))
                self.belief_cache = {}
                self.seen[key] = 0
        return super()._decide(obs, world)

    def _outcome(self, old, new, intent):
        out = super()._outcome(old, new, intent)
        if "handkey" in self.fixes and intent[0] == "PICK" and intent[3]:
            self.E.setdefault((intent[2], "PICK", 0), [0] * 6)[["PASS", "NOOP", "HURT", "GOAL", "PICK", "OPEN"].index(out)] += 1
        return out


def main(argv=None) -> None:
    argv = argv or sys.argv[1:]
    fam, fixes = argv[0], tuple(argv[1:])
    mem = B1.start_memory(1)
    cfg = Config()
    for e in CORRECTED:
        cfg = cfg.apply(e)
    mem = mem.reconfigure(cfg)
    ok, stuck, tops = 0, 0, Counter()
    for i in range(10):
        w = B1.W.make_world(fam, 7_000_000 + i, "A2")
        ag = Fixed(source=mem)
        ag.fixes = fixes
        r = ag.run(w)
        name = namer(w)
        ok += r["success"]
        t = stuck_point(ag.steps, repeats=6)
        if not r["success"]:
            stuck += t is not None
            c = Counter(f"{it[0]}:{name(it[2])}" for _, _, it in ag.steps if it)
            tops[" + ".join(k for k, _ in c.most_common(2))] += 1
        w.close()
    print(f"{fam} fixes={fixes or '-'}: success {ok}/10; failures by top intents: {dict(tops)}")


if __name__ == "__main__":
    main()
