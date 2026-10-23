"""MEMORIA-X: predictions P1-P5 from lab/echo58/memx/exam/m*.json (contract §5, amendment 1).

    PYTHONPATH=/home/user/REALRXOS/RXos python3 -m echoai.echo58.memx.report

Counts per macro-seed (n = 10) are integers out of 50 episodes per family.
Each macro-seed has its own block of exam worlds; every arm runs on it.
"""
from __future__ import annotations

import json
from typing import Dict, List

from .bench import EXAM, LAB, MACROS, holm, wilcoxon_greater

ALPHA = 0.01


def load() -> List[Dict]:
    eps = []
    for m in MACROS:
        eps += json.loads((LAB / "exam" / f"m{m:02d}.json").read_text())["episodes"]
    return eps


def count(eps, arm, regime, families, field, m) -> int:
    return sum(e[field] for e in eps if e["arm"] == arm and e["macro"] == m
               and e["regime"] == regime and e["family"] in families)


def series(eps, arm, regime, families, field) -> List[int]:
    return [count(eps, arm, regime, families, field, m) for m in MACROS]


def lower(eps, a, b, regime, fams, field) -> float:
    """p for H1: arm a has less of `field` than arm b (paired by macro-seed)."""
    return wilcoxon_greater([y - x for x, y in zip(series(eps, a, regime, fams, field),
                                                   series(eps, b, regime, fams, field))])


def mean(xs: List[int]) -> float:
    return sum(xs) / len(xs)


def evaluate(eps: List[Dict]) -> Dict:
    out: Dict = {"table": {}}
    arms = sorted({e["arm"] for e in eps})
    for regime in ("A1", "A2"):
        for f in EXAM:
            for arm in arms:
                out["table"][f"{regime}|{f}|{arm}"] = {
                    k: mean(series(eps, arm, regime, (f,), k))
                    for k in ("success", "harm", "harm_probe", "harm_auto", "harm_other", "wasted", "steps")}

    # P1 · harm, A1, pooled exam families
    h = {a: mean(series(eps, a, "A1", EXAM, "harm")) for a in ("aprendida", "vacia", "marginal", "barajada", "ortogonal")}
    ps = {c: lower(eps, "aprendida", c, "A1", EXAM, "harm") for c in ("vacia", "marginal", "barajada", "ortogonal")}
    hp = holm(ps, ALPHA)
    p1 = h["aprendida"] * 100 <= 30 * h["vacia"] and all(hp.values()) and all(h["aprendida"] < h[c] for c in ps)
    out["P1"] = {"pass": p1, "harm_mean": h, "p": ps, "holm": hp}

    # P2 · Pareto: success of aprendida >= vacía and >= marginal, A1 and A2 (non-inferiority, point means)
    p2 = {}
    for regime in ("A1", "A2"):
        s = {a: mean(series(eps, a, regime, EXAM, "success")) for a in ("aprendida", "vacia", "marginal")}
        p2[regime] = {"success_mean": s, "pass": s["aprendida"] >= s["vacia"] and s["aprendida"] >= s["marginal"],
                      "p_better_than_vacia": lower(eps, "vacia", "aprendida", regime, EXAM, "success")}
    out["P2"] = {"pass": all(v["pass"] for v in p2.values()), **p2}

    # P3 · role transfer in A2
    dyn, unl = ("DynObs16",), ("UnlockPickup",)
    hd = {a: mean(series(eps, a, "A2", dyn, "harm")) for a in ("aprendida", "vacia", "marginal", "sin_auto")}
    wu = {a: mean(series(eps, a, "A2", unl, "wasted")) for a in ("aprendida", "vacia", "marginal")}
    ps3 = {"dyn_vs_vacia": lower(eps, "aprendida", "vacia", "A2", dyn, "harm"),
           "dyn_vs_marginal": lower(eps, "aprendida", "marginal", "A2", dyn, "harm"),
           "dyn_vs_sin_auto": lower(eps, "aprendida", "sin_auto", "A2", dyn, "harm"),
           "unl_vs_vacia": lower(eps, "aprendida", "vacia", "A2", unl, "wasted"),
           "unl_vs_marginal": lower(eps, "aprendida", "marginal", "A2", unl, "wasted")}
    hp3 = holm(ps3, ALPHA)
    p3 = (hd["aprendida"] * 100 <= 50 * hd["vacia"] and wu["aprendida"] * 100 <= 65 * wu["vacia"]
          and all(hp3.values()))
    out["P3"] = {"pass": p3, "dyn_harm_mean": hd, "unlock_wasted_mean": wu, "p": ps3, "holm": hp3}
    # reported, not deciding (amendment 2 §10): Dynamic-Obstacles-16x16 tests alone, own Holm
    dyn_ps = {k: v for k, v in ps3.items() if k.startswith("dyn_")}
    dyn_holm = holm(dyn_ps, ALPHA)
    out["P3_dyn_only"] = {"pass": hd["aprendida"] * 100 <= 50 * hd["vacia"] and all(dyn_holm.values()),
                          "holm": dyn_holm}

    # P4 · without the bound (reported)
    out["P4"] = {r: {a: {k: mean(series(eps, a, r, EXAM, k)) for k in ("success", "harm")}
                     for a in ("aprendida", "sin_cota")} for r in ("A1", "A2")}
    # P5 · orthogonal memory vs empty (reported)
    out["P5"] = {r: {a: mean(series(eps, a, r, EXAM, "harm")) for a in ("ortogonal", "vacia")} for r in ("A1", "A2")}
    out["green"] = bool(p1 and out["P2"]["pass"] and p3)
    return out


def main() -> None:
    res = evaluate(load())
    (LAB / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    for k in ("P1", "P2", "P3"):
        print(k, "PASS" if res[k]["pass"] else "FAIL")
    print("GREEN" if res["green"] else "NOT GREEN")


if __name__ == "__main__":
    main()
