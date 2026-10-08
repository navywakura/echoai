"""Prospective DREAM-D v3 campaign and independent full reconstruction."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import file_hash, read_json
from echoai.echo4.dream_bench import evaluate as legacy_evaluate, persist, summary
from echoai.echo4.dream_history import sha
from echoai.echo4.dream_policy import Policy as LegacyPolicy, ranking
from echoai.echo4.dream_v2 import promote
from echoai.echo4.dream_v2_bench import sources as inherited_sources
from echoai.echo4.dream_v3 import (
    CONDITIONS, DEVELOPMENT, Qwen, ReplayEvaluator, binding, cases, context,
    evaluate, exam_bodies, histories, read_proposal, starters,
)
from echoai.echo4.dream_v3_profile import Archive, CATALOG, PROFILE, Policy, collect, prepare
from echoai.echo4.world import Body

SCHEMA = "echo4-dream-d-v3"
DEV = ROOT / "lab/echo4/dream1-d-v3-development"
LEGACY_POLICY = LegacyPolicy((4, 5, 0, 1, 2, 3))


def sources():
    extra = ("echo4/dream_v3_profile.py", "echo4/dream_v3.py", "echo4/dream_v3_bench.py",
             "echo4/dream_v3_development.py", "tests/test_echo4_dream1_v3.py",
             "docs/ECHO4-DREAM1-D-V3-DESIGN.md")
    return {**inherited_sources(), **{name: file_hash(ROOT / name) for name in extra}}


def development_binding():
    report = read_json(DEV / "report.json")
    unsigned = dict(report)
    digest = unsigned.pop("reproduction_sha256")
    if (sha(canonical(unsigned)) != digest or report["parent"] != binding()
            or report["dream1_green"] is not False or canonical(report["bodies"]) != canonical(DEVELOPMENT)):
        raise ValueError("development custody mismatch")
    if not all(r["parity"] for r in report["results"]):
        raise ValueError("development parity failed")
    return {p.name: file_hash(p) for p in sorted(DEV.iterdir()) if p.is_file()}


def load_history():
    report = read_json(DEV / "report.json")
    groups, prepared = [], {}
    for i, cost in enumerate(report["collection"]):
        path = DEV / f"history-{i}.json"
        if file_hash(path) != cost["sha256"]:
            raise ValueError("development history digest mismatch")
        rows = []
        for row in read_json(path):
            body = Body(**row["private_context"]["body"])
            condition = tuple(row["private_context"]["condition"])
            if body not in prepared:
                prepared[body] = prepare(body)
            archive = Archive.loads(canonical(row["archive"]), row["sha256"])
            if collect(body, condition, prepared[body]).dumps() != archive.dumps():
                raise ValueError("conditional history physical reconstruction mismatch")
            rows.append((body, condition, prepared[body], archive))
        groups.append(rows)
    return groups, report["collection"]


def build(directory, metadata, proposer=None, *, checking=False, progress=lambda _: None):
    manifest, parent, dev, exams = sources(), binding(), development_binding(), exam_bodies()
    lock = {"schema": SCHEMA, "profile": PROFILE, "catalog": CATALOG,
            "sources": manifest, "parent": parent, "development": dev, "exams": exams,
            "conditions": CONDITIONS, "model": metadata,
            "gain_fixed_ppm": 100000, "gain_random_ppm": 50000,
            "max_proposals_per_arm": 8, "max_native_steps": 12}
    lock_digest = persist(directory, "lock.json", lock, checking)
    progress("v3: reconstruct development histories; no prospective cases yet")
    groups, initial_cost = load_history()
    groups = list(groups)
    incumbent = Policy()  # Explicit new profile; old v2 retained as separate control.
    previous = incumbent.identity
    initial = {"history_contexts": sum(map(len, groups)), "groups": len(groups),
               "policy": incumbent.data(), "revalidation_cost": initial_cost}
    persist(directory, "initial.json", initial, checking)
    cycles = []
    for cycle, bodies in enumerate(exams):
        replay = ReplayEvaluator(groups)
        proposals, receipts = {}, {}
        for turn, label in enumerate(("initial", "feedback", "no_feedback", "empty_first", "empty_second")):
            data = context(replay, incumbent, proposals.get("initial", ()) if label == "feedback" else (),
                           empty=label.startswith("empty_"))
            name = f"proposal-{cycle}-{label}.json"
            progress(f"v3 cycle {cycle+1}/3: Qwen {label}")
            receipt = read_json(directory / name) if checking else proposer(data, 5 * cycle + turn)
            candidates, cost, error = read_proposal(receipt, data, 5 * cycle + turn, metadata["model_sha256"])
            persist(directory, name, receipt, checking)
            proposals[label] = candidates
            receipts[label] = {"sha256": file_hash(directory / name), "cost": cost,
                               "valid_candidates": len(candidates), "error": error}
        candidate, scores = replay.select(incumbent, proposals["initial"] + proposals["feedback"])
        no_feedback, _ = replay.select(incumbent, proposals["initial"] + proposals["no_feedback"])
        no_history, _ = replay.select(incumbent, proposals["empty_first"] + proposals["empty_second"])
        no_qwen, control_scores = replay.select(incumbent, starters())
        no_replay = next(iter(proposals["initial"]), incumbent)
        selection = {"history_contexts": sum(map(len, groups)), "history_groups": len(groups),
                     "candidate": candidate.data(), "incumbent": incumbent.data(), "scores": scores,
                     "no_feedback": no_feedback.data(), "no_history": no_history.data(),
                     "no_qwen": no_qwen.data(), "no_qwen_scores": control_scores,
                     "no_replay": no_replay.data(),
                     "candidate_counts": {
                         label: {"slots": len(pool), "distinct": len(set(pool))}
                         for label, pool in {
                             "dream": proposals["initial"] + proposals["feedback"],
                             "no_feedback": proposals["initial"] + proposals["no_feedback"],
                             "no_history": proposals["empty_first"] + proposals["empty_second"],
                             "no_qwen": starters()}.items()}}
        persist(directory, f"selection-{cycle}.json", selection, checking)
        progress(f"v3 cycle {cycle+1}/3: frozen selection, new native exam")
        exam = cases(bodies)
        policies = {"dream": candidate, "incumbent": incumbent, "fixed": Policy(),
                    "random": Policy(), "no_qwen": no_qwen, "no_feedback": no_feedback,
                    "no_history": no_history, "no_replay": no_replay, "adaptive": Policy()}

        def run(label, policy, rows, *, offline=False):
            return evaluate(policy, rows, replay=offline, active=label == "adaptive",
                            random_seed=260924 + cycle * 10000 if label == "random" else None)

        arms = {label: run(label, p, exam) for label, p in policies.items()}
        arms["legacy_v2"] = legacy_evaluate(LEGACY_POLICY, exam)
        active, decision = promote(incumbent, candidate, arms["incumbent"], arms["dream"], arms["fixed"])
        # Additional anchor, not a weakened replacement for the matched controls.
        if ranking(arms["dream"]) < ranking(arms["legacy_v2"]):
            active, decision = incumbent, "rollback_legacy"
        version = {"cycle": cycle, "parent": previous, "candidate": candidate.data(),
                   "active": active.data(), "decision": decision,
                   "selection_sha256": file_hash(directory / f"selection-{cycle}.json")}
        previous = persist(directory, f"version-{cycle}.json", version, checking)
        online_digest = persist(directory, f"online-{cycle}.json", arms, checking)
        extension, cost = histories(directory, f"history-online-{cycle}.json", exam, checking=checking)
        parity = all(arms[label] == run(label, p, extension, offline=True) for label, p in policies.items())
        statistics = {label: summary(rows) for label, rows in arms.items()}
        count = len(exam)
        checks = {
            "qwen_real_candidates": all(r["valid_candidates"] > 0 and not r["error"] for r in receipts.values()),
            "gain_fixed": (statistics["dream"]["correct"] - statistics["fixed"]["correct"]) * 10 >= count,
            "gain_random": (statistics["dream"]["correct"] - statistics["random"]["correct"]) * 20 >= count,
            "promotion_allowed": decision in ("accepted", "incumbent_retained"),
            "no_regression_incumbent": ranking(arms["dream"]) >= ranking(arms["incumbent"]),
            "no_regression_legacy": ranking(arms["dream"]) >= ranking(arms["legacy_v2"]),
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
        progress(f"cycle {cycle+1}: " + json.dumps(statistics, sort_keys=True))
    checks = {"three_cycles": len(cycles) == 3,
              "strict_history_improvement": any(c["strict_history_improvement"] for c in cycles),
              "all_cycles": all(all(c["checks"].values()) for c in cycles),
              "sources_and_parents": manifest == sources() and parent == binding() and dev == development_binding()}
    report = {"schema": SCHEMA, "sources": manifest, "parent": parent, "development": dev,
              "lock_sha256": lock_digest, "initial": initial, "model": metadata, "cycles": cycles,
              "checks": checks, "criteria_passed": all(checks.values()), "dream1_green": False,
              "active_policy": incumbent.data(),
              "scope": "conditional restored WORLD-1 exploration; fixed weights; not product integration"}
    report["reproduction_sha256"] = sha(canonical(report))
    return report


def campaign(directory, server, model, *, port=8094, threads=4):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    with Qwen(server, model, directory, port=port, threads=threads) as backend:
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
        if (report["schema"] != SCHEMA or report["sources"] != sources()
                or report["parent"] != binding() or report["development"] != development_binding()):
            raise ValueError("source/profile/parent mismatch")
        metadata = report["model"]
        if metadata["weights_updated"] is not False:
            raise ValueError("weights modified")
        for kind in ("model", "server"):
            if file_hash(Path(metadata[kind])) != metadata[kind + "_sha256"]:
                raise ValueError("model/server changed")
        if canonical(build(directory, metadata, checking=True, progress=progress)) != canonical(report):
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
    if args.command == "campaign":
        if args.server is None or args.model is None:
            parser.error("campaign requires explicit local model/server")
        report = campaign(args.directory, args.server, args.model, port=args.port, threads=args.threads)
        result = {k: report[k] for k in ("criteria_passed", "dream1_green", "checks", "reproduction_sha256")}
    else:
        result = verify(args.directory, progress=lambda s: print(s, file=sys.stderr, flush=True))
        if args.write_receipt:
            persist(args.directory, "audit-receipt.json", result, False)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
