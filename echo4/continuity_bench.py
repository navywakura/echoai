"""CONT-A development evidence, with fresh-process resume; not full closure."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from echoai.echo4.boundary_world import Experiment, run_pair
from echoai.echo4.continuity import ROOT, ContinuityRun, canonical, load, source_hashes
from echoai.echo4.self_agent import SelfAgent
from echoai.echo4.world import Body

CASES = (
    ("initial", 60, 46, 2, 0, 12),
    ("learned", 60, 46, 2, 5, 16),
    ("history0", 32, 64, 0, 1, 12),
    ("history4", 63, 71, 4, 9, 12),
    ("terminal", 32, 64, 2, 128, 8),
)


def prepared(h, temperature, depth, cut):
    """Real matched calibration receipts, then native learning, no Q editing."""
    body = Body(h, temperature)
    agent = SelfAgent(initial=body, depth=depth)
    for action in (0, 1):
        for i in range(1, 9):
            pair = run_pair(Experiment(body, action), action * 8 + i)[0]
            agent.calibrate_self_reference(pair)
    agent.seal_self_reference()
    run = ContinuityRun(agent)
    for _ in range(cut):
        if agent.episode_terminal:
            break
        run.step()
    return run


def trajectory(run, horizon):
    if type(horizon) is not int or not 0 <= horizon <= 128:
        raise ValueError("invalid resume horizon")
    initial_hash = run.state_hash()
    rows = []
    for index in range(horizon):
        if run.agent.episode_terminal:
            break
        # Same explicit external schedule in reference and restored process.
        greedy = index % 4 == 3
        action = run.step(greedy=greedy)
        agent = run.agent
        rows.append({"turn": run.next_turn, "greedy": greedy, "action": action,
                     "reward": agent.last_reward, "gate": agent.last_gate_decision,
                     "wsp": agent.observation(agent.env.cell()).hex(),
                     "body": asdict(agent.env.body), "resource_in": agent.env.resource_in,
                     "resource_used": agent.env.resource_used,
                     "resource_spill": agent.env.resource_spill,
                     "state_sha256": run.state_hash()})
    agent = run.agent
    return {"initial_sha256": initial_hash, "steps": rows,
            "final_sha256": run.state_hash(), "terminal": agent.episode_terminal,
            "cortex_calls": agent.metrics.cortex_calls,
            "false_facts": agent.metrics.false_facts, "destroyed": agent.cam.destroyed,
            "balanced": agent.env.balanced}


def resumed(path, digest, horizon):
    result = subprocess.run(
        [sys.executable, "-m", "echoai.echo4.continuity_bench", "resume",
         str(Path(path).resolve()), digest, str(horizon)],
        cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True,
        timeout=120, check=True,
    )
    return json.loads(result.stdout)


def bench_sources():
    extra = ("echo4/continuity_bench.py", "echo4/boundary_world.py",
             "tests/test_echo4_continuity1.py", "docs/ECHO4-CONTINUITY1-DESIGN.md")
    return {**source_hashes(), **{name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                 for name in extra}}


def campaign(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    locked = bench_sources()
    rows = []
    for name, h, temperature, depth, cut, horizon in CASES:
        run = prepared(h, temperature, depth, cut)
        path = directory / (name + ".json")
        digest = run.save(path)
        saved_turn = run.next_turn
        reference = trajectory(run, horizon)
        restored = resumed(path, digest, horizon)
        rows.append({"case": name, "checkpoint_sha256": digest,
                     "checkpoint_bytes": path.stat().st_size, "saved_turn": saved_turn,
                     "reference": reference, "restored": restored,
                     "equal": reference == restored})
    passed = (locked == bench_sources() and all(row["equal"] for row in rows)
              and all(row["restored"]["balanced"] and
                      not any(row["restored"][key] for key in
                              ("cortex_calls", "false_facts", "destroyed")) for row in rows))
    report = {"schema": "continuity-a-development-v1", "sources": locked,
              "cases": rows, "development_passed": passed,
              "continuity1_green": False,
              "limits": ["SelfAgent/DockEnv nominal only", "no active recovery session",
                         "no body/individual transfer or lineage closure", "no DREAM/LLM calls"]}
    with (directory / "report.json").open("xb") as handle:
        handle.write(canonical(report))
    return report


def verify(directory):
    """Read-only reconstruction, not trust in the report's self-assessment."""
    directory = Path(directory)
    report = json.loads((directory / "report.json").read_bytes())
    findings = []
    if (report.get("schema") != "continuity-a-development-v1"
            or report.get("sources") != bench_sources()
            or report.get("continuity1_green") is not False
            or report.get("development_passed") is not True):
        findings.append("envelope/source/status mismatch")
    rows = report.get("cases", [])
    if len(rows) != len(CASES):
        findings.append("case count mismatch")
    for spec, row in zip(CASES, rows):
        name, h, temperature, depth, cut, horizon = spec
        original = prepared(h, temperature, depth, cut)
        raw = original.dumps()
        digest = hashlib.sha256(raw).hexdigest()
        path = directory / (name + ".json")
        if path.read_bytes() != raw:
            findings.append(name + ": checkpoint differs from original execution")
            continue
        saved_turn = original.next_turn
        reference = trajectory(original, horizon)
        restored = resumed(path, digest, horizon)
        expected = {"case": name, "checkpoint_sha256": digest,
                    "checkpoint_bytes": len(raw), "saved_turn": saved_turn,
                    "reference": reference, "restored": restored, "equal": reference == restored}
        if row != expected or reference != restored:
            findings.append(name + ": trajectory mismatch")
    return {"valid": not findings, "findings": findings, "continuity1_green": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("campaign", "verify"):
        commands.add_parser(command).add_argument("directory", type=Path)
    child = commands.add_parser("resume")
    child.add_argument("path", type=Path)
    child.add_argument("digest")
    child.add_argument("horizon", type=int)
    args = parser.parse_args()
    if args.command == "resume":
        result = trajectory(load(args.path, expected_sha256=args.digest), args.horizon)
    elif args.command == "verify":
        result = verify(args.directory)
    else:
        report = campaign(args.directory)
        result = {"development_passed": report["development_passed"],
                  "cases": len(report["cases"]), "continuity1_green": False}
    print(json.dumps(result, sort_keys=True))
    if result.get("valid") is False or result.get("development_passed") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
