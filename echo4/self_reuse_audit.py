"""SELF-C v2: matched exposure, native T-based task execution, full replay."""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict
import hashlib
from itertools import product
import json
from pathlib import Path

from echoai.echo4.boundary_world import Experiment, packet, run_pair
from echoai.echo4.self_attribution import CATALOG, ProbePlan
from echoai.echo4.self_audit import canonical, private_cause
from echoai.echo4.self_probe_audit import public, run_condition
from echoai.echo4.self_probe_world import run_probe
from echoai.echo4.self_recovery_audit import SOURCES as PREVIOUS_SOURCES, row_state, sensory_hash
from echoai.echo4.self_recovery_world import RecoveryEnv, physical_step
from echoai.echo4.self_reuse_agent import SelfReuseAgent
from echoai.echo4.world import Body

ROOT = Path(__file__).resolve().parents[1]
SOURCES = (*PREVIOUS_SOURCES, "docs/ECHO4-SELF1-C-V2-DESIGN.md", "echo4/self_reuse.py",
           "echo4/self_reuse_agent.py", "echo4/self_reuse_audit.py", "tests/test_echo4_self1c_v2.py")
ARMS = ("selective", "unprotected", "freeze_all", "no_t")
GRIDS = {"develop": ((30, 37), (48, 65)), "confirm": ((31, 38), (49, 66)), "smoke": ((30,), (48,))}
SCHOOL_REPEATS, EXPOSURE_REPEATS = 8, 12


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def sources():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def restore_trial(agent, body, *, hc=True, tc=True, heat=0):
    """PRIVATE executor restoration; never a policy action or memory reset."""
    if agent.trial_active or agent.sensation.pending is not None:
        raise RuntimeError("cannot restore an unfinished trial")
    agent.env = RecoveryEnv(body, h_coupled=hc, temperature_coupled=tc, heat=heat)
    agent.H, agent.temperature = body.h, body.temperature
    agent.life_turns, agent.episode_terminal = 0, False
    agent.clear_context()
    agent.sensation.start(packet(body))


def school(body):
    agent = SelfReuseAgent(initial=body)
    original_q = copy.deepcopy(vars(agent.q))
    for action in (0, 1):
        for i in range(1, 9):
            agent.calibrate_self_reference(run_pair(Experiment(body, action), 8 * action + i)[0])
    agent.seal_self_reference()
    nominal = run_probe(body, ProbePlan(17, 0, CATALOG[0], 0, 0))[0]
    traces = []
    for _ in range(SCHOOL_REPEATS):
        for action in range(3):
            restore_trial(agent, body)
            agent.arm_school(action, token=agent.trial_token + 1, restored=True)
            before = agent.observation(agent.env.cell())
            executed = agent.turn(agent.metrics.turns, greedy=True)
            traces.append({"before": before.hex(), "action": executed,
                           "after": agent.observation(agent.env.cell()).hex(), "restored": True,
                           "balanced": agent.env.balanced, "terminal": agent.episode_terminal,
                           "q_unchanged": original_q == vars(agent.q)})
    return agent, nominal, traces


