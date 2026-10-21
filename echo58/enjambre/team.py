"""ENJAMBRE-1 (C v1): a team of ECHO agents with a private memory each and one global memory
written only through 16-byte WSP postcards (contract ENJAMBRE1-DESIGN.md §3-§4).

    private   each agent's own ConfMemory (layer 1 identity, layer 2 role), live while it plays
    global    append-only board of postcards; the view sums, per key, the latest postcard of
              each sender (resending adds no evidence) and speaks with the same lower bound
    notes     layer-1 entries of one world handed by postcard to an agent that comes to help
    remote    "entering id p changes a cell of id g elsewhere" (domain 2), counted against all
              entries of p; it travels in postcards and notes like the rest

A reader answers here (private l1 of the world it is in) -> private l1 -> private l2 -> notes ->
global. Integers only; no names.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

import navi10_wsp

from ..acumula.config import Config, ConfMemory, rule
from ..memx.memory import OUTCOMES, Memory

ACTS = ("ENTER", "PICK", "TOGGLE")
L2, L1, RM = 0, 1, 2                            # postcard `domain`: which layer the entry is


def best(counts: List[int]) -> Tuple[int, int, int]:
    """(outcome index, its count, total) of a count vector, as a postcard carries it."""
    o = max(range(len(OUTCOMES)), key=lambda k: (counts[k], -k))
    return o, counts[o], sum(counts)


def card(layer: int, sender: int, key: Tuple, counts: List[int]) -> bytes:
    o, n, total = best(counts) if layer != RM else (0, 0, 0)
    if layer == L2:
        sig, act, hand = key
        return navi10_wsp.pack(src=sig, rel=ACTS.index(act), dst=o, flags=hand, domain=L2,
                               generator=sender, slot=min(total, 255), seq=min(n, 255))
    if layer == RM:
        p, g = key
        return navi10_wsp.pack(src=p, dst=g, domain=RM, generator=sender, slot=min(counts[1], 255),
                               seq=min(counts[0], 255))
    ident, sig, act, hand = key
    return navi10_wsp.pack(src=ident, rel=ACTS.index(act), dst=o, flags=hand, domain=L1,
                           generator=sender, style=sig, slot=min(total, 255), seq=min(n, 255))


def read(raw: bytes) -> Tuple[int, int, Tuple, int, int, int]:
    """(layer, sender, key, outcome, count, total) of a postcard."""
    p = navi10_wsp.unpack(raw)
    x = p["ext"]
    if x["domain"] == RM:
        return RM, x["generator"], (p["src"], p["dst"]), 0, x["seq"], x["slot"]
    act = ACTS[p["rel"]]
    key = (p["src"], act, p["flags"]) if x["domain"] == L2 else (p["src"], x["style"], act, p["flags"])
    return x["domain"], x["generator"], key, p["dst"], x["seq"], x["slot"]


def as_counts(entries) -> List[int]:
    """Sum postcards (outcome, count, total) into a count vector: the rest of each total is
    booked as 'other' so the bound sees the full denominator."""
    c = [0] * (len(OUTCOMES) + 1)
    for o, n, total in entries:
        c[o] += n
        c[-1] += total - n
    return c


def bound(c: Optional[List[int]], n_min: int, pct: int) -> Optional[str]:
    if not c:
        return None
    named = c[:-1]
    total = sum(c)
    o = max(range(len(OUTCOMES)), key=lambda k: (named[k], -k))
    if named[o] >= n_min and named[o] * 100 >= pct * total:
        return OUTCOMES[o]
    bad = named[OUTCOMES.index("NOOP")] + named[OUTCOMES.index("HURT")]
    if bad >= n_min and bad * 100 >= pct * total:
        return "HURT"
    return None


class Board:
    """The global memory: an append-only list of postcards and its summed view."""

    def __init__(self):
        self.log: List[bytes] = []
        self.latest: Dict[Tuple, Dict[int, Tuple[int, int, int]]] = {}
        self.destroyed = 0

    def post(self, raw: bytes) -> None:
        assert len(raw) == navi10_wsp.WSP_BYTES
        self.log.append(raw)
        layer, sender, key, o, n, total = read(raw)
        self.latest.setdefault((layer, key), {})[sender] = (o, n, total)

    def view(self, shuffle_seed: Optional[int] = None) -> Dict[Tuple, List[int]]:
        """Summed counts per key. With a seed, the ids (layer 1, remote) and the layer-2 signatures
        are permuted among those seen: same entries, wrong keys."""
        v = {k: as_counts(s.values()) for k, s in self.latest.items()}
        if shuffle_seed is None:
            return v
        rng = random.Random(shuffle_seed)
        ids = sorted({i for (l, k) in v if l == L1 for i in (k[0], k[3]) if i} |
                     {i for (l, k) in v if l == RM for i in k})
        sigs = sorted({k[0] for (l, k) in v if l == L2})
        pid = dict(zip(ids, rng.sample(ids, len(ids))))
        psg = dict(zip(sigs, rng.sample(sigs, len(sigs))))
        out = {}
        for (l, k), c in v.items():
            if l == L2:
                k = (psg[k[0]],) + k[1:]
            elif l == L1:
                k = (pid[k[0]], k[1], k[2], pid.get(k[3], 0))
            else:
                k = (pid[k[0]], pid[k[1]])
            out[(l, k)] = c
        return out


class Private:
    """An agent's own memory, plus which world each of its observations came from."""

    def __init__(self):
        self.mem = ConfMemory(Config(), Memory())
        self.world: Optional[int] = None
        self.by_world: Dict[int, Dict[Tuple, List[int]]] = {}
        self.remote: Dict[Tuple, List[int]] = {}               # (p, g) -> [changes seen, entries of p]
        self.entries: Dict[int, int] = {}
        self.remote_world: Dict[int, Dict[Tuple, List[int]]] = {}
        self.entries_world: Dict[Tuple, int] = {}               # (world, p) -> entries of p there

    def remote_observe(self, p: int, changed) -> None:
        """One entry into id p, and the ids of the cells that changed elsewhere at that moment."""
        self.entries[p] = self.entries.get(p, 0) + 1
        self.entries_world[(self.world, p)] = self.entries_world.get((self.world, p), 0) + 1
        here = self.remote_world.setdefault(self.world, {})
        for g in changed:
            for d in (self.remote, here):
                d.setdefault((p, g), [0, 0])[0] += 1
        for d, n in ((self.remote, self.entries[p]), (here, self.entries_world[(self.world, p)])):
            for (q, g), c in d.items():
                if q == p:
                    c[1] = n

    def observe(self, ident: int, sig: int, act: str, hand: int, outcome: str) -> None:
        self.mem.observe(ident, sig, act, hand, outcome)
        k = self.mem.cfg.l1_key(ident, sig, act, hand)
        self.by_world.setdefault(self.world, {}).setdefault(k, [0] * len(OUTCOMES))[OUTCOMES.index(outcome)] += 1

    @property
    def destroyed(self) -> int:
        return self.mem.destroyed + self.mem.chain.destroyed

    def l2_cards(self, sender: int) -> List[bytes]:
        return [card(L2, sender, k, c) for k, c in sorted(self.mem.l2.items()) if len(k) == 3]

    def l1_cards(self, sender: int) -> List[bytes]:
        return [card(L1, sender, k, c) for k, c in sorted(self.mem.l1.items())]

    def remote_cards(self, sender: int) -> List[bytes]:
        return [card(RM, sender, k, c) for k, c in sorted(self.remote.items())]

    def notes_cards(self, sender: int, world: int) -> List[bytes]:
        return [card(L1, sender, k, c) for k, c in sorted(self.by_world.get(world, {}).items())] + \
               [card(RM, sender, k, c) for k, c in sorted(self.remote_world.get(world, {}).items())]


