"""Reproducible BOUNDARY-1 campaign and full replay auditor (separate CLI)."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import random

from echoai.core.cam import Cam
from echoai.echo4.boundary import ALL, MASK, BoundaryMap, Estimate, Pair, Trial, public_record
from echoai.echo4.boundary_agent import BoundaryAgent
from echoai.echo4.boundary_world import FAMILIES, INVALID, coincidence, experiment, judge, packet, run_pair
from echoai.echo4.sensation_predictor import SensationPredictor
from echoai.echo4.world import Body
from echoai.nexus0.world import World

ROOT = Path(__file__).resolve().parents[1]
SEEDS = {"development": 42001, "B": 42002, "C": 42003}
BLOCKS = {"development": 2, "B": 16, "C": 16}
SOURCES = (
    "docs/ECHO4-BOUNDARY1-DESIGN.md", "echo4/boundary.py", "echo4/boundary_agent.py",
    "echo4/boundary_world.py", "echo4/boundary_bench.py", "tests/test_echo4_boundary1.py",
    "echo4/sensation_predictor.py", "echo4/sensation.py", "echo4/sensation_agent.py",
    "echo4/adapter.py", "echo4/world.py", "nexus0/world.py", "nexus0/pattern.py",
    "nexus0/encoder.py", "nexus0/env.py", "nexus0/constants.py", "nexus0/gate.py",
    "nexus0/loop.py", "nexus0/qtable.py", "core/cam.py", "core/qn.py",
    "core/wsp.py",
)


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sources() -> dict:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def masks(value: Estimate) -> tuple:
    return value.influence, value.no_observed_effect, value.unknown


def metrics() -> dict:
    return dict(total=0, correct=0, exact_estimate=0, baseline_correct=0,
                unknown=0, false_influence=0, invalid_total=0, invalid_abstained=0,
                lag_total=0, lag_correct=0, ablation_unknown=0)


def stage_acceptance(stage: dict) -> dict:
    n = stage["total"]
    return {
        "accuracy": n > 0 and 100 * stage["correct"] >= 95 * n,
        "each_family": all(m["total"] > 0 and 100 * m["correct"] >= 90 * m["total"]
                           for m in stage["families"].values()),
        "no_false_influence": stage["false_influence"] == 0,
        "invalid_abstention": stage["invalid_total"] > 0 and stage["invalid_abstained"] == stage["invalid_total"],
        "lag": stage["lag_total"] > 0 and stage["lag_correct"] == stage["lag_total"],
        "beats_coincidence": 100 * (stage["correct"] - stage["baseline_correct"]) >= 10 * n,
        "ablation_abstains": stage["ablation_unknown"] == n,
        "frozen": stage["frozen_blocks"] == stage["blocks"] * len(FAMILIES),
        "invariants": stage["cam_destroyed"] == stage["cam_facts"] == 0,
        "bounded": stage["max_rows"] <= 128 and stage["max_pairs"] <= 4096,
    }


def run_stage(name: str, blocks: int, emit=lambda stage, record: None) -> dict:
    rng = random.Random(SEEDS[name])
    result = {**metrics(), "stage": name, "seed": SEEDS[name], "blocks": blocks,
              "families": {f: metrics() for f in FAMILIES}, "frozen_blocks": 0,
              "cam_destroyed": 0, "cam_facts": 0, "max_rows": 0, "max_pairs": 0,
              "max_cam_used": 0, "sensations": [0, 0, 0, 0], "training_pairs": 0,
              "rejected_training_pairs": 0, "trace_records": 0}
    for family in FAMILIES:
        for block in range(blocks):
            cam = Cam()
            sensory = SensationPredictor(cam, World())
            boundary, ablation = BoundaryMap(cam), BoundaryMap(cam)
            identifier = 0
            for phase, repetitions in (("identification", 8), ("exam", 4)):
                if phase == "exam":
                    boundary.freeze()
                    ablation.freeze()
                    sensory.freeze()
                    frozen = boundary.model_hash(), sensory.model_hash(), ablation.model_hash()
                for action in (0, 1):
                    for repetition in range(repetitions):
                        identifier += 1
                        spec = experiment(family, action, name, rng)
                        # Query BEFORE executing the held-out intervention.
                        predicted = boundary.estimate(packet(spec.initial), action)
                        ablated = ablation.estimate(packet(spec.initial), action)
                        pair, private, sensations = run_pair(spec, identifier, reverse=bool(rng.getrandbits(1)),
                                                             fault=family, sensation=sensory)
                        rejected = False
                        if phase == "identification":
                            result["training_pairs"] += 1
                            try:
                                boundary.observe(pair)
                            except ValueError:
                                rejected = True
                                result["rejected_training_pairs"] += 1
                            try:
                                ablation.observe(replace(pair, restored=False))
                            except ValueError:
                                pass
                        expected = judge(family, private)  # evaluator only; never passed to learner
                        baseline = coincidence(pair)
                        if phase == "exam":
                            for target in (result, result["families"][family]):
                                target["total"] += 1
                                target["correct"] += masks(predicted) == masks(expected)
                                target["exact_estimate"] += predicted == expected
                                target["baseline_correct"] += masks(expected) == (baseline, MASK ^ baseline, ALL ^ MASK)
                                target["unknown"] += predicted == Estimate()
                                target["false_influence"] += bool(predicted.influence & ~expected.influence)
                                target["invalid_total"] += family in INVALID
                                target["invalid_abstained"] += family in INVALID and predicted == Estimate()
                                target["lag_total"] += family in ("full", "delayed")
                                target["lag_correct"] += family in ("full", "delayed") and predicted.first_effect == expected.first_effect
                                target["ablation_unknown"] += ablated == Estimate()
                        for sensation in sensations:
                            result["sensations"][sensation["label"]] += 1
                        emit(name, {"family": family, "block": block, "phase": phase,
                                    "repetition": repetition, "public": public_record(pair),
                                    "private_audit_only": private, "prediction_before_trial": asdict(predicted),
                                    "expected_after_trial": asdict(expected), "baseline": baseline,
                                    "rejected": rejected, "sensations": sensations})
                        result["trace_records"] += 1
            result["frozen_blocks"] += frozen == (boundary.model_hash(), sensory.model_hash(), ablation.model_hash())
            result["cam_destroyed"] += cam.destroyed
            result["cam_facts"] += sum(s.has_fact for s in cam.slot if s.occupied)
            result["max_cam_used"] = max(result["max_cam_used"], cam.used)
            result["max_rows"] = max(result["max_rows"], len(boundary.rows))
            result["max_pairs"] = max(result["max_pairs"], boundary.pairs)
    result["checks"] = stage_acceptance(result)
    result["passed"] = all(result["checks"].values())
    return result


class _ScheduledProbe(BoundaryAgent):
    """Declared laboratory pulses, not an autonomous maintenance policy."""
    pulse = 2

    def _propose(self, slot, turn_i, greedy=False):
        return self.pulse if turn_i == 0 else 2


def native_probe() -> dict:
    outcomes = []
    for action in (0, 1):
        initial = Body(30 if action == 0 else 35, 50)
        owner = None
        false_facts = destroyed = cortex_calls = 0
        for identifier in range(1, 9):
            # Agent.respawn correctly rejects live bodies. Separate explicitly
            # restored trials use fresh Agents; do not bypass that invariant.
            treatment, reference = _ScheduledProbe(initial=initial), _ScheduledProbe(initial=initial)
            treatment.pulse = action
            if owner is None:
                owner = treatment
            trials = []
            for agent in (treatment, reference):
                frames, actions, decisions = [agent.observation(agent.env.cell())], [], []
                terminal = [not agent.env.body.alive]
                for tick in (0, 1):
                    actions.append(agent.turn(tick))
                    decisions.append(agent.last_gate_decision)
                    frames.append(agent.observation(agent.env.cell()))
                    terminal.append(not agent.env.body.alive)
                trials.append(Trial(identifier, agent.pulse, tuple(frames), (0, 1, 2),
                                    tuple(actions), tuple(decisions), tuple(terminal)))
                false_facts += agent.metrics.false_facts
                destroyed += agent.cam.destroyed
                cortex_calls += agent.metrics.cortex_calls
            owner.observe_intervention(Pair(identifier, True, True, *trials))
        estimate = owner.influence_estimate(packet(initial), action)
        outcomes.append({"action": action, "estimate": asdict(estimate),
                         "shared_cam": owner.boundary.cam is owner.cam is owner.sensation.cam,
                         "shared_t": owner.sensation.world is owner.t,
                         "false_facts": false_facts, "destroyed": destroyed,
                         "cortex_calls": cortex_calls,
                         "sensory_observed": owner.last_sensation is not None})
    return {"cases": outcomes,
            "passed": all(o["estimate"]["influence"] == MASK and o["shared_cam"] and o["shared_t"]
                          and o["sensory_observed"] and not (o["false_facts"] or o["destroyed"] or o["cortex_calls"])
                          for o in outcomes)}


def run_campaign(emit=lambda stage, record: None, *, quick=False) -> dict:
    before = sources()
    report = {"schema": "e4-boundary1-v1", "profile": "smoke" if quick else "official",
              "sources": before, "stages": {}, "native": native_probe()}
    for stage, blocks in BLOCKS.items():
        report["stages"][stage] = run_stage(stage, 1 if quick else blocks, emit)
        if not report["stages"][stage]["passed"]:
            break  # keep red; never open C following a failed B
    report["sources_unchanged"] = before == sources()
    report["passed"] = (len(report["stages"]) == 3 and report["native"]["passed"]
                        and report["sources_unchanged"] and all(s["passed"] for s in report["stages"].values()))
    report["closure_eligible"] = report["passed"] and not quick
    return report


def campaign(output: Path, *, quick=False) -> dict:
    output.mkdir(parents=True, exist_ok=False)  # never overwrite evidence
    handles, digests = {}, {}

    def emit(stage, record):
        if stage not in handles:
            handles[stage] = (output / f"{stage}.jsonl").open("xb")
            digests[stage] = hashlib.sha256()
        raw = canonical(record)
        handles[stage].write(raw)
        digests[stage].update(raw)

    try:
        report = run_campaign(emit, quick=quick)
    finally:
        for handle in handles.values():
            handle.close()
    report["traces"] = {stage: digest.hexdigest() for stage, digest in digests.items()}
    report["certificate"] = hashlib.sha256(canonical(report)).hexdigest()
    with (output / "report.json").open("xb") as handle:
        handle.write(canonical(report))
    return report


def audit(output: Path) -> dict:
    """Fresh full execution, including all receipts/private truth, not report trust."""
    findings, handles, digests = [], {}, {}
    try:
        stored = json.loads((output / "report.json").read_bytes())
        if stored.get("sources") != sources():
            raise ValueError("source manifest mismatch")
        if stored.get("profile") not in ("official", "smoke"):
            raise ValueError("invalid profile")

        def emit(stage, record):
            if stage not in handles:
                handles[stage] = (output / f"{stage}.jsonl").open("rb")
                digests[stage] = hashlib.sha256()
            raw = canonical(record)
            if handles[stage].readline() != raw:
                raise ValueError(f"{stage}: replay trace/receipt mismatch")
            digests[stage].update(raw)

        rebuilt = run_campaign(emit, quick=stored["profile"] == "smoke")
        if any(handle.read(1) for handle in handles.values()):
            raise ValueError("unexpected trailing trace data")
        rebuilt["traces"] = {stage: digest.hexdigest() for stage, digest in digests.items()}
        rebuilt["certificate"] = hashlib.sha256(canonical(rebuilt)).hexdigest()
        if canonical(rebuilt) != canonical(stored):
            raise ValueError("report/certificate differs from full replay")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        findings.append(str(exc))
    finally:
        for handle in handles.values():
            handle.close()
    return {"valid": not findings, "findings": findings,
            "certificate": stored.get("certificate") if not findings else None,
            "closure_eligible": bool(not findings and stored.get("closure_eligible"))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("campaign", "verify", "develop"))
    parser.add_argument("directory", nargs="?", type=Path)
    parser.add_argument("--quick", action="store_true", help="smoke only, never closure")
    parser.add_argument("--write-receipt", action="store_true", help="create audit receipt exclusively")
    args = parser.parse_args()
    if args.command == "develop":
        report = run_stage("development", 2)
        ok = report["passed"]
    elif args.directory is None:
        parser.error("campaign/verify requires evidence directory")
    elif args.command == "campaign":
        report = campaign(args.directory, quick=args.quick)
        ok = report["passed"]
    else:
        report = audit(args.directory)
        ok = report["valid"]
        if args.write_receipt:
            with (args.directory / "audit-receipt.json").open("xb") as handle:
                handle.write(canonical(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
