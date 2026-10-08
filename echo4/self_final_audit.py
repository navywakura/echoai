"""Joint SELF-1 exams: native reuse/lives, abstention, source lock and full replay."""
from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, replace
import hashlib
import importlib
from itertools import product
import json
from pathlib import Path
import sys

from echoai.core.qn import SLOT_FLAG_INHIBIT
from echoai.echo4.boundary_world import packet
from echoai.echo4.self_audit import canonical, private_cause
from echoai.echo4.self_attribution import SelfAttributor
from echoai.echo4.self_final import SelfSession, SCOPE
from echoai.echo4.self_final_world import novel_probe
from echoai.echo4.self_probe_audit import public
from echoai.echo4.self_probe_world import run_probe
from echoai.echo4.self_recovery import MODES, RecoveryStop
from echoai.echo4 import self_recovery_audit as lives
from echoai.echo4.self_recovery_world import RecoveryEnv, physical_step
from echoai.echo4 import self_reuse_audit as reuse
from echoai.echo4.world import Body

ROOT = Path(__file__).resolve().parents[1]
SOURCES = tuple(dict.fromkeys((*reuse.SOURCES, "echo4/sensation_campaign.py",
    "docs/ECHO4-SELF1-FINAL-DESIGN.md", "echo4/self_final.py",
    "echo4/self_final_world.py", "echo4/self_final_audit.py", "tests/test_echo4_self1_final.py")))
GRIDS = {"A": ((60, 65), (46, 67)), "B": ((61, 66), (47, 68)),
         "C": ((62, 67), (50, 71)), "smoke": ((60,), (46,))}
NEGATIVES = ("persistent_heat", "delayed_heat", "reversed_cooling", "late_change",
             "interrupted", "unrestored", "wrong_context", "missing_execution",
             "stale_ticks", "wrong_token", "truncated", "veto")
PARENTS = (
    ("sensation1-predictor-v1", "sensation_campaign", "audit_evidence",
     "96f2deaeefdc40a38d45710dc732106f68295d7a81553bef4b6e554a8f8d1b88"),
    ("boundary1-v1", "boundary_bench", "audit",
     "48789bd52dd733f4f278c09160894d5869530ad0ecfeebe21735ab06e43641f6"),
    ("self1-a-v1", "self_audit", "verify",
     "eeb52994b6b26200f1bcd73b3349530d4a39b5be4e514d7d0568cbf4bf43f6da"),
    ("self1-b-v1", "self_probe_audit", "verify",
     "06fae2d4da1513243d64fb33b14c8c945d3be0f9a450363e1c109798f4ffd0a3"),
    ("self1-c-v1", "self_recovery_audit", "verify",
     "15d8bfba9210027dce9edf4ee3bc5f8a54b6b6bc678f6869e94e01313c3a5b89"),
    ("self1-c-v2", "self_reuse_audit", "verify",
     "74bbdfddfac8199ba8763abee5dbe5fe364fdcea04d0ee3981ed58cdeb2590a0"),
)


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sources():
    return {name: file_hash(ROOT / name) for name in SOURCES}


def parents():
    result = {}
    for name, _, _, _ in PARENTS:
        directory = ROOT / "lab/echo4" / name
        paths = [directory / "report.json", directory / "audit-receipt.json", *sorted(directory.glob("*.jsonl"))]
        result[name] = {p.name: file_hash(p) for p in paths}
    return result


def model_hash(agent):
    return reuse.digest({"sensory_cam_t": agent.sensation.model_hash(),
                         "q": vars(agent.q), "reference": agent.self_change.model_hash()})


