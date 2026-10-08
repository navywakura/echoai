"""ROLES-D preregistered exam. Opening D requires Roger's freeze approval.

Thresholds are fixed in docs/ECHO4-ROLES1-CD-DESIGN.md before any cohort life.
Uses RolesCSession (veto fix); nominal behaviour equals the sealed A/B session
(witness C0). Only the fresh-process audit receipt can grant roles1_green.
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
from echoai.echo4 import roles as R
from echoai.echo4 import roles_bench as ab
from echoai.echo4 import roles_c_bench as c
from echoai.echo4.roles_c import RolesCSession

SCHEMA = "echo4-roles1-d-v1"
COHORTS = (tuple(range(264001, 264009)), tuple(range(264101, 264109)))
PARENT = ROOT / "lab/echo4/roles1-c-dev-v1"
PARENT_DIGEST = "ba7225c4217a99786b85a63070e554588cf27783819ba333ae0ed205bd41e863"
NET_MARGIN = 256          # per life, vs every other arm
RECOVERY_MAX = 96         # per life, total over three drifts
LAST_REGIME_MIN = 72      # per life, successes of 96 in the last regime


def execute(seed, arm):
    s = RolesCSession(seed, ab.ROUNDS, arm=arm)
    frames = [s.step() for _ in range(ab.ROUNDS)]
    receipts = s.memory.receipts()
    summary = {"focal_net": sum(f["net"][0] for f in frames), "joint_net": sum(sum(f["net"]) for f in frames),
               "per_regime": [sum(f["output"][0] > 0 for f in frames[k:k + R.PERIOD])
                              for k in range(0, ab.ROUNDS, R.PERIOD)],
               "recovery": ab.recovery(frames), "private_credit_excluded": list(s.private_credit),
               "to_claimant": sum(f["assignee"] == s.claimant - 1 for f in frames)}
    checks = {"invariant": s.invariant(), "replay": ab.reconstruct(frames, receipts, arm, s.claimant),
              "claims_not_facts": s.memory.claimants() == {s.claimant},
              "drift_real": all(sum(a != b for a, b in zip(s.regimes[i], s.regimes[i + 1])) >= 2
                                for i in range(len(s.regimes) - 1))}
    return {"summary": summary, "checks": checks, "digest": c.nominal_digest(frames)}


def life(seed):
    arms = {arm: execute(seed, arm) for arm in R.ARMS}
    deterministic = execute(seed, "competence")["digest"] == arms["competence"]["digest"]
    return {"seed": seed, "deterministic": deterministic, "arms": arms}


def judge(lives):
    n = len(lives)
    net = {a: sum(l["arms"][a]["summary"]["focal_net"] for l in lives) for a in R.ARMS}
    rec = {a: sum(sum(l["arms"][a]["summary"]["recovery"]) for l in lives) for a in R.ARMS}
    last = sum(l["arms"]["competence"]["summary"]["per_regime"][-1] for l in lives)
    first = {a: sum(l["arms"][a]["summary"]["per_regime"][0] for l in lives) for a in R.ARMS}
    criteria = {
        "net_margin": all(net["competence"] - net[a] >= NET_MARGIN * n for a in R.ARMS if a != "competence"),
        "recovery": rec["competence"] <= RECOVERY_MAX * n and rec["competence"] < rec["cumulative"],
        "last_regime": last >= LAST_REGIME_MIN * n,
        "no_life_below_static": all(l["arms"]["competence"]["summary"]["focal_net"]
                                    >= l["arms"]["static_role"]["summary"]["focal_net"] for l in lives),
        "integrity": all(l["deterministic"] and all(all(a["checks"].values()) for a in l["arms"].values())
                         for l in lives)}
    return {"lives": n, "focal_net": net, "recovery_total": rec, "last_regime_competence": last,
            "first_regime_published": first,
            "joint_net_published": {a: sum(l["arms"][a]["summary"]["joint_net"] for l in lives) for a in R.ARMS},
            "criteria": criteria, "passed": all(criteria.values())}


def sources():
    return {**c.sources(), "echo4/roles_d.py": file_hash(ROOT / "echo4/roles_d.py")}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or receipt["reproduction_sha256"] != PARENT_DIGEST
            or receipt["valid"] is not True or receipt["findings"] != [] or report["phase_c_valid"] is not True):
        raise ValueError("ROLES-C custody mismatch")
    c.parent()
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def tests():
    names = ("echoai.tests.test_echo4_roles1", "echoai.tests.test_echo4_roles1c")
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromNames(names))
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def campaign(directory, cohorts=COHORTS, *, checking=False, progress=None):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "cohorts": cohorts,
                       "thresholds": {"net": NET_MARGIN, "recovery": RECOVERY_MAX, "last": LAST_REGIME_MIN},
                       "contract": "docs/ECHO4-ROLES1-CD-DESIGN.md"})
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
              "roles1_green": False, "note": "only the audit receipt may grant roles1_green"}
    report["reproduction_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    persist(directory, "report.json", report, checking)
    return report


def verify(directory):
    findings, value, passed, official = [], None, False, False
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
        cohorts = tuple(tuple(s) for s in read_json(directory / "lock.json")["cohorts"])
        official = cohorts == COHORTS
        passed = campaign(directory, cohorts, checking=True)["criteria_passed"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "criteria_passed": bool(passed and not findings),
            "roles1_green": bool(passed and official and not findings),
            "scope": "ROLES C/D reconstruction with RELATION and ROLES custody"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("exam", "dry", "verify"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command in ("exam", "dry"):
        args.directory.mkdir(parents=True, exist_ok=False)
        cohorts = COHORTS if args.command == "exam" else (ab.DEVELOPMENT,)
        r = campaign(args.directory, cohorts, progress=lambda k, s: print("cohort", k, "seed", s, flush=True))
        print(json.dumps({"criteria_passed": r["criteria_passed"],
                          "cohorts": [{k: x[k] for k in ("focal_net", "recovery_total", "last_regime_competence",
                                                         "first_regime_published", "criteria")}
                                      for x in r["cohorts"]], "reproduction_sha256": r["reproduction_sha256"]},
                         indent=1))
        return 0 if r["criteria_passed"] else 1
    r = verify(args.directory)
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", r, False)
    print(json.dumps(r, indent=2))
    return 0 if r["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
