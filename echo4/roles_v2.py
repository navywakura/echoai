"""ROLES-1 v2: the only change is native periodic exploration for the learner.

D v1 was red: a Q tie in a failure row plus no exploration after the evidence
budget (evidence_greedy=True) trapped one life. v2 builds every learner with
evidence_greedy=False. Everything else is v1 + C (veto fix), unchanged.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4 import roles as R
from echoai.echo4 import roles_bench as ab
from echoai.echo4 import roles_c_bench as c
from echoai.echo4 import roles_d as d
from echoai.echo4.roles_c import RolesCSession

SCHEMA_DEV = "echo4-roles1-v2-dev-v1"
SCHEMA_EXAM = "echo4-roles1-v2-d-v1"
DEVELOPMENT = (311, 323, 347)
COHORTS = (tuple(range(265001, 265009)), tuple(range(265101, 265109)))
PARENT = ROOT / "lab/echo4/roles1-d-v1"
PARENT_DIGEST = "168e978b6c160b321c1a244d878c8971ffdbf1bb239b43cca9af20c572119462"
DEV_DIR = ROOT / "lab/echo4/roles1-v2-dev-v1"


class RolesV2Session(RolesCSession):
    def __init__(self, seed, rounds, *, evidence_greedy=False, **kwargs):
        super().__init__(seed, rounds, **kwargs)
        if type(evidence_greedy) is not bool:
            raise ValueError("evidence_greedy flag")
        self.focal.evidence_greedy = evidence_greedy


def execute(seed, arm):
    with patch.object(d, "RolesCSession", RolesV2Session):
        return d.execute(seed, arm)


def life(seed):
    with patch.object(d, "RolesCSession", RolesV2Session):
        return d.life(seed)


def development(seeds=DEVELOPMENT):
    lives = []
    for seed in seeds:
        row = life(seed)
        arms = row["arms"]
        net = {a: arms[a]["summary"]["focal_net"] for a in R.ARMS}
        rec = {a: sum(arms[a]["summary"]["recovery"]) for a in R.ARMS}
        lives.append({"seed": seed, "focal_net": net, "recovery_total": rec,
                      "per_regime": {a: arms[a]["summary"]["per_regime"] for a in R.ARMS},
                      "beats": {a: net["competence"] > net[a] for a in R.ARMS if a != "competence"},
                      "recovers_faster": rec["competence"] < rec["cumulative"],
                      "integrity": row["deterministic"] and all(all(a["checks"].values()) for a in arms.values())})
    criterion = all(all(l["beats"].values()) and l["recovers_faster"] and l["integrity"] for l in lives)
    return {"lives": lives, "development_criterion": criterion}


def c0_v1_parity():
    """With evidence_greedy=True the v2 session reproduces the C v1 session exactly."""
    ok = True
    for seed in DEVELOPMENT:
        a = RolesCSession(seed, 192)
        b = RolesV2Session(seed, 192, evidence_greedy=True)
        ok &= all(a.step() == b.step() for _ in range(192))
    return {"passed": bool(ok)}


def witnesses():
    result = {"c0_v1_parity": c0_v1_parity()}
    with patch.object(c, "RolesCSession", RolesV2Session), patch.object(c, "SEEDS", DEVELOPMENT):
        for name, fn in c.WITNESSES.items():
            if name != "c0_nominal_parity":
                result[name] = fn()
    return result


def sources():
    extras = ("echo4/roles_v2.py", "tests/test_echo4_roles1_v2.py", "docs/ECHO4-ROLES1-V2-DESIGN.md")
    return {**d.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    if (report["reproduction_sha256"] != PARENT_DIGEST or receipt["reproduction_sha256"] != PARENT_DIGEST
            or receipt["valid"] is not True or receipt["roles1_green"] is not False or receipt["findings"] != []):
        raise ValueError("ROLES D v1 (red) custody mismatch")
    d.parent()
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def tests():
    names = ("echoai.tests.test_echo4_roles1", "echoai.tests.test_echo4_roles1c", "echoai.tests.test_echo4_roles1_v2")
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromNames(names))
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def sealed(directory, schema, body, *, checking):
    manifest, ancestry, artifacts = sources(), parent(), {}
    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)
    save("lock.json", {"schema": schema, "sources": manifest, "parent": ancestry, **body["lock"]})
    for name, value in body["artifacts"]().items():
        save(name, value)
    unit = tests()
    save("tests.json", unit)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    report = {"schema": schema, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "tests": unit, **body["report"](), "roles1_green": False}
    report["passed"] = report["passed"] and unit["passed"]
    report["reproduction_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    persist(directory, "report.json", report, checking)
    return report


def dev_campaign(directory, *, checking=False):
    cache = {}
    def artifacts():
        cache["dev"], cache["w"] = development(), witnesses()
        return {"development.json": cache["dev"], "witnesses.json": cache["w"]}
    def report():
        return {"lives": [{k: l[k] for k in ("seed", "focal_net", "recovery_total", "beats", "recovers_faster")}
                          for l in cache["dev"]["lives"]],
                "witnesses": {k: v["passed"] for k, v in cache["w"].items()},
                "passed": cache["dev"]["development_criterion"] and all(v["passed"] for v in cache["w"].values())}
    return sealed(directory, SCHEMA_DEV, {"lock": {"seeds": DEVELOPMENT, "scope": "v2 development + C witnesses"},
                                          "artifacts": artifacts, "report": report}, checking=checking)


def exam_campaign(directory, cohorts=COHORTS, *, checking=False):
    dev = read_json(DEV_DIR / "report.json")
    receipt = read_json(DEV_DIR / "audit-receipt.json")
    if not (dev["passed"] and receipt["valid"] and receipt["reproduction_sha256"] == dev["reproduction_sha256"]):
        raise ValueError("v2 development not sealed and valid")
    cache = {}
    def artifacts():
        cache["results"], out = [], {}
        for k, seeds in enumerate(cohorts):
            lives = [life(seed) for seed in seeds]
            out[f"cohort{k}.json"] = lives
            cache["results"].append(d.judge(lives))
        return out
    def report():
        return {"cohorts": cache["results"], "dev_digest": dev["reproduction_sha256"],
                "passed": all(r["passed"] for r in cache["results"])}
    return sealed(directory, SCHEMA_EXAM, {"lock": {"cohorts": cohorts, "dev_digest": dev["reproduction_sha256"],
                                                    "contract": "docs/ECHO4-ROLES1-V2-DESIGN.md"},
                                           "artifacts": artifacts, "report": report}, checking=checking)


def verify(directory, kind):
    findings, value, passed, official = [], None, False, False
    try:
        report = read_json(directory / "report.json")
        unsigned = dict(report)
        value = unsigned.pop("reproduction_sha256")
        if hashlib.sha256(canonical(unsigned)).hexdigest() != value:
            raise ValueError("report digest mismatch")
        if report["sources"] != sources() or report["parent"] != parent():
            raise ValueError("source/parent mismatch")
        for name, digest in report["artifacts"].items():
            if file_hash(directory / name) != digest:
                raise ValueError("artifact digest mismatch: " + name)
        if kind == "dev":
            passed = dev_campaign(directory, checking=True)["passed"]
        else:
            cohorts = tuple(tuple(s) for s in read_json(directory / "lock.json")["cohorts"])
            official = cohorts == COHORTS
            passed = exam_campaign(directory, cohorts, checking=True)["passed"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "criteria_passed": bool(passed and not findings),
            "roles1_green": bool(kind == "exam" and passed and official and not findings),
            "scope": f"ROLES-1 v2 {kind} reconstruction with full custody"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("dev", "exam", "verify-dev", "verify-exam", "explore"))
    parser.add_argument("directory", type=Path, nargs="?")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command == "explore":
        r = development()
        print(json.dumps({"criterion": r["development_criterion"],
                          "lives": [{k: l[k] for k in ("seed", "focal_net", "recovery_total", "per_regime")}
                                    for l in r["lives"]]}, indent=1))
        return 0
    if args.command in ("dev", "exam"):
        args.directory.mkdir(parents=True, exist_ok=False)
        r = (dev_campaign if args.command == "dev" else exam_campaign)(args.directory)
        print(json.dumps({k: v for k, v in r.items() if k not in ("sources", "parent", "artifacts", "tests")},
                         indent=1))
        return 0 if r["passed"] else 1
    r = verify(args.directory, "dev" if args.command == "verify-dev" else "exam")
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", r, False)
    print(json.dumps(r, indent=2))
    return 0 if r["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