def diagnose(base, nominal, body, hc=True, tc=True, heat=0, *, fault=""):
    session = SelfSession(base.new_self_diagnosis(packet(body), nominal))
    traces, truth, terminals, physical_steps, balanced = [], True, 0, 0, True
    maximum = {"h": 0, "t": 0, "forecast_codes": 0}
    for token in range(18, 25):
        plan = session.choose(token)
        if plan is None:
            break
        resource = session.resources()
        maximum["h"] = max(maximum["h"], resource["h_candidates"])
        maximum["t"] = max(maximum["t"], resource["t_candidates"])
        maximum["forecast_codes"] = max(maximum["forecast_codes"], resource["pending_forecast_codes"])
        prior = {"plan": asdict(plan), "diagnosis": session.diagnosis(),
                 "forecast_sha256": reuse.digest(session.model.pending[1:])}
        if fault in ("persistent_heat", "delayed_heat", "reversed_cooling", "external_mimic"):
            receipt, private = novel_probe(body, plan, fault)
            balanced &= all(row["balanced"] for row in private["resource_ledger"])
        else:
            actual_heat = 32 if fault == "late_change" and session.model.diagnosis()["label"] != "unknown" else heat
            receipt, private = run_probe(body, plan, h_coupled=hc, temperature_coupled=tc,
                                         heat=actual_heat, veto_at=2 if fault == "veto" else 0)
        original = public(receipt)
        physical_steps += len(receipt.applied)
        terminals += sum(receipt.terminal)
        if fault == "unrestored":
            receipt = replace(receipt, restored=False)
        elif fault == "wrong_context":
            receipt = replace(receipt, same_context=False)
        elif fault == "missing_execution":
            receipt = replace(receipt, applied=(None,) + receipt.applied[1:])
        elif fault == "stale_ticks":
            receipt = replace(receipt, ticks=(0,) * len(receipt.ticks))
        elif fault == "wrong_token":
            receipt = replace(receipt, token=token + 1)
        elif fault == "truncated":
            receipt = replace(receipt, packets=receipt.packets[:-1])
        result = session.consume(receipt)
        truth &= (body.h, hc) in session.model.h_candidates and (body.temperature, tc, heat) in session.model.t_candidates
        traces.append({"before_execution": prior, "physical_receipt": original,
                       "consumed_receipt": public(receipt), "private_audit_only": private, "after": result})
        if fault == "interrupted":
            session.cancel()
        if session.finished:
            break
    try:
        session.authorized_model()
        denied = False
    except ValueError:
        denied = True
    report = {"diagnosis": session.diagnosis(), "traces": traces, "truth_retained": truth,
              "terminalities": terminals, "physical_steps": physical_steps, "restores": len(traces),
              "authorization_denied": denied, "bounded": maximum["h"] <= 64 and maximum["t"] <= 160
              and maximum["forecast_codes"] <= 1792 and len(traces) <= 6 and physical_steps <= 48,
              "maximum": maximum, "balanced": balanced}
    return session, report


def native_veto(base, diagnosis, body):
    agent = copy.deepcopy(base)
    agent.env = RecoveryEnv(body)
    agent.start_recovery(diagnosis, restored=True, same_context=True)
    agent.cam.slot[agent.cam.get(packet(body))].flags |= SLOT_FLAG_INHIBIT
    before = reuse.digest(vars(agent.t)), lives.sensory_hash(agent.sensation)
    action = agent.turn(0, greedy=True)
    denied = False
    try:
        agent.turn(1, greedy=True)
    except RecoveryStop:
        denied = True
    return {"passed": action == 2 and agent.last_gate_decision == 2 and denied
            and before == (reuse.digest(vars(agent.t)), lives.sensory_hash(agent.sensation))
            and agent.env.total_steps == 1 and agent.env.balanced,
            "action": action, "gate": agent.last_gate_decision,
            "steps": agent.env.total_steps, "stop": agent.recovery.stopped}


