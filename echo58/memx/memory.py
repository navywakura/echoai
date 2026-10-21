"""MEMORIA-X: integer consequence memory, append-only on disk.

Two layers of counters, both keyed by what the agent can see:

    layer 1  (id, sig sans size, act, hand) -> outcome counts identity
    layer 2  (sig, act, hand != 0)       -> outcome counts   role

`sig` is the observable signature of an id (does it move by itself, how many
cells it covers, how much of it lies on the border). A rule speaks only when
its lower bound holds:

    n_best >= n_min  and  n_best * 100 >= pct * n_total

A contradiction raises n_total and silences the rule; nothing is erased
(destroyed == 0). On disk every observation is one JSON line chained by
SHA-256, so a memory is its own receipt. Integers only.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

OUTCOMES = ("PASS", "NOOP", "HURT", "GOAL", "PICK", "OPEN")
N_MIN = 3
PCT = 85
GENESIS = "0" * 64


def l1_key(ident: int, sig: int, act: str, hand: int) -> Tuple:
    return (ident, sig & ~0b1100, act, hand)    # identity: size-free (moves by itself? on the border?)


def l2_key(sig: int, act: str, hand: int) -> Tuple:
    if sig & 16:                                # what moves by itself: size-free (amendment 2)
        sig &= ~0b1100
    return (sig, act, 1 if hand else 0)


class Memory:
    def __init__(self, n_min: int = N_MIN, pct: int = PCT):
        self.n_min = n_min
        self.pct = pct
        self.l1: Dict[Tuple, List[int]] = {}
        self.l2: Dict[Tuple, List[int]] = {}
        self.records: List[dict] = []
        self.head = GENESIS
        self.destroyed = 0
        self.queries = 0
        self.hits = 0

    # -- learning ---------------------------------------------------------
    def observe(self, ident: int, sig: int, act: str, hand: int, outcome: str) -> None:
        o = OUTCOMES.index(outcome)
        self.l1.setdefault(l1_key(ident, sig, act, hand), [0] * len(OUTCOMES))[o] += 1
        self.l2.setdefault(l2_key(sig, act, hand), [0] * len(OUTCOMES))[o] += 1
        rec = {"i": ident, "s": sig, "a": act, "h": hand, "o": outcome, "prev": self.head}
        self.head = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
        rec["sha"] = self.head
        self.records.append(rec)

    # -- recall -------------------------------------------------------------
    def _rule(self, counts: Optional[List[int]]) -> Optional[str]:
        if not counts:
            return None
        best = max(range(len(OUTCOMES)), key=lambda k: (counts[k], -k))
        n, total = counts[best], sum(counts)
        if n >= self.n_min and n * 100 >= self.pct * total:
            return OUTCOMES[best]
        bad = counts[OUTCOMES.index("NOOP")] + counts[OUTCOMES.index("HURT")]
        if bad >= self.n_min and bad * 100 >= self.pct * total:
            return "HURT"                       # "cannot go there" holds even if how it fails varies
        return None

    def recall(self, ident: int, sig: int, act: str, hand: int) -> Optional[str]:
        self.queries += 1
        r = self._rule(self.l1.get(l1_key(ident, sig, act, hand)))
        if r is None:
            r = self._rule(self.l2.get(l2_key(sig, act, hand)))
        if r is not None:
            self.hits += 1
        return r

    # -- variants for the control arms ------------------------------------
    def with_bound(self, n_min: int, pct: int) -> "Memory":
        m = Memory(n_min, pct)
        m.l1, m.l2, m.records, m.head = self.l1, self.l2, self.records, self.head
        return m

    def shuffled(self, seed: int) -> "Memory":
        """Same entries, keys permuted: ids among ids, signatures among signatures."""
        rng = random.Random(seed)
        ids = sorted({k[0] for k in self.l1} | {k[3] for k in self.l1 if k[3]})
        s1 = sorted({k[1] for k in self.l1})               # layer-1 sigs are already size-free
        s2 = sorted({k[0] for k in self.l2})
        pid = dict(zip(ids, rng.sample(ids, len(ids))))
        p1 = dict(zip(s1, rng.sample(s1, len(s1))))
        p2 = dict(zip(s2, rng.sample(s2, len(s2))))
        m = Memory(self.n_min, self.pct)
        for (i, s, a, h), c in self.l1.items():
            m.l1[l1_key(pid[i], p1[s], a, pid.get(h, 0))] = list(c)
        for (s, a, h), c in self.l2.items():
            m.l2[(p2[s], a, h)] = list(c)
        m.head = self.head
        return m

    def without_auto(self) -> "Memory":
        """Same memory minus everything learned about things that move by themselves."""
        m = Memory(self.n_min, self.pct)
        m.l1 = {k: list(c) for k, c in self.l1.items() if not k[1] & 16}
        m.l2 = {k: list(c) for k, c in self.l2.items() if not k[0] & 16}
        m.head = self.head
        return m

    def rules(self) -> Dict[str, int]:
        out = {"l1_keys": len(self.l1), "l2_keys": len(self.l2), "l1_rules": 0, "l2_rules": 0}
        out["l1_rules"] = sum(self._rule(c) is not None for c in self.l1.values())
        out["l2_rules"] = sum(self._rule(c) is not None for c in self.l2.values())
        return out

    # -- disk -----------------------------------------------------------------
    def save(self, path: Path) -> str:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(f"{path}: memories are append-only, never overwritten")
        with path.open("w") as f:
            for r in self.records:
                f.write(json.dumps(r, sort_keys=True) + "\n")
        return self.head

    @classmethod
    def load(cls, path: Path, n_min: int = N_MIN, pct: int = PCT) -> "Memory":
        m = cls(n_min, pct)
        prev = GENESIS
        with Path(path).open() as f:
            for line in f:
                r = json.loads(line)
                sha = r.pop("sha")
                if r["prev"] != prev or hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest() != sha:
                    raise ValueError(f"{path}: broken chain at record {len(m.records)}")
                m.observe(r["i"], r["s"], r["a"], r["h"], r["o"])
                prev = sha
        return m

    def postcards(self) -> Iterable[bytes]:
        """Each active layer-2 rule as one 16-byte WSP postcard (for track C)."""
        import navi10_wsp
        for (sig, act, hand), c in sorted(self.l2.items()):
            r = self._rule(c)
            if r is None:
                continue
            yield navi10_wsp.pack(src=sig & 0xFF, rel=("ENTER", "PICK", "TOGGLE").index(act),
                                  dst=OUTCOMES.index(r), E={}, flags=hand,
                                  slot=min(sum(c), 255), seq=min(max(c), 255))
