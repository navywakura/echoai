"""SELF-C development experiment: actual Agent turns and private replay judge."""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict
from functools import lru_cache
import hashlib
from itertools import product
import json
from pathlib import Path

from echoai.echo4.boundary_world import Experiment, packet, run_pair
from echoai.echo4.self_attribution import CATALOG, ProbePlan
from echoai.echo4.self_audit import canonical, private_cause
from echoai.echo4.self_probe_audit import SOURCES as PREVIOUS_SOURCES, public, run_condition
from echoai.echo4.self_probe_world import run_probe
from echoai.echo4.self_recovery import MODES, RecoveryStop
from echoai.echo4.self_recovery_agent import SelfRecoveryAgent
from echoai.echo4.self_recovery_world import RecoveryEnv, physical_step
from echoai.echo4.world import Body

ROOT = Path(__file__).resolve().parents[1]
HORIZON = 24
SOURCES = (*PREVIOUS_SOURCES, "docs/ECHO4-SELF1-C-DESIGN.md", "echo4/self_recovery.py",
           "echo4/self_recovery_agent.py", "echo4/self_recovery_world.py",
           "echo4/self_recovery_audit.py", "tests/test_echo4_self1c.py")


def sources():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def learn_trace(agent, trace):
    """Nominal school consumes measured packets only, never true successors."""
    agent.sensation.start(trace.packets[0])
    for before, action, after in zip(trace.packets, trace.applied, trace.packets[1:]):
        slot = agent.sensation._slot(before, create=True)
        agent.sensation.anticipate(action)
        nxt = agent.sensation._slot(after, create=True)
        agent.t.observe(slot, action, nxt)
        agent.sensation.observe(after)


def school(body):
    agent = SelfRecoveryAgent(initial=body)
    for action in (0, 1):
        for i in range(1, 9):
            pair = run_pair(Experiment(body, action), 8 * action + i)[0]
            agent.calibrate_self_reference(pair)
            learn_trace(agent, pair.reference)
            learn_trace(agent, pair.treatment)
    agent.seal_self_reference()
    nominal, _ = run_probe(body, ProbePlan(17, 0, CATALOG[0], 0, 0))
    learn_trace(agent, nominal)
    agent.sensation.start(packet(body))  # declared restoration after school
    return agent, nominal


@lru_cache(maxsize=262144)
def viable(h, theta, hc, tc, heat, remaining):
    """Private finite-horizon reachability, never delivered to the policy."""
    body = Body(h, theta)
    if not body.alive:
        return False
    if remaining == 0:
        return True
    for action in range(3):
        nxt = physical_step(body, action, hc, tc, heat)
        if viable(nxt.h, nxt.temperature, hc, tc, 0, remaining - 1):
            return True
    return False


def row_state(world, slot):
    return {"pred": list(world.pred[slot]), "n": list(world.n[slot]),
            "alt": list(world.alt[slot]), "alt_n": list(world.alt_n[slot]),
            "inv": [list(row) for row in world.inv[slot]],
            "conflicts": world.conflicts, "inv_dropped": world.inv_dropped}


def sensory_hash(predictor):
    data = {"memory": vars(predictor.memory),
            "contexts": sorted((k.hex(), v) for k, v in predictor.contexts.items()),
            "context_dropped": predictor.context_dropped, "cam_dropped": predictor.cam_dropped}
    return hashlib.sha256(canonical(data)).hexdigest()


