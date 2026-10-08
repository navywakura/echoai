"""DREAM-D v2 campaign; prospective exams, real local Qwen and full audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import file_hash, read_json
from echoai.echo4.dream_bench import (
    CONDITIONS, cases, evaluate, histories, persist, sources as v1_sources, summary,
)
from echoai.echo4.dream_history import sha
from echoai.echo4.dream_policy import Policy, ranking
from echoai.echo4.dream_qwen import read_proposal
from echoai.echo4.dream_v2 import (
    FeedbackQwen, ReplayEvaluator, binding, context, control_candidates,
    exam_bodies, load_history, promote,
)

SCHEMA = "echo4-dream-d-v2"


def sources():
    extra = ("echo4/dream_v2.py", "echo4/dream_v2_bench.py",
             "tests/test_echo4_dream1_v2.py", "docs/ECHO4-DREAM1-D-V2-DESIGN.md")
    return {**v1_sources(), **{p: file_hash(ROOT / p) for p in extra}}


def build(directory, metadata, proposer=None, *, checking=False, progress=lambda _: None):
    manifest, parent, exams = sources(), binding(), exam_bodies()
    lock = {"schema": SCHEMA, "sources": manifest, "parent": parent,
            "exams": exams, "conditions": CONDITIONS, "model": metadata,
            "gain_fixed_ppm": 100000, "gain_random_ppm": 50000}
    lock_digest = persist(directory, "lock.json", lock, checking)
    groups, incumbent = load_history()
    groups = list(groups)  # the campaign owns expansion, not its history provider
    initial = {"contexts": sum(map(len, groups)), "groups": len(groups),
               "policy": incumbent.data(), "history_digests": {
                   k: v for k, v in parent.items() if k.startswith("history-")}}
    persist(directory, "initial.json", initial, checking)
    previous = sha(canonical(incumbent.data()))
    cycles = []
    for cycle, bodies in enumerate(exams):
        progress(f"DREAM v2 cycle {cycle + 1}/3: historical replay")
        replay = ReplayEvaluator(groups)
        proposals, receipts = {}, {}
        for turn, label in enumerate(("initial", "feedback", "no_history")):
            data = context(replay, incumbent, proposals.get("initial", ()) if turn == 1 else (),
                           empty=label == "no_history")
            name = f"proposal-{cycle}-{label}.json"
            progress(f"DREAM v2 cycle {cycle + 1}/3: Qwen {label}")
            receipt = read_json(directory / name) if checking else proposer(data, 3 * cycle + turn)
            policies, cost, error = read_proposal(receipt, data, 3 * cycle + turn, metadata["model_sha256"])
            persist(directory, name, receipt, checking)
            proposals[label] = policies
            receipts[label] = {"sha256": file_hash(directory / name), "cost": cost,
                               "valid_candidates": len(policies), "error": error}
        candidate, scores = replay.select(incumbent, proposals["initial"] + proposals["feedback"])
        no_feedback, _ = replay.select(incumbent, proposals["initial"])
        no_history, _ = replay.select(incumbent, proposals["no_history"])
        no_qwen, no_qwen_scores = replay.select(incumbent, control_candidates(cycle))
        no_replay = next(iter(proposals["initial"]), incumbent)
        selection = {"history_contexts": sum(map(len, groups)), "history_groups": len(groups),
                     "candidate": candidate.data(), "incumbent": incumbent.data(),
                     "scores": scores, "no_feedback": no_feedback.data(),
                     "no_history": no_history.data(), "no_qwen": no_qwen.data(),
                     "no_qwen_scores": no_qwen_scores, "no_replay": no_replay.data()}
        persist(directory, f"selection-{cycle}.json", selection, checking)
        progress(f"DREAM v2 cycle {cycle + 1}/3: frozen selection, new WORLD-1 trials")
        exam = cases(bodies)
        policies = {"dream": candidate, "incumbent": incumbent, "fixed": Policy(),
                    "random": Policy(), "no_qwen": no_qwen, "no_feedback": no_feedback,
                    "no_history": no_history, "no_replay": no_replay, "self_active": Policy()}

        def run(label, policy, rows, *, offline=False):
            return evaluate(policy, rows, replay=offline, active=label == "self_active",
                            random_seed=260923 + cycle * 10000 if label == "random" else None)

        arms = {label: run(label, policy, exam) for label, policy in policies.items()}
        active, decision = promote(incumbent, candidate, arms["incumbent"], arms["dream"], arms["fixed"])
        version = {"cycle": cycle, "parent": previous, "candidate": candidate.data(),
                   "active": active.data(), "decision": decision,
                   "selection_sha256": file_hash(directory / f"selection-{cycle}.json")}
        previous = persist(directory, f"version-{cycle}.json", version, checking)
        online_digest = persist(directory, f"online-{cycle}.json", arms, checking)
        extension, cost = histories(directory, f"history-online-{cycle}.json", exam, checking=checking)
        parity = all(arms[label] == run(label, policy, extension, offline=True)
                     for label, policy in policies.items())
        statistics = {label: summary(rows) for label, rows in arms.items()}
        count = len(exam)
        checks = {
            "qwen_real_candidates": all(r["valid_candidates"] > 0 and not r["error"] for r in receipts.values()),
            "gain_fixed": (statistics["dream"]["correct"] - statistics["fixed"]["correct"]) * 10 >= count,
            "gain_random": (statistics["dream"]["correct"] - statistics["random"]["correct"]) * 20 >= count,
            "promotion_allowed": decision in ("accepted", "incumbent_retained"),
            "no_regression_incumbent": ranking(arms["dream"]) >= ranking(arms["incumbent"]),
            "no_regression_fixed": ranking(arms["dream"]) >= ranking(arms["fixed"]),
            "safe": all(r["wrong"] == r["terminalities"] == 0 and r["invariants"] for r in statistics.values()),
            "online_replay_equal": parity,
        }
        cycles.append({"cycle": cycle, "selection": selection, "proposals": receipts,
                       "metrics": statistics, "checks": checks, "decision": decision,
                       "version_sha256": previous, "online_sha256": online_digest,
                       "extension": cost, "replay_cost": replay.cost(),
                       "strict_history_improvement": replay.score(candidate) > replay.score(incumbent)})
        groups.append(extension)
        incumbent = active
        progress(f"cycle {cycle + 1}: " + json.dumps(statistics, sort_keys=True))
    checks = {"three_cycles": len(cycles) == 3,
              "strict_history_improvement": any(c["strict_history_improvement"] for c in cycles),
              "all_cycles": all(all(c["checks"].values()) for c in cycles),
              "sources_and_parent": manifest == sources() and parent == binding()}
    report = {"schema": SCHEMA, "sources": manifest, "parent": parent,
              "lock_sha256": lock_digest, "initial": initial, "model": metadata,
              "cycles": cycles, "checks": checks, "criteria_passed": all(checks.values()),
              "dream1_green": False, "active_policy": incumbent.data(),
              "scope": "stratified restored WORLD-1 diagnosis; fixed weights; not product integration"}
    report["reproduction_sha256"] = sha(canonical(report))
    return report


def campaign(directory, server, model, *, port=8094, threads=4):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    with FeedbackQwen(server, model, directory, port=port, threads=threads) as backend:
        result = build(directory, backend.metadata, backend.propose,
                       progress=lambda s: print(s, file=sys.stderr, flush=True))
        if file_hash(backend.model) != backend.metadata["model_sha256"]:
            raise ValueError("model changed during campaign")
    persist(directory, "report.json", result, False)
    return result


def verify(directory, *, progress=lambda _: None):
    findings, report = [], {}
    try:
        directory = Path(directory)
        report = read_json(directory / "report.json")
        if report["schema"] != SCHEMA or report["sources"] != sources() or report["parent"] != binding():
            raise ValueError("sources/profile/parent mismatch")
        model = report["model"]
        if model["weights_updated"] is not False:
            raise ValueError("weights modified")
        for kind in ("server", "model"):
            if file_hash(Path(model[kind])) != model[kind + "_sha256"]:
                raise ValueError("binary/model changed")
        rebuilt = build(directory, model, checking=True, progress=progress)
        if canonical(rebuilt) != canonical(report):
            raise ValueError("report reconstruction mismatch")
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings,
            "dream1_green": not findings and report.get("criteria_passed") is True,
            "reproduction_sha256": report.get("reproduction_sha256") if not findings else None,
            "qwen_reinferred": False, "model_receipts_audited": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("campaign", "verify"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--server", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--port", type=int, default=8094)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    progress = lambda s: print(s, file=sys.stderr, flush=True)
    if args.command == "campaign":
        if args.server is None or args.model is None:
            parser.error("campaign requires explicit local server and model")
        report = campaign(args.directory, args.server, args.model, port=args.port, threads=args.threads)
        result = {k: report[k] for k in ("criteria_passed", "dream1_green", "checks", "reproduction_sha256")}
    else:
        result = verify(args.directory, progress=progress)
        if args.write_receipt:
            persist(args.directory, "audit-receipt.json", result, False)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
