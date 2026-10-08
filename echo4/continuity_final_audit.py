"""CONT-D source-locked A/B/C exam and independently reconstructive closure."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from echoai.echo4 import continuity_final_cases as cases

ROOT = cases.a.ROOT
SCHEMA = "echo4-continuity-final-v1"
PARENTS = {
    "continuity1-a-v1": "d6686ed530bf714b2feeb010d8c62647c83c14664936c03eea4e08b4d22c4d37",
    "continuity1-b-v1": "e36113d375f220d7d1b7f390b13818d7f1a2de480f51315d033aa5557697d3db",
    "continuity1-c-v1": "4c2bae3b6f68e74a30aa9712a42bdf0f47c9178b463b1af5459dab7639174b40",
    "self1-final-v1": "ff75512efa0709a4088e8fae2bc216d4072854713da831c244ac7c99672d71e0",
}
SELF_CERTIFICATE = "98ffc1ca438171a9bfb6a3926f5d3eef142f9338bc04827e311fc2bedec1a463"


def file_hash(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes(), object_pairs_hook=cases.a._unique_pairs,
                      parse_float=cases.a._no_float, parse_constant=cases.a._no_float)


def sources():
    extras = ("echo4/continuity_final_cases.py", "echo4/continuity_final_audit.py",
              "docs/ECHO4-CONTINUITY1-D-DESIGN.md", "docs/ECHO4-CONTINUITY1-D-PREFLIGHT.md",
              "tests/test_echo4_continuity1d.py")
    return {**cases.ab.bench_sources(), **cases.cb.sources(),
            **{name: file_hash(ROOT / name) for name in extras}}


def parents():
    result = {}
    for name, expected in PARENTS.items():
        directory = ROOT / "lab/echo4" / name
        if file_hash(directory / "report.json") != expected:
            raise ValueError("sealed parent report changed: " + name)
        report = read_json(directory / "report.json")
        if any(file_hash(ROOT / path) != sha for path, sha in report["sources"].items()):
            raise ValueError("sealed parent source changed: " + name)
        files = sorted(directory.glob("*.json")) + sorted(directory.glob("*.jsonl"))
        result[name] = {str(p.relative_to(ROOT)): file_hash(p) for p in files}
    certificate = read_json(ROOT / "lab/echo4/self1-final-v1/audit-receipt.json")
    if (certificate.get("self1_green") is not True or certificate.get("valid") is not True
            or certificate.get("reproduction_sha256") != SELF_CERTIFICATE):
        raise ValueError("missing original SELF closure")
    return result


def resumed(path, sha256, profile, horizon):
    result = subprocess.run([sys.executable, "-m", "echoai.echo4.continuity_final_audit", "resume",
                             str(Path(path).resolve()), sha256, profile, str(horizon)],
                            cwd=ROOT.parent, capture_output=True, text=True, timeout=180, check=True)
    return json.loads(result.stdout)


def evaluate(stage, case, path, *, checking=False):
    run, cost = cases.prepared(stage, case)
    raw, profile = run.dumps(), cases.kind(run)
    sha256 = cases.sha(raw)
    if checking:
        if path.read_bytes() != raw:
            raise ValueError(stage + "/" + case + ": checkpoint differs from reconstruction")
    else:
        run.save(path)
    loaded = cases.module(profile).loads(raw, expected_sha256=sha256)
    exact = loaded.dumps() == raw
    # Fresh subprocess continuation is compared to the original live run,
    # not to two reloads of the same potentially lossy serializer.
    reference = cases.trajectory(run, cases.STAGES[stage][2])
    restored = resumed(path, sha256, profile, cases.STAGES[stage][2])
    return {"case": case, "profile": profile, "preparation_cost": cost,
            "checkpoint_sha256": sha256, "checkpoint_bytes": len(raw), "roundtrip_exact": exact,
            "reference": reference, "restored": restored, "equal": reference == restored}


def stage_checks(rows, control, mutants):
    if any("error" in r for r in rows):
        return {"complete": False, "execution": False, "controls": control["passed"], "mutants": mutants["passed"]}
    indexed = {r["case"]: r["reference"] for r in rows}
    terminal_cases = ("nominal_terminal", "terminal", "terminal_fork")
    return {"complete": [r["case"] for r in rows] == list(cases.CASES),
            "exact_continuations": all(r["roundtrip_exact"] and r["equal"] for r in rows),
            "invariants": all(r["reference"]["balanced"] and not any(r["reference"][k]
                for k in ("cortex_calls", "false_facts", "destroyed")) for r in rows),
            "terminal_preserved": all(indexed[n]["terminal"] and not indexed[n]["events"] for n in terminal_cases),
            "stops_preserved": not indexed["veto"]["events"] and not indexed["stopped"]["events"],
            "abstention_preserved": not indexed["ambiguous"]["events"] and not indexed["cancelled"]["events"],
            "quarantine_preserved": all(indexed[n]["quarantined"] and len(indexed[n]["events"]) == 1
                and indexed[n]["events"][0]["event"] == "quarantine_block"
                for n in ("body_quarantine", "descendant_quarantine")),
            "fork_physics": cases.physical(indexed["fork_left"]) == cases.physical(indexed["fork_right"]),
            "fork_identity": indexed["fork_left"]["scope"] != indexed["fork_right"]["scope"],
            "controls": control["passed"], "mutants": mutants["passed"]}


def stage(name, directory, emit, progress, *, checking=False):
    rows = []
    for case in cases.CASES:
        progress(name + "/" + case)
        try:
            row = evaluate(name, case, directory / (name + "-" + case + ".json"), checking=checking)
        except (ValueError, RuntimeError, AssertionError, OSError, subprocess.SubprocessError) as exc:
            if checking:
                raise ValueError(name + "/" + case + ": " + str(exc)) from exc
            row = {"case": case, "error": str(exc), "equal": False}
        rows.append(row)
        emit({"event": "case", "stage": name, "row": row})
        if "error" in row:
            break
    control, mutants = cases.controls(name), cases.mutant_suite(name)
    emit({"event": "controls", "stage": name, "control": control, "mutants": mutants})
    checks = stage_checks(rows, control, mutants)
    return {"cases": rows, "control": control, "mutants": mutants,
            "checks": checks, "passed": all(checks.values())}


def campaign(directory, emit, progress, *, smoke=False, checking=False):
    manifest, ancestry = sources(), parents()
    stages = {"A": stage("A", directory, emit, progress, checking=checking)}
    lock = None
    if not smoke and stages["A"]["passed"]:
        if manifest != sources() or ancestry != parents():
            raise ValueError("sources/parents changed before lock")
        lock = {"event": "freeze_before_B", "sources": manifest, "parents": ancestry,
                "A_sha256": cases.c.digest(stages["A"]), "scope": cases.SCOPE}
        emit(lock)  # recorder fsyncs this before any B recipe runs
        for name in ("B", "C"):
            if manifest != sources() or ancestry != parents():
                raise ValueError("lock changed; another version/exam is required")
            stages[name] = stage(name, directory, emit, progress, checking=checking)
            if not stages[name]["passed"]:
                break
    unchanged = manifest == sources() and ancestry == parents()
    eligible = (not smoke and lock is not None and list(stages) == ["A", "B", "C"]
                and unchanged and all(s["passed"] for s in stages.values()))
    return {"schema": SCHEMA, "profile": "smoke" if smoke else "campaign", "scope": cases.SCOPE,
            "sources": manifest, "parents": ancestry, "stages": stages,
            "lock_sha256": None if lock is None else cases.c.digest(lock),
            "sources_and_parents_unchanged": unchanged, "closure_eligible": eligible,
            "continuity1_green": False}


def record(directory, *, smoke=False, progress=lambda value: None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    trace_hash = hashlib.sha256()
    with (directory / "traces.jsonl").open("xb") as trace:
        def emit(value):
            raw = cases.a.canonical(value) + b"\n"
            trace.write(raw)
            trace.flush()
            if value["event"] == "freeze_before_B":
                os.fsync(trace.fileno())
            trace_hash.update(raw)
        report = campaign(directory, emit, progress, smoke=smoke)
    report["trace_sha256"] = trace_hash.hexdigest()
    report["reproduction_sha256"] = cases.c.digest(report)
    with (directory / "report.json").open("xb") as handle:
        handle.write(cases.a.canonical(report))
    return report


def verify(directory, *, progress=lambda value: None):
    stored, audits, findings = {}, {}, []
    try:
        directory = Path(directory)
        stored = read_json(directory / "report.json")
        if (type(stored) is not dict or stored.get("schema") != SCHEMA
                or stored.get("profile") not in ("smoke", "campaign")):
            raise ValueError("invalid final report")
        if stored.get("sources") != sources() or stored.get("parents") != parents():
            raise ValueError("source/parent mismatch")
        trace_hash = hashlib.sha256()
        with (directory / "traces.jsonl").open("rb") as trace:
            def emit(value):
                raw = cases.a.canonical(value) + b"\n"
                if trace.readline() != raw:
                    raise ValueError("journal differs from complete replay")
                trace_hash.update(raw)
            rebuilt = campaign(directory, emit, progress, smoke=stored["profile"] == "smoke", checking=True)
            if trace.read(1):
                raise ValueError("unexpected trailing journal")
        rebuilt["trace_sha256"] = trace_hash.hexdigest()
        rebuilt["reproduction_sha256"] = cases.c.digest(rebuilt)
        if cases.a.canonical(stored) != cases.a.canonical(rebuilt):
            raise ValueError("report differs from complete replay")
        if stored["profile"] == "campaign":
            for name, implementation in (("continuity1-a-v1", cases.ab),
                                         ("continuity1-b-v1", cases.bb),
                                         ("continuity1-c-v1", cases.cb)):
                progress("Replaying ancestor " + name)
                audit = implementation.verify(ROOT / "lab/echo4" / name)
                audits[name] = audit
                if audit.get("valid") is not True:
                    raise ValueError("ancestor failed: " + name)
        if stored["sources"] != sources() or stored["parents"] != parents():
            raise ValueError("source/parent changed during audit")
    except (OSError, ValueError, TypeError, KeyError, IndexError, RuntimeError, subprocess.SubprocessError) as exc:
        findings.append(str(exc))
    green = (not findings and stored.get("closure_eligible") is True and len(audits) == 3)
    return {"valid": not findings, "findings": findings, "continuity1_green": green,
            "scope": cases.SCOPE, "parent_audits": audits,
            "self_binding": "existing certificate and full source/artifact integrity; not new SELF replay",
            "reproduction_sha256": stored.get("reproduction_sha256") if not findings else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("campaign", "verify"):
        command = sub.add_parser(name)
        command.add_argument("directory", type=Path)
        if name == "campaign":
            command.add_argument("--smoke", action="store_true")
        else:
            command.add_argument("--write-receipt", action="store_true")
    child = sub.add_parser("resume")
    child.add_argument("path", type=Path)
    child.add_argument("digest")
    child.add_argument("profile", choices=("A", "B", "C"))
    child.add_argument("horizon", type=int)
    args = parser.parse_args()
    progress = lambda value: print(value, file=sys.stderr, flush=True)
    if args.command == "resume":
        run = cases.module(args.profile).load(args.path, expected_sha256=args.digest)
        result = cases.trajectory(run, args.horizon)
    elif args.command == "campaign":
        report = record(args.directory, smoke=args.smoke, progress=progress)
        result = {"closure_eligible": report["closure_eligible"], "continuity1_green": False,
                  "stages": {k: {"passed": v["passed"], "checks": v["checks"]} for k, v in report["stages"].items()},
                  "reproduction_sha256": report["reproduction_sha256"]}
    else:
        result = verify(args.directory, progress=progress)
        if args.write_receipt:
            with (args.directory / "audit-receipt.json").open("xb") as handle:
                handle.write(cases.a.canonical(result))
    print(json.dumps(result, sort_keys=True))
    if result.get("valid") is False or args.command == "campaign" and not args.smoke and not result["closure_eligible"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
