"""``python3 -m echoai.nexus0.sim3`` — validate, preflight, bench, audit.

Every command prints JSON to stdout and returns a non-zero exit code when
the thing it checked did not close. A missing dependency prints its cause
and the next command to run; it never prints a number it did not measure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from echoai.nexus0.sim3 import audit as auditor
from echoai.nexus0.sim3 import bench as benchmod
from echoai.nexus0.sim3 import ci as cimod
from echoai.nexus0.sim3 import declarations
from echoai.nexus0.sim3 import runner as runnermod
from echoai.nexus0.sim3 import runtime as runtimemod
from echoai.nexus0.sim3.canon import Sim3Error
from echoai.nexus0.sim3.pkg import load_package, load_protocol
from echoai.nexus0.sim3.runtime import ECHOAI

DEFAULT_PROTOCOL = ECHOAI / "docs" / "examples" / "sim3" / "protocol.json"


def _out(obj) -> None:
    json.dump(obj, sys.stdout, indent=2, sort_keys=True, ensure_ascii=False)
    sys.stdout.write("\n")


def cmd_validate(args) -> int:
    try:
        protocol = load_protocol(Path(args.protocol))
        package = load_package(Path(args.package), protocol)
    except Sim3Error as exc:
        _out({"valid": False, "cause": exc.as_dict()})
        return 1
    result = {
        "valid": True,
        "protocol_sha256": protocol.sha256,
        "package": package.public_view(),
        "roles": package.roles,
        "spawn_mm": list(package.spawn_mm),
        "rig_start_mm": list(package.rig_start_mm),
        "approach_mm": list(package.approach_mm),
        "connectivity_attach_nodes": list(package.connectivity_nodes),
    }
    if not args.no_libsdformat:
        runtime = runtimemod.load_lock(args.lock)
        if not runtime.lock:
            runtime = runtimemod.preflight(lock_path=args.lock, write=False)
        if runtime.available:
            source = (Path(args.package) / "world.sdf").read_bytes()
            result["libsdformat"] = runtimemod.check_sdf(runtime, source)
            if not result["libsdformat"]["valid"]:
                result["valid"] = False
        else:
            result["libsdformat"] = {"status": "not_run", "reason": runtime.reason}
    _out(result)
    return 0 if result["valid"] else 1


def cmd_preflight(args) -> int:
    runtime = runtimemod.preflight(lock_path=Path(args.output) if args.output
                                   else None, write=True)
    _out(runtime.lock)
    return 0 if runtime.available else 2


def cmd_bench(args) -> int:
    if not args.rehearsal:
        print("SIM-3 runs rehearsal data only; pass --rehearsal.", file=sys.stderr)
        return 2
    report = benchmod.run(report_path=Path(args.output) if args.output else None,
                          protocol_path=Path(args.protocol),
                          lock_path=Path(args.lock) if args.lock else None,
                          verbose=not args.quiet)
    summary = {
        "sim3_green": report["sim3_green"],
        "group_status": report["group_status"],
        "report": str(args.output or benchmod.DEFAULT_REPORT),
        "report_sha256": report["report_sha256"],
        "wall_clock_s": report["wall_clock_s"],
    }
    _out(summary)
    return 0 if report["sim3_green"] else 1


def cmd_audit(args) -> int:
    result = auditor.run(Path(args.report), do_self_test=not args.no_self_test)
    _out(result)
    return 0 if result["evidence_valid"] and result["sim3_green_as_reported"] else 1


def cmd_declaration(args) -> int:
    try:
        result = declarations.validate(args.kind, Path(args.path))
    except Sim3Error as exc:
        _out({"valid": False, "cause": exc.as_dict()})
        return 1
    _out({k: v for k, v in result.items() if k != "data"})
    return 0


def cmd_run(args) -> int:
    result = runnermod.run(lock_path=Path(args.lock), report_path=Path(args.output),
                           protocol_path=Path(args.protocol),
                           accept_lock_change=args.accept_lock_change,
                           verbose=not args.quiet)
    _out(result)
    return 0 if result.get("status") == "pass" else 1


def cmd_ci(args) -> int:
    return cimod.run(Path(args.output))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="echoai.nexus0.sim3",
                                     description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate", help="check one package against the profile")
    p.add_argument("--package", required=True)
    p.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    p.add_argument("--lock", default=None)
    p.add_argument("--no-libsdformat", action="store_true")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("preflight", help="discover and freeze the runtime lock")
    p.add_argument("--output", default=str(runtimemod.DEFAULT_LOCK))
    p.set_defaults(func=cmd_preflight)

    p = sub.add_parser("bench", help="run the preregistered rehearsal bench")
    p.add_argument("--rehearsal", action="store_true")
    p.add_argument("--output", default=str(benchmod.DEFAULT_REPORT))
    p.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    p.add_argument("--lock", default=None)
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("audit", help="reconstruct the evidence in a report")
    p.add_argument("report")
    p.add_argument("--no-self-test", action="store_true")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("declaration", help="validate a frozen campaign, family or slice")
    p.add_argument("kind", choices=sorted(declarations.KINDS))
    p.add_argument("path")
    p.set_defaults(func=cmd_declaration)

    p = sub.add_parser("run", help="one host: image/preflight, bench, audit")
    p.add_argument("--lock", default=str(runtimemod.DEFAULT_LOCK))
    p.add_argument("--output", default=str(benchmod.DEFAULT_REPORT))
    p.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    p.add_argument("--accept-lock-change", action="store_true")
    p.add_argument("--quiet", action="store_true")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("ci", help="unit CI; backend only when SIM3_CI_BACKEND=1")
    p.add_argument("--output", default=str(runtimemod.ECHOAI / "lab" / "echo3_sim3_ci.json"))
    p.set_defaults(func=cmd_ci)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Sim3Error as exc:
        _out({"error": exc.as_dict()})
        return 3


if __name__ == "__main__":
    sys.exit(main())
