"""DREAM-B/C/D closed-loop campaign and reconstruction, local LLM opt-in."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from itertools import product
import json
import os
from pathlib import Path
import random
import sys

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import file_hash, read_json
from echoai.echo4.dream_history import sha
from echoai.echo4.dream_history_bench import parent_binding, sources as inherited_sources
from echoai.echo4.dream_policy import Policy, promotion, ranking, run_policy, select
from echoai.echo4.dream_probe import ProbeArchive, collect, model_for, native, prepare
from echoai.echo4.dream_qwen import LocalQwen, read_proposal
from echoai.echo4.self_audit import cam_hash, private_cause
from echoai.echo4.self_attribution import CATALOG
from echoai.echo4.world import Body

SCHEMA = "echo4-dream-bcd-v1"
TRAIN = ((66, 43), (68, 47), (70, 51), (72, 55))
EXAMS = (((82, 44), (84, 48), (86, 52), (88, 56)),
         ((83, 45), (85, 49), (87, 53), (89, 57)),
         ((90, 46), (92, 50), (94, 54), (96, 58)))
CONDITIONS = tuple(product((True, False), (True, False), (-16, -4, 0, 4, 16)))


def sources():
    extra = ("echo4/dream_policy.py", "echo4/dream_probe.py", "echo4/dream_qwen.py",
             "echo4/dream_bench.py", "tests/test_echo4_dream1.py",
             "docs/ECHO4-DREAM1-BCD-DESIGN.md")
    return {**inherited_sources(), **{p: file_hash(ROOT / p) for p in extra}}


def persist(directory, name, value, checking):
    raw = canonical(value)
    path = directory / name
    if checking:
        if path.read_bytes() != raw:
            raise ValueError("reconstruction mismatch: " + name)
    else:
        with path.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    return sha(raw)


def cases(bodies):
    rows = []
    for values in bodies:
        body = Body(*values)
        prepared = prepare(body)
        for condition in CONDITIONS:
            rows.append((body, condition, prepared))
    return rows


def histories(directory, name, rows, *, checking):
    result, stored = [], []
    for body, condition, prepared in rows:
        archive = collect(body, condition, prepared)
        stored.append({"private_context": {"body": asdict(body), "condition": list(condition)},
                       "archive": json.loads(archive.dumps()), "sha256": sha(archive.dumps())})
        result.append((body, condition, prepared, archive))
    digest = persist(directory, name, stored, checking)
    return result, {"sha256": digest, "contexts": len(result),
                    "collection_steps": sum(b["native_steps"] for r in stored for b in r["archive"]["branches"]),
                    "calibration_steps": 72 * len({tuple(asdict(b).values()) for b, _, _ in rows})}


def evaluate(policy, rows, *, replay=False, active=False, random_seed=None):
    outcomes = []
    for i, row in enumerate(rows):
        body, condition, prepared = row[:3]
        reference = prepared[0]
        frozen = reference.model_hash(), cam_hash(reference.boundary.cam)
        chosen = policy
        if random_seed is not None:
            order = list(range(6))
            random.Random(random_seed + i).shuffle(order)
            chosen = Policy(tuple(order))
        model = model_for(body, prepared)
        if replay:
            archive = row[3]
            if archive._data["reference_sha256"] != reference.model_hash():
                raise ValueError("nominal calibration mismatch")
            session = archive.replay()
            request = session.request
        else:
            request = lambda plan: native(body, condition, plan)
        outcome = run_policy(model, chosen, request, active=active)
        truth = private_cause(*condition)
        outcome.update(correct=outcome["diagnosis"]["label"] == truth,
                       wrong=outcome["diagnosis"]["label"] not in (truth, "unknown"),
                       truth_retained=(body.h, condition[0]) in model.h_candidates
                           and (body.temperature, condition[1], condition[2]) in model.t_candidates,
                       reference_preserved=frozen == (reference.model_hash(), cam_hash(reference.boundary.cam)),
                       cam_facts=sum(s.has_fact for s in reference.boundary.cam.slot if s.occupied),
                       destroyed=reference.boundary.cam.destroyed)
        outcomes.append(outcome)
    return outcomes


def summary(rows):
    return {"cases": len(rows), "correct": sum(r["correct"] for r in rows),
            "wrong": sum(r["wrong"] for r in rows),
            "unknown": sum(r["diagnosis"]["label"] == "unknown" for r in rows),
            "steps": sum(r["steps"] for r in rows), "queries": sum(r["queries"] for r in rows),
            "terminalities": sum(r["terminalities"] for r in rows),
            "invariants": all(r["truth_retained"] and r["reference_preserved"]
                and not r["cam_facts"] and not r["destroyed"] and r["reserved_steps"] <= 12 for r in rows)}


def observed_summary(history):
    """Explicitly query every allowed historical arm; no private labels exported."""
    observed = []
    for index in range(6):
        enabled = tuple(int(i == index) for i in range(6))
        rows = evaluate(Policy(enabled=enabled), history, replay=True)
        observed.append({"experiment": index, "contexts": len(rows),
                         "resolved": ranking(rows)[0], "steps": sum(r["steps"] for r in rows),
                         "queries": sum(r["queries"] for r in rows),
                         "unknown_branches": sum(e["status"] == "unknown" for r in rows for e in r["events"])})
    return observed


def rotations():
    order = tuple(range(6))
    return tuple(Policy(order[k:] + order[:k]) for k in range(6))


def build(directory, metadata, proposer=None, *, checking=False, progress=lambda s: None):
    manifest = sources()
    binding = parent_binding()
    baseline = Policy()
    lock = {"schema": SCHEMA, "sources": manifest, "parent_binding": binding,
            "train": TRAIN, "exams": EXAMS, "conditions": CONDITIONS,
            "baseline": baseline.data(), "model": metadata}
    # Synced before any held-out evaluation; never silently replace an exam.
    lock_digest = persist(directory, "lock.json", lock, checking)
    history, initial_cost = histories(directory, "history-initial.json", cases(TRAIN), checking=checking)
    incumbent = baseline
    cycles = []
    previous_version = sha(canonical(baseline.data()))
    for cycle, bodies in enumerate(EXAMS):
        progress(f"DREAM cycle {cycle + 1}/3: replay and Qwen proposals")
        observed = observed_summary(history)
        candidate_sets, proposal_rows = {}, {}
        for label, data in (("history", observed), ("no_history", [])):
            name = f"proposal-{cycle}-{label}.json"
            receipt = read_json(directory / name) if checking else proposer(data, cycle)
            candidates, cost, error = read_proposal(receipt, data, cycle, metadata["model_sha256"])
            persist(directory, name, receipt, checking)
            candidate_sets[label] = candidates
            proposal_rows[label] = {"receipt_sha256": file_hash(directory / name), "cost": cost,
                                    "error": error, "valid_candidates": len(candidates)}
        cache = {}

        def replay(policy):
            if policy.identity not in cache:
                cache[policy.identity] = evaluate(policy, history, replay=True)
            return cache[policy.identity]

        candidate, scores = select(incumbent, candidate_sets["history"], replay)
        no_qwen, control_scores = select(baseline, rotations(), replay)
        no_history = next(iter(candidate_sets["no_history"]), baseline)
        selection = {"history_sha256": sha(canonical(observed)), "history_contexts": len(history),
                     "incumbent": incumbent.data(), "candidate": candidate.data(), "scores": scores,
                     "no_qwen_scores": control_scores, "no_qwen": no_qwen.data(),
                     "no_history": no_history.data()}
        # Choice is immutable on disk before opening this cycle's holdout.
        persist(directory, f"selection-{cycle}.json", selection, checking)
        progress(f"DREAM cycle {cycle + 1}/3: new WORLD-1 trials")
        exam = cases(bodies)
        arms = {"dream": evaluate(candidate, exam), "incumbent": evaluate(incumbent, exam),
                "fixed": evaluate(baseline, exam),
                "random": evaluate(baseline, exam, random_seed=260922 + cycle * 1000),
                "no_history": evaluate(no_history, exam), "no_qwen": evaluate(no_qwen, exam),
                "self_active": evaluate(baseline, exam, active=True)}
        active, decision = promotion(incumbent, candidate, arms["incumbent"], arms["dream"])
        version = {"cycle": cycle, "parent": previous_version, "candidate": candidate.data(),
                   "active": active.data(), "decision": decision,
                   "selection_sha256": file_hash(directory / f"selection-{cycle}.json")}
        previous_version = persist(directory, f"version-{cycle}.json", version, checking)
        trace_digest = persist(directory, f"online-{cycle}.json", arms, checking)
        # Only now may the new cases enter the replay pool for the next cycle.
        extension, extension_cost = histories(directory, f"history-online-{cycle}.json", exam, checking=checking)
        # Causal replay parity for every controller, after the online evaluation.
        replay_equal = all(arms[label] == evaluate(policy, extension, replay=True,
                                active=label == "self_active",
                                random_seed=260922 + cycle * 1000 if label == "random" else None)
                           for label, policy in (("dream", candidate), ("incumbent", incumbent),
                               ("fixed", baseline), ("random", baseline), ("no_history", no_history),
                               ("no_qwen", no_qwen), ("self_active", baseline)))
        statistics = {name: summary(value) for name, value in arms.items()}
        checks = {"qwen_real_candidates": all(r["valid_candidates"] > 0 and not r["error"]
                                              for r in proposal_rows.values()),
                  "gain_fixed": statistics["dream"]["correct"] >= statistics["fixed"]["correct"] + 8,
                  "gain_random": statistics["dream"]["correct"] >= statistics["random"]["correct"] + 4,
                  "no_online_regression": ranking(arms["dream"]) >= ranking(arms["incumbent"]),
                  "safe": all(r["wrong"] == r["terminalities"] == 0 and r["invariants"] for r in statistics.values()),
                  "online_replay_equal": replay_equal}
        cycles.append({"cycle": cycle, "selection": selection, "proposals": proposal_rows,
                       "metrics": statistics, "checks": checks, "decision": decision,
                       "version_sha256": previous_version, "online_sha256": trace_digest,
                       "extension": extension_cost,
                       "replay_cost": {"queries": sum(r["queries"] for rows in cache.values() for r in rows)
                                                + sum(r["queries"] for r in observed),
                                       "represented_steps": sum(r["steps"] for rows in cache.values() for r in rows)
                                                + sum(r["steps"] for r in observed),
                                       "native_steps": 0, "llm_calls": 0}})
        history.extend(extension)
        incumbent = active
        progress(f"cycle {cycle + 1}: " + json.dumps(statistics, sort_keys=True))
    strict_improvement = any(tuple(s["score"]) > tuple(c["selection"]["scores"][0]["score"])
                             for c in cycles for s in c["selection"]["scores"][1:])
    checks = {"three_cycles": len(cycles) == 3, "strict_history_improvement": strict_improvement,
              "all_cycles": all(all(c["checks"].values()) for c in cycles),
              "sources_and_parents": manifest == sources() and binding == parent_binding()}
    report = {"schema": SCHEMA, "lock_sha256": lock_digest, "sources": manifest,
              "model": metadata, "initial_history": initial_cost, "cycles": cycles,
              "checks": checks, "criteria_passed": all(checks.values()), "dream1_green": False,
              "active_policy": incumbent.data(),
              "scope": "restored diagnostic probes; fixed weights; no live product integration"}
    report["reproduction_sha256"] = sha(canonical(report))
    return report


def campaign(directory, server, model, *, port=8094, threads=4):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    with LocalQwen(server, model, directory, port=port, threads=threads) as backend:
        report = build(directory, backend.metadata, backend.propose,
                       progress=lambda s: print(s, file=sys.stderr, flush=True))
        if file_hash(backend.model) != backend.metadata["model_sha256"]:
            raise ValueError("model file changed during campaign")
    persist(directory, "report.json", report, False)
    return report


def verify(directory, *, progress=lambda s: None):
    findings, report = [], {}
    try:
        directory = Path(directory)
        report = read_json(directory / "report.json")
        if report["schema"] != SCHEMA or report["sources"] != sources():
            raise ValueError("source or profile mismatch")
        metadata = report["model"]
        if metadata["weights_updated"] is not False:
            raise ValueError("weights were changed")
        if file_hash(metadata["model"]) != metadata["model_sha256"] or file_hash(metadata["server"]) != metadata["server_sha256"]:
            raise ValueError("local model/binary identity mismatch")
        rebuilt = build(directory, metadata, checking=True, progress=progress)
        if canonical(rebuilt) != canonical(report):
            raise ValueError("report differs from full reconstruction")
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
            parser.error("campaign requires explicit --server and --model")
        result = campaign(args.directory, args.server, args.model, port=args.port, threads=args.threads)
        output = {"criteria_passed": result["criteria_passed"], "checks": result["checks"],
                  "dream1_green": False, "reproduction_sha256": result["reproduction_sha256"]}
    else:
        output = verify(args.directory, progress=lambda s: print(s, file=sys.stderr, flush=True))
        if args.write_receipt:
            persist(args.directory, "audit-receipt.json", output, False)
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
