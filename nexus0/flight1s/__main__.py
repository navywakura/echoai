"""``python3 -m echoai.nexus0.flight1s`` — validate, preflight, bench, audit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from echoai.nexus0.sim3.canon import Sim3Error, sha256_bytes
from echoai.nexus0.sim3.generate import generate_suite, rehearsal_assignment
from echoai.nexus0.sim3.pkg import load_protocol as load_world_protocol
from echoai.nexus0.sim3.seal import REHEARSAL_SECRET
from echoai.nexus0.flight1s import audit as auditor
from echoai.nexus0.flight1s import bench as benchmod
from echoai.nexus0.flight1s import protocol as protomod
from echoai.nexus0.flight1s import runner as runnermod
from echoai.nexus0.flight1s import runtime as runtimemod
from echoai.nexus0.flight1s import worldbuild


def _out(obj) -> None:
    json.dump(obj, sys.stdout, indent=2, sort_keys=True, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_validate(args) -> int:
    import tempfile

    try:
        proto = protomod.load(Path(args.protocol) if args.protocol else None)
    except Sim3Error as exc:
        _out({"valid": False, "cause": exc.as_dict()})
        return 1
    world_proto = load_world_protocol(benchmod.WORLD_PROTOCOL)
    family_sha = sha256_bytes(benchmod.FAMILY.read_bytes())
    result = {
        "valid": True,
        "protocol_sha256": proto.sha256,
        "force_mn": proto["disturbance"]["force_mn"],
        "bands": proto["bands"],
        "world_protocol_sha256": world_proto.sha256,
        "world_protocol_matches": world_proto.sha256
                                  == proto["worlds"]["protocol_sha256"],
        "family_sha256": family_sha,
        "family_matches": family_sha == proto["worlds"]["family_sha256"],
        "systems": [c for _, c in worldbuild.WORLD_SYSTEMS
                    + worldbuild.FLIGHT_SYSTEMS],
    }
    with tempfile.TemporaryDirectory() as tmp:
        packages = generate_suite(Path(tmp), world_proto, REHEARSAL_SECRET,
                                  rehearsal_assignment())
        envelopes = [worldbuild.check_envelope(g.package, g.package_id,
                                               proto["body"]).as_dict()
                     for g in packages]
    result["envelopes"] = envelopes
    result["envelopes_ok"] = all(e["ok"] for e in envelopes)
    result["valid"] = bool(result["world_protocol_matches"]
                           and result["family_matches"]
                           and result["envelopes_ok"])
    _out(result)
    return 0 if result["valid"] else 1


def cmd_preflight(args) -> int:
    runtime = runtimemod.preflight(
        lock_path=Path(args.output) if args.output else None, write=True)
    _out(runtime.lock)
    return 0 if runtime.available else 2


def cmd_bench(args) -> int:
    if not args.rehearsal:
        print("FLIGHT-1S runs rehearsal data only; pass --rehearsal.",
              file=sys.stderr)
        return 2
    report = benchmod.run(
        report_path=Path(args.output) if args.output else None,
        protocol_path=Path(args.protocol) if args.protocol else None,
        lock_path=Path(args.lock) if args.lock else None,
        verbose=not args.quiet)
    _out({"flight1s_green": report["flight1s_green"],
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
    parser = argparse.ArgumentParser(prog="echoai.nexus0.flight1s",
                                     description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate", help="check the protocol, worlds and envelope")
    p.add_argument("--protocol", default=None)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("preflight", help="discover and freeze the runtime lock")
    p.add_argument("--output", default=str(runtimemod.DEFAULT_LOCK))
    p.set_defaults(func=cmd_preflight)

    p = sub.add_parser("bench", help="run the 48-episode preregistered bench")
    p.add_argument("--rehearsal", action="store_true")
    p.add_argument("--output", default=str(benchmod.DEFAULT_REPORT))
    p.add_argument("--protocol", default=None)
    p.add_argument("--lock", default=None)
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("audit", help="reconstruct the evidence in a report")
    p.add_argument("report")
    p.add_argument("--no-self-test", action="store_true")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("run", help="one host: image, preflight, bench, audit")
    p.add_argument("--lock", default=None)
    p.add_argument("--output", default=None)
    p.add_argument("--protocol", default=None)
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