def expose(base, diagnosis, body, hc, tc, heat, arm):
    agent = copy.deepcopy(base)
    report = {"writes": 0, "body_contamination": 0, "external_writes": 0,
              "held": 0, "held_unchanged": 0, "terminalities": 0,
              "balanced": True, "traces": []}
    before_reference = agent.self_change.model_hash()
    before_q = digest(vars(agent.q))
    for _ in range(EXPOSURE_REPEATS):
        for action in range(3):
            restore_trial(agent, body, hc=hc, tc=tc, heat=heat)
            agent.arm_exposure(diagnosis, action, mode=arm, token=agent.trial_token + 1,
                               restored=True, same_context=True)
            slot = agent.cam.get(packet(body))
            row_before, sensory_before = row_state(agent.t, slot), sensory_hash(agent.sensation)
            captured = {}
            step = agent.env.step_homeostatic

            def capture(a, h, temperature):
                captured["prior"] = hashlib.sha256(repr(agent.recovery.pending).encode()).hexdigest()
                return step(a, h, temperature)

            agent.env.step_homeostatic = capture
            try:
                executed = agent.turn(agent.metrics.turns, greedy=True)
            finally:
                agent.env.step_homeostatic = step
            after = agent.observation(agent.env.cell())
            allowed = agent.recovery.last["allowed"]
            body_effect = after != packet(physical_step(body, executed, True, True, heat))
            row_after, sensory_after = row_state(agent.t, slot), sensory_hash(agent.sensation)
            report["writes"] += allowed
            report["body_contamination"] += allowed and body_effect
            report["external_writes"] += allowed and not body_effect and heat != 0
            report["held"] += not allowed
            report["held_unchanged"] += not allowed and row_before == row_after and sensory_before == sensory_after
            report["terminalities"] += agent.episode_terminal
            report["balanced"] &= agent.env.balanced
            report["traces"].append({"token": agent.trial_token, "restored": True,
                                     "before": packet(body).hex(), "after": after.hex(),
                                     "action": executed, "proposed": agent.last_proposed_action,
                                     "gate": agent.last_gate_decision, "forecast_sha256": captured["prior"],
                                     "allowed": allowed, "body_effect_private": body_effect,
                                     "row_before": row_before, "row_after": row_after,
                                     "sensory_before": sensory_before, "sensory_after": sensory_after})
    report["reference_preserved"] = before_reference == agent.self_change.model_hash()
    report["q_unchanged"] = before_q == digest(vars(agent.q))
    report["t_after"] = row_state(agent.t, agent.cam.get(packet(body)))
    return agent, report


def task_memory_hash(agent):
    return digest({"t": vars(agent.t), "q": vars(agent.q), "sensory": sensory_hash(agent.sensation)})


def task(agent, body, heat, target, *, use_t=True):
    restore_trial(agent, body, heat=heat)  # operator restored nominal couplings
    before_memory = task_memory_hash(agent)
    agent.arm_reuse(target, token=agent.trial_token + 1, restored=True,
                    nominal_body_confirmed=True, use_t=use_t)
    captured = {}
    step = agent.env.step_homeostatic

    def capture(action, h, temperature):
        captured["decision"] = asdict(agent.reuse_decision)
        captured["prediction"] = agent.last_sensory_prediction.slot
        return step(action, h, temperature)

    agent.env.step_homeostatic = capture
    try:
        action = agent.turn(agent.metrics.turns, greedy=True)
    finally:
        agent.env.step_homeostatic = step
    actual = agent.observation(agent.env.cell())
    return {"goal": target.hex(), "before": packet(body).hex(), "after": actual.hex(),
            "action": action, "proposed": agent.last_proposed_action, "gate": agent.last_gate_decision,
            "before_execution": captured, "success": actual == target and not agent.episode_terminal,
            "memory_frozen": before_memory == task_memory_hash(agent),
            "terminal": agent.episode_terminal, "balanced": agent.env.balanced,
            "restored": True, "nominal_body_confirmed": True}


def summary():
    return {"tasks": 0, "success": 0, "matched": 0, "frozen": 0, "terminalities": 0,
            "writes": 0, "body_contamination": 0, "external_writes": 0, "held": 0,
            "held_unchanged": 0, "reference_preserved": 0, "invariant_cases": 0,
            "q_unchanged_cases": 0, "balanced_tasks": 0,
            "by_cause": {cause: {"tasks": 0, "success": 0} for cause in ("nominal", "own", "external", "mixed")}}


