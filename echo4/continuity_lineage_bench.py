"""CONT-C development recipes, full-state continuations and independent replay."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from echoai.echo4 import continuity_active_bench as previous
from echoai.echo4 import continuity_lineage as c
from echoai.echo4.boundary_world import Experiment, packet, run_pair
from echoai.echo4.self_attribution import CATALOG, ProbePlan
from echoai.echo4.self_probe_world import run_probe
from echoai.echo4.self_recovery import RecoveryStop
from echoai.echo4.self_recovery_world import physical_step
from echoai.echo4.self_reuse_agent import SelfReuseAgent
from echoai.echo4.world import Body

CASES = ("resume_diagnostic", "resume_recovery", "resume_reuse", "fork_left", "fork_right",
         "fork_goal0", "fork_goal1", "body_quarantine", "body_commissioned", "body_active",
         "reuse_body_quarantine", "reuse_body_active", "descendant_quarantine", "descendant_active",
         "reuse_descendant_active", "second_body", "commissioned_fork", "terminal_resume",
         "terminal_fork", "terminal_descendant_quarantine", "terminal_descendant_active")
HORIZON = 4


def wrap(active):
    raw = active.dumps()
    return c.LineageRun.import_active(raw, expected_sha256=hashlib.sha256(raw).hexdigest(),
                                      individual="echo-1", body="body-1")


def calibration(body):
    pairs = tuple(run_pair(Experiment(body, action), 8 * action + i)[0]
                  for action in (0, 1) for i in range(1, 9))
    nominal = run_probe(body, ProbePlan(17, 0, CATALOG[0], 0, 0))[0]
    return pairs, nominal


def commission(run):
    run.commission(*calibration(run.agent.env.initial), scope=run.scope)


def finish_diagnosis(run):
    active = run._active()
    while not active.session.finished:
        if active.session.model.pending is None and run.choose_probe(active.session.model.last_token + 1) is None:
            break
        if active.inbox is None:
            run.queue_receipt(previous.physical_receipt(active), scope=run.scope)
        run.consume_receipt()


def authorize(run, target_action=0):
    if type(run.agent) is SelfReuseAgent:
        target = packet(physical_step(run.agent.env.initial, target_action, True, True, 0))
        run.arm_reuse(target, scope=run.scope, token=run.agent.trial_token + 1,
                      restored=True, nominal_body_confirmed=True)
    else:
        run.start_recovery(scope=run.scope, restored=True, same_context=True)


def prepared(case):
    if case not in CASES:
        raise ValueError("unknown lineage case")
    if case.startswith("terminal_"):
        parent = wrap(previous.prepared("terminal"))
        if case == "terminal_resume":
            return parent
        if case == "terminal_fork":
            return parent.fork("left", "right")[0]
    elif case.startswith("fork_goal"):
        active = previous.new_run(reuse_agent=True, hc=True)
        previous.finish_diagnosis(active)
        siblings = wrap(active).fork("left", "right")
        action = int(case[-1])
        run = siblings[action]
        authorize(run, action)
        return run
    else:
        is_reuse = case.startswith("reuse_") or case == "resume_reuse"
        parent = wrap(previous.prepared("reuse_done" if is_reuse else "recovery_learned"))
    if case == "resume_diagnostic":
        return wrap(previous.prepared("inbox"))
    if case == "resume_recovery":
        return parent
    if case == "resume_reuse":
        return wrap(previous.prepared("reuse_armed"))
    if case in ("fork_left", "fork_right"):
        return parent.fork("left", "right")[case == "fork_right"]
    descendant = "descendant" in case
    run = parent.allocate_body(Body(60, 46), body_id="body-2", token="allocation-1",
                               individual="echo-2" if descendant else None)
    if case.endswith("quarantine"):
        return run
    commission(run)
    if case == "body_commissioned":
        return run
    if case == "commissioned_fork":
        return run.fork("left", "right")[0]
    finish_diagnosis(run)
    authorize(run)
    run.step(greedy=True)
    if case == "second_body":
        run = run.allocate_body(Body(61, 46), body_id="body-3", token="allocation-2")
        commission(run)
    return run


def trajectory(run, horizon=HORIZON):
    c.integer(horizon, 0, 128)
    initial = run.state_hash()
    rows = []

    def record(event, action=None):
        a = run.agent
        rows.append({"event": event, "action": action, "body": asdict(a.env.body),
                     "turns": a.metrics.turns, "life_turns": a.life_turns,
                     "reward": a.last_reward, "gate": a.last_gate_decision,
                     "diagnosis": None if run.active is None else run.active.session.diagnosis(),
                     "learning": None if a.recovery is None else a.recovery.last,
                     "state_sha256": run.state_hash()})

    if run.active is None:
        before = run.state_hash()
        try:
            run.step()
        except RuntimeError:
            if run.state_hash() != before:
                raise AssertionError("quarantine rejection changed state")
            record("quarantine_block")
        else:
            raise AssertionError("quarantined body acted")
    else:
        active = run.active
        while active.phase == "diagnostic" and not active.session.finished:
            if active.session.model.pending is None:
                plan = run.choose_probe(active.session.model.last_token + 1)
                record("choose")
                if plan is None:
                    break
            if active.inbox is None:
                run.queue_receipt(previous.physical_receipt(active), scope=run.scope)
                record("receive")
            run.consume_receipt()
            record("consume")
        if active.phase == "diagnostic" and active.session.diagnosis()["confirmed"]:
            authorize(run)
            record("authorize")
        for index in range(horizon):
            if (active.phase == "diagnostic" or run.agent.episode_terminal
                    or run.agent.recovery is not None and run.agent.recovery.stopped
                    or type(run.agent) is SelfReuseAgent and not run.agent.trial_active):
                break
            try:
                action = run.step(greedy=index % 2 == 0)
                record("turn", action)
            except RecoveryStop:
                record("stop")
                break
    a = run.agent
    return json.loads(c.b.base.canonical({"initial_sha256": initial, "events": rows,
        "final_sha256": run.state_hash(), "identity": run.identity, "scope": run.scope,
        "terminal": a.episode_terminal, "quarantined": run.active is None,
        "balanced": a.env.balanced, "turns": a.metrics.turns, "life_turns": a.life_turns,
        "cortex_calls": a.metrics.cortex_calls, "false_facts": a.metrics.false_facts,
        "destroyed": a.cam.destroyed}))


def resumed(path, sha256, horizon=HORIZON):
    result = subprocess.run([sys.executable, "-m", "echoai.echo4.continuity_lineage_bench", "resume",
                             str(Path(path).resolve()), sha256, str(horizon)], cwd=c.b.ROOT.parent,
                            capture_output=True, text=True, timeout=180, check=True)
    return json.loads(result.stdout)


def sources():
    extras = ("echo4/continuity_lineage_bench.py", "tests/test_echo4_continuity1c.py",
              "docs/ECHO4-CONTINUITY1-C-DESIGN.md")
    return {**previous.sources(), **c.source_hashes(),
            **{p: hashlib.sha256((c.b.ROOT / p).read_bytes()).hexdigest() for p in extras}}


def row(case, path, run, raw):
    sha256 = hashlib.sha256(raw).hexdigest()
    reference = trajectory(run)
    restored = resumed(path, sha256)
    return {"case": case, "checkpoint_sha256": sha256, "checkpoint_bytes": len(raw),
            "reference": reference, "restored": restored, "equal": reference == restored}


def checks(rows):
    by_case = {r["case"]: r["reference"] for r in rows}
    same = [by_case[name] for name in ("fork_left", "fork_right")]
    # State hashes must differ by lineage; actual decisions/body trajectories
    # under identical inputs must not differ merely because of branch labels.
    def physical(result):
        return [{k: v for k, v in e.items() if k != "state_sha256"} for e in result["events"]]
    goals = [by_case[name] for name in ("fork_goal0", "fork_goal1")]
    return {"exact_resume": all(r["equal"] for r in rows),
            "invariants": all(r["reference"]["balanced"] and not any(r["reference"][k]
                for k in ("cortex_calls", "false_facts", "destroyed")) for r in rows),
            "same_inputs_same_physics": physical(same[0]) == physical(same[1]),
            "distinct_branches": same[0]["scope"] != same[1]["scope"],
            "observed_divergence": goals[0]["events"][0]["action"] != goals[1]["events"][0]["action"]
                and goals[0]["events"][0]["body"] != goals[1]["events"][0]["body"],
            "terminal_preserved": all(by_case[n]["terminal"] and not by_case[n]["events"]
                                       for n in ("terminal_resume", "terminal_fork")),
            "quarantine_no_actions": all(r["events"] == [r["events"][0]]
                and r["events"][0]["event"] == "quarantine_block" and r["life_turns"] == 0
                for n, r in by_case.items() if n.endswith("quarantine"))}


def report(rows, locked):
    results = checks(rows)
    results["sources_unchanged"] = locked == sources()
    return {"schema": "continuity-c-development-v1", "sources": locked, "cases": rows,
            "checks": results, "development_passed": all(results.values()), "continuity1_green": False,
            "limits": ["virtual CONT-B lineage; not subjective identity", "trusted custody, not distributed exclusion",
                       "supervised calibration/allocation, not self-repair", "CONT-D pending; no LLM/DREAM"]}


def campaign(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    locked, rows = sources(), []
    for case in CASES:
        run = prepared(case)
        path, raw = directory / (case + ".json"), run.dumps()
        run.save(path)
        rows.append(row(case, path, run, raw))
    result = report(rows, locked)
    with (directory / "report.json").open("xb") as handle:
        handle.write(c.b.base.canonical(result))
    return result


def verify(directory):
    findings = []
    try:
        directory = Path(directory)
        saved = json.loads((directory / "report.json").read_bytes())
        if type(saved) is not dict or saved.get("sources") != sources():
            raise ValueError("report/source mismatch")
        locked, rows = sources(), []
        for case in CASES:
            run = prepared(case)
            raw, path = run.dumps(), directory / (case + ".json")
            if path.read_bytes() != raw:
                raise ValueError(case + ": checkpoint differs from reconstruction")
            rows.append(row(case, path, run, raw))
        rebuilt = report(rows, locked)
        if saved != rebuilt or not rebuilt["development_passed"]:
            raise ValueError("report differs from full replay")
    except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError) as exc:
        findings.append(str(exc))
    return {"valid": not findings, "findings": findings, "continuity1_green": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("campaign", "verify"):
        sub.add_parser(name).add_argument("directory", type=Path)
    resume = sub.add_parser("resume")
    resume.add_argument("path", type=Path)
    resume.add_argument("digest")
    resume.add_argument("horizon", type=int)
    args = parser.parse_args()
    if args.command == "resume":
        result = trajectory(c.load(args.path, expected_sha256=args.digest), args.horizon)
    elif args.command == "verify":
        result = verify(args.directory)
    else:
        recorded = campaign(args.directory)
        result = {"cases": len(recorded["cases"]), "development_passed": recorded["development_passed"],
                  "checks": recorded["checks"], "continuity1_green": False}
    print(json.dumps(result, sort_keys=True))
    if result.get("valid") is False or result.get("development_passed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
