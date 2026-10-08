"""python -m echoai.echo4 {audit,demo,sensation-audit}; JSON stdout only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("audit", help="Exhaustive world and observation audit")
    commands.add_parser("sensation-audit", help="Exhaustive 0/2/4-step sensory audit")
    campaign = commands.add_parser("sensation-campaign", help="Train then run frozen B/C sensory prediction")
    campaign.add_argument("--development", action="store_true", help="Separate small development corpus, never a certificate")
    campaign.add_argument("--output-dir", type=Path, help="New evidence directory; refuses overwrite")
    verify = commands.add_parser("sensation-verify", help="Recompute campaign and verify evidence, read-only")
    verify.add_argument("directory", type=Path)
    demo = commands.add_parser("demo", help="Single life, existing agent, learning on")
    demo.add_argument("--turns", type=int, default=256)
    demo.add_argument("--greedy", action="store_true",
                      help="No exploration; this does NOT freeze learning")
    demo.add_argument("--trace", action="store_true", help="Include per-turn trace")
    args = parser.parse_args(argv)
    if args.command == "audit":
        from echoai.echo4.audit import world_audit
        report = world_audit()
    elif args.command == "sensation-audit":
        from echoai.echo4.sensation_audit import temporal_audit
        report = temporal_audit()
    elif args.command == "sensation-campaign":
        from echoai.echo4.sensation_campaign import campaign
        report = campaign(development=args.development, output_dir=args.output_dir)
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0 if args.development or report["sensation_predictive_green"] else 1
    elif args.command == "sensation-verify":
        from echoai.echo4.sensation_campaign import audit_evidence
        try:
            report = audit_evidence(args.directory)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            report = {"valid": False, "findings": [str(exc)], "sensation_predictive_green": False}
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0 if report["valid"] else 1
    else:
        from echoai.echo4.demo import run_demo
        try:
            report = run_demo(args.turns, greedy=args.greedy, include_trace=args.trace)
        except ValueError as exc:
            parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    # Success means the diagnostic ran, not that the agent passed an exam.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