def negative_suite(stage, bases, emit):
    report = {"cases": 0, "passed": 0, "physical_steps": 0, "restores": 0,
              "terminalities": 0, "by_fault": {name: {"cases": 0, "passed": 0} for name in NEGATIVES}}
    for body, base, nominal, continuous in bases:
        before = model_hash(base)
        for fault in NEGATIVES:
            _, result = diagnose(base, nominal, body, fault=fault)
            passed = (result["authorization_denied"] and result["diagnosis"]["label"] == "unknown"
                      and result["bounded"] and result["balanced"] and before == model_hash(base))
            if fault == "veto":
                receipts = [t["physical_receipt"] for t in result["traces"]]
                passed &= len(receipts) == 1 and len(receipts[0]["applied"]) == 2 and receipts[0]["gates"][-1] == 2
            report["cases"] += 1
            report["passed"] += passed
            report["by_fault"][fault]["cases"] += 1
            report["by_fault"][fault]["passed"] += passed
            for key in ("physical_steps", "restores", "terminalities"):
                report[key] += result[key]
            emit({"phase": "negative", "stage": stage, "fault_private": fault,
                  "initial_private": asdict(body), "passed": passed, "result": result})
    # An out-of-prior mechanism can be observationally IDENTICAL. Publish
    # this failure of unrestricted identification; do not score it as truth.
    body, base, nominal, continuous = bases[0]
    _, altered = diagnose(base, nominal, body, False, False)
    _, mimic = diagnose(base, nominal, body, fault="external_mimic")
    a = [t["physical_receipt"] for t in altered["traces"]]
    b = [t["physical_receipt"] for t in mimic["traces"]]
    report["alias_witness"] = a == b and altered["diagnosis"] == mimic["diagnosis"]
    emit({"phase": "unidentifiable_outside_prior", "stage": stage,
          "unrestricted_cause_identifiable": False, "body_fault": altered,
          "external_action_dependent_force": mimic})
    nominal_session, _ = diagnose(base, nominal, body)
    report["native_veto"] = native_veto(continuous, nominal_session.authorized_model(), body)
    witness = Body(37, 65)
    reference, _ = lives.school(witness)
    _, insufficient = diagnose(reference, None, witness, heat=4)
    report["insufficient_reference"] = insufficient["authorization_denied"] and insufficient["diagnosis"]["label"] == "unknown"
    emit({"phase": "additional_guards", "stage": stage,
          "native_veto": report["native_veto"], "short_reference": insufficient})
    report["all_passed"] = (report["cases"] == report["passed"] and report["alias_witness"]
                            and report["native_veto"]["passed"] and report["insufficient_reference"])
    return report


def accumulate_reuse(counter, exposed, outcomes, agent, cause):
    for key in ("writes", "body_contamination", "external_writes", "held", "held_unchanged", "reference_preserved"):
        counter[key] += exposed[key]
    counter["q_unchanged_cases"] += exposed["q_unchanged"]
    counter["terminalities"] += exposed["terminalities"]
    counter["invariant_cases"] += (agent.metrics.false_facts == agent.metrics.cortex_calls == agent.cam.destroyed == 0
                                    and exposed["balanced"] and agent.env.resets == 0)
    for outcome in outcomes:
        counter["tasks"] += 1
        counter["success"] += outcome["success"]
        counter["matched"] += bool(outcome["before_execution"]["decision"]["matches"])
        counter["frozen"] += outcome["memory_frozen"]
        counter["balanced_tasks"] += outcome["balanced"]
        counter["terminalities"] += outcome["terminal"]
        counter["by_cause"][cause]["tasks"] += 1
        counter["by_cause"][cause]["success"] += outcome["success"]


