"""SELF-B development census and fresh replay; never a full SELF green."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from dataclasses import asdict
import hashlib
from itertools import product
import json
from pathlib import Path

from echoai.core.cam import Cam
from echoai.echo4.boundary import BoundaryMap
from echoai.echo4.boundary_world import Experiment, packet, run_pair
from echoai.echo4.self_audit import SOURCES as PREVIOUS_SOURCES, canonical, cam_hash, private_cause
from echoai.echo4.self_attribution import CATALOG, ProbePlan, SelfAttributor
from echoai.echo4.self_model import SelfChangeMonitor
from echoai.echo4.self_probe_world import run_probe
from echoai.echo4.world import Body

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (*PREVIOUS_SOURCES, "docs/ECHO4-SELF1-B-DESIGN.md", "echo4/self_attribution.py",
           "echo4/self_probe_agent.py", "echo4/self_probe_world.py", "echo4/self_probe_audit.py",
           "tests/test_echo4_self1b.py")
MODES = ("active", "wait_only", "without_long_reference", "fixed")


def sources():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def public(trace):
    value = asdict(trace)
    value["packets"] = [p.hex() for p in trace.packets]
    return value


def calibrate(body):
    monitor = SelfChangeMonitor(BoundaryMap(Cam()))
    for action in (0, 1):
        for i in range(1, 9):
            monitor.calibrate(run_pair(Experiment(body, action), 8 * action + i)[0])
    monitor.seal()
    trace, _ = run_probe(body, ProbePlan(17, 0, CATALOG[0], 0, 0))
    return monitor, trace


def run_condition(model, body, hc, tc, heat, *, mode):
    traces = []
    truth_retained = True
    terminalities = 0
    for token in range(18, 24):
        plan = model.choose(token, mode=mode if mode in ("fixed", "wait_only") else "active")
        if plan is None:
            break
        # Logged pre-execution. The physical executor cannot inform this choice.
        prior = model.diagnosis()
        before = {"plan": asdict(plan), "diagnosis": prior,
                  "forecast_sha256": hashlib.sha256(canonical((model.pending[1], model.pending[2]))).hexdigest()}
        receipt, private = run_probe(body, plan, h_coupled=hc, temperature_coupled=tc, heat=heat)
        result = model.consume(receipt)
        # Evaluator-only checks. Never passed back as teaching signals.
        truth_retained &= (body.h, hc) in model.h_candidates and (body.temperature, tc, heat) in model.t_candidates
        terminalities += sum(receipt.terminal)
        traces.append({"before_execution": before, "public": public(receipt),
                       "private_audit_only": private, "after": result})
    return {"diagnosis": model.diagnosis(), "probes": traces,
            "truth_retained": truth_retained, "terminalities": terminalities,
            "resources": model.resources()}


def metrics():
    return {"total": 0, "correct": 0, "unknown": 0, "wrong": 0, "actions": 0,
            "probes": 0, "terminalities": 0, "truth_retained": 0,
            "max_actions": 0, "max_probes": 0,
            "by_cause": {name: {"total": 0, "correct": 0, "unknown": 0, "wrong": 0}
                         for name in ("nominal", "own", "external", "mixed")},
            "sequences": Counter()}


def accumulate(result, outcome, truth):
    diagnosis = outcome["diagnosis"]
    label = diagnosis["label"]
    for target in (result, result["by_cause"][truth]):
        target["total"] += 1
        target["correct"] += label == truth
        target["unknown"] += label == "unknown"
        target["wrong"] += label not in (truth, "unknown")
    result["actions"] += diagnosis["executed_ticks"]
    result["probes"] += diagnosis["probes"]
    result["max_actions"] = max(result["max_actions"], diagnosis["executed_ticks"])
    result["max_probes"] = max(result["max_probes"], diagnosis["probes"])
    result["terminalities"] += outcome["terminalities"]
    result["truth_retained"] += outcome["truth_retained"]
    result["sequences"]["".join(str(probe["before_execution"]["plan"]["index"]) for probe in outcome["probes"])] += 1


def census(*, quick=False, emit=lambda record: None):
    manifest = sources()
    report = {"schema": "e4-self1-b-v1", "profile": "smoke" if quick else "development-census",
              "sources": manifest, "self1_green": False,
              "controllers": {mode: metrics() for mode in MODES},
              "initial_states": 0, "nominal_actions_per_initial": 72,
              "nominal_preserved": 0, "facts": 0, "destroyed": 0,
              "witness": [], "max_h_candidates": 0, "max_t_candidates": 0}
    hs, ts = ((30, 38), (48, 50, 52)) if quick else (range(29, 41), range(40, 73))
    for h, theta in product(hs, ts):
        body = Body(h, theta)
        reference, nominal = calibrate(body)
        emit({"phase": "nominal", "initial_private": asdict(body), "long_reference": public(nominal),
              "reference_sha256": reference.model_hash()})
        preserved = reference.model_hash(), cam_hash(reference.boundary.cam)
        base = SelfAttributor(reference, packet(body), nominal)
        short_base = SelfAttributor(reference, packet(body), None)
        report["initial_states"] += 1
        report["max_h_candidates"] = max(report["max_h_candidates"], len(base.h_candidates), len(short_base.h_candidates))
        report["max_t_candidates"] = max(report["max_t_candidates"], len(base.t_candidates), len(short_base.t_candidates))
        for hc, tc, heat in product((True, False), (True, False), (-16, -4, 0, 4, 16)):
            truth = private_cause(hc, tc, heat)
            runs = {}
            for mode in MODES:
                model = copy.deepcopy(short_base if mode == "without_long_reference" else base)
                outcome = run_condition(model, body, hc, tc, heat, mode=mode)
                accumulate(report["controllers"][mode], outcome, truth)
                runs[mode] = outcome
            emit({"phase": "diagnosis", "private_audit_only": {"initial": asdict(body),
                  "h_coupled": hc, "temperature_coupled": tc, "heat": heat, "cause": truth}, "runs": runs})
        report["nominal_preserved"] += preserved == (reference.model_hash(), cam_hash(reference.boundary.cam))
        report["facts"] += sum(s.has_fact for s in reference.boundary.cam.slot if s.occupied)
        report["destroyed"] += reference.boundary.cam.destroyed
    # The concrete old ambiguity witness, separately reported in every profile.
    body = Body(37, 65)
    reference, nominal = calibrate(body)
    for hc, heat in ((True, 0), (False, 0), (True, 4), (False, 4)):
        outcome = run_condition(SelfAttributor(reference, packet(body), nominal), body, hc, True, heat, mode="active")
        report["witness"].append({"truth": private_cause(hc, True, heat), "outcome": outcome})
    active = report["controllers"]["active"]
    report["sources_unchanged"] = manifest == sources()
    report["checks"] = {
        "complete": all(r["total"] == (120 if quick else 7920) for r in report["controllers"].values()),
        "no_wrong_attribution": all(r["wrong"] == 0 for r in report["controllers"].values()),
        "coverage": 100 * active["correct"] >= 75 * active["total"],
        "each_cause": all(100 * c["correct"] >= 50 * c["total"] for c in active["by_cause"].values()),
        "witness_resolved": all(w["truth"] == w["outcome"]["diagnosis"]["label"] for w in report["witness"]),
        "truth_survives": all(r["truth_retained"] == r["total"] for r in report["controllers"].values()),
        "no_terminal": all(r["terminalities"] == 0 for r in report["controllers"].values()),
        "bounded": report["max_h_candidates"] <= 64 and report["max_t_candidates"] <= 160 and
                   all(r["max_actions"] <= 48 and r["max_probes"] <= 6 for r in report["controllers"].values()),
        "preserved": report["nominal_preserved"] == report["initial_states"] and report["facts"] == report["destroyed"] == 0,
        "sources": report["sources_unchanged"],
    }
    report["diagnostic_checks_passed"] = all(report["checks"].values())
    return report


def record(output: Path, *, quick=False):
    output.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256()
    with (output / "traces.jsonl").open("xb") as trace:
        def emit(value):
            raw = canonical(value)
            trace.write(raw)
            digest.update(raw)
        report = census(quick=quick, emit=emit)
    report["trace_sha256"] = digest.hexdigest()
    report["reproduction_sha256"] = hashlib.sha256(canonical(report)).hexdigest()
    with (output / "report.json").open("xb") as handle:
        handle.write(canonical(report))
    return report


def verify(output: Path):
    findings = []
    try:
        stored = json.loads((output / "report.json").read_bytes())
        if stored.get("sources") != sources() or stored.get("profile") not in ("smoke", "development-census"):
            raise ValueError("source manifest/profile mismatch")
        digest = hashlib.sha256()
        with (output / "traces.jsonl").open("rb") as trace:
            def emit(value):
                raw = canonical(value)
                if trace.readline() != raw:
                    raise ValueError("replay/trace mismatch")
                digest.update(raw)
            rebuilt = census(quick=stored["profile"] == "smoke", emit=emit)
            if trace.read(1):
                raise ValueError("unexpected trailing trace")
        rebuilt["trace_sha256"] = digest.hexdigest()
        rebuilt["reproduction_sha256"] = hashlib.sha256(canonical(rebuilt)).hexdigest()
        if canonical(stored) != canonical(rebuilt):
            raise ValueError("report differs from full replay")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "self1_green": False,
            "reproduction_sha256": stored.get("reproduction_sha256") if not findings else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("census", "verify"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command == "census":
        report = record(args.directory, quick=args.quick)
        ok = report["diagnostic_checks_passed"]
    else:
        report = verify(args.directory)
        ok = report["valid"]
        if args.write_receipt:
            with (args.directory / "audit-receipt.json").open("xb") as handle:
                handle.write(canonical(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
