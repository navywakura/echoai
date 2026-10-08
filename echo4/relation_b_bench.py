"""RELATION-B development bench. Development seeds only; never an exam."""
import argparse
import hashlib
import json

import io
from pathlib import Path
import unittest

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4 import relation_bench as parent_module
from echoai.echo4.interaction_cases import fixture, summary, ROUNDS, FORMATION
from echoai.echo4.relation_help import HelpSession, B_ARMS, bucket, shuffled, row, settle

SCHEMA = "echo4-relation1-b-dev-v1"
PARENT = ROOT / "lab/echo4/relation1-a-v1"
PARENT_DIGEST = "ce24ccaa61f9d8b9b781274857b6ce15a9e75817bbf8d0b5fd2649a403369539"
DEVELOPMENT = (151, 163, 179)
B_FORMATION = 96  # First B encounters use the native evidence exploration.
LEARNED = ("other_only", "shuffled", "pooled", "no_history")
# Resource levels differ by design once B spends from the same ledgers; A
# parity is over actions, costs, outputs, receipts, forecasts and gates.
RESOURCE_FIELDS = {"relation_heads", "before", "after", "ledger"}


def b_summary(frames):
    result = {"net": [0, 0, 0], "paid": [0, 0, 0], "output": [0, 0, 0], "private_credit_excluded": [0, 0, 0]}
    counts = {"asked": 0, "helped": 0, "refused": 0, "solo": 0, "wait": 0, "incapable": 0}
    for f in frames:
        for key in ("net", "paid", "output"):
            result[key][0] += f[key][0]
            result[key][f["handle"]] += f[key][1]
        result["private_credit_excluded"][f["handle"]] += f["private_credit"]
        counts["asked"] += f["asked"]
        counts["helped"] += f["helped"]
        counts["refused"] += f["asked"] and not f["helped"]
        counts["solo"] += f["action"] == 1 and not f["incapable"][0]
        counts["wait"] += f["action"] == 2
        counts["incapable"] += sum(f["incapable"])
    return {**result, **counts, "rounds": len(frames), "joint_net": sum(result["net"])}


def reconstruct_b(frames, history, arm, seed):
    """Rebuild B levels, rows and settlements from the learner's own receipts."""
    for f in frames:
        prior = [e for e in history if e["observation"]["tick"] < f["tick"]]
        dyad = [e for e in prior if bytes.fromhex(e["wsp"])[14] == f["handle"]]
        level = (bucket(dyad) if arm == "history" else
                 bucket(shuffled(dyad, seed, f["tick"])) if arm == "shuffled" else
                 bucket(prior) if arm == "pooled" else 0)
        before = (f["ledger"][0] + f["paid"][0], f["ledger"][f["handle"]] + f["paid"][1])
        expected = row(arm, before[0], level=level, handle=f["handle"], cue=f["cue"]).hex()
        if f["level"] != level or (arm != "other_only" and f["row"] != expected):
            return False
        event = settle(f["action"], f["help_action"], before)
        if any(event[k] != f[k] for k in event):
            return False
    return True


def execute(seed, b_arm, *, reverse=False):
    cues, schedule, swapped = fixture(seed)
    session = HelpSession(cues, schedule, b_arm=b_arm, seed=seed, swapped=swapped)
    a_frames, b_frames = [], []
    order = (1, 0) if reverse else (0, 1)
    for t in range(ROUNDS):
        if t >= FORMATION:
            b_frames.append(session.help_step(greedy=t >= FORMATION + B_FORMATION))
        frame = session.step(greedy=t >= FORMATION, order=order)
        a_frames.append(frame)
    checks = {"invariants": session.invariant(),
              "relation_valid": all(m.invariant() for m in session.relations),
              "b_replay": reconstruct_b(b_frames, session.relations[0].history(), b_arm, seed),
              "native_steps": session.focal.metrics.turns == ROUNDS + len(b_frames)}
    return {"seed": seed, "b_arm": b_arm, "swapped": swapped,
            "a_digest": hashlib.sha256(canonical([{k: v for k, v in f.items() if k not in RESOURCE_FIELDS}
                                                  for f in a_frames])).hexdigest(),
            "relation_digests": [m.digest() for m in session.relations],
            "b_frames": b_frames, "b": b_summary(b_frames),
            "b_late": b_summary(b_frames[B_FORMATION:]),
            "a_whole": summary(a_frames), "ledger": tuple(session.ledger), "checks": checks}


