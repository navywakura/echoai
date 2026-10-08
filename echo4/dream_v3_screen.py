"""Reproducible prior screening on opened v2 cycle2, NOT execution evidence."""
from itertools import product
from pathlib import Path
import argparse
import json

from echoai.echo4.continuity import canonical
from echoai.echo4.continuity_final_audit import file_hash
from echoai.echo4.dream_bench import CONDITIONS, persist
from echoai.echo4.dream_history import sha
from echoai.echo4.dream_probe import model_for, prepare
from echoai.echo4.dream_v2 import exam_bodies
from echoai.echo4.self_attribution import CATALOG, forecast, possible_labels
from echoai.echo4.world import Body


def screen():
    sequences = tuple(product(range(3), repeat=8))
    resolved, admissible = [0] * len(sequences), [0] * len(sequences)
    bodies = exam_bodies()[1]  # old/open v2, never v3.exam_bodies
    for values in bodies:
        body = Body(*values)
        model = model_for(body, prepare(body))
        hs, ts = model.h_candidates, model.t_candidates
        hp = {c: forecast(c, CATALOG[2], thermal=False) for c in hs}
        tp = {c: forecast(c, CATALOG[2], thermal=True) for c in ts}
        rows = []
        for hc, tc, heat in CONDITIONS:
            ht, tt = (body.h, hc), (body.temperature, tc, heat)
            if any(seq is None for seq in (*hp.values(), *tp.values())):
                rows.append((hs, ts, ht, tt))
            else:
                rows.append((tuple(c for c in hs if hp[c] == hp[ht]),
                             tuple(c for c in ts if tp[c] == tp[tt]), ht, tt))
        for i, actions in enumerate(sequences):
            hp = {c: forecast(c, actions, thermal=False) for c in hs}
            tp = {c: forecast(c, actions, thermal=True) for c in ts}
            for h, t, ht, tt in rows:
                if len(possible_labels(h, t)) == 1:
                    resolved[i] += 1
                    continue
                if any(hp[c] is None for c in h) or any(tp[c] is None for c in t):
                    continue
                admissible[i] += 1
                after_h = tuple(c for c in h if hp[c] == hp[ht])
                after_t = tuple(c for c in t if tp[c] == tp[tt])
                resolved[i] += len(possible_labels(after_h, after_t)) == 1
    rows = [{"actions": seq, "resolved": resolved[i], "admissible_after_short": admissible[i]}
            for i, seq in enumerate(sequences)]
    report = {"scope": "prior-only development screening, not observed receipts or a policy",
              "source_sha256": file_hash(Path(__file__)), "opened_bodies": bodies,
              "cases": len(bodies) * len(CONDITIONS), "candidate_sequences": len(sequences),
              "physical_calibration_steps": 72 * len(bodies), "llm_calls": 0,
              "simulated_probe_receipts": 0, "max_resolved": max(resolved),
              "scores": rows, "dream1_green": False}
    report["reproduction_sha256"] = sha(canonical(report))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=False)
    report = screen()
    persist(args.directory, "report.json", report, False)
    print(json.dumps({k: report[k] for k in ("max_resolved", "candidate_sequences", "reproduction_sha256")}))


if __name__ == "__main__":
    main()