class Reader:
    """What one agent's policy asks: private l1 -> private l2 -> notes -> global (contract §3)."""

    def __init__(self, cfg: Config, private: Optional[Private], glob: Optional[Dict], notes: Dict,
                 world: Optional[int] = None):
        self.cfg, self.private, self.glob, self.notes = cfg, private, glob, notes
        self.here = private.by_world.setdefault(world, {}) if private is not None else {}
        self.last: Optional[Tuple] = None
        self.queries = self.hits = 0
        self.by_source = {"here": 0, "private": 0, "notes": 0, "global": 0}

    def recall(self, ident: int, sig: int, act: str, hand: int) -> Optional[str]:
        self.queries += 1
        b1, b2 = self.cfg.bounds[1], self.cfg.bounds[2]
        k1 = self.cfg.l1_key(ident, sig, act, hand)
        k2 = self.cfg.l2_key(sig, act, hand)
        asks = [("here", 1, k1, lambda: rule(self.here.get(k1), *b1))]
        if self.private is not None:
            asks += [("private", 1, k1, lambda: rule(self.private.mem.l1.get(k1), *b1)),
                     ("private", 2, k2, lambda: rule(self.private.mem.l2.get(k2), *b2))]
        asks.append(("notes", 1, k1, lambda: bound(self.notes.get(k1), *b1)))
        if self.glob is not None:
            asks.append(("global", 1, k1, lambda: bound(self.glob.get((L1, k1)), *b1)))
            asks.append(("global", 2, k2, lambda: bound(self.glob.get((L2, k2)), *b2)))
        self.last = None
        for src, layer, k, ask in asks:
            r = ask()
            if r is not None:
                self.hits += 1
                self.by_source[src] += 1
                self.last = (layer, k)
                return r
        return None

    def knows(self, p: int, g: int) -> bool:
        """Does entering id p change cells of id g (own remote memory, then notes, then global)?"""
        n_min, pct = self.cfg.bounds[1]
        sources = []
        if self.private is not None:
            c = self.private.remote.get((p, g))
            sources.append(None if c is None else [c[0], 0, 0, 0, 0, 0, c[1] - c[0]])
        sources.append(self.notes.get((RM, (p, g))))
        if self.glob is not None:
            sources.append(self.glob.get((RM, (p, g))))
        for c in sources:
            if c and c[0] >= n_min and c[0] * 100 >= pct * sum(c):
                return True
        return False
