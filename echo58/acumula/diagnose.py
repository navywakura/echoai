"""From measured failures to candidate edits (contract §3), and the full menu for the random arm."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List, Tuple

from .config import NMINS, PCTS, SPLIT_BITS, Config


def blame(failures: List[Tuple]) -> Counter:
    """How many failures each (layer, key) explains."""
    return Counter((layer, key) for layer, key, _ in failures)


def best_split(key: Tuple, cfg: Config, raw: List[Tuple]) -> int:
    """The signature bit that best separates the outcomes seen under a layer-2 key (0 if none helps).

    Purity = sum over the two halves of the count of their commonest outcome; integers only.
    """
    coarse = key if len(key) == 3 else key[:3]
    recs = [(s, o) for i, s, a, h, o in raw if cfg.l2_key(s, a, h) == key]
    if not recs:
        return 0

    def purity(groups):
        return sum(max(Counter(g).values()) for g in groups if g)

    base = purity([[o for _, o in recs]])
    best, gain = 0, 0
    for b in SPLIT_BITS:
        if not cfg.valid(("refine", coarse, b)):
            continue
        p = purity([[o for s, o in recs if s & b], [o for s, o in recs if not s & b]])
        if p - base > gain:
            best, gain = b, p - base
    return best


def candidates(failures: List[Tuple], cfg: Config, raw: List[Tuple]) -> List[Tuple]:
    """Edits that touch the rules that misled, most-blamed key first within each tier.

    Tiers: split by the bit that best separates its outcomes, verify, silence;
    then merge, only for a bit shared by >= 2 blamed keys.
    """
    by_key = [key for (layer, key), _ in blame(failures).most_common() if layer == 2]
    out: List[Tuple] = []

    def add(edit):
        if cfg.valid(edit) and edit not in out:
            out.append(edit)

    if any(layer == 1 for layer, _, _ in failures):
        add(("order",))
    for key in by_key:
        b = best_split(key, cfg, raw)
        if b:
            add(("refine", key if len(key) == 3 else key[:3], b))
    for key in by_key:
        add(("verify", key))
    for key in by_key:
        add(("silence", key))
    bits = Counter(b for key in by_key for b in (1, 2, 4, 8) if key[0] & b)
    for b, nkeys in bits.most_common():
        if nkeys >= 2:
            add(("merge", b))
    return out


def menu(cfg: Config, l2_keys) -> List[Tuple]:
    """Every valid edit over the layer-2 keys the memory has (what the random arm draws from)."""
    out = []
    for key in sorted(l2_keys, key=repr):
        coarse = key if len(key) == 3 else key[:3]
        out += [("silence", key), ("verify", key)] + [("refine", coarse, b) for b in SPLIT_BITS]
    out += [("merge", b) for b in (1, 2, 4, 8)]
    out += [("bound", l, n, p) for l in (1, 2) for n in NMINS for p in PCTS]
    out.append(("order",))
    seen, valid = set(), []
    for e in out:
        if e not in seen and cfg.valid(e):
            seen.add(e)
            valid.append(e)
    return valid
