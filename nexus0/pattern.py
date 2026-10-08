"""
PATTERN-0 — a temporal regularity that one-step T cannot see.

`World` answers T(s, a) → s'. That is one step, and one step is sometimes
not enough: the same slot under the same action can have two successors,
and which one arrives depends on where the body came from. T is not wrong
about that — it is blind to it by construction, and its KCC keeps the
incumbent, so it answers one of the two and is right about half the time.

This is the smallest thing that can see it: a context of order two.

    (slot_anterior, slot_actual, acción) → slot_siguiente

An **extension** of the predictor, not a second brain and not a
replacement. It never writes `World.pred/n/alt`, it holds no WSP, no
kind, no reward and no fact — CAM already holds what happened — and it
takes no turn, no clock and no name of any world. Integers in, an integer
or `None` out.

What it costs is declared and constant. A fixed open-addressed table of
`capacity` entries, five parallel integer lists, linear probing, and no
growth of any kind: no dict that gets bigger with the run, no LRU, no
eviction, no silent overwrite. When it is full and a new context arrives,
the context is **dropped and counted**. A memory that quietly forgot in
order to look like it remembered would be the one thing this slice is
supposed to rule out.

Two thresholds, both declared before any exam:

    min_hits    a context seen once is a coincidence, not a rule
    alt_n == 0  a rule that has ever been contradicted is held, and not
                offered — `predict()` returns None for it

Same KCC discipline as `World`: a contradicting successor becomes the
alternative and only displaces the incumbent by strictly beating its
count. Counters saturate rather than wrap.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Tuple

from echoai.nexus0.constants import N_SLOTS, UNKNOWN_NEXT

# Declared, constant, and reported. 512 contexts of 5 integers each.
PATTERN_CAPACITY = 512
# One observation is a coincidence. Fixed here, before any exam is run,
# and never chosen from an exam's result.
PATTERN_MIN_HITS = 2
# How far back the context reaches. Two: the previous slot and this one.
PATTERN_ORDER = 2

EMPTY_KEY = -1
SATURATE = 65535
_ACTION_BITS = 4
_SLOT_BITS = 12


def context_key(prev: int, cur: int, action: int) -> int:
    """One integer per context. Exact: 12 + 12 + 4 bits, no collision.

    CAM has 4096 slots and no world here has more than sixteen gears, so
    the three fields pack without overlapping and the key is the context
    rather than a hash of it.
    """
    return (((int(prev) & 0xFFF) << (_SLOT_BITS + _ACTION_BITS))
            | ((int(cur) & 0xFFF) << _ACTION_BITS)
            | (int(action) & 0xF))


class PatternMemory:
    """Order-2 contexts, fixed capacity, integers only."""

    def __init__(self, capacity: int = PATTERN_CAPACITY,
                 min_hits: int = PATTERN_MIN_HITS) -> None:
        if int(capacity) <= 0:
            raise ValueError("una memoria de capacidad cero no es una memoria")
        self.capacity = int(capacity)
        self.min_hits = int(min_hits)
        self.order = PATTERN_ORDER
        self.key: List[int] = [EMPTY_KEY] * self.capacity
        self.pred: List[int] = [UNKNOWN_NEXT] * self.capacity
        self.n: List[int] = [0] * self.capacity
        self.alt: List[int] = [UNKNOWN_NEXT] * self.capacity
        self.alt_n: List[int] = [0] * self.capacity
        self.size = 0
        # Contexts the table had no room for. Counted, never forgotten in
        # silence: a full memory says so instead of pretending.
        self.dropped = 0
        self.conflicts = 0
        # Every call to observe(). The exam has to make none of these.
        self.observations = 0

    # --- the table ------------------------------------------------------
    def _find(self, key: int, create: bool = False) -> int:
        """Linear probing over a table that never grows. -1 if absent."""
        start = key % self.capacity
        for step in range(self.capacity):
            i = (start + step) % self.capacity
            if self.key[i] == key:
                return i
            if self.key[i] == EMPTY_KEY:
                if not create:
                    return -1
                self.key[i] = key
                self.size += 1
                return i
        return -1

    def observe(self, prev: int, cur: int, action: int, nxt: int) -> None:
        """One transition, in context. KCC, saturating, never overwriting."""
        self.observations += 1
        nxt = int(nxt) & (N_SLOTS - 1)
        i = self._find(context_key(prev, cur, action), create=True)
        if i < 0:
            # Full, and this context is new. It is not remembered and the
            # table says so; nothing already in it is touched.
            self.dropped += 1
            return
        if self.pred[i] == UNKNOWN_NEXT:
            self.pred[i] = nxt
            self.n[i] = 1
            return
        if self.pred[i] == nxt:
            if self.n[i] < SATURATE:
                self.n[i] += 1
            return
        self.conflicts += 1
        if self.alt[i] != nxt:
            if self.alt[i] == UNKNOWN_NEXT or self.alt_n[i] == 0:
                self.alt[i] = nxt
                self.alt_n[i] = 1
            else:
                return  # a third successor: counted as a conflict, not kept
        elif self.alt_n[i] < SATURATE:
            self.alt_n[i] += 1
        if self.alt_n[i] > self.n[i]:
            self.pred[i], self.alt[i] = self.alt[i], self.pred[i]
            self.n[i], self.alt_n[i] = self.alt_n[i], self.n[i]

    # --- what it will say -----------------------------------------------
    def mature(self, prev: int, cur: int, action: int) -> bool:
        i = self._find(context_key(prev, cur, action))
        if i < 0 or self.pred[i] == UNKNOWN_NEXT:
            return False
        return self.n[i] >= self.min_hits and self.alt_n[i] == 0

    def predict(self, prev: int, cur: int, action: int) -> Optional[int]:
        """The successor this context has always had, or None.

        None until `min_hits`, and None for ever after a contradiction:
        the memory answers where it has a rule and stands aside where it
        has only a memory. No turn, no clock, no world in the signature.
        """
        i = self._find(context_key(prev, cur, action))
        if i < 0 or self.pred[i] == UNKNOWN_NEXT:
            return None
        if self.n[i] < self.min_hits or self.alt_n[i] > 0:
            return None
        return int(self.pred[i])

    def hits(self, prev: int, cur: int, action: int) -> int:
        i = self._find(context_key(prev, cur, action))
        return 0 if i < 0 else int(self.n[i])

    def entries(self) -> List[Tuple[int, int, int, int, int, int]]:
        """(key, pred, n, alt, alt_n, index) for every occupied slot."""
        return [(self.key[i], self.pred[i], self.n[i], self.alt[i],
                 self.alt_n[i], i)
                for i in range(self.capacity) if self.key[i] != EMPTY_KEY]

    def mature_counts(self) -> Dict[int, int]:
        """Frequency of every context that has reached a rule."""
        out: Dict[int, int] = {}
        for key, pred, n, _alt, alt_n, _i in self.entries():
            if pred != UNKNOWN_NEXT and n >= self.min_hits and alt_n == 0:
                out[key] = int(n)
        return out

    def snapshot_hash(self) -> str:
        """Every integer that decides an answer. Not the fast path."""
        blob = repr([self.capacity, self.min_hits, self.key, self.pred,
                     self.n, self.alt, self.alt_n]).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()


class ContextPredictor:
    """T first, context second — or rather the other way round, explicitly.

    The composition is the whole integration PATTERN-0 asks for: where the
    context has a mature rule it answers, and everywhere else the answer
    falls through to `World.predict` unchanged. It holds no state, writes
    to neither, and is opt-in — no `Agent` builds one.
    """

    def __init__(self, world, memory: PatternMemory) -> None:
        self.world = world
        self.memory = memory

    def predict(self, prev: int, cur: int, action: int):
        """Return (successor or None, which of the two answered)."""
        hit = self.memory.predict(prev, cur, action)
        if hit is not None:
            return hit, "pattern"
        return self.world.predict(cur, action), "t"