def stage(name, emit):
    report = {"stage": name, "conditions": 0, "diagnoses_correct": 0, "blocked_conditions": 0,
              "diagnostic_steps": 0, "diagnostic_restores": 0, "challenge_probes": 0,
              "diagnostic_safe": 0, "diagnostic_bounded": 0, "base_preserved": 0,
              "preparation_steps_per_body": 168, "preparation_restores_per_body": 90,
              "nominal_bodies": 0, "nominal_valid": 0, "exposure_matched": 0, "no_t_same_training": 0,
              "same_continuous_actions": 0, "arms": {a: reuse.summary() for a in reuse.ARMS},
              "paired": {a: {"wins": 0, "losses": 0, "ties": 0} for a in reuse.ARMS[1:]},
              "continuous": {a: lives.totals() for a in MODES}}
    bases = []
    for h, theta in product(*GRIDS[name]):
        body = Body(h, theta)
        base, nominal, school = reuse.school(body)
        continuous, nominal_life = lives.school(body)
        if nominal != nominal_life:
            raise RuntimeError("nominal evidence differs across experimental branches")
        bases.append((body, base, nominal, continuous))
        report["nominal_bodies"] += 1
        report["nominal_valid"] += all(t["balanced"] and not t["terminal"] and t["q_unchanged"] for t in school)
        before = model_hash(base)
        emit({"phase": "school", "stage": name, "initial_private": asdict(body),
              "nominal_reference": public(nominal), "reuse_school": school, "model_sha256": before,
              "continuous_model_sha256": model_hash(continuous)})
        heats = (-16, 0, 16) if name == "smoke" else (-16, -4, 0, 4, 16)
        for hc, tc, heat in product((True, False), (True, False), heats):
            session, diagnostic = diagnose(base, nominal, body, hc, tc, heat)
            cause = private_cause(hc, tc, heat)
            report["conditions"] += 1
            report["diagnoses_correct"] += diagnostic["diagnosis"]["label"] == cause
            report["diagnostic_steps"] += diagnostic["physical_steps"]
            report["diagnostic_restores"] += diagnostic["restores"]
            report["challenge_probes"] += diagnostic["diagnosis"]["challenge_probes"]
            report["diagnostic_safe"] += diagnostic["truth_retained"] and diagnostic["terminalities"] == 0
            report["diagnostic_bounded"] += diagnostic["bounded"]
            report["base_preserved"] += before == model_hash(base)
            if diagnostic["authorization_denied"]:
                report["blocked_conditions"] += 1
                # Denominators retain failed requested goals. No guessed model
                # is manufactured to make either branch continue.
                for arm in report["arms"].values():
                    arm["tasks"] += 3
                    arm["by_cause"][cause]["tasks"] += 3
                emit({"phase": "blocked", "stage": name, "private_initial": asdict(body),
                      "private_condition": [hc, tc, heat], "unexecuted_goals_per_arm": 3,
                      "diagnostic": diagnostic})
                continue
            model = session.authorized_model()
            outcomes, training, runs = {}, {}, {}
            order = (2, 1, 0) if name == "C" else (0, 1, 2)
            goals = [packet(physical_step(body, action, True, True, heat)) for action in order]
            for arm in reuse.ARMS:
                agent, exposed = reuse.expose(base, model, body, hc, tc, heat, arm)
                training[arm] = exposed
                outcomes[arm] = [reuse.task(agent, body, heat, goal, use_t=arm != "no_t") for goal in goals]
                accumulate_reuse(report["arms"][arm], exposed, outcomes[arm], agent, cause)
            fingerprints = [reuse.digest([(t["before"], t["action"], t["after"], t["gate"])
                                          for t in training[a]["traces"]]) for a in reuse.ARMS]
            report["exposure_matched"] += len(set(fingerprints)) == 1
            report["no_t_same_training"] += training["selective"] == training["no_t"]
            for arm in reuse.ARMS[1:]:
                for active, control in zip(outcomes["selective"], outcomes[arm]):
                    key = "ties" if active["success"] == control["success"] else "wins" if active["success"] else "losses"
                    report["paired"][arm][key] += 1
            feasible = lives.viable(h, theta, hc, tc, heat, lives.HORIZON)
            for mode in MODES:
                result = lives.episode(continuous, model, body, hc, tc, heat, mode)
                runs[mode] = result
                counter = report["continuous"][mode]
                counter["conditions"] += 1
                counter["viable"] += feasible
                counter["infeasible"] += not feasible
                counter["completed_viable"] += feasible and result["completed"]
                counter["stops"] += bool(result["stopped"])
                for key in ("completed", "steps", "terminalities", "held", "held_unchanged", "writes",
                            "body_contamination", "legitimate_writes", "external_writes", "truth_retained",
                            "reference_preserved", "resets", "false_facts", "destroyed", "cortex_calls", "resource_balanced"):
                    counter[key] += result[key]
                for key in ("max_h_candidates", "max_t_candidates"):
                    counter[key] = max(counter[key], result[key])
            report["same_continuous_actions"] += runs["selective"]["actions"] == runs["no_protection"]["actions"]
            emit({"phase": "joint", "stage": name, "private_audit_only": {"initial": asdict(body),
                  "hc": hc, "tc": tc, "heat": heat, "cause": cause, "viable": feasible},
                  "diagnostic": diagnostic, "training": training, "tasks": outcomes, "continuous": runs})
    report["negatives"] = negative_suite(name, bases, emit)
    n = 12 if name == "smoke" else 80
    primary = report["arms"]["selective"]
    live = report["continuous"]["selective"]
    report["checks"] = {
        "complete": report["conditions"] == n and report["blocked_conditions"] == 0
                    and all(a["tasks"] == 3 * n for a in report["arms"].values())
                    and all(a["conditions"] == n for a in report["continuous"].values()),
        "diagnosis": report["diagnoses_correct"] == report["diagnostic_safe"] == n and report["challenge_probes"] > 0,
        "bounded": report["diagnostic_bounded"] == n and all(a["max_h_candidates"] <= 64
                   and a["max_t_candidates"] <= 160 for a in report["continuous"].values()),
        "reuse_coverage": 100 * primary["success"] >= 60 * primary["tasks"],
        "reuse_each_cause": all(3 * r["success"] >= r["tasks"] for r in primary["by_cause"].values()),
        "reuse_gain": all(100 * (primary["success"] - report["arms"][a]["success"]) >= 5 * primary["tasks"] for a in reuse.ARMS[1:]),
        "body_benefit": primary["by_cause"]["own"]["success"] > report["arms"]["unprotected"]["by_cause"]["own"]["success"],
        "external_benefit": primary["by_cause"]["external"]["success"] > report["arms"]["freeze_all"]["by_cause"]["external"]["success"],
        "nominal_no_loss": all(primary["by_cause"]["nominal"]["success"] >= report["arms"][a]["by_cause"]["nominal"]["success"] for a in ("unprotected", "freeze_all")),
        "protection": primary["body_contamination"] == live["body_contamination"] == 0
                      and report["arms"]["unprotected"]["body_contamination"] > 0,
        "retained_learning": primary["held"] == primary["held_unchanged"] > 0 and primary["external_writes"] > 0
                            and live["held"] == live["held_unchanged"],
        "matched": report["exposure_matched"] == report["no_t_same_training"] == report["same_continuous_actions"] == n,
        "frozen_reuse": all(a["tasks"] == a["frozen"] and a["q_unchanged_cases"] == n for a in report["arms"].values()),
        "continuous_recovery": live["completed_viable"] > 0 and 100 * live["completed_viable"] >= 90 * live["viable"]
                               and live["terminalities"] == 0 and live["truth_retained"] == n,
        "abstention": report["negatives"]["all_passed"],
        "invariants": report["base_preserved"] == n and report["nominal_valid"] == report["nominal_bodies"]
          and all(a["reference_preserved"] == a["invariant_cases"] == n and a["terminalities"] == 0
                  and a["balanced_tasks"] == a["tasks"] for a in report["arms"].values())
          and all(a["resets"] == a["false_facts"] == a["destroyed"] == a["cortex_calls"] == 0
                  and a["reference_preserved"] == a["resource_balanced"] == n for a in report["continuous"].values()),
    }
    report["passed"] = all(report["checks"].values())
    return report


