"""A configuration says how a memory is read; edits change it, never the observations.

Signature bits (agent.py): 1|2 border, 4|8 size, 16 moves by itself,
32 commonest interior id, 64 second commonest. The base configuration reads
exactly like track A: layer 1 on (id, sig without size and rank), layer 2 on
(sig without rank, and without size when it moves by itself).

Edits (contract §2):
    silence(k)      layer-2 key k answers nothing
    verify(k)       a non-HURT answer of k is treated as unknown (test it here)
    refine(k, b)    layer-2 key k is split by signature bit b
    merge(b)        layer 2 ignores bit b for static things
    bound(l, n, p)  N_MIN and percent bound of layer l
    order           ask layer 2 before layer 1
Integers only.
"""
from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Optional, Tuple

from ..memx.memory import OUTCOMES, Memory

BORDER, SIZE, AUTO, RANK0, RANK1 = 0b11, 0b1100, 16, 32, 64
RANKS = RANK0 | RANK1
SPLIT_BITS = (1, 2, 4, 8, RANK0, RANK1)          # bits an edit may add back or drop
NMINS, PCTS = (2, 3, 5), (70, 85, 95)
HURT, NOOP = OUTCOMES.index("HURT"), OUTCOMES.index("NOOP")


class Config:
    def __init__(self):
        self.silence: set = set()
        self.verify: set = set()
        self.refine: Dict[Tuple, int] = {}            # coarse layer-2 key -> extra bits
        self.merge = 0                                 # bits dropped for static things
        self.bounds = {1: (3, 85), 2: (3, 85)}
        self.l2_first = False
        self.edits: List[Tuple] = []                   # accepted edits, in order

    def copy(self) -> "Config":
        c = Config()
        c.silence, c.verify, c.refine = set(self.silence), set(self.verify), dict(self.refine)
        c.merge, c.bounds, c.l2_first, c.edits = self.merge, dict(self.bounds), self.l2_first, list(self.edits)
        return c

    def apply(self, edit: Tuple) -> "Config":
        c = self.copy()
        kind = edit[0]
        if kind == "silence":
            c.silence.add(edit[1])
        elif kind == "verify":
            c.verify.add(edit[1])
        elif kind == "refine":
            c.refine[edit[1]] = c.refine.get(edit[1], 0) | edit[2]
        elif kind == "merge":
            c.merge |= edit[1]
        elif kind == "bound":
            c.bounds[edit[1]] = (edit[2], edit[3])
        elif kind == "order":
            c.l2_first = True
        else:
            raise ValueError(edit)
        c.edits.append(edit)
        return c

    def valid(self, edit: Tuple) -> bool:
        """An edit is valid if it changes something."""
        kind = edit[0]
        if kind == "silence":
            return edit[1] not in self.silence
        if kind == "verify":
            return edit[1] not in self.verify and edit[1] not in self.silence
        if kind == "refine":
            return not self.refine.get(edit[1], 0) & edit[2] and not coarse_bits(edit[1][0], self) & edit[2]
        if kind == "merge":
            return not self.merge & edit[1]
        if kind == "bound":
            return self.bounds[edit[1]] != (edit[2], edit[3])
        if kind == "order":
            return not self.l2_first
        return False

    def l1_key(self, ident: int, sig: int, act: str, hand: int) -> Tuple:
        return (ident, sig & (AUTO | BORDER), act, hand)

    def coarse(self, sig: int, act: str, hand: int) -> Tuple:
        s = sig & ~RANKS
        if s & AUTO:
            s &= ~SIZE
        else:
            s &= ~self.merge
        return (s, act, 1 if hand else 0)

    def l2_key(self, sig: int, act: str, hand: int) -> Tuple:
        k = self.coarse(sig, act, hand)
        extra = self.refine.get(k, 0)
        return k if not extra else (k[0] | (sig & extra), act, k[2], extra)

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.edits, sort_keys=True, default=list).encode()).hexdigest()[:12]