def development(seeds=DEVELOPMENT, *, progress=None):
    lives = []
    for seed in seeds:
        arms = {arm: execute(seed, arm) for arm in B_ARMS}
        backwards = execute(seed, "history", reverse=True)
        order_invariant = (canonical(backwards["b_frames"]) == canonical(arms["history"]["b_frames"])
                           and backwards["a_digest"] == arms["history"]["a_digest"])
        a_parity = len({arms[a]["a_digest"] for a in B_ARMS}) == 1
        history_parity = len({tuple(arms[a]["relation_digests"]) for a in B_ARMS}) == 1
        focal = {a: arms[a]["b"]["net"][0] for a in B_ARMS}
        beats = {a: focal["history"] > focal[a] for a in (*LEARNED, "solo")}
        lives.append({"seed": seed, "a_parity": a_parity, "history_parity": history_parity,
                      "order_invariant": order_invariant,
                      "focal_b_net": focal, "late_focal_b_net": {a: arms[a]["b_late"]["net"][0] for a in B_ARMS},
                      "joint_b_net": {a: arms[a]["b"]["joint_net"] for a in B_ARMS},
                      "beats": beats, "arms": {a: {k: arms[a][k] for k in ("b", "b_late", "a_whole", "ledger", "checks")}
                                               for a in B_ARMS}})
        if progress:
            progress(seed, focal)
    criterion = all(all(l["beats"].values()) and l["a_parity"] and l["history_parity"] and l["order_invariant"]
                    and all(all(v["checks"].values()) for v in l["arms"].values()) for l in lives)
    return {"lives": lives, "development_criterion": criterion, "relation1_green": False}


def sources():
    extras = ("echo4/relation_help.py", "echo4/relation_b_bench.py",
              "tests/test_echo4_relation1b.py", "docs/ECHO4-RELATION1-B-DESIGN.md")
    return {**parent_module.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report = read_json(PARENT / "report.json")
    receipt = read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or report["phase_a_valid"] is not True
            or receipt["reproduction_sha256"] != PARENT_DIGEST or receipt["valid"] is not True
            or receipt["findings"] != [] or receipt["relation1_green"] is not False):
        raise ValueError("RELATION-A custody mismatch")
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def tests():
    suite = unittest.defaultTestLoader.loadTestsFromName("echoai.tests.test_echo4_relation1b")
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def campaign(directory, *, checking=False):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "seeds": DEVELOPMENT,
                       "rounds": ROUNDS, "a_formation": FORMATION, "b_formation": B_FORMATION,
                       "scope": "RELATION-B development only; never an exam; C/D unopened"})
    result, unit = development(), tests()
    save("development.json", result)
    save("tests.json", unit)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    report = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "lives": [{k: l[k] for k in ("seed", "a_parity", "history_parity", "order_invariant", "focal_b_net",
                                           "late_focal_b_net", "joint_b_net", "beats")} for l in result["lives"]],
              "tests": unit, "development_criterion": result["development_criterion"] and unit["passed"],
              "relation1_green": False, "exam_opened": False}
    report["reproduction_sha256"] = parent_module.sha(report)
    persist(directory, "report.json", report, checking)
    return report


def verify(directory):
    findings, value = [], None
    try:
        report = read_json(directory / "report.json")
        unsigned = dict(report)
        value = unsigned.pop("reproduction_sha256")
        if parent_module.sha(unsigned) != value or report["schema"] != SCHEMA:
            raise ValueError("report digest/schema mismatch")
        if report["sources"] != sources() or report["parent"] != parent():
            raise ValueError("source/parent mismatch")
        for name, digest in report["artifacts"].items():
            if file_hash(directory / name) != digest:
                raise ValueError("artifact digest mismatch: " + name)
        campaign(directory, checking=True)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "relation1_green": False, "scope": "RELATION-B development reconstruction; not an exam"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("campaign", "verify", "explore"))
    parser.add_argument("directory", type=Path, nargs="?")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command == "explore":
        result = development(progress=lambda s, f: print(s, json.dumps(f), flush=True))
        print(json.dumps({"development_criterion": result["development_criterion"]}))
        return 0
    if args.command == "campaign":
        if args.write_receipt:
            parser.error("audit in a fresh process")
        args.directory.mkdir(parents=True, exist_ok=False)
        result = campaign(args.directory)
        print(json.dumps({k: result[k] for k in ("development_criterion", "relation1_green", "reproduction_sha256")}, indent=2))
        return 0 if result["development_criterion"] else 1
    result = verify(args.directory)
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", result, False)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
