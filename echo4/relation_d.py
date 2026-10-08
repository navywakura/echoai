"""RELATION-D preregistered exam. Opening D requires Roger's freeze approval.

Two new cohorts; thresholds fixed in docs/ECHO4-RELATION1-CD-DESIGN.md before
any cohort life is executed. Only the fresh-process audit receipt can grant
relation1_green. `dry` runs the identical pipeline on development seeds.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import unittest

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4.relation_help import B_ARMS
from echoai.echo4 import relation_b_bench as b
from echoai.echo4 import relation_c_bench as c

SCHEMA = "echo4-relation1-d-v1"
COHORTS = (tuple(range(263001, 263009)), tuple(range(263101, 263109)))
PARENT = ROOT / "lab/echo4/relation1-c-dev-v1"
PARENT_DIGEST = "ac7a1aab95f228270142d6dc49d05edf96287e5485b9cc06c0e3c3c9253df3cb"
LEARNED = b.LEARNED
FULL_MARGIN = 64      # per life, 192 B rounds, vs each learned arm and solo
GREEDY_MARGIN = 8     # per life, last 96 greedy rounds, vs other_only and shuffled
JOINT_MARGIN = 256    # per cohort, joint physical B net, vs each learned arm


def life(seed):
    arms = {arm: b.execute(seed, arm) for arm in B_ARMS}
    backwards = b.execute(seed, "history", reverse=True)
    return {"seed": seed,
            "a_parity": len({arms[a]["a_digest"] for a in B_ARMS}) == 1,
            "history_parity": len({tuple(arms[a]["relation_digests"]) for a in B_ARMS}) == 1,
            "order_invariant": (canonical(backwards["b_frames"]) == canonical(arms["history"]["b_frames"])
                                and backwards["a_digest"] == arms["history"]["a_digest"]),
            "checks": {a: arms[a]["checks"] for a in B_ARMS},
            "b": {a: arms[a]["b"] for a in B_ARMS}, "b_late": {a: arms[a]["b_late"] for a in B_ARMS},
            "a_whole": {a: arms[a]["a_whole"] for a in B_ARMS}}


def judge(lives):
    n = len(lives)
    focal = {a: sum(l["b"][a]["net"][0] for l in lives) for a in B_ARMS}
    late = {a: sum(l["b_late"][a]["net"][0] for l in lives) for a in B_ARMS}
    joint = {a: sum(l["b"][a]["joint_net"] for l in lives) for a in B_ARMS}
    whole = {a: sum(l["a_whole"][a]["net"][0] + l["b"][a]["net"][0] for l in lives) for a in B_ARMS}
    criteria = {
        "full_margin": all(focal["history"] - focal[a] >= FULL_MARGIN * n for a in (*LEARNED, "solo")),
        "greedy_margin": all(late["history"] - late[a] >= GREEDY_MARGIN * n for a in ("other_only", "shuffled")),
        "joint_margin": all(joint["history"] - joint[a] >= JOINT_MARGIN for a in LEARNED),
        "no_life_below_solo": all(l["b"]["history"]["net"][0] >= l["b"]["solo"]["net"][0] for l in lives),
        "integrity": all(l["a_parity"] and l["history_parity"] and l["order_invariant"]
                         and all(all(v.values()) for v in l["checks"].values()) for l in lives)}
    return {"lives": n, "focal_b_net": focal, "late_focal_b_net": late, "joint_b_net": joint,
            "whole_life_focal_net_published": whole,
            "private_credit_excluded": {a: [sum(l["b"][a]["private_credit_excluded"][i] for l in lives)
                                            for i in range(3)] for a in B_ARMS},
            "criteria": criteria, "passed": all(criteria.values())}


def sources():
    extras = ("echo4/relation_d.py", "tests/test_echo4_relation1c.py")
    return {**c.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or receipt["reproduction_sha256"] != PARENT_DIGEST
            or receipt["valid"] is not True or receipt["findings"] != [] or report["phase_c_valid"] is not True):
        raise ValueError("RELATION-C custody mismatch")
    c.parent()  # B and A custody
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def tests():
    names = ("echoai.tests.test_echo4_relation1a", "echoai.tests.test_echo4_relation1b",
             "echoai.tests.test_echo4_relation1c")
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def campaign(directory, cohorts=COHORTS, *, checking=False, progress=None):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "cohorts": cohorts,
                       "margins": {"full": FULL_MARGIN, "greedy": GREEDY_MARGIN, "joint": JOINT_MARGIN},
                       "contract": "docs/ECHO4-RELATION1-CD-DESIGN.md"})
    results = []
    for k, seeds in enumerate(cohorts):
        lives = []
        for seed in seeds:
            lives.append(life(seed))
            if progress:
                progress(k, seed)
        save(f"cohort{k}.json", lives)
        results.append(judge(lives))
    unit = tests()
    save("tests.json", unit)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    report = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "cohorts": results, "tests": unit,
              "criteria_passed": all(r["passed"] for r in results) and unit["passed"],
              "relation1_green": False, "note": "only the audit receipt may grant relation1_green"}
    report["reproduction_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    persist(directory, "report.json", report, checking)
    return report


def verify(directory):
    findings, value, passed = [], None, False
    try:
        report = read_json(directory / "report.json")
        unsigned = dict(report)
        value = unsigned.pop("reproduction_sha256")
        if hashlib.sha256(canonical(unsigned)).hexdigest() != value or report["schema"] != SCHEMA:
            raise ValueError("report digest/schema mismatch")
        if report["sources"] != sources() or report["parent"] != parent():
            raise ValueError("source/parent mismatch")
        for name, digest in report["artifacts"].items():
            if file_hash(directory / name) != digest:
                raise ValueError("artifact digest mismatch: " + name)
        lock = read_json(directory / "lock.json")
        cohorts = tuple(tuple(s) for s in lock["cohorts"])
        passed = campaign(directory, cohorts, checking=True)["criteria_passed"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    official = not findings and lock_is_exam(directory)
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "criteria_passed": bool(passed and not findings),
            "relation1_green": bool(passed and official),
            "scope": "RELATION C/D reconstruction with A/B/C custody"}


def lock_is_exam(directory):
    try:
        return tuple(tuple(s) for s in read_json(directory / "lock.json")["cohorts"]) == COHORTS
    except (OSError, KeyError, ValueError, TypeError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("exam", "dry", "verify"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command in ("exam", "dry"):
        args.directory.mkdir(parents=True, exist_ok=False)
        cohorts = COHORTS if args.command == "exam" else (b.DEVELOPMENT,)
        r = campaign(args.directory, cohorts, progress=lambda k, s: print("cohort", k, "seed", s, flush=True))
        print(json.dumps({"criteria_passed": r["criteria_passed"],
                          "cohorts": [{k: x[k] for k in ("focal_b_net", "late_focal_b_net", "joint_b_net", "criteria")}
                                      for x in r["cohorts"]], "reproduction_sha256": r["reproduction_sha256"]}, indent=1))
        return 0 if r["criteria_passed"] else 1
    r = verify(args.directory)
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", r, False)
    print(json.dumps(r, indent=2))
    return 0 if r["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