def coarse_bits(s: int, cfg: Config) -> int:
    """Bits a coarse layer-2 signature already carries."""
    present = BORDER | (0 if s & AUTO else SIZE)
    return present & ~cfg.merge


def rule(counts: Optional[List[int]], n_min: int, pct: int) -> Optional[str]:
    """Track A's lower-bound rule, with its conservative 'cannot go there' fallback."""
    if not counts:
        return None
    best = max(range(len(OUTCOMES)), key=lambda k: (counts[k], -k))
    n, total = counts[best], sum(counts)
    if n >= n_min and n * 100 >= pct * total:
        return OUTCOMES[best]
    bad = counts[NOOP] + counts[HURT]
    if bad >= n_min and bad * 100 >= pct * total:
        return "HURT"
    return None


class ConfMemory:
    """Raw observations (append-only, chained in a Memory) read through a Config."""

    def __init__(self, cfg: Config, chain: Optional[Memory] = None):
        self.cfg = cfg
        self.chain = chain                      # None for throw-away copies (probe)
        self.raw: List[Tuple] = []
        self.l1: Dict[Tuple, List[int]] = {}
        self.l2: Dict[Tuple, List[int]] = {}
        self.last: Optional[Tuple] = None       # (layer, key) that answered the last recall
        self.queries = self.hits = 0
        self.destroyed = 0
        self.surprises: Optional[List[Tuple]] = None   # set to [] to log prediction errors

    def _index(self, rec: Tuple) -> None:
        i, s, a, h, o = rec
        k = OUTCOMES.index(o)
        self.l1.setdefault(self.cfg.l1_key(i, s, a, h), [0] * len(OUTCOMES))[k] += 1
        self.l2.setdefault(self.cfg.l2_key(s, a, h), [0] * len(OUTCOMES))[k] += 1

    def observe(self, ident: int, sig: int, act: str, hand: int, outcome: str) -> None:
        if self.surprises is not None:              # δ: the rule that held said something else
            k2 = self.cfg.l2_key(sig, act, hand)
            said = rule(self.l2.get(k2), *self.cfg.bounds[2])
            if said is not None and said != outcome and k2 not in self.cfg.silence:
                self.surprises.append((2, k2, outcome))
        rec = (ident, sig, act, hand, outcome)
        self.raw.append(rec)
        self._index(rec)
        if self.chain is not None:
            self.chain.observe(*rec)

    def reconfigure(self, cfg: Config) -> "ConfMemory":
        """Same observations, read through another configuration (shares the chain)."""
        m = ConfMemory(cfg, self.chain)
        m.raw = self.raw
        for rec in self.raw:
            m._index(rec)
        return m

    def probe_copy(self) -> "ConfMemory":
        m = ConfMemory(self.cfg, None)
        m.raw = list(self.raw)
        m.l1 = {k: list(c) for k, c in self.l1.items()}
        m.l2 = {k: list(c) for k, c in self.l2.items()}
        return m

    def _layer2(self, sig, act, hand):
        k = self.cfg.l2_key(sig, act, hand)
        if k in self.cfg.silence:
            return None, k
        r = rule(self.l2.get(k), *self.cfg.bounds[2])
        if r is not None and r != "HURT" and k in self.cfg.verify:
            return None, k
        return r, k

    def recall(self, ident: int, sig: int, act: str, hand: int) -> Optional[str]:
        self.queries += 1
        k1 = self.cfg.l1_key(ident, sig, act, hand)
        layers = ((2, None), (1, k1)) if self.cfg.l2_first else ((1, k1), (2, None))
        self.last = None
        for layer, k in layers:
            if layer == 1:
                r = rule(self.l1.get(k), *self.cfg.bounds[1])
            else:
                r, k = self._layer2(sig, act, hand)
            if r is not None:
                self.hits += 1
                self.last = (layer, k)
                return r
        return None