def episode(base, diagnosis, body, hc, tc, heat, mode):
    agent = copy.deepcopy(base)
    agent.env = RecoveryEnv(body, h_coupled=hc, temperature_coupled=tc, heat=heat)
    agent.start_recovery(diagnosis, restored=True, same_context=True, mode=mode)
    result = {"completed": False, "steps": 0, "terminalities": 0, "stopped": "",
              "writes": 0, "body_contamination": 0, "held": 0, "held_unchanged": 0,
              "legitimate_writes": 0, "external_writes": 0, "truth_retained": True,
              "trace": [], "actions": [], "max_h_candidates": len(agent.recovery.h),
              "max_t_candidates": len(agent.recovery.t)}
    reference_hash = agent.self_change.model_hash()
    for tick in range(HORIZON):
        if agent.episode_terminal:
            break
        before = agent.observation(agent.env.cell())
        slot = agent.sensation._slot(before, create=True)
        row_before, pattern_before = row_state(agent.t, slot), sensory_hash(agent.sensation)
        physical_before = agent.env.body
        predicted = {}
        # Executor-independent capture occurs before the original physics call.
        original_step = agent.env.step_homeostatic

        def captured_step(action, h, temperature):
            predicted.update({"forecast": agent.recovery.pending,
                              "proposed": agent.last_proposed_action,
                              "gate": agent.last_gate_decision})
            return original_step(action, h, temperature)

        agent.env.step_homeostatic = captured_step
        try:
            action = agent.turn(tick, greedy=True)
        except RecoveryStop as exc:
            result["stopped"] = str(exc)
            break
        finally:
            agent.env.step_homeostatic = original_step
        after = agent.observation(agent.env.cell())
        row_after, pattern_after = row_state(agent.t, slot), sensory_hash(agent.sensation)
        pulse = heat if tick == 0 else 0
        counterfactual = physical_step(physical_before, action, True, True, pulse)
        body_effect = packet(counterfactual) != after
        allowed = agent.recovery.last["allowed"]
        result["writes"] += allowed
        result["body_contamination"] += allowed and body_effect
        result["legitimate_writes"] += allowed and not body_effect
        result["external_writes"] += allowed and pulse != 0 and not body_effect
        result["held"] += not allowed
        result["held_unchanged"] += not allowed and row_before == row_after and pattern_before == pattern_after
        result["truth_retained"] &= (agent.env.body.h, hc) in agent.recovery.h and (agent.env.body.temperature, tc, heat) in agent.recovery.t
        result["actions"].append(action)
        result["trace"].append({"before": before.hex(), "after": after.hex(),
                                "action": action, "proposed": predicted["proposed"], "gate": predicted["gate"],
                                "forecast_sha256": hashlib.sha256(repr(predicted["forecast"]).encode()).hexdigest(),
                                "learning": agent.recovery.last, "row_before": row_before, "row_after": row_after,
                                "sensory_before": pattern_before, "sensory_after": pattern_after,
                                "private_audit_only": {"before": asdict(physical_before), "after": asdict(agent.env.body),
                                                       "nominal_body_after": asdict(counterfactual), "body_effect": body_effect}})
        result["max_h_candidates"] = max(result["max_h_candidates"], len(agent.recovery.h))
        result["max_t_candidates"] = max(result["max_t_candidates"], len(agent.recovery.t))
    result.update({"steps": agent.life_turns, "terminalities": agent.deaths,
                   "completed": agent.life_turns == HORIZON and not agent.episode_terminal,
                   "resets": agent.env.resets, "reference_preserved": reference_hash == agent.self_change.model_hash(),
                   "resource_balanced": agent.env.balanced,
                   "false_facts": agent.metrics.false_facts, "destroyed": agent.cam.destroyed,
                   "cortex_calls": agent.metrics.cortex_calls, "resources": agent.recovery.resources(),
                   "stopped": result["stopped"] or agent.recovery.stopped})
    return result


def totals():
    return {name: 0 for name in ("conditions", "completed", "viable", "completed_viable", "infeasible",
            "steps", "terminalities", "stops", "writes", "body_contamination", "held", "held_unchanged",
            "legitimate_writes", "external_writes", "truth_retained", "reference_preserved", "resets",
            "false_facts", "destroyed", "cortex_calls", "resource_balanced", "max_h_candidates", "max_t_candidates")}


