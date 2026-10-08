"""MAINT B/C/D source-locked development, prospective exam and native audit."""
import argparse
import copy
import hashlib
from itertools import product
import json
from pathlib import Path
import random
import subprocess
import sys

from echoai.echo4 import maintain_bench as a
from echoai.echo4 import maintain_continuity as c
from echoai.echo4.continuity import ROOT, canonical
from echoai.echo4.continuity_final_audit import file_hash, read_json
from echoai.echo4.dream_bench import persist
from echoai.echo4.maintain_control import MaintainControl
from echoai.echo4.maintain_model import MODES, MaintainStop
from echoai.echo4.maintain_world import MaintenanceEnv
from echoai.echo4.world import Body

SCHEMA = "echo4-maintain-final-v1"
PARENT = ROOT / "lab/echo4/maintain1-a-v1"
PARENT_DIGEST = "ec4a6d1eee3c2f1f985209727d95a8a675ed8f4ceaceb7dd48bfa89e1ef8d91c"
DEVELOPMENT = ((80, 72), (73, 56), (73, 88), (89, 56), (89, 88))
HORIZON = 256
RECURRENCE = ((48, "clogged"), (112, "clogged"), (176, "clogged"))
SCENARIOS = {
    "nominal": ("healthy", 0, 3, ()), "external": ("healthy", 2, 3, ()),
    "clogged": ("clogged", 0, 3, ()), "mixed": ("clogged", 2, 3, ()),
    "recurrent": ("healthy", 0, 3, RECURRENCE),
    "recurrent_mixed": ("healthy", 2, 3, RECURRENCE),
    "irreparable": ("seized", 0, 3, ()), "no_spares": ("clogged", 0, 0, ()),
    "exhausted": ("healthy", 0, 1, RECURRENCE),
    "hot_stress": ("clogged", 4, 3, RECURRENCE),
}
RECOVERABLE = tuple(SCENARIOS)[:6]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def sources():
    extra = ("echo4/maintain_model.py", "echo4/maintain_control.py", "echo4/maintain_continuity.py",
             "echo4/maintain_final.py", "tests/test_echo4_maintain1.py", "docs/ECHO4-MAINTAIN1-BCD-DESIGN.md")
    return {**a.sources(), **{p: file_hash(ROOT / p) for p in extra}}


def parent():
    report, receipt = read_json(PARENT / "report.json"), read_json(PARENT / "audit-receipt.json")
    unsigned = dict(report)
    digest = unsigned.pop("reproduction_sha256")
    if (digest != PARENT_DIGEST or sha(canonical(unsigned)) != digest
            or receipt["valid"] is not True or receipt["maintain1_green"] is not False
            or receipt["reproduction_sha256"] != digest or report["sources"] != a.sources()
            or report["parent"] != a.parent_binding()):
        raise ValueError("MAINT-A parent mismatch")
    return {p.name: file_hash(p) for p in sorted(PARENT.iterdir()) if p.is_file()}


def exam_bodies():
    rng, excluded, result = random.Random(260925), set(DEVELOPMENT), []
    for _ in range(2):
        pool = [p for p in product(range(65, 96), range(49, 96)) if p not in excluded]
        group = tuple(rng.sample(pool, 12))
        excluded.update(group)
        result.append(group)
    return tuple(result)


def prepared(body, scenario, mode="adaptive", *, veto_at=0):
    fault, heat, spares, events = SCENARIOS[scenario]
    env = MaintenanceEnv(Body(*body), fault=fault, spares=spares, external_heat=heat)
    return c.MaintainRun(MaintainControl(env, mode=mode), events=events, veto_at=veto_at)


def trajectory(run, horizon):
    frames = []
    for _ in range(horizon):
        try:
            event = run.step()
        except MaintainStop:
            break
        frames.append(event)
        if run.agent.maintenance.stopped:
            break
    return {"frames": frames, "state_sha256": sha(run.dumps())}


