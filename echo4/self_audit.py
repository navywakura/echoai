"""SELF-A identifiability census. Private truth never enters SelfChangeMonitor.

This is development evidence, not the E4-SELF-1 attribution/recovery exam.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
from itertools import product
import json
from pathlib import Path

from echoai.core.cam import Cam
from echoai.core.wsp import unpack
from echoai.echo4.boundary import BoundaryMap, public_record
from echoai.echo4.boundary_bench import SOURCES as BOUNDARY_SOURCES
from echoai.echo4.boundary_world import Experiment, run_pair
from echoai.echo4.self_model import SelfChangeMonitor
from echoai.echo4.world import Body

ROOT = Path(__file__).resolve().parents[1]
CAUSES = ("nominal", "own", "external", "mixed")
COUPLINGS = ((True, True), (True, False), (False, True), (False, False))
HEAT = (-16, -4, 0, 4, 16)
SOURCES = (*BOUNDARY_SOURCES, "docs/ECHO4-SELF1-DESIGN.md", "echo4/self_model.py",
           "echo4/self_agent.py", "echo4/self_audit.py", "tests/test_echo4_self1.py")


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sources() -> dict:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def cam_hash(cam) -> str:
    value = {"slots": [(i, asdict(s)) for i, s in enumerate(cam.slot) if s.occupied],
             "keys": sorted((key.hex(), slot) for key, slot in cam.key_index.items()),
             "used": cam.used, "destroyed": cam.destroyed}
    raw = json.dumps(value, sort_keys=True, default=lambda x: x.hex()).encode()
    return hashlib.sha256(raw).hexdigest()


def normalized(pair) -> dict:
    result = public_record(pair)
    # Opaque independent experiment nonces cannot encode the cause.
    result["identifier"] = 1
    for name in ("treatment", "reference"):
        result[name]["token"] = 1
    return result


def private_cause(h_coupled: bool, temperature_coupled: bool, heat: int) -> str:
    own = not (h_coupled and temperature_coupled)
    external = heat != 0
    return "mixed" if own and external else "own" if own else "external" if external else "nominal"


def expected_change(before, after) -> tuple[int, int]:
    """Judge reads actual WSP components independently of monitor.signature."""
    decoded = [{arm: [unpack(p)["E"] for p in getattr(pair, arm).packets]
                for arm in ("treatment", "reference")} for pair in (before, after)]
    reference_mask = effect_mask = 0
    for offset, name in enumerate(("U", "B")):
        for tick in (1, 2):
            ref, effect = [], []
            for era in decoded:
                drift = era["reference"][tick][name] - era["reference"][0][name]
                contrast = era["treatment"][tick][name] - era["treatment"][0][name] - drift
                ref.append(drift)
                effect.append(contrast)
            if ref[0] != ref[1]:
                reference_mask |= 1 << (8 + offset)
            if effect[0] != effect[1]:
                effect_mask |= 1 << (8 + offset)
    return reference_mask, effect_mask


def add_group(groups, key, condition):
    group = groups.setdefault(key, {"counts": Counter(), "examples": {}})
    cause = condition["cause"]
    group["counts"][cause] += 1
    group["examples"].setdefault(cause, condition)


def group_report(groups, *, witnesses=6) -> dict:
    ambiguous = [(key, group) for key, group in groups.items() if len(group["counts"]) > 1]
    # Prefer a direct own/external collision where the finite bank has one.
    ambiguous.sort(key=lambda item: (not {"own", "external"}.issubset(item[1]["counts"]), item[0]))
    total = sum(sum(g["counts"].values()) for g in groups.values())
    return {"conditions": total, "public_classes": len(groups),
            "ambiguous_classes": len(ambiguous),
            "conditions_in_ambiguous_classes": sum(sum(g["counts"].values()) for _, g in ambiguous),
            "forced_classifier_correct_upper_bound": sum(max(g["counts"].values()) for g in groups.values()),
            "witnesses": [{"public_sha256": hashlib.sha256(key).hexdigest(),
                           "cause_counts": dict(group["counts"]),
                           "conditions": list(group["examples"].values())}
                          for key, group in ambiguous[:witnesses]]}


def public_case(condition) -> list:
    """Reconstruct full public evidence of an ambiguity witness from physics."""
    body = Body(**condition["initial"])
    result = []
    for action in (0, 1):
        before = run_pair(Experiment(body, action), 1)[0]
        after = run_pair(Experiment(body, action, condition["h_coupled"],
                                    condition["temperature_coupled"], condition["heat"]), 2)[0]
        result.append([normalized(before), normalized(after)])
    return result


def check_witness(witness, *, dual: bool) -> bool:
    conditions = witness["conditions"]
    if len({c["cause"] for c in conditions}) < 2:
        return False
    keys = []
    for condition in conditions:
        truth = private_cause(condition["h_coupled"], condition["temperature_coupled"], condition["heat"])
        if condition["cause"] != truth:
            return False
        public = public_case(condition)
        keys.append(canonical(public if dual else public[condition["action"]]))
    return all(key == keys[0] for key in keys) and hashlib.sha256(keys[0]).hexdigest() == witness["public_sha256"]


def census(*, quick=False, emit=lambda record: None) -> dict:
    manifest = sources()
    single, dual = {}, {}
    result = {"schema": "e4-self1-a-v1", "profile": "smoke" if quick else "development-census",
              "sources": manifest, "self1_green": False, "stage": "SELF-A",
              "conditions": 0, "comparisons": 0, "calibration_pairs": 0,
              "change_checks_correct": 0, "attribution_unknown": 0,
              "reference_and_cam_preserved": 0, "initial_states": 0,
              "cam_facts": 0, "cam_destroyed": 0, "max_rows": 0,
              "causes": dict.fromkeys(CAUSES, 0),
              "diagnostics": {cause: {"changed": 0, "matches": 0, "unknown": 0} for cause in CAUSES}}
    hs, temperatures = ((30, 38), (48, 50, 52)) if quick else (range(29, 41), range(40, 73))
    for h, theta in product(hs, temperatures):
        body, cam = Body(h, theta), Cam()
        monitor = SelfChangeMonitor(BoundaryMap(cam))
        before, identifier = {}, 0
        for action in (0, 1):
            for _ in range(8):
                identifier += 1
                p, _, _ = run_pair(Experiment(body, action), identifier)
                monitor.calibrate(p)
                before[action] = p
                result["calibration_pairs"] += 1
                emit({"phase": "calibration", "initial_private": asdict(body), "public": public_record(p)})
        monitor.seal()
        frozen = monitor.model_hash(), cam_hash(cam)
        result["initial_states"] += 1
        for (hc, tc), heat in product(COUPLINGS, HEAT):
            condition = {"initial": asdict(body), "h_coupled": hc,
                         "temperature_coupled": tc, "heat": heat, "cause": private_cause(hc, tc, heat)}
            public, queries = [], []
            result["conditions"] += 1
            result["causes"][condition["cause"]] += 1
            for action in (0, 1):
                identifier += 1
                current, _, _ = run_pair(Experiment(body, action, hc, tc, heat), identifier)
                change = monitor.compare(current)
                expected = expected_change(before[action], current)
                result["comparisons"] += 1
                result["change_checks_correct"] += (change.reference_changed, change.action_effect_changed) == expected and change.known == 768
                result["attribution_unknown"] += change.attribution == "unknown"
                status = "changed" if change.reason == "observed_change" else "matches" if change.reason == "matches_reference" else "unknown"
                result["diagnostics"][condition["cause"]][status] += 1
                observation = [normalized(before[action]), normalized(current)]
                public.append(observation)
                queries.append({"action": action, "change": asdict(change)})
                add_group(single, canonical(observation), {**condition, "action": action})
            add_group(dual, canonical(public), condition)
            emit({"phase": "comparison", "private_audit_only": condition,
                  "public_baseline_and_current": public, "queries": queries})
        result["reference_and_cam_preserved"] += frozen == (monitor.model_hash(), cam_hash(cam))
        result["cam_facts"] += sum(s.has_fact for s in cam.slot if s.occupied)
        result["cam_destroyed"] += cam.destroyed
        result["max_rows"] = max(result["max_rows"], len(monitor.references))
    result["single_action"] = group_report(single)
    result["both_actions"] = group_report(dual)
    result["sources_unchanged"] = sources() == manifest
    result["checks"] = {
        "complete": result["conditions"] == (120 if quick else 7920) and result["comparisons"] == 2 * result["conditions"],
        "all_observed_changes_checked": result["change_checks_correct"] == result["comparisons"],
        "no_unjustified_attribution": result["attribution_unknown"] == result["comparisons"],
        "preserved": result["reference_and_cam_preserved"] == result["initial_states"],
        "invariants": result["cam_facts"] == result["cam_destroyed"] == 0 and result["max_rows"] <= 128,
        "ambiguous_even_with_both_actions": bool(result["both_actions"]["ambiguous_classes"]),
        "witnesses_replay": all(check_witness(w, dual=key == "both_actions")
                                for key in ("single_action", "both_actions") for w in result[key]["witnesses"]),
        "source_manifest": result["sources_unchanged"],
    }
    result["self_a_checks_passed"] = all(result["checks"].values())
    return result


def record(output: Path, *, quick=False) -> dict:
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


def verify(output: Path) -> dict:
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
        if canonical(rebuilt) != canonical(stored):
            raise ValueError("report differs from reproduced evidence")
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
        ok = report["self_a_checks_passed"]
    else:
        report = verify(args.directory)
        ok = report["valid"]
        if args.write_receipt:
            with (args.directory / "audit-receipt.json").open("xb") as handle:
                handle.write(canonical(report))
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
