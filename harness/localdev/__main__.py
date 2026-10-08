"""CLI: python3 -m harness.localdev --help."""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import shutil
import sys

from .common import ROOT, TOOLS, digest, save, snapshot
from .engine import demo, http_proposer, repair
from .inventory import inspect_tree
from .runner import validate


def core_checks() -> list[dict]:
    return [
        {"id": "syntax", "mode": "syntax", "timeout_s": 60},
        {"id": "nexus-core", "mode": "unittest", "coverage": True, "timeout_s": 90,
         "tests": ["tests.test_nexus0."+name for name in
                   ("TestWorld", "TestTConf", "TestCorridor", "TestGate", "TestBench")]},
        {"id": "grid-properties", "mode": "unittest", "coverage": True, "timeout_s": 60,
         "tests": ["harness.localdev.cpu_contracts"]},
        {"id": "rsi-protocol-mocked", "mode": "unittest", "coverage": False, "timeout_s": 90,
         "tests": ["tests.test_rsi1"],
         "mocks": ["LLM transport, private tiny replica 999, artifact destination; no scientific exam"]},
        {"id": "types-localdev", "mode": "command", "timeout_s": 120,
         "command": ["/tools/bin/python", "-m", "mypy", "--check-untyped-defs", "--ignore-missing-imports",
                     "--follow-imports=silent", "--cache-dir", "/tmp/mypy", "harness/localdev"]},
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Local ECHO development checks; no scientific gate or automatic merge.")
    parser.add_argument("command", choices=("doctor", "scan", "run", "loop", "demo"))
    parser.add_argument("--output", type=Path, help="new evidence directory (defaults to lab/localdev/timestamp)")
    parser.add_argument("--allow", action="append", default=[], help="exact mutable source path; repeat for more files")
    parser.add_argument("--test", action="append", default=[], help="fixed unittest module/class; repeat for more tests")
    parser.add_argument("--endpoint", help="explicit OpenAI-compatible chat/completions URL; no implicit API calls")
    parser.add_argument("--model", help="fixed model identifier for this loop")
    parser.add_argument("--key-file", type=Path, help="optional explicit key file, never copied to workers or receipts")
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--max-seconds", type=int, default=600)
    args = parser.parse_args()
    if args.command == "doctor":
        info = {"python": sys.version.split()[0], "bubblewrap": shutil.which("bwrap"),
                "managed_mypy": (TOOLS/"bin/mypy").is_file(),
                "gcc": shutil.which("gcc"), "clang": shutil.which("clang"),
                "source": str(ROOT), "requires_linux_user_namespaces": True, "scientific_gate": False}
        print(json.dumps(info, indent=2))
        return 0 if info["bubblewrap"] and info["managed_mypy"] else 1
    output = (args.output or ROOT/"lab/localdev"/dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")).resolve()
    if output.exists():
        parser.error("output exists; choose a new evidence directory")
    if args.command == "scan":
        result = inspect_tree(ROOT, output)
        print(json.dumps({"output": str(output), **result}, indent=2))
        return int(bool(result["errors"]))
    if args.command == "demo":
        result = demo(output)
    elif args.command == "loop":
        if not args.endpoint or not args.model or not args.allow or not args.test:
            parser.error("loop requires --allow, --test, --endpoint and --model")
        checks = [{"id": "syntax", "mode": "syntax"},
                  {"id": "behavior", "mode": "unittest", "tests": args.test, "coverage": True},
                  {"id": "types-candidate", "mode": "command", "timeout_s": 120,
                   "command": ["/tools/bin/python", "-m", "mypy", "--check-untyped-defs",
                               "--ignore-missing-imports", "--follow-imports=silent", "--cache-dir", "/tmp/mypy", *args.allow]}]
        result = repair(ROOT, output, args.allow, checks,
                        http_proposer(args.endpoint, args.model, args.key_file),
                        max_attempts=args.max_attempts, max_seconds=args.max_seconds,
                        provider=args.model)
    else:
        hashes = snapshot(ROOT, output/"work/echoai")
        save(output/"snapshot.json", hashes)
        checks = core_checks() if not args.test else [
            {"id": "syntax", "mode": "syntax"},
            {"id": "selected", "mode": "unittest", "tests": args.test, "coverage": True}]
        save(output/"contract.json", {"checks": checks, "scientific_gate": False})
        result = validate(output/"work/echoai", output/"checks", checks)
        changed = [p for p, sha in hashes.items() if not (ROOT/p).exists() or digest((ROOT/p).read_bytes()) != sha]
        result["changed_original"] = changed
        if changed:
            result["status"] = "CUSTODY_FAILED"
        save(output/"result.json", result)
    print(json.dumps({"output": str(output), "status": result["status"], "scientific_gate": False}, indent=2))
    return int(result["status"] != "PASSED")


if __name__ == "__main__":
    raise SystemExit(main())