def episode(body, scenario, mode, *, horizon=HORIZON):
    run = prepared(body, scenario, mode)
    frames, invariants, confirmed, previous_repairs, confirmation_pending = [], True, 0, 0, False
    for _ in range(horizon):
        try:
            event = run.step()
        except MaintainStop:
            break
        frames.append(event)
        agent, env = run.agent, run.agent.env
        if event["event"] == "step":
            tr = env.last_transition
            invariants &= (env.balanced and env.spares_balanced and tr.balanced
                           and Body(agent.H, agent.temperature) == env.body
                           and len(agent.observation(env.cell())) == 16 and env.resets == 0
                           and agent.cam.destroyed == 0 and agent.metrics.false_facts == 0
                           and agent.metrics.cortex_calls == 0)
            # Confirmation is evaluated by a later *executed* cooling action,
            # not by the service label or the controller's own assertion.
            if confirmation_pending and tr.action == 1 and env.last_service.fault_before == "healthy":
                if tr.before.temperature - tr.after.temperature == 16 - env._external_heat:
                    confirmed += 1
                    confirmation_pending = False
            if env.repairs > previous_repairs:
                previous_repairs = env.repairs
                confirmation_pending = True
        if agent.maintenance.stopped:
            break
    agent, env = run.agent, run.agent.env
    # Structural/custody validation is independent of policy inputs.
    c.validate(agent, run.next_turn)
    return {"body": body, "scenario": scenario, "mode": mode, "frames": frames,
            "trace_sha256": sha(canonical(frames)), "ledger": env.audit_state(),
            "final": (env.body.h, env.body.temperature), "terminal": agent.episode_terminal,
            "stopped": agent.maintenance.stopped, "conflicts": agent.maintenance.conflicts,
            "model_predictions": agent.maintenance.predictions,
            "confirmed_recoveries": confirmed, "complete": run.next_turn == horizon,
            "invariants": bool(invariants)}


def summary(rows):
    return {"episodes": len(rows), "complete": sum(r["complete"] for r in rows),
            "terminal": sum(r["terminal"] for r in rows),
            "stops": sum(bool(r["stopped"]) for r in rows),
            "confirmed_recoveries": sum(r["confirmed_recoveries"] for r in rows),
            "model_predictions": sum(r["model_predictions"] for r in rows),
            **{k: sum(r["ledger"][k] for r in rows) for k in (
                "steps", "work_done", "repairs", "services_paid", "service_attempts",
                "resource_in", "resource_used", "resource_spill", "service_resource_used")}}


def batch(bodies, progress=lambda _: None):
    arms = {mode: [] for mode in MODES}
    for i, body in enumerate(bodies):
        progress(f"body {i+1}/{len(bodies)} {body}")
        for scenario in SCENARIOS:
            for mode in MODES:
                arms[mode].append(episode(body, scenario, mode))
    totals = {mode: summary(rows) for mode, rows in arms.items()}
    adaptive = totals["adaptive"]
    core = [r for r in arms["adaptive"] if r["scenario"] in RECOVERABLE]
    expected_repairs = len(bodies) * 8
    checks = {
        "gain_no_repair": adaptive["work_done"] * 100 >= totals["no_repair"]["work_done"] * 110,
        "gain_no_history": adaptive["work_done"] * 100 >= totals["no_history"]["work_done"] * 110,
        "gain_fixed": adaptive["work_done"] * 100 >= totals["fixed"]["work_done"] * 105,
        "core_completion": sum(r["complete"] for r in core) * 100 >= len(core) * 90,
        "effective_repairs": sum(r["ledger"]["repairs"] for r in core) * 100 >= expected_repairs * 80,
        "executed_confirmation": sum(r["confirmed_recoveries"] for r in core) * 100 >= expected_repairs * 80,
        "adaptive_no_deaths": adaptive["terminal"] == 0,
        "invariants": all(r["invariants"] for rows in arms.values() for r in rows),
        "irreparable_not_repaired": all(r["ledger"]["repairs"] == 0 for rows in arms.values()
                                         for r in rows if r["scenario"] == "irreparable"),
        "cost_without_success_reported": any(r["ledger"]["services_paid"] > r["ledger"]["repairs"]
                                             for r in arms["adaptive"]),
    }
    by_scenario = {s: {m: summary([r for r in rows if r["scenario"] == s]) for m, rows in arms.items()}
                   for s in SCENARIOS}
    losses = {m: sum(r["ledger"]["work_done"] < control["ledger"]["work_done"]
                     for r, control in zip(arms["adaptive"], arms[m])) for m in MODES if m != "adaptive"}
    return {"arms": arms, "totals": totals, "by_scenario": by_scenario, "paired_work_losses": losses,
            "core_complete": sum(r["complete"] for r in core), "core_episodes": len(core),
            "expected_core_repairs": expected_repairs, "checks": checks, "passed": all(checks.values())}