def census(*, quick=False, emit=lambda value: None):
    manifest = sources()
    report = {"schema": "e4-self1-c-v1", "profile": "smoke" if quick else "development",
              "sources": manifest, "self1_green": False, "horizon": HORIZON,
              "controllers": {mode: totals() for mode in MODES}, "diagnostic_steps": 0,
              "diagnostic_probes": 0, "diagnoses_correct": 0, "nominal_actions_per_initial": 72,
              "same_actions_without_protection": 0, "different_actions_without_attribution": 0}
    hs, ts = ((34,), (60,)) if quick else ((29, 34, 39), (44, 52, 60, 68))
    for h, theta in product(hs, ts):
        body = Body(h, theta)
        base, nominal = school(body)
        emit({"phase": "school", "private_initial": asdict(body), "nominal": public(nominal),
              "learned_model_sha256": base.sensation.model_hash(), "reference": base.self_change.model_hash()})
        for hc, tc, heat in product((True, False), (True, False), (-16, -4, 0, 4, 16)):
            diagnosis = base.new_self_diagnosis(packet(body), nominal)
            measured = run_condition(diagnosis, body, hc, tc, heat, mode="active")
            report["diagnostic_steps"] += diagnosis.executed_ticks
            report["diagnostic_probes"] += len(diagnosis.used)
            report["diagnoses_correct"] += diagnosis.diagnosis()["label"] == private_cause(hc, tc, heat)
            feasible = viable(h, theta, hc, tc, heat, HORIZON)
            runs = {}
            for mode in MODES:
                result = episode(base, diagnosis, body, hc, tc, heat, mode)
                runs[mode] = result
                summary = report["controllers"][mode]
                summary["conditions"] += 1
                summary["viable"] += feasible
                summary["infeasible"] += not feasible
                summary["completed_viable"] += feasible and result["completed"]
                summary["stops"] += bool(result["stopped"])
                for key in ("completed", "steps", "terminalities", "writes", "body_contamination", "held", "held_unchanged",
                            "legitimate_writes", "external_writes", "truth_retained", "reference_preserved", "resets",
                            "false_facts", "destroyed", "cortex_calls", "resource_balanced"):
                    summary[key] += result[key]
                for key in ("max_h_candidates", "max_t_candidates"):
                    summary[key] = max(summary[key], result[key])
            report["same_actions_without_protection"] += runs["selective"]["actions"] == runs["no_protection"]["actions"]
            report["different_actions_without_attribution"] += runs["selective"]["actions"] != runs["no_attribution"]["actions"]
            emit({"phase": "recovery", "private_audit_only": {"initial": asdict(body), "hc": hc, "tc": tc,
                  "heat": heat, "viable": feasible}, "diagnostic": measured, "runs": runs})
    active = report["controllers"]["selective"]
    n = 20 if quick else 240
    report["checks"] = {
        "complete": all(c["conditions"] == n for c in report["controllers"].values()),
        "diagnosis": report["diagnoses_correct"] == n,
        "recovery": 100 * active["completed_viable"] >= 90 * active["viable"],
        "behavioral_gain": active["completed"] > report["controllers"]["no_attribution"]["completed"],
        "selective_protection": active["body_contamination"] == 0 < report["controllers"]["no_protection"]["body_contamination"],
        "retained_models": active["held"] > 0 and active["held"] == active["held_unchanged"],
        "learning_not_frozen": active["legitimate_writes"] > 0 and active["external_writes"] > 0 and report["controllers"]["all_self"]["writes"] == 0,
        "same_policy_control": report["same_actions_without_protection"] == n,
        "no_selective_death": active["terminalities"] == 0,
        "truth_survives": active["truth_retained"] == n,
        "invariants": all(c["resets"] == c["false_facts"] == c["destroyed"] == c["cortex_calls"] == 0
                          and c["reference_preserved"] == c["resource_balanced"] == n for c in report["controllers"].values()),
        "bounded": all(c["max_h_candidates"] <= 64 and c["max_t_candidates"] <= 160 for c in report["controllers"].values()),
        "sources": manifest == sources(),
    }
    report["development_checks_passed"] = all(report["checks"].values())
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
    with (output / "report.json").open("xb") as target:
        target.write(canonical(report))
    return report


def verify(output: Path):
    stored = {}
    findings = []
    try:
        stored = json.loads((output / "report.json").read_bytes())
        if stored.get("sources") != sources() or stored.get("profile") not in ("smoke", "development"):
            raise ValueError("source manifest/profile mismatch")
        digest = hashlib.sha256()
        with (output / "traces.jsonl").open("rb") as trace:
            def emit(value):
                raw = canonical(value)
                if trace.readline() != raw:
                    raise ValueError("trace differs from physical replay")
                digest.update(raw)
            rebuilt = census(quick=stored["profile"] == "smoke", emit=emit)
            if trace.read(1):
                raise ValueError("unexpected trailing trace")
        rebuilt["trace_sha256"] = digest.hexdigest()
        rebuilt["reproduction_sha256"] = hashlib.sha256(canonical(rebuilt)).hexdigest()
        if canonical(stored) != canonical(rebuilt):
            raise ValueError("report differs from physical replay")
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
        ok = report["development_checks_passed"]
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
