"""Track A's agent, plus two rank bits in the signature and a log of which rule misled it.

The rank bits (32: the commonest interior id, 64: the second commonest) are
hidden by the base configuration, so with it this agent plays exactly like
track A's. Integers only; no names anywhere.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from ..memx.agent import Agent
from .config import RANK0, RANK1


class XAgent(Agent):
    def run(self, world, max_steps: int = 100000, frames=None) -> Dict:
        self.why: Dict[Tuple, Tuple] = {}          # (id, act, hand) -> (layer, key) that answered
        self.failures: List[Tuple] = []            # (layer, key, outcome) of beliefs that failed
        r = super().run(world, max_steps, frames)
        r["failures"] = self.failures
        return r

    def _scan(self, grid) -> None:
        super()._scan(grid)
        H, W = len(grid), len(grid[0])
        inner: Dict[int, int] = {}
        for y in range(1, H - 1):
            for x in range(1, W - 1):
                inner[grid[y][x]] = inner.get(grid[y][x], 0) + 1
        top = sorted(inner, key=lambda i: (-inner[i], i))
        self.rank = {i: RANK0 if n == 0 else RANK1 for n, i in enumerate(top[:2])}

    def sig(self, ident: int) -> int:
        s = self.sig_cache.get(ident)
        if s is None:
            s = self.sig_cache[ident] = super().sig(ident) | self.rank.get(ident, 0)
        return s

    def belief(self, ident: int, act: str, hand: int):
        key = (ident, act, hand)
        fresh = key not in self.belief_cache and not self.E.get(key) and self.source is not None
        b = super().belief(ident, act, hand)
        if fresh and b is not None and getattr(self.source, "last", None) is not None:
            self.why[key] = self.source.last
        return b

    def _outcome(self, old, new, intent) -> str:
        out = Agent._outcome(old, new, intent)
        act, _, ident, hand, _ = intent
        key = (ident, act, hand)
        if out in ("HURT", "NOOP") and key in self.why and key not in self.E:
            layer, k = self.why[key]
            self.failures.append((layer, k, out))
        return out
