"""ROLES-1 A/B development bench. Development seeds only; never an exam."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import unittest

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4 import relation_d as parent_module
from echoai.echo4.roles import (RolesSession, ARMS, PERIOD, SELF, last_attempt, cumulative_success,
                                row, settle, competent, UNKNOWN)

SCHEMA = "echo4-roles1-ab-dev-v2"  # v1 audit rejected float means; kept, not overwritten
PARENT = ROOT / "lab/echo4/relation1-d-v1"
PARENT_DIGEST = "42a6efc51d7bbbe413d104fdb099039cf02f5b670e2a8e6245fd8f2526c48345"
DEVELOPMENT = (211, 223, 241)
ROUNDS = 384
RUN = 6  # recovery = rounds after a drift until 6 consecutive successes begin
LEARNED = ("cumulative", "static_role", "claimed_rank")


def recovery(frames):
    result = []
    for start in range(PERIOD, len(frames), PERIOD):
        window = frames[start:start + PERIOD]
        found = PERIOD
        for i in range(len(window) - RUN + 1):
            if all(f["output"][0] > 0 for f in window[i:i + RUN]):
                found = i
                break
        result.append(found)
    return result


def reconstruct(frames, receipts, arm, claimant):
    """Rebuild evidence, rows and settlements from the learner's own receipts."""
    for f in frames:
        prior = [r for r in receipts if r["tick"] < f["tick"]]
        if arm == "competence":
            evidence = last_attempt(prior, f["type"])
        elif arm == "cumulative":
            evidence = cumulative_success(prior, f["type"])
        elif arm == "claimed_rank":
            evidence = claimant - 1
        else:
            evidence = UNKNOWN
        spent0 = f["paid"][0]
        before = tuple(f["ledger"][i] + f["paid"][i] for i in range(3))
        if f["evidence"] != evidence or f["row"] != row(arm, f["type"], before[0], evidence=evidence).hex():
            return False
        event = settle(f["assignee"], f["accepted"], f["competent"] == f["assignee"], before)
        if any(event[k] != f[k] for k in event) or spent0 != event["paid"][0]:
            return False
    return True


def execute(seed, arm, rounds=ROUNDS):
    s = RolesSession(seed, rounds, arm=arm)
    frames = [s.step() for _ in range(rounds)]
    receipts = s.memory.receipts()
    per_regime = [sum(f["output"][0] > 0 for f in frames[k:k + PERIOD]) for k in range(0, rounds, PERIOD)]
    summary = {"focal_net": sum(f["net"][0] for f in frames),
               "joint_net": sum(sum(f["net"]) for f in frames),
               "successes": sum(f["output"][0] > 0 for f in frames), "per_regime": per_regime,
               "recovery": recovery(frames), "delegated": sum(f["assignee"] != SELF for f in frames),
               "declined": sum(f["accepted"] is False for f in frames),
               "counterpart_paid": [sum(f["paid"][i] for f in frames) for i in (1, 2)],
               "private_credit_excluded": list(s.private_credit),
               "to_claimant": sum(f["assignee"] == s.claimant - 1 for f in frames)}
    checks = {"invariant": s.invariant(), "replay": reconstruct(frames, receipts, arm, s.claimant),
              "claims_not_facts": s.memory.claimants() == {s.claimant} and s.memory.claims == rounds,
              "drift_real": all(sum(a != b for a, b in zip(s.regimes[i], s.regimes[i + 1])) >= 2
                                for i in range(len(s.regimes) - 1))}
    digest = hashlib.sha256(canonical(frames)).hexdigest()
    return {"seed": seed, "arm": arm, "frames": frames, "summary": summary, "checks": checks, "digest": digest}


def development(seeds=DEVELOPMENT, *, progress=None):
    lives = []
    for seed in seeds:
        arms = {arm: execute(seed, arm) for arm in ARMS}
        repeat = execute(seed, "competence")["digest"] == arms["competence"]["digest"]
        net = {a: arms[a]["summary"]["focal_net"] for a in ARMS}
        rec = {a: sum(arms[a]["summary"]["recovery"]) for a in ARMS}  # integer total over drifts
        beats = {a: net["competence"] > net[a] for a in ARMS if a != "competence"}
        lives.append({"seed": seed, "deterministic": repeat, "focal_net": net, "recovery_total": rec,
                      "beats": beats, "recovers_faster_than_cumulative": rec["competence"] < rec["cumulative"],
                      "arms": {a: {"summary": arms[a]["summary"], "checks": arms[a]["checks"],
                                   "digest": arms[a]["digest"]} for a in ARMS}})
        if progress:
            progress(seed, net)
    criterion = all(all(l["beats"].values()) and l["recovers_faster_than_cumulative"] and l["deterministic"]
                    and all(all(v["checks"].values()) for v in l["arms"].values()) for l in lives)
    return {"lives": lives, "development_criterion": criterion, "roles1_green": False}


def sources():
    extras = ("echo4/roles.py", "echo4/roles_bench.py", "tests/test_echo4_roles1.py",
              "docs/ECHO4-ROLES1-AB-DESIGN.md")
    return {**parent_module.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or receipt["reproduction_sha256"] != PARENT_DIGEST
            or receipt["valid"] is not True or receipt["relation1_green"] is not True or receipt["findings"] != []):
        raise ValueError("RELATION custody mismatch")
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def tests():
    suite = unittest.defaultTestLoader.loadTestsFromName("echoai.tests.test_echo4_roles1")
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def campaign(directory, *, checking=False):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "seeds": DEVELOPMENT,
                       "rounds": ROUNDS, "scope": "ROLES A/B development; never an exam; C/D unopened"})
    result, unit = development(), tests()
    save("development.json", result)
    save("tests.json", unit)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    report = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "lives": [{k: l[k] for k in ("seed", "focal_net", "recovery_total", "beats",
                                           "recovers_faster_than_cumulative", "deterministic")}
                        for l in result["lives"]],
              "tests": unit, "development_criterion": result["development_criterion"] and unit["passed"],
              "roles1_green": False, "exam_opened": False}
    report["reproduction_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    persist(directory, "report.json", report, checking)
    return report


def verify(directory):
    findings, value = [], None
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
        campaign(directory, checking=True)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "roles1_green": False, "scope": "ROLES A/B development reconstruction; not an exam"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("campaign", "verify", "explore"))
    parser.add_argument("directory", type=Path, nargs="?")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command == "explore":
        r = development(progress=lambda s, n: print(s, json.dumps(n), flush=True))
        print(json.dumps({"criterion": r["development_criterion"],
                          "recovery": [l["recovery_total"] for l in r["lives"]]}))
        return 0
    if args.command == "campaign":
        args.directory.mkdir(parents=True, exist_ok=False)
        r = campaign(args.directory)
        print(json.dumps({k: r[k] for k in ("lives", "development_criterion", "reproduction_sha256")}, indent=1))
        return 0 if r["development_criterion"] else 1
    r = verify(args.directory)
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", r, False)
    print(json.dumps(r, indent=2))
    return 0 if r["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