def resumed(path, digest, horizon):
    p = subprocess.run([sys.executable, "-m", "echoai.echo4.maintain_final", "resume", str(path.resolve()),
                        "--digest", digest, "--steps", str(horizon)], cwd=ROOT.parent,
                       capture_output=True, text=True, check=True, timeout=120)
    return json.loads(p.stdout)


def continuity_cases():
    return {"initial": ("nominal", 0, 0, False), "partial_one": ("clogged", 1, 0, False),
            "partial_two": ("clogged", 2, 0, False), "after_service": ("clogged", 6, 0, False),
            "future_fault": ("recurrent", 47, 0, False), "exhaustion": ("exhausted", 100, 0, False),
            "no_spares": ("no_spares", 4, 0, False), "irreparable": ("irreparable", 3, 0, False),
            "veto": ("clogged", 3, 3, False), "operator": ("clogged", 2, 0, True),
            "terminal": ("hot_stress", 1, 1, False), "budget": ("nominal", 512, 0, False)}


def mutant_suite(raw):
    original = json.loads(raw)
    mutants = []
    for tag, field, value in (("maintain_env", "_spares", 4), ("maintain_env", "resource_used", 0),
                              ("maintain_model", "progress", 4), ("maintain_model", "steps", 99),
                              ("maintain_model", "pending", True), ("maintain_model", "boxes", {"tuple": []}),
                              ("maintain_agent", "cortex_enabled", True), ("maintain_agent", "H", 0)):
        data = copy.deepcopy(original)
        record = next(r for r in data["state"]["objects"] if r["type"] == tag)
        record["fields"][field] = value
        mutants.append((tag + ":" + field, canonical(data)))
    data = copy.deepcopy(original)
    data["sources"] = {}
    mutants.append(("sources", canonical(data)))
    data = copy.deepcopy(original)
    data["cursor"] = 99
    mutants.append(("cursor", canonical(data)))
    results = {}
    for name, changed in mutants:
        try:
            c.loads(changed, expected_sha256=sha(changed))
        except (ValueError, TypeError, KeyError):
            results[name] = True
        else:
            results[name] = False
    try:
        c.loads(raw + b" ", expected_sha256=sha(raw))
    except ValueError:
        results["external_digest"] = True
    else:
        results["external_digest"] = False
    return results


def continuity_suite(directory, *, checking=False, progress=lambda _: None):
    rows, mutation_raw = [], None
    for name, (scenario, count, veto, stop) in continuity_cases().items():
        progress("continuity " + name)
        run = prepared((80, 124) if name == "terminal" else (80, 72), scenario, veto_at=veto)
        for _ in range(count):
            try:
                run.step()
            except MaintainStop:
                break
        if stop:
            run.stop()
        raw = run.dumps()
        if name == "partial_two":
            mutation_raw = raw
        path = directory / ("continuity-" + name + ".json")
        if checking:
            if path.read_bytes() != raw:
                raise ValueError("checkpoint reconstruction mismatch: " + name)
        else:
            run.save(path)
        before = {"progress": run.agent.env._progress, "paid": run.agent.env.services_paid,
                  "stopped": run.agent.maintenance.stopped, "terminal": run.agent.episode_terminal}
        reference = trajectory(run, 32)
        other = resumed(path, sha(raw), 32)
        rows.append({"case": name, "before": before, "checkpoint_sha256": sha(raw),
                     "checkpoint_bytes": len(raw), "reference": reference, "resumed": other,
                     "equal": canonical(reference) == canonical(other)})
    mutants = mutant_suite(mutation_raw)
    initial = {r["case"]: r["before"] for r in rows}
    checks = {"equal_continuations": all(r["equal"] for r in rows), "mutants": all(mutants.values()),
              "partial_preserved": initial["partial_one"]["progress"] == 1 and initial["partial_two"]["progress"] == 2,
              "paid_preserved": initial["after_service"]["paid"] == 1,
              "terminal_preserved": initial["terminal"]["terminal"],
              "operator_preserved": initial["operator"]["stopped"] == "operator",
              "veto_preserved": initial["veto"]["stopped"] == "gate_veto"}
    return {"rows": rows, "mutants": mutants, "checks": checks, "passed": all(checks.values())}