def stage(name, emit):
    report = {"stage": name, "conditions": 0, "diagnoses_correct": 0, "diagnostic_steps": 0,
              "diagnostic_restores": 0, "diagnostic_truth_retained": 0, "diagnostic_terminalities": 0,
              "nominal_bodies": 0, "nominal_safe_bodies": 0, "nominal_q_unchanged_bodies": 0,
              "nominal_steps_per_body": 96, "nominal_restores_per_body": 57, "exposure_steps_per_arm": 36,
              "task_restores_per_arm": 3, "exposure_matched": 0, "no_t_same_training": 0,
              "arms": {arm: summary() for arm in ARMS},
              "paired": {arm: {"wins": 0, "losses": 0, "ties": 0} for arm in ARMS[1:]}}
    for h, theta in product(*GRIDS[name]):
        body = Body(h, theta)
        base, nominal, school_traces = school(body)
        report["nominal_bodies"] += 1
        report["nominal_safe_bodies"] += all(t["balanced"] and not t["terminal"] for t in school_traces)
        report["nominal_q_unchanged_bodies"] += all(t["q_unchanged"] for t in school_traces)
        emit({"phase": "school", "stage": name, "initial_private": asdict(body),
              "nominal_reference": public(nominal), "t_school": school_traces,
              "model_sha256": base.sensation.model_hash()})
        for hc, tc, heat in product((True, False), (True, False), (-16, 0, 16)):
            diagnosis = base.new_self_diagnosis(packet(body), nominal)
            measured = run_condition(diagnosis, body, hc, tc, heat, mode="active")
            cause = private_cause(hc, tc, heat)
            report["diagnoses_correct"] += diagnosis.diagnosis()["label"] == cause
            report["conditions"] += 1
            report["diagnostic_steps"] += diagnosis.executed_ticks
            report["diagnostic_restores"] += len(diagnosis.used)
            report["diagnostic_truth_retained"] += measured["truth_retained"]
            report["diagnostic_terminalities"] += measured["terminalities"]
            outcomes, training = {}, {}
            # Goal generator belongs to the judge. Only goal bytes cross to selector.
            order = (2, 1, 0) if name == "confirm" else (0, 1, 2)
            targets = [packet(physical_step(body, a, True, True, heat)) for a in order]
            for arm in ARMS:
                agent, exposed = expose(base, diagnosis, body, hc, tc, heat, arm)
                training[arm] = exposed
                outcomes[arm] = [task(agent, body, heat, goal, use_t=arm != "no_t") for goal in targets]
                counters = report["arms"][arm]
                for key in ("writes", "body_contamination", "external_writes", "held", "held_unchanged", "reference_preserved"):
                    counters[key] += exposed[key]
                counters["terminalities"] += exposed["terminalities"]
                counters["q_unchanged_cases"] += exposed["q_unchanged"]
                counters["invariant_cases"] += (agent.metrics.false_facts == agent.metrics.cortex_calls == agent.cam.destroyed == 0
                                                and exposed["balanced"] and agent.env.resets == 0)
                for outcome in outcomes[arm]:
                    counters["tasks"] += 1
                    counters["success"] += outcome["success"]
                    counters["matched"] += bool(outcome["before_execution"]["decision"]["matches"])
                    counters["frozen"] += outcome["memory_frozen"]
                    counters["balanced_tasks"] += outcome["balanced"]
                    counters["terminalities"] += outcome["terminal"]
                    counters["by_cause"][cause]["tasks"] += 1
                    counters["by_cause"][cause]["success"] += outcome["success"]
            fingerprints = [digest([(t["before"], t["action"], t["after"], t["gate"])
                                    for t in training[arm]["traces"]]) for arm in ARMS]
            report["exposure_matched"] += len(set(fingerprints)) == 1
            report["no_t_same_training"] += training["no_t"] == training["selective"]
            for arm in ARMS[1:]:
                for active, control in zip(outcomes["selective"], outcomes[arm]):
                    key = "ties" if active["success"] == control["success"] else "wins" if active["success"] else "losses"
                    report["paired"][arm][key] += 1
            emit({"phase": "reuse", "stage": name, "private_audit_only": {"initial": asdict(body),
                  "hc": hc, "tc": tc, "heat": heat, "cause": cause},
                  "diagnosis": measured, "training": training, "tasks": outcomes})
    primary = report["arms"]["selective"]
    n = 12 if name == "smoke" else 48
    report["checks"] = {
        "complete": report["conditions"] == n and all(a["tasks"] == 3 * n for a in report["arms"].values()),
        "diagnosis": report["diagnoses_correct"] == report["diagnostic_truth_retained"] == n
                     and report["diagnostic_terminalities"] == 0,
        "coverage": 100 * primary["success"] >= 60 * primary["tasks"],
        "each_cause": all(3 * r["success"] >= r["tasks"] for r in primary["by_cause"].values()),
        "paired_gain": all(100 * (primary["success"] - report["arms"][arm]["success"]) >= 5 * primary["tasks"] for arm in ARMS[1:]),
        "body_benefit": primary["by_cause"]["own"]["success"] > report["arms"]["unprotected"]["by_cause"]["own"]["success"],
        "external_benefit": primary["by_cause"]["external"]["success"] > report["arms"]["freeze_all"]["by_cause"]["external"]["success"],
        "nominal_no_loss": all(primary["by_cause"]["nominal"]["success"] >= report["arms"][arm]["by_cause"]["nominal"]["success"] for arm in ("unprotected", "freeze_all")),
        "protection": primary["body_contamination"] == 0 < report["arms"]["unprotected"]["body_contamination"],
        "selective_learning": primary["external_writes"] > 0 and primary["held"] > 0 and primary["held"] == primary["held_unchanged"],
        "matched_exposure": report["exposure_matched"] == report["no_t_same_training"] == n,
        "frozen_tasks": all(a["tasks"] == a["frozen"] and a["q_unchanged_cases"] == n for a in report["arms"].values())
                        and report["nominal_q_unchanged_bodies"] == report["nominal_bodies"],
        "invariants": all(a["reference_preserved"] == a["invariant_cases"] == n and a["terminalities"] == 0
                          and a["balanced_tasks"] == a["tasks"] for a in report["arms"].values())
                      and report["nominal_safe_bodies"] == report["nominal_bodies"],
    }
    report["passed"] = all(report["checks"].values())
    return report


