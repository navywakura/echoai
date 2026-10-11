"""ECHO-5 mission commands. Importing this script performs no work."""

from pathlib import Path
import sys


def main():
    import argparse
    import json
    import platform
    root = Path(__file__).resolve().parents[1]
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise RuntimeError("use ECHO-5 .venv/bin/python -I -B scripts/run_sitl.py")
    if platform.python_version() != (root/".python-version").read_text().strip():
        raise RuntimeError("use the pinned ECHO-5 interpreter")
    if Path(sys.prefix).resolve() != (root/".venv").resolve():
        raise RuntimeError("use ECHO-5's own .venv")
    sys.path.insert(0, str(root/"src"))
    parser = argparse.ArgumentParser(description="Local isolated simulation only; no physical transport")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("availability", help="read-only local image/source checks, no container launch")
    run = commands.add_parser("run", help="start a NEW real Gazebo/PX4 campaign")
    run.add_argument("--out", required=True)
    run.add_argument("--phase", choices=("development", "confirmation"), default="development")
    run.add_argument("--seed", type=int)
    run.add_argument("--cases", type=int, default=6)
    run.add_argument("--episode-timeout-s", type=int, default=900)
    run.add_argument("--campaign-timeout-s", type=int, default=18000)
    audit = commands.add_parser("audit", help="independent receipt audit, no flight replay")
    audit.add_argument("output")
    software = commands.add_parser("software", help="software MissionAgent benchmark; no SITL claim")
    software.add_argument("--out", required=True)
    software.add_argument("--seed", type=int, default=51601)
    software.add_argument("--cases", type=int, default=12)
    commands.add_parser("agent-worker", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.command == "agent-worker":
        from echo5.budget import Budget
        from echo5.mission import MissionBridge
        line = sys.stdin.readline(2_000_001)
        if not line.endswith("\n") or len(line) > 2_000_000:
            raise ValueError("bounded agent init required")
        init = json.loads(line)
        if set(init) != {"goal", "budget", "mode"}:
            raise ValueError("private agent init field")
        actor = MissionBridge(init["goal"], budget=Budget(init["budget"]), mode=init["mode"])
        print(json.dumps(dict(ready=True, goal_id=actor.goal["goal_id"])), flush=True)
        while True:
            line = sys.stdin.readline(2_000_001)
            if not line:
                return 0
            if not line.endswith("\n") or len(line) > 2_000_000:
                raise ValueError("bounded observation required")
            request = json.loads(line)
            if set(request) != {"raw", "sequence", "now_ns", "outcome"}:
                raise ValueError("private worker field")
            if request["outcome"] is not None:
                actor.observe_consequence(request["outcome"])
            elif request["sequence"] != 0:
                raise ValueError("missing_public_execution_outcome")
            result = actor.decide(request["raw"], sequence=request["sequence"], now_ns=request["now_ns"])
            print(json.dumps(result, sort_keys=True, allow_nan=False), flush=True)
    if args.command == "availability":
        from echo5.sitl import availability
        report = availability()
        print(json.dumps(report, indent=2))
        return int(bool(report["blockers"]))
    if args.command == "audit":
        from echo5.sitl import audit_sitl_campaign
        report = audit_sitl_campaign(args.output)
        print(json.dumps(dict(gates=report["gates"], findings=report["findings"]), indent=2))
        return 0 if report["valid"] else 1
    from echo5.trace import Recorder
    if args.command == "software":
        from echo5.mission import run_benchmark
        output = Path(args.out).resolve()
        if not output.is_relative_to((root/"artifacts").resolve()):
            raise ValueError("software outputs must be inside ECHO-5/artifacts")
        output.mkdir(parents=True, exist_ok=False)
        with Recorder(output/"thought.jsonl") as journal:
            report = run_benchmark(dict(seed=args.seed, cases=args.cases), journal=journal)
        with (output/"report.json").open("x") as stream:
            json.dump(report, stream, sort_keys=True, indent=2, allow_nan=False)
        print(json.dumps(report["gates"], indent=2))
        return 0 if report["gates"]["software_correctness"] else 1
    from echo5.sitl import run_sitl_campaign, CONTRACT
    # The campaign owns output creation. A sibling trace avoids pre-creating it.
    output = Path(args.out).resolve()
    if not output.is_relative_to((root/"artifacts").resolve()) or output.exists():
        raise ValueError("use a new ECHO-5/artifacts output directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    trace = output.with_name(output.name+".thought.jsonl")
    if trace.exists():
        raise FileExistsError(trace)
    seed = args.seed if args.seed is not None else json.loads(CONTRACT.read_text())['sitl'][args.phase + '_seed']
    with Recorder(trace) as journal:
        report = run_sitl_campaign(dict(output=str(output), phase=args.phase, seed=seed, cases=args.cases,
                                       episode_timeout_s=args.episode_timeout_s,
                                       campaign_timeout_s=args.campaign_timeout_s), journal=journal)
    print(json.dumps(dict(status=report["status"], gates=report["gates"],
                          next_command=f".venv/bin/python -I -B scripts/run_sitl.py audit {output}"), indent=2))
    # A successful measurement still needs the separate auditor for sitl_valid.
    return 0 if report["gates"]["measurements_pass"] else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print(type(exc).__name__+": "+str(exc), file=sys.stderr)
        sys.exit(1)
