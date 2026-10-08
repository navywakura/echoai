"""``python3 -m echoai.nexus0.flight1s.v2`` — the v2 CLI.

A separate entry point on purpose. Adding ``--protocol`` to the v1 CLI
would change ``nexus0/flight1s/__main__.py``, which is inside the v1
runtime lock's code inventory, and the v1 report would stop
reconstructing — exactly the failure the v2 brief forbids. So v1's
commands keep their meaning byte for byte, and every v2 command names
its protocol explicitly, defaulting to the frozen v2 instance.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

from echoai.nexus0.sim3.canon import Sim3Error, sha256_bytes
from echoai.nexus0.sim3.generate import generate_suite, rehearsal_assignment
from echoai.nexus0.sim3.pkg import load_protocol as load_world_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from echoai.nexus0.flight1s import worldbuild
from echoai.nexus0.flight1s.bench import FAMILY, WORLD_PROTOCOL
from echoai.nexus0.flight1s.v2 import audit as auditor
from echoai.nexus0.flight1s.v2 import bench as benchmod
from echoai.nexus0.flight1s.v2 import protocol as protomod
from echoai.nexus0.flight1s.v2 import runner as runnermod
from echoai.nexus0.flight1s.v2 import runtime as runtimemod


def _out(obj) -> None:
    json.dump(obj, sys.stdout, indent=2, sort_keys=True, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_validate(args) -> int:
    try:
        proto = protomod.load(Path(args.protocol) if args.protocol else None)
    except Sim3Error as exc:
        _out({"valid": False, "cause": exc.as_dict()})
        return 1
    world_proto = load_world_protocol(WORLD_PROTOCOL)
    family_sha = sha256_bytes(FAMILY.read_bytes())
    margin = protomod.exit_margin_mm()
    result = {
        "valid": True,
        "protocol_version": 2,
        "protocol_sha256": proto.sha256,
        "supersedes": proto["supersedes"],
        "v1_undisturbed": runtimemod.check_v1_undisturbed(),
        "force_mn": proto["disturbance"]["force_mn"],
        "stimulus": proto["stimulus"],
        "challenge": proto["challenge"],
        "recovery": proto["recovery"],
        "challenge_threshold_mm": proto["challenge"]["recovery_radius_mm"]
                                  + proto["challenge"]["exit_margin_mm"],
        "margin_recomputed": margin,
        "margin_matches": proto["challenge"]["exit_margin_mm"]
                          == margin["exit_margin_mm"],
        "world_protocol_matches": world_proto.sha256
                                  == proto["worlds"]["protocol_sha256"],
        "family_matches": family_sha == proto["worlds"]["family_sha256"],
    }
    with tempfile.TemporaryDirectory() as tmp:
        packages = generate_suite(Path(tmp), world_proto, REHEARSAL_SECRET,
                                  rehearsal_assignment())
        envelopes = [worldbuild.check_envelope(g.package, g.package_id,
                                               proto["body"]).as_dict()
                     for g in packages]
    result["envelopes_ok"] = all(e["ok"] for e in envelopes)
    result["worst_wall_margin_mm"] = min(e["wall_margin_mm"] for e in envelopes)
    result["valid"] = bool(result["world_protocol_matches"]
                           and result["family_matches"]
                           and result["envelopes_ok"]
                           and result["margin_matches"]
                           and result["v1_undisturbed"]["ok"])
    _out(result)
    return 0 if result["valid"] else 1


def cmd_preflight(args) -> int:
    proto_sha = ""
    if args.protocol or protomod.DEFAULT_PATH.exists():
        try:
            proto_sha = protomod.load(
                Path(args.protocol) if args.protocol else None).sha256
        except Sim3Error:
            proto_sha = ""
    runtime = runtimemod.preflight(
        lock_path=Path(args.output) if args.output else None, write=True,
        protocol_sha256=proto_sha)
    _out(runtime.lock)
    return 0 if runtime.available else 2


def cmd_bench(args) -> int:
    if not args.rehearsal:
        print("FLIGHT-1S v2 runs rehearsal data only; pass --rehearsal.",
              file=sys.stderr)
        return 2
    report = benchmod.run(
        report_path=Path(args.output) if args.output else None,
        protocol_path=Path(args.protocol) if args.protocol else None,
        lock_path=Path(args.lock) if args.lock else None,
        verbose=not args.quiet)
    _out({"flight1s_green": report["flight1s_green"],
          "protocol_version": 2,
          "group_status": report["group_status"],
          "report": str(args.output or benchmod.DEFAULT_REPORT),
          "report_sha256": report["report_sha256"],
          "wall_clock_s": report["wall_clock_s"]})
    return 0 if report["flight1s_green"] else 1


def cmd_audit(args) -> int:
    result = auditor.run(Path(args.report), do_self_test=not args.no_self_test)
    _out(result)
    return 0 if result["evidence_valid"] and result["flight1s_green_as_reported"] \
        else 1


def cmd_run(args) -> int:
    result = runnermod.run(
        lock_path=Path(args.lock) if args.lock else runtimemod.DEFAULT_LOCK,
        report_path=Path(args.output) if args.output else benchmod.DEFAULT_REPORT,
        protocol_path=Path(args.protocol) if args.protocol else None,
        accept_lock_change=args.accept_lock_change, verbose=not args.quiet)
    _out(result)
    return 0 if result.get("status") == "pass" else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="echoai.nexus0.flight1s.v2",
                                     description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate", help="check the v2 protocol and the worlds")
    p.add_argument("--protocol", default=None)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("preflight", help="freeze the v2 runtime lock")
    p.add_argument("--protocol", default=None)
    p.add_argument("--output", default=str(runtimemod.DEFAULT_LOCK))
    p.set_defaults(func=cmd_preflight)

    p = sub.add_parser("bench", help="run the 48-episode v2 bench")
    p.add_argument("--rehearsal", action="store_true")
    p.add_argument("--protocol", default=None)
    p.add_argument("--output", default=str(benchmod.DEFAULT_REPORT))
    p.add_argument("--lock", default=None)
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("audit", help="reconstruct the evidence in a v2 report")
    p.add_argument("report")
    p.add_argument("--no-self-test", action="store_true")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("run", help="one host: image, preflight, bench, audit")
    p.add_argument("--protocol", default=None)
    p.add_argument("--lock", default=None)
    p.add_argument("--output", default=None)
    p.add_argument("--accept-lock-change", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Sim3Error as exc:
        _out({"error": exc.as_dict()})
        return 3


if __name__ == "__main__":
    sys.exit(main())