def campaign(directory, *, checking=False, progress=lambda _: None):
    manifest, ancestry, exams = sources(), parent(), exam_bodies()
    lock = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "exams": exams,
            "scenarios": SCENARIOS, "horizon": HORIZON, "gain_percent": (110, 105, 110),
            "completion_percent": 90, "repair_percent": 80}
    lock_sha = persist(directory, "lock.json", lock, checking)
    development = batch(DEVELOPMENT, lambda s: progress("B " + s))
    persist(directory, "development.json", development, checking)
    continuity = continuity_suite(directory, checking=checking, progress=progress)
    persist(directory, "continuity.json", continuity, checking)
    stages = []
    if development["passed"] and continuity["passed"]:
        for i, bodies in enumerate(exams):
            stages.append(batch(bodies, lambda s: progress(f"D{i+1} " + s)))
            persist(directory, f"exam-{i+1}.json", stages[-1], checking)
    if sources() != manifest or parent() != ancestry:
        raise ValueError("sources or parent changed during campaign")
    criteria = (development["passed"] and continuity["passed"] and len(stages) == 2
                and all(s["passed"] for s in stages))
    report = {"schema": SCHEMA, "sources": manifest, "parent": ancestry, "lock_sha256": lock_sha,
              "scope": "model-conditional autonomous virtual maintenance; not learned physics or general repair",
              "development": {k: development[k] for k in ("totals", "checks", "passed")},
              "continuity": {k: continuity[k] for k in ("checks", "passed", "mutants")},
              "exams": [{k: s[k] for k in ("totals", "checks", "passed", "by_scenario", "paired_work_losses",
                                          "core_complete", "core_episodes", "expected_core_repairs")} for s in stages],
              "criteria_passed": bool(criteria), "maintain1_green": False}
    report["reproduction_sha256"] = sha(canonical(report))
    persist(directory, "report.json", report, checking)
    return report


def verify(directory, *, progress=lambda _: None):
    findings, digest, green = [], None, False
    try:
        stored = read_json(directory / "report.json")
        if type(stored) is not dict:
            raise ValueError("invalid report shape")
        digest = stored.get("reproduction_sha256")
        if stored["sources"] != sources() or stored["parent"] != parent():
            raise ValueError("source/parent mismatch")
        result = campaign(directory, checking=True, progress=progress)
        baseline = a.verify(PARENT)
        if baseline["valid"] is not True:
            raise ValueError("MAINT-A reconstruction failed")
        green = result["criteria_passed"]
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "reproduction_sha256": digest,
            "maintain1_green": bool(green and not findings),
            "scope": "declared virtual model-conditional maintenance profile only"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("development", "campaign", "verify", "resume"))
    parser.add_argument("directory", type=Path)
    parser.add_argument("--digest")
    parser.add_argument("--steps", type=int, default=32)
    parser.add_argument("--write-receipt", action="store_true")
    args = parser.parse_args()
    progress = lambda s: print(s, file=sys.stderr, flush=True)
    if args.command == "resume":
        if not 0 <= args.steps <= 512:
            parser.error("invalid continuation budget")
        run = c.loads(args.directory.read_bytes(), expected_sha256=args.digest)
        print(json.dumps(trajectory(run, args.steps)))
        return 0
    if args.command in ("development", "campaign"):
        if args.write_receipt:
            parser.error("audit separately before writing a receipt")
        args.directory.mkdir(parents=True, exist_ok=False)
        if args.command == "development":
            result = batch(DEVELOPMENT, progress)
            persist(args.directory, "development.json", result, False)
            print(json.dumps({k: result[k] for k in ("totals", "checks", "passed")}, indent=2))
            return 0
        result = campaign(args.directory, progress=progress)
        print(json.dumps({k: result[k] for k in ("criteria_passed", "maintain1_green", "reproduction_sha256")}, indent=2))
        return 0 if result["criteria_passed"] else 1
    result = verify(args.directory, progress=progress)
    if args.write_receipt:
        persist(args.directory, "audit-receipt.json", result, False)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
