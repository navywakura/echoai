"""Source-locked INTERACTION B/C/D campaign and fresh-process reconstruction."""
import argparse
import io
import json
from pathlib import Path
import unittest

from echoai.echo4 import interaction_bench as a
from echoai.echo4 import interaction_cases as cases
from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import read_json, file_hash
from echoai.echo4.dream_bench import persist
from echoai.echo4.interaction_learning import ARMS

SCHEMA = "echo4-interaction1-bcd-v1"
PARENT = ROOT / "lab/echo4/interaction1-a-v1"
PARENT_DIGEST = "da8cc00befb52ac1abc9942bae1aa8eacf3fbe2049501dfebd26c2a1ed57c1c3"
TEST_MODULE = "echoai.tests.test_echo4_interaction1bcd"


def sources():
    extras = ("echo4/interaction_learning.py", "echo4/interaction_social.py", "echo4/interaction_cases.py",
              "echo4/interaction_final.py", "tests/test_echo4_interaction1bcd.py",
              "docs/ECHO4-INTERACTION1-BCD-DESIGN.md")
    return {**a.sources(), **{p: file_hash(ROOT / p) for p in extras}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    unsigned = dict(report)
    value = unsigned.pop("reproduction_sha256")
    if (value != PARENT_DIGEST or a.sha(unsigned) != value
            or receipt["valid"] is not True or receipt["phase_a_valid"] is not True
            or receipt["interaction1_green"] is not False or receipt["findings"] != []
            or receipt["reproduction_sha256"] != value
            or report["sources"] != a.sources() or report["parent"] != a.parent()):
        raise ValueError("INTERACTION-A custody mismatch")
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def unit_checks():
    suite = unittest.defaultTestLoader.loadTestsFromName(TEST_MODULE)
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return {"tests": result.testsRun, "failures": [(str(t), e) for t, e in result.failures],
            "errors": [(str(t), e) for t, e in result.errors], "skipped": result.skipped,
            "passed": result.wasSuccessful() and result.testsRun > 0 and not result.skipped}


def compact_cohort(value):
    return {"seeds": value["seeds"], "totals": value["totals"], "checks": value["checks"],
            "passed": value["passed"], "lives": [
                {"seed": l["seed"], "arms": {arm: {k: v for k, v in row.items() if k != "frames"}
                                               for arm, row in l["arms"].items()}} for l in value["lives"]]}


def campaign(directory, *, checking=False, progress=None):
    manifest, ancestry = sources(), parent()
    artifacts = {}

    def save(name, value):
        artifacts[name] = persist(directory, name, value, checking)

    save("lock.json", {"schema": SCHEMA, "sources": manifest, "parent": ancestry,
                       "development": cases.DEVELOPMENT, "cohorts": cases.COHORTS,
                       "rounds": cases.ROUNDS, "formation": cases.FORMATION,
                       "margin_per_life": cases.MARGIN, "arms": ARMS,
                       "scope": "asymmetric one-step native interaction; private credits excluded"})
    b = cases.cohort(cases.DEVELOPMENT, progress=progress)
    save("b-development.json", b)
    c, tests = cases.adverse(), unit_checks()
    save("c-limits.json", c)
    save("c-tests.json", tests)
    eligible = b["passed"] and c["passed"] and tests["passed"]
    exams = []
    if eligible:
        # Preflight results are durable BEFORE opening any held-out seed.
        for index, seeds in enumerate(cases.COHORTS, 1):
            result = cases.cohort(seeds, progress=progress)
            save(f"d-cohort-{index}.json", result)
            exams.append(compact_cohort(result))
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources/parent changed during campaign")
    result = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "artifacts": artifacts,
              "b": compact_cohort(b), "c": {"witnesses_passed": c["passed"],
                                              "cases": len(c["cases"]), "tests": tests},
              "d_opened": bool(eligible), "d": exams,
              "criteria_passed": bool(eligible and len(exams) == 2 and all(e["passed"] for e in exams)),
              "interaction1_green": False, "closure_requires_fresh_process_audit": True,
              "accounting": {"development_native_steps_with_reverse": len(cases.DEVELOPMENT) * len(ARMS) * 2880,
                             "exam_native_steps_with_reverse": sum(len(e["seeds"]) for e in exams) * len(ARMS) * 2880,
                             "adverse_native_steps": sum(r["native_steps"] for r in c["cases"].values()),
                             "unit_checks": "additional deterministic development-only tests; not scored exam lives"},
              "subjective_consciousness_tested": False, "integrated_agent_tested": False}
    result["reproduction_sha256"] = a.sha(result)
    persist(directory, "report.json", result, checking)
    return result


def check_header(directory):
    report = read_json(directory / "report.json")
    unsigned = dict(report)
    value = unsigned.pop("reproduction_sha256")
    if report["schema"] != SCHEMA or a.sha(unsigned) != value:
        raise ValueError("report digest/schema mismatch")
    if report["sources"] != sources() or report["parent"] != parent():
        raise ValueError("source/parent mismatch")
    expected = {"lock.json", "b-development.json", "c-limits.json", "c-tests.json"}
    if report["d_opened"] is True:
        expected |= {"d-cohort-1.json", "d-cohort-2.json"}
    if set(report["artifacts"]) != expected:
        raise ValueError("artifact names mismatch")
    for name, digest in report["artifacts"].items():
        if file_hash(directory / name) != digest:
            raise ValueError("artifact digest mismatch: " + name)
    return report


def verify(directory, *, progress=None):
    findings, value, criteria = [], None, False
    try:
        report = check_header(directory)
        value = report["reproduction_sha256"]
        rebuilt = campaign(directory, checking=True, progress=progress)
        criteria = rebuilt["criteria_passed"]
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, IndexError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": value,
            "interaction1_green": bool(criteria and not findings),
            "scope": "native reconstruction of B/C/D, custody of A; no subjective consciousness claim"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("campaign", "verify"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    def progress(seed):
        print(f"completed seed {seed}", flush=True)
    if args.command == "campaign":
        if args.write_receipt:
            parser.error("audit must run in a fresh process")
        args.directory.mkdir(parents=True, exist_ok=False)
        result = campaign(args.directory, progress=progress)
        print(json.dumps({k: result[k] for k in ("criteria_passed", "interaction1_green", "reproduction_sha256")}, indent=2))
        return 0 if result["criteria_passed"] else 1
    result = verify(args.directory, progress=progress)
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", result, False)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] and result["interaction1_green"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
