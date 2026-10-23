"""ENJAMBRE-1 (C v1): predictions E1-E4 from lab/echo58/enjambre/exam/*.json (contract §11).

    PYTHONPATH=/home/user/REALRXOS/RXos python3 -m echoai.echo58.enjambre.report
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from ..memx.bench import holm, wilcoxon_greater

LAB = Path(__file__).resolve().parents[2] / "lab" / "echo58" / "enjambre"
ARMS = ("enjambre", "sin_global", "sin_ayuda", "sin_privada", "global_barajada", "aislados", "uno_solo")
TESTS = {"sin_global": "score", "global_barajada": "score", "sin_ayuda": "score",   # control -> metric
         "sin_privada": "failed", "aislados": "score"}
ALPHA = 0.01
ROUNDS = 30


def load(folder: Path = LAB / "exam") -> Dict[str, Dict[int, Dict]]:
    runs: Dict[str, Dict[int, Dict]] = {a: {} for a in ARMS}
    for p in sorted(folder.glob("*.json")):
        x = json.loads(p.read_text())
        if "crash" in x:
            raise SystemExit(f"{p.name} crashed: the exam is incomplete")
        runs[x["arm"]][x["macro"]] = x
    return runs


def no_plates(x: Dict) -> int:
    return sum(r for r, w in zip(x["solved_round"], x["worlds"]) if w["kind"] != "plate")


def evaluate(runs: Dict[str, Dict[int, Dict]]) -> Dict:
    macros = sorted(runs["enjambre"])
    team = [a for a in ARMS if a != "uno_solo"]
    out: Dict = {"macros": len(macros),
                 "sums": {a: {k: sum(runs[a][m][k] for m in macros) for k in ("score", "solved", "failed", "harm")}
                          for a in team}}
    ps = {b: wilcoxon_greater([runs[b][m][k] - runs["enjambre"][m][k] for m in macros]) for b, k in TESTS.items()}
    hp = holm(ps, ALPHA)
    wins = {b: [sum(runs[b][m][k] > runs["enjambre"][m][k] for m in macros),
                sum(runs[b][m][k] == runs["enjambre"][m][k] for m in macros),
                sum(runs[b][m][k] < runs["enjambre"][m][k] for m in macros)] for b, k in TESTS.items()}
    out["tests"] = {b: {"metric": TESTS[b], "p": ps[b], "holm": hp[b], "win_tie_loss": wins[b]} for b in TESTS}
    out["E1"] = hp["sin_global"] and hp["global_barajada"]
    out["E2"] = hp["sin_ayuda"]
    out["E3"] = hp["sin_privada"]
    out["E4"] = hp["aislados"]
    out["E2_without_plates"] = {"p": wilcoxon_greater([no_plates(runs["sin_ayuda"][m]) - no_plates(runs["enjambre"][m])
                                                       for m in macros]),
                                "enjambre": sum(no_plates(runs["enjambre"][m]) for m in macros),
                                "sin_ayuda": sum(no_plates(runs["sin_ayuda"][m]) for m in macros)}
    out["by_kind_harm"] = {a: {k: sum(runs[a][m]["by_kind"][k]["harm"] for m in macros)
                               for k in runs[a][macros[0]]["by_kind"]} for a in team}
    out["uno_solo"] = {k: sum(runs["uno_solo"][m][k] for m in macros) for k in ("solved", "episodes", "failed", "harm")}
    out["enjambre_episodes"] = sum(runs["enjambre"][m]["episodes"] for m in macros)
    out["sharing"] = {k: sum(runs["enjambre"][m][k] for m in macros)
                      for k in ("postcards", "notes_cards", "helps", "asked", "held")}
    out["answers"] = {s: sum(runs["enjambre"][m]["answers"][s] for m in macros) for s in ("here", "private", "notes", "global")}
    out["destroyed"] = sum(runs[a][m]["destroyed"] for a in ARMS for m in macros)
    out["card_bytes"] = sorted({b for a in team for m in macros for b in runs[a][m]["card_bytes"]})
    out["green"] = bool(out["E1"] and out["E2"] and out["E3"] and out["E4"] and out["destroyed"] == 0
                        and out["card_bytes"] in ([16], []))
    return out


def main() -> None:
    res = evaluate(load())
    (LAB / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    for k in ("E1", "E2", "E3", "E4"):
        print(k, "PASS" if res[k] else "FAIL")
    print("GREEN" if res["green"] else "NOT GREEN")


if __name__ == "__main__":
    main()