def campaign(*, quick=False, emit=lambda value: None, progress=lambda value: None):
    manifest, ancestry = sources(), parents()
    first = "smoke" if quick else "A"
    progress("Executing " + first)
    stages = {first: stage(first, emit)}
    lock = None
    if not quick and stages["A"]["passed"]:
        lock = {"phase": "freeze_before_B", "sources": manifest, "parents": ancestry,
                "A_sha256": reuse.digest(stages["A"]), "scope": SCOPE}
        emit(lock)
        for name in ("B", "C"):
            if sources() != manifest:
                raise ValueError("sources changed after lock; new exam version required")
            progress("Executing " + name)
            stages[name] = stage(name, emit)
    unchanged = sources() == manifest and parents() == ancestry
    eligible = not quick and lock is not None and unchanged and all(s["passed"] for s in stages.values())
    return {"schema": "e4-self1-final-v1", "profile": "smoke" if quick else "campaign", "scope": SCOPE,
            "sources": manifest, "parents": ancestry, "stages": stages, "sources_and_parents_unchanged": unchanged,
            "lock_sha256": reuse.digest(lock) if lock is not None else None,
            "closure_eligible": eligible, "self1_green": False}


def record(output, *, quick=False, progress=lambda value: None):
    output.mkdir(parents=True, exist_ok=False)
    trace_digest = hashlib.sha256()
    with (output / "traces.jsonl").open("xb") as trace:
        def emit(value):
            raw = canonical(value)
            trace.write(raw)
            trace.flush()  # lock is on disk before opening B
            trace_digest.update(raw)
        report = campaign(quick=quick, emit=emit, progress=progress)
    report["trace_sha256"] = trace_digest.hexdigest()
    report["reproduction_sha256"] = reuse.digest(report)
    with (output / "report.json").open("xb") as handle:
        handle.write(canonical(report))
    return report


