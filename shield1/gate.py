"""SHIELD-1 integer core: a risk gate on top of a blind proposer (docs/SHIELD1-DESIGN.md).

Everything here is int: closeness 0..100 per lidar bin, tiers, counts,
risk in percent. Floats live only at the boundary (shield1/run.py turns the
simulator's lidar into ints and a heading into actuator commands).

A proposer (blind goal seeker) names the heading it wants. The gate ranks
all headings lexicographically -- (danger, distance from the proposed
heading) -- and answers OK (keep it), MODIFY (the nearest safe heading) or
BLOCK (brake: momentum carries the robot into danger, or no heading is
safe; it turns to the least dangerous heading while braking). Reward never
buys risk back: safety is compared first, progress only among equals.

What is dangerous:
  ECHO-P (prior)   told which lidar channels cost; contact assumed at the top tier.
  ECHO-L (learned) not told. Per channel and tier it counts steps and steps
                   with cost; a channel "hurts at tier t" once, over n >= MIN_N
                   steps at t, k - isqrt(n) of them still are HURT percent. Tables start
                   at 0; until something hurts the gate says OK to everything.
Both then keep the same geometric margin: a heading is dangerous when a
hurting channel reads within MARGIN tiers of its contact tier in the cone
around that heading (the cone widens as things get close).
"""

from __future__ import annotations

from math import isqrt
from typing import Dict, List, Optional, Sequence, Tuple

BINS = 16
EDGES = (50, 65, 75, 82, 88, 93)  # closeness 0..100 -> tier 0..6; 93 = inside a 0.2 m hazard (lidar 3 m)
TIERS = len(EDGES) + 1
MARGIN = 3           # danger starts this many tiers before contact
MIN_N = 10           # observations of a (channel, tier) before it can hurt
HURT = 50            # percent of steps with cost at a tier that make it "contact",
                     # judged on the lower bound k - isqrt(n) (few samples cannot hurt)
OK, MODIFY, BLOCK = 0, 1, 2


def tier(closeness: int) -> int:
    return sum(closeness >= e for e in EDGES)


def ang(a: int, b: int) -> int:
    d = (a - b) % BINS
    return min(d, BINS - d)


def width(closeness: int) -> int:
    """Bins a reading spreads over: a 0.2 m disc covers more angle up close."""
    return 1 if closeness < 82 else (2 if closeness < 88 else 3)


def heading_closeness(chan: Sequence[int], h: int) -> int:
    """Closest reading whose angular spread covers heading h."""
    return max((q for b, q in enumerate(chan) if ang(b, h) <= width(q)), default=0)


class HurtTable:
    """Per channel, per tier of its closest reading: steps seen, steps with cost."""

    def __init__(self, channels: Sequence[str]):
        self.channels = tuple(channels)
        self.n = {c: [0] * TIERS for c in self.channels}
        self.k = {c: [0] * TIERS for c in self.channels}

    def observe(self, lid: Dict[str, Sequence[int]], cost: int) -> None:
        for c in self.channels:
            t = tier(max(lid[c]))
            self.n[c][t] += 1
            self.k[c][t] += cost

    def rate(self, c: str, t: int) -> int:
        n = self.n[c][t]
        return -1 if n < MIN_N else self.k[c][t] * 100 // n

    def hurts(self, c: str, t: int) -> bool:
        n, k = self.n[c][t], self.k[c][t]
        return n >= MIN_N and (k - isqrt(n)) * 100 >= HURT * n

    def contact(self, c: str) -> Optional[int]:
        """Lowest tier at which channel c hurts, None if it never has."""
        for t in range(TIERS):
            if self.hurts(c, t):
                return t
        return None

    def snapshot(self) -> Dict[str, List[int]]:
        return {c: [self.rate(c, t) for t in range(TIERS)] for c in self.channels}


class Gate:
    def __init__(self, channels: Sequence[str], mode: str, costly: Sequence[str] = (),
                 margin: int = MARGIN):
        assert mode in ("learned", "prior")
        self.mode = mode
        self.margin = margin
        self.channels = tuple(channels)
        self.costly = tuple(costly)
        self.table = HurtTable(channels)
        self.learning = mode == "learned"
        self.counts = [0, 0, 0]

    def danger_tiers(self) -> Dict[str, int]:
        """Channel -> first tier counted as danger."""
        if self.mode == "prior":
            return {c: TIERS - 1 - self.margin for c in self.costly}
        out = {}
        for c in self.channels:
            t = self.table.contact(c)
            if t is not None:
                out[c] = max(t - self.margin, 0)
        return out

    def _danger(self, lid: Dict[str, Sequence[int]], h: int, dt: Dict[str, int]) -> int:
        """How deep into danger heading h is: 0 = safe, else tiers past the line + 1."""
        d = 0
        for c, t0 in dt.items():
            t = tier(heading_closeness(lid[c], h))
            if t >= t0:
                d = max(d, t - t0 + 1)
        return d

    def decide(self, lid: Dict[str, Sequence[int]], proposed: int,
               move: Optional[int]) -> Tuple[int, bool, int]:
        """move: lidar bin the velocity points to (None when nearly still).
        Returns (heading, brake, verdict)."""
        dt = self.danger_tiers()
        if not dt:
            self.counts[OK] += 1
            return proposed, False, OK
        scored = [(self._danger(lid, h, dt), ang(h, proposed), h) for h in range(BINS)]
        best = min(scored)
        moving_into = move is not None and self._danger(lid, move, dt) > 0
        if best[0] or moving_into:
            verdict = BLOCK
        elif best[2] == proposed:
            verdict = OK
        else:
            verdict = MODIFY
        self.counts[verdict] += 1
        return best[2], verdict == BLOCK, verdict

    def observe(self, lid: Dict[str, Sequence[int]], cost: int) -> None:
        """After each env step: the lidar it produced and whether it cost."""
        if self.learning:
            self.table.observe(lid, cost)
