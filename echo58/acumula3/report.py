"""ACUMULA-3 (B v3): predictions Q1-Q6 from lab/echo58/acumula3/exam/*.json (contract ACUMULA3-DESIGN.md §5).

    PYTHONPATH=/home/user/REALRXOS/RXos python3 -m echoai.echo58.acumula3.report
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List

from ..memx.bench import MACROS, holm, wilcoxon_greater

LAB = Path(__file__).resolve().parents[2] / "lab" / "echo58" / "acumula3"
ARMS = ("recursiva", "azar", "sin_acumular", "fija", "lote_final", "vacia_online", "piezas_dadas")
CONTROLS = ("azar", "sin_acumular", "fija", "lote_final", "vacia_online")
ALPHA = 0.01


def load(folder: Path = LAB / "exam") -> Dict[str, Dict[int, Dict]]:
    runs: Dict[str, Dict[int, Dict]] = {a: {} for a in ARMS}
    for p in sorted(folder.glob("*.json")):
        x = json.loads(p.read_text())
        if "crash" in x:
            raise SystemExit(f"{p.name} crashed: the exam is incomplete")
        runs[x["arm"]][x["macro"]] = x
    return runs


def probe(x: Dict, r: int, field: str) -> int:
    return sum(v[field] for v in x["probe"][str(r)].values())


def mean(xs: List[int]) -> float:
    return sum(xs) / len(xs)


def evaluate(runs: Dict[str, Dict[int, Dict]], macros=MACROS) -> Dict:
    out: Dict = {}
    curve = {a: {r: {f: mean([probe(runs[a][m], r, f) for m in macros]) for f in ("failed", "harm")}
                 for r in range(6)} for a in ARMS}
    out["curve"] = curve

    # Q1 · >= 3 consecutive transitions with strictly fewer failures and no more harm
    c = curve["recursiva"]
    steps = [c[r]["failed"] < c[r - 1]["failed"] and c[r]["harm"] <= c[r - 1]["harm"] for r in range(1, 6)]
    run = best = 0
    for s in steps:
        run = run + 1 if s else 0
        best = max(best, run)
    out["Q1"] = {"pass": best >= 3, "steps": steps, "longest_run": best}

    # Q2 · after round 5, fewer probe failures than every control (Holm over five one-sided Wilcoxon)
    def less(a: str, b: str) -> float:
        return wilcoxon_greater([probe(runs[b][m], 5, "failed") - probe(runs[a][m], 5, "failed") for m in macros])
    ps = {b: less("recursiva", b) for b in CONTROLS}
    hp = holm(ps, ALPHA)
    out["Q2"] = {"pass": all(hp.values()), "p": ps, "holm": hp,
                 "failed_r5": {a: curve[a][5]["failed"] for a in ARMS}}

    # Q3 · no regression on track A's exam families with the final configuration (same final memory)
    q3 = {k: {f: mean([sum(v[f] for v in runs["recursiva"][m]["q3"][k].values()) for m in macros])
              for f in ("harm", "success")} for k in ("base", "final")}
    out["Q3"] = {"pass": q3["final"]["harm"] <= q3["base"]["harm"] and q3["final"]["success"] >= q3["base"]["success"],
                 **q3}

    # Q4 · dependence (reported): macros with an edit accepted at r >= 2 after an earlier rejection
    out["Q4"] = {"macros_with_late_after_reject": sum(1 for m in macros if runs["recursiva"][m]["late_after_reject"]),
                 "edits": Counter(e for m in macros for e in runs["recursiva"][m]["late_after_reject"]).most_common()}

    # Q5 · ECHO's choice vs all pieces handed over (reported)
    out["Q5"] = {"failed_r5": {a: curve[a][5]["failed"] for a in ("recursiva", "piezas_dadas")},
                 "p_recursiva_fewer": less("recursiva", "piezas_dadas"),
                 "p_piezas_dadas_fewer": less("piezas_dadas", "recursiva")}

    # Q6 · what was accepted, by round (reported)
    out["Q6"] = {a: Counter(f"r{rr['round']} {e}" for m in macros for rr in runs[a][m]["rounds"]
                            for e in rr["accepted"]).most_common(25) for a in ARMS if a != "vacia_online"}
    out["destroyed"] = sum(runs[a][m].get("destroyed", 0) for a in ARMS for m in macros)
    out["green"] = bool(out["Q1"]["pass"] and out["Q2"]["pass"] and out["Q3"]["pass"] and out["destroyed"] == 0)
    return out


def main() -> None:
    res = evaluate(load())
    (LAB / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True, default=str))
    for k in ("Q1", "Q2", "Q3"):
        print(k, "PASS" if res[k]["pass"] else "FAIL")
    print("GREEN" if res["green"] else "NOT GREEN")


if __name__ == "__main__":
    main()