def verify(output, *, progress=lambda value: None):
    stored, findings, parent_audits = {}, [], {}
    try:
        stored = json.loads((output / "report.json").read_bytes())
        if not isinstance(stored, dict) or stored.get("profile") not in ("smoke", "campaign"):
            raise ValueError("invalid report schema/profile")
        if stored.get("sources") != sources() or stored.get("parents") != parents():
            raise ValueError("source or ancestor binding mismatch")
        trace_digest = hashlib.sha256()
        with (output / "traces.jsonl").open("rb") as trace:
            def emit(value):
                raw = canonical(value)
                if trace.readline() != raw:
                    raise ValueError("trace differs from complete physical replay")
                trace_digest.update(raw)
            rebuilt = campaign(quick=stored["profile"] == "smoke", emit=emit, progress=progress)
            if trace.read(1):
                raise ValueError("unexpected trailing trace")
        rebuilt["trace_sha256"] = trace_digest.hexdigest()
        rebuilt["reproduction_sha256"] = reuse.digest(rebuilt)
        if canonical(stored) != canonical(rebuilt):
            raise ValueError("report differs from complete physical replay")
        if stored["profile"] == "campaign":
            for name, module, function, expected in PARENTS:
                progress("Replaying ancestor " + name)
                audit = getattr(importlib.import_module("echoai.echo4." + module), function)(ROOT / "lab/echo4" / name)
                parent_audits[name] = audit
                if not audit.get("valid") or expected not in audit.values():
                    raise ValueError("ancestor replay failed: " + name)
        if stored["sources"] != sources() or stored["parents"] != parents():
            raise ValueError("sources/ancestors changed during replay")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        findings.append(str(exc))
    green = (not findings and stored.get("closure_eligible", False) and len(parent_audits) == len(PARENTS))
    return {"valid": not findings, "findings": findings, "self1_green": green,
            "scope": SCOPE, "parent_audits": parent_audits,
            "reproduction_sha256": stored.get("reproduction_sha256") if not findings else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("campaign", "verify"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    progress = lambda value: print(value, file=sys.stderr, flush=True)
    if args.command == "campaign":
        report = record(args.directory, quick=args.quick, progress=progress)
        ok = report["closure_eligible"] or args.quick
    else:
        report = verify(args.directory, progress=progress)
        ok = report["valid"]
        if args.write_receipt:
            with (args.directory / "audit-receipt.json").open("xb") as handle:
                handle.write(canonical(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