def campaign(*, quick=False, emit=lambda value: None):
    manifest = sources()
    stages = {name: stage(name, emit) for name in (("smoke",) if quick else ("develop", "confirm"))}
    unchanged = manifest == sources()
    return {"schema": "e4-self1-c-v2", "profile": "smoke" if quick else "campaign",
            "sources": manifest, "stages": stages, "sources_unchanged": unchanged,
            "self_c_v2_green": not quick and unchanged and all(s["passed"] for s in stages.values()),
            "self1_green": False}


def record(output: Path, *, quick=False):
    output.mkdir(parents=True, exist_ok=False)
    trace_digest = hashlib.sha256()
    with (output / "traces.jsonl").open("xb") as trace:
        def emit(value):
            raw = canonical(value)
            trace.write(raw)
            trace_digest.update(raw)
        report = campaign(quick=quick, emit=emit)
    report["trace_sha256"] = trace_digest.hexdigest()
    report["reproduction_sha256"] = digest(report)
    with (output / "report.json").open("xb") as handle:
        handle.write(canonical(report))
    return report


def verify(output: Path):
    stored, findings = {}, []
    try:
        stored = json.loads((output / "report.json").read_bytes())
        if not isinstance(stored, dict):
            raise ValueError("report must be an object")
        if stored.get("sources") != sources() or stored.get("profile") not in ("smoke", "campaign"):
            raise ValueError("source manifest/profile mismatch")
        trace_digest = hashlib.sha256()
        with (output / "traces.jsonl").open("rb") as trace:
            def emit(value):
                raw = canonical(value)
                if trace.readline() != raw:
                    raise ValueError("trace differs from full replay")
                trace_digest.update(raw)
            rebuilt = campaign(quick=stored["profile"] == "smoke", emit=emit)
            if trace.read(1):
                raise ValueError("unexpected trailing trace")
        rebuilt["trace_sha256"] = trace_digest.hexdigest()
        rebuilt["reproduction_sha256"] = digest(rebuilt)
        if canonical(stored) != canonical(rebuilt):
            raise ValueError("report differs from full replay")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "self1_green": False,
            "self_c_v2_green": not findings and stored.get("self_c_v2_green", False),
            "reproduction_sha256": stored.get("reproduction_sha256") if not findings else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("campaign", "verify"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    if args.command == "campaign":
        report = record(args.directory, quick=args.quick)
        ok = report["self_c_v2_green"] or args.quick
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
