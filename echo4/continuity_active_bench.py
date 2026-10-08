"""CONT-B development campaign: full state, fresh process, read-only replay."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path

from echoai.core.qn import SLOT_FLAG_INHIBIT

from echoai.echo4 import continuity_active as c
from echoai.echo4 import self_recovery_audit as lives
from echoai.echo4 import self_reuse_audit as reuse
from echoai.echo4.boundary_world import packet
from echoai.echo4.self_probe_world import run_probe
from echoai.echo4.self_recovery import RecoveryStop
from echoai.echo4.self_recovery_world import RecoveryEnv, physical_step
from echoai.echo4.self_reuse_agent import SelfReuseAgent
from echoai.echo4.world import Body

CASES = ("initial", "pending", "inbox", "consumed", "confirmed", "cancelled", "invalid",
         "recovery_initial", "recovery_learned", "unprotected", "veto", "stopped", "terminal",
         "exposure_armed", "exposure_done", "reuse_armed", "reuse_done", "reuse_no_t")


def new_run(*, reuse_agent=False, hc=False, tc=True, heat=0):
    body = Body(60, 46)
    if reuse_agent:
        agent, nominal, _ = reuse.school(body)
        reuse.restore_trial(agent, body, hc=hc, tc=tc, heat=heat)
    else:
        agent, nominal = lives.school(body)
        agent.env = RecoveryEnv(body, h_coupled=hc, temperature_coupled=tc, heat=heat)
    return c.ActiveRun(agent, nominal)


def physical_receipt(run):
    """Private executor only. These flags never enter SelfSession inference."""
    plan = run.session.model.pending[0]
    env = run.agent.env
    return run_probe(env.initial, plan, h_coupled=env._hc,
                     temperature_coupled=env._tc, heat=env._heat)[0]


def finish_diagnosis(run):
    while not run.session.finished:
        if run.session.model.pending is None and run.choose_probe(run.session.model.last_token + 1) is None:
            break
        if run.inbox is None:
            run.queue_receipt(physical_receipt(run))
        run.consume_receipt()


def prepared(case):
    if case not in CASES:
        raise ValueError("unknown case")
    is_reuse = case.startswith(("reuse_", "exposure_"))
    run = new_run(reuse_agent=is_reuse, hc=case.startswith("reuse_"))
    if case == "initial":
        return run
    if case in ("pending", "inbox", "consumed", "cancelled", "invalid"):
        run.choose_probe(18)
        if case == "cancelled":
            run.cancel()
        elif case != "pending":
            receipt = physical_receipt(run)
            run.queue_receipt(replace(receipt, token=19) if case == "invalid" else receipt)
            if case != "inbox":
                run.consume_receipt()
        return run
    finish_diagnosis(run)
    if case == "confirmed":
        return run
    if case == "terminal":
        # Explicit negative witness: an unmodelled pulse arrives AFTER the
        # diagnosis. Real physics reaches a terminal; persistence must not
        # repair it or claim that post-hoc rejection prevented the damage.
        run.agent.env = RecoveryEnv(run.agent.env.initial, h_coupled=False, heat=-127)
    if case.startswith("exposure_"):
        run.arm_exposure(0, mode="selective", token=run.agent.trial_token + 1,
                         restored=True, same_context=True)
    elif case.startswith("reuse_"):
        target = packet(physical_step(run.agent.env.initial, 0, True, True, 0))
        run.arm_reuse(target, token=run.agent.trial_token + 1, restored=True,
                      nominal_body_confirmed=True, use_t=case != "reuse_no_t")
    else:
        mode = "no_protection" if case == "unprotected" else "selective"
        run.start_recovery(restored=True, same_context=True, mode=mode)
    if case == "veto":
        slot = run.agent.cam.get(run.initial)
        run.agent.cam.slot[slot].flags |= SLOT_FLAG_INHIBIT
    steps = 3 if case in ("recovery_learned", "unprotected") else 1 if case.endswith("_done") or case == "veto" else 0
    if case in ("stopped", "terminal"):
        steps = 128
    for _ in range(steps):
        if run.agent.episode_terminal:
            break
        try:
            run.step(greedy=True)
        except RecoveryStop:
            break
    if case == "stopped" and not run.agent.recovery.stopped:
        raise AssertionError("missing real stop witness")
    if case == "terminal" and not run.agent.episode_terminal:
        raise AssertionError("missing real terminal witness")
    return run


def trajectory(run, horizon=8):
    c.integer(horizon, 0, 128)
    initial = run.state_hash()
    rows = []

    def record(event, action=None):
        a = run.agent
        rows.append({"event": event, "action": action, "phase": run.phase,
                     "next_turn": run.next_turn, "life_turns": a.life_turns,
                     "diagnosis": run.session.diagnosis(), "body": asdict(a.env.body),
                     "gate": a.last_gate_decision, "reward": a.last_reward,
                     "learning": None if a.recovery is None else a.recovery.last,
                     "diagnostic_clock": run.diagnostic_clock(),
                     "state_sha256": run.state_hash()})

    while run.phase == "diagnostic" and not run.session.finished:
        if run.session.model.pending is None:
            plan = run.choose_probe(run.session.model.last_token + 1)
            record("choose")
            if plan is None:
                break
        if run.inbox is None:
            run.queue_receipt(physical_receipt(run))
            record("receive")
        run.consume_receipt()
        record("consume")
    if run.phase == "diagnostic" and run.session.diagnosis()["confirmed"]:
        if type(run.agent) is SelfReuseAgent:
            target = packet(physical_step(run.agent.env.initial, 0, True, True, 0))
            run.arm_reuse(target, token=run.agent.trial_token + 1, restored=True,
                          nominal_body_confirmed=True)
        else:
            run.start_recovery(restored=True, same_context=True)
        record("authorize")
    for index in range(horizon):
        if run.phase == "diagnostic" or run.agent.episode_terminal:
            break
        if run.agent.recovery is not None and run.agent.recovery.stopped:
            break
        if type(run.agent) is SelfReuseAgent and not run.agent.trial_active:
            break
        try:
            action = run.step(greedy=index % 4 == 3)
            record("turn", action)
        except RecoveryStop:
            record("stop")
            break
    a = run.agent
    result = {"initial_sha256": initial, "events": rows, "final_sha256": run.state_hash(),
            "terminal": a.episode_terminal, "stopped": "" if a.recovery is None else a.recovery.stopped,
            "diagnostic_clock": run.diagnostic_clock(), "next_turn": run.next_turn,
            "life_turns": a.life_turns, "balanced": a.env.balanced,
            "cortex_calls": a.metrics.cortex_calls, "false_facts": a.metrics.false_facts,
            "destroyed": a.cam.destroyed}
    # Match the subprocess/public JSON contract (e.g. possible-label tuples).
    return json.loads(c.base.canonical(result))


def resumed(path, digest, horizon=8):
    result = subprocess.run([sys.executable, "-m", "echoai.echo4.continuity_active_bench",
                             "resume", str(Path(path).resolve()), digest, str(horizon)],
                            cwd=c.ROOT.parent, capture_output=True, text=True, timeout=120, check=True)
    return json.loads(result.stdout)


def sources():
    extras = ("echo4/continuity_active_bench.py", "echo4/self_probe_world.py",
              "echo4/boundary_world.py", "echo4/self_recovery_audit.py", "echo4/self_reuse_audit.py",
              "tests/test_echo4_continuity1b.py", "docs/ECHO4-CONTINUITY1-B-DESIGN.md")
    return {**c.source_hashes(), **{p: hashlib.sha256((c.ROOT / p).read_bytes()).hexdigest() for p in extras}}


def row(case, path, run, raw):
    digest = hashlib.sha256(raw).hexdigest()
    reference = trajectory(run)
    restored = resumed(path, digest)
    return {"case": case, "checkpoint_sha256": digest, "checkpoint_bytes": len(raw),
            "reference": reference, "restored": restored, "equal": reference == restored}


def campaign(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    locked, rows = sources(), []
    for case in CASES:
        run = prepared(case)
        path = directory / (case + ".json")
        raw = run.dumps()
        run.save(path)
        rows.append(row(case, path, run, raw))
    passed = locked == sources() and all(r["equal"] and r["restored"]["balanced"] and
             not any(r["restored"][k] for k in ("cortex_calls", "false_facts", "destroyed")) for r in rows)
    report = {"schema": "continuity-b-development-v1", "sources": locked, "cases": rows,
              "development_passed": passed, "continuity1_green": False,
              "limits": ["trusted executor and complete synchronous operations", "one diagnostic session and life/trial",
                         "no mid-probe/turn capture, body transfer or lineage", "no LLM/DREAM", "not general safety"]}
    with (directory / "report.json").open("xb") as handle:
        handle.write(c.base.canonical(report))
    return report


def verify(directory):
    directory = Path(directory)
    report = json.loads((directory / "report.json").read_bytes())
    findings = []
    if (report.get("schema") != "continuity-b-development-v1" or report.get("sources") != sources()
            or report.get("development_passed") is not True or report.get("continuity1_green") is not False):
        findings.append("envelope/source/status mismatch")
    rows = report.get("cases", [])
    if len(rows) != len(CASES):
        findings.append("case count mismatch")
    for case, actual in zip(CASES, rows):
        original = prepared(case)
        raw = original.dumps()
        path = directory / (case + ".json")
        if path.read_bytes() != raw:
            findings.append(case + ": checkpoint differs from reconstruction")
            continue
        expected = row(case, path, original, raw)
        if actual != expected or expected["equal"] is not True:
            findings.append(case + ": continuation differs")
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
        report = campaign(args.directory)
        result = {"development_passed": report["development_passed"], "cases": len(report["cases"]),
                  "continuity1_green": False}
    print(json.dumps(result, sort_keys=True))
    if result.get("valid") is False or result.get("development_passed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
